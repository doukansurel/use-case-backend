from typing import Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base exception for application errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: Optional[Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class EntityNotFoundError(AppException):
    """Raised when a requested resource/entity is not found."""
    def __init__(self, entity_name: str, entity_id: Any):
        super().__init__(
            message=f"{entity_name} ile belirtilen kimlik ({entity_id}) bulunamadı.",
            status_code=status.HTTP_404_NOT_FOUND
        )


class EntityAlreadyExistsError(AppException):
    """Raised when creating an entity that already exists (e.g. duplicate unique key)."""
    def __init__(self, entity_name: str, field_name: str, value: Any):
        super().__init__(
            message=f"{entity_name} '{field_name}' alanı '{value}' değeriyle zaten mevcut.",
            status_code=status.HTTP_409_CONFLICT
        )


class BusinessLogicError(AppException):
    """Raised when a business rule constraint is violated."""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Global handler for custom AppException."""
    payload = {
        "success": False,
        "error": {
            "type": exc.__class__.__name__,
            "message": exc.message,
            "status_code": exc.status_code,
        }
    }
    if exc.details is not None:
        payload["error"]["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=payload)
