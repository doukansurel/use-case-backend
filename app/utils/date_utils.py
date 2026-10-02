from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """Geçerli saat dilimi duyarlı (timezone-aware) UTC zamanını döner."""
    return datetime.now(timezone.utc)


def format_iso_timestamp(dt: Optional[datetime] = None) -> str:
    """Verilen datetime nesnesini veya mevcut UTC anını ISO 8601 formatlı string olarak döner."""
    if dt is None:
        dt = utc_now()
    return dt.isoformat()
