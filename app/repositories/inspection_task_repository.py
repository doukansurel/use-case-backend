from typing import Optional, List, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.inspection_task import InspectionTask
from app.schemas.inspection_task import InspectionTaskCreate
from app.repositories.base import BaseRepository


class InspectionTaskRepository(BaseRepository[InspectionTask, InspectionTaskCreate, Any]):
    def __init__(self):
        super().__init__(InspectionTask)

    def _build_filter_query(
        self,
        review_status: Optional[str] = None,
        workflow_status: Optional[str] = None,
        is_relevant: Optional[bool] = None,
        is_product_defect: Optional[bool] = None,
        product_id: Optional[str] = None,
        category: Optional[str] = None,
    ):
        query = select(InspectionTask)
        if review_status:
            query = query.where(InspectionTask.review_status == review_status.upper())
        if workflow_status:
            query = query.where(InspectionTask.workflow_status == workflow_status.upper())
        if is_relevant is not None:
            query = query.where(InspectionTask.is_relevant == is_relevant)
        if is_product_defect is not None:
            query = query.where(InspectionTask.is_product_defect == is_product_defect)
        if product_id:
            query = query.where(InspectionTask.product_id.ilike(f"%{product_id}%"))
        if category:
            query = query.where(InspectionTask.category.ilike(f"%{category}%"))
        return query

    async def filter_tasks(
        self,
        db: AsyncSession,
        *,
        review_status: Optional[str] = None,
        workflow_status: Optional[str] = None,
        is_relevant: Optional[bool] = None,
        is_product_defect: Optional[bool] = None,
        product_id: Optional[str] = None,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[InspectionTask]:
        """Görevleri dinamik filtrelerle sayfalı olarak getirir."""
        query = self._build_filter_query(
            review_status=review_status,
            workflow_status=workflow_status,
            is_relevant=is_relevant,
            is_product_defect=is_product_defect,
            product_id=product_id,
            category=category
        )
        query = query.order_by(InspectionTask.id.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_filtered(
        self,
        db: AsyncSession,
        *,
        review_status: Optional[str] = None,
        workflow_status: Optional[str] = None,
        is_relevant: Optional[bool] = None,
        is_product_defect: Optional[bool] = None,
        product_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> int:
        """Filtreye uyan toplam kayıt sayısını döner."""
        base_query = self._build_filter_query(
            review_status=review_status,
            workflow_status=workflow_status,
            is_relevant=is_relevant,
            is_product_defect=is_product_defect,
            product_id=product_id,
            category=category
        )
        count_query = select(func.count()).select_from(base_query.subquery())
        res = await db.execute(count_query)
        return res.scalar() or 0

    async def get_recent(self, db: AsyncSession, limit: int = 10) -> List[InspectionTask]:
        """Son eklenen görevleri getirir."""
        result = await db.execute(
            select(InspectionTask).order_by(InspectionTask.id.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_labeling_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Etiketleme ve AI tahminlerine ilişkin özet KPI metriklerini hesaplar."""
        total = await db.scalar(select(func.count(InspectionTask.id))) or 0
        relevant = await db.scalar(
            select(func.count(InspectionTask.id)).where(InspectionTask.is_relevant.is_(True))
        ) or 0
        irrelevant = await db.scalar(
            select(func.count(InspectionTask.id)).where(InspectionTask.is_relevant.is_(False))
        ) or 0

        ai_defect = await db.scalar(
            select(func.count(InspectionTask.id)).where(InspectionTask.is_product_defect.is_(True))
        ) or 0
        ai_clean = await db.scalar(
            select(func.count(InspectionTask.id)).where(InspectionTask.is_product_defect.is_(False))
        ) or 0

        pending_review = await db.scalar(
            select(func.count(InspectionTask.id)).where(InspectionTask.review_status == "PENDING_REVIEW")
        ) or 0
        approved = await db.scalar(
            select(func.count(InspectionTask.id)).where(InspectionTask.review_status == "APPROVED")
        ) or 0
        corrected = await db.scalar(
            select(func.count(InspectionTask.id)).where(InspectionTask.review_status == "CORRECTED")
        ) or 0
        rejected = await db.scalar(
            select(func.count(InspectionTask.id)).where(InspectionTask.review_status == "REJECTED")
        ) or 0

        human_verified_defect = await db.scalar(
            select(func.count(InspectionTask.id)).where(InspectionTask.user_is_defect.is_(True))
        ) or 0
        human_verified_clean = await db.scalar(
            select(func.count(InspectionTask.id)).where(InspectionTask.user_is_defect.is_(False))
        ) or 0

        failed_count = await db.scalar(
            select(func.count(InspectionTask.id)).where(InspectionTask.workflow_status == "FAILED")
        ) or 0

        ai_defect_rate = round((ai_defect / relevant * 100), 2) if relevant > 0 else 0.0

        return {
            "total_tasks": total,
            "relevant_count": relevant,
            "irrelevant_count": irrelevant,
            "ai_defect_count": ai_defect,
            "ai_clean_count": ai_clean,
            "ai_defect_rate": ai_defect_rate,
            "failed_count": failed_count,
            "pending_review_count": pending_review,
            "approved_count": approved,
            "corrected_count": corrected,
            "rejected_count": rejected,
            "human_verified_defect_count": human_verified_defect,
            "human_verified_clean_count": human_verified_clean,
        }


inspection_task_repository = InspectionTaskRepository()
