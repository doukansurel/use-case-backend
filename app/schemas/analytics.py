from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.schemas.inspection_task import InspectionTaskResponse


class LabelingStatsResponse(BaseModel):
    """Etiketleme ve kalite kontrol paneli genel metrikleri."""
    total_tasks: int
    relevant_count: int
    irrelevant_count: int
    ai_defect_count: int
    ai_clean_count: int
    ai_defect_rate: float
    failed_count: Optional[int] = 0

    # İnsan onay / etiketleme metrikleri
    pending_review_count: int
    approved_count: int
    corrected_count: int
    rejected_count: int
    human_verified_defect_count: int
    human_verified_clean_count: int

    recent_tasks: List[InspectionTaskResponse]
