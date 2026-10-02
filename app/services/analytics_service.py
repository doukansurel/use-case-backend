from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.analytics import LabelingStatsResponse
from app.repositories.inspection_task_repository import inspection_task_repository
from app.utils.mappers import map_tasks_to_responses


class AnalyticsService:
    def __init__(self):
        self.repo = inspection_task_repository

    async def get_labeling_stats(self, db: AsyncSession) -> LabelingStatsResponse:
        stats = await self.repo.get_labeling_stats(db)
        recent_raw = await self.repo.get_recent(db, limit=6)
        recent_tasks = map_tasks_to_responses(recent_raw)

        return LabelingStatsResponse(
            total_tasks=stats["total_tasks"],
            relevant_count=stats["relevant_count"],
            irrelevant_count=stats["irrelevant_count"],
            ai_defect_count=stats["ai_defect_count"],
            ai_clean_count=stats["ai_clean_count"],
            ai_defect_rate=stats["ai_defect_rate"],
            pending_review_count=stats["pending_review_count"],
            approved_count=stats["approved_count"],
            corrected_count=stats["corrected_count"],
            rejected_count=stats["rejected_count"],
            human_verified_defect_count=stats["human_verified_defect_count"],
            human_verified_clean_count=stats["human_verified_clean_count"],
            recent_tasks=recent_tasks
        )


analytics_service = AnalyticsService()
