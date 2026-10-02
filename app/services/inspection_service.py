from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.inspection_task import InspectionTask
from app.schemas.inspection_task import (
    InspectionTaskCreate,
    InspectionTaskReviewSubmit,
    InspectionTaskResponse,
    PaginatedTaskResponse,
)
from app.repositories.inspection_task_repository import inspection_task_repository
from app.workflows import run_qc_pipeline
from app.core.exceptions import EntityNotFoundError, BusinessLogicError
from app.utils.mappers import map_task_to_response, map_tasks_to_responses


class InspectionService:
    def __init__(self):
        self.repo = inspection_task_repository

    async def execute_and_create(
        self, db: AsyncSession, payload: InspectionTaskCreate
    ) -> InspectionTaskResponse:
        """
        1. LangGraph İş Akışını (Alakalılık Kontrolü -> Kategori & Kusur LLM Değerlendirmesi) çalıştırır.
        2. Alakasız ise akış otomatik kapanır ve kayıt 'REJECTED_IRRELEVANT' olarak açılır.
        3. Alakalı ise 'COMPLETED' ve 'PENDING_REVIEW' (kullanıcı onayı bekleniyor) olarak veritabanına kaydeder.
        """
        # LangGraph iş akışını tetikle
        img_input = payload.image_base64 or payload.image_url
        workflow_result = await run_qc_pipeline(
            product_id=payload.product_id,
            image_url=img_input
        )

        is_relevant = workflow_result.get("is_relevant", True)
        workflow_status = workflow_result.get("workflow_status", "COMPLETED")

        # Alakasız görsel ise otomatik inceleme reddedildi durumu
        initial_review_status = "PENDING_REVIEW" if is_relevant else "REJECTED"

        task_record = await self.repo.create(
            db,
            obj_in={
                "product_id": payload.product_id,
                "image_base64": img_input,
                "image_url": payload.image_url or img_input,
                "category": workflow_result.get("category"),
                "is_relevant": is_relevant,
                "relevance_message": workflow_result.get("relevance_message"),
                "workflow_status": workflow_status,
                "is_product_defect": workflow_result.get("is_product_defect"),
                "confidence_score": workflow_result.get("confidence_score"),
                "defect_description": workflow_result.get("defect_description"),
                "ai_timestamp": workflow_result.get("timestamp"),
                "review_status": initial_review_status,
            }
        )

        return map_task_to_response(task_record)

    async def get_by_id(self, db: AsyncSession, task_id: int) -> InspectionTaskResponse:
        task = await self.repo.get(db, task_id)
        if not task:
            raise EntityNotFoundError("Kalite Kontrol Görevi", task_id)
        return map_task_to_response(task)

    async def submit_review(
        self, db: AsyncSession, task_id: int, review: InspectionTaskReviewSubmit
    ) -> InspectionTaskResponse:
        """
        Kullanıcı onayı ile etiketleme (Human Annotation):
        Operatör AI tahminini onaylar (APPROVED), düzeltir (CORRECTED) veya reddeder (REJECTED).
        """
        task = await self.repo.get(db, task_id)
        if not task:
            raise EntityNotFoundError("Kalite Kontrol Görevi", task_id)

        update_payload = {
            "review_status": review.review_status.upper(),
            "user_is_defect": review.user_is_defect,
            "user_defect_description": review.user_defect_description,
            "user_category": review.user_category,
            "user_notes": review.user_notes,
            "reviewed_by": review.reviewed_by,
            "reviewed_at": datetime.now(timezone.utc),
        }

        updated = await self.repo.update(db, db_obj=task, obj_in=update_payload)
        return map_task_to_response(updated)

    async def list_tasks(
        self,
        db: AsyncSession,
        *,
        review_status: Optional[str] = None,
        is_relevant: Optional[bool] = None,
        is_product_defect: Optional[bool] = None,
        product_id: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> PaginatedTaskResponse:
        skip = (page - 1) * limit
        items = await self.repo.filter_tasks(
            db,
            review_status=review_status,
            is_relevant=is_relevant,
            is_product_defect=is_product_defect,
            product_id=product_id,
            category=category,
            skip=skip,
            limit=limit
        )
        total = await self.repo.count_filtered(
            db,
            review_status=review_status,
            is_relevant=is_relevant,
            is_product_defect=is_product_defect,
            product_id=product_id,
            category=category
        )

        return PaginatedTaskResponse(
            total=total,
            page=page,
            limit=limit,
            items=map_tasks_to_responses(items)
        )

    async def delete_task(self, db: AsyncSession, task_id: int) -> dict:
        task = await self.repo.get(db, task_id)
        if not task:
            raise EntityNotFoundError("Kalite Kontrol Görevi", task_id)
        await self.repo.remove(db, id=task_id)
        return {"success": True, "message": f"Görev #{task_id} başarıyla silindi."}


inspection_service = InspectionService()
