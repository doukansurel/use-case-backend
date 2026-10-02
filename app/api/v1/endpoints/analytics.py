from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.analytics import LabelingStatsResponse
from app.services.analytics_service import analytics_service

router = APIRouter()


@router.get("/dashboard", response_model=LabelingStatsResponse, summary="Etiketleme & Kalite Kontrol Özeti")
async def get_labeling_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Etiketleme ilerleme durumu, insan onayı oranları, kusurlu ürün yüzdeleri ve son görevler.
    """
    return await analytics_service.get_labeling_stats(db)
