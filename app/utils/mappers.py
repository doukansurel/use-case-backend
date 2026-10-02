from __future__ import annotations
from typing import TYPE_CHECKING, List, Iterable, Any
from app.schemas.inspection_task import InspectionTaskResponse, LLMEvaluationOutput
from app.utils.date_utils import format_iso_timestamp

if TYPE_CHECKING:
    from app.models.inspection_task import InspectionTask


def map_task_to_response(task: InspectionTask | Any) -> InspectionTaskResponse:
    """
    InspectionTask veritabanı modelini API yanıt şemasına (InspectionTaskResponse) dönüştürür.
    Modeldeki alanları standartlaştırılmış LLMEvaluationOutput yapısıyla birleştirir.
    """
    timestamp_str = (
        getattr(task, "ai_timestamp", None)
        or (task.created_at.isoformat() if getattr(task, "created_at", None) else format_iso_timestamp())
    )

    ai_eval = LLMEvaluationOutput(
        product_id=task.product_id,
        timestamp=timestamp_str,
        category=getattr(task, "category", None),
        is_product_defect=getattr(task, "is_product_defect", None),
        confidence_score=getattr(task, "confidence_score", None),
        defect_description=getattr(task, "defect_description", None),
        evaluation_source=getattr(task, "evaluation_source", "llm"),
        model_version=getattr(task, "model_version", None),
        prompt_version=getattr(task, "prompt_version", None),
    )

    b64_val = getattr(task, "image_base64", None) or getattr(task, "image_url", "")

    return InspectionTaskResponse(
        id=task.id,
        product_id=task.product_id,
        image_base64=b64_val,
        image_url=task.image_url,
        category=getattr(task, "category", None),
        is_relevant=task.is_relevant,
        relevance_message=getattr(task, "relevance_message", None),
        workflow_status=task.workflow_status,
        error=getattr(task, "error", None),
        evaluation_source=getattr(task, "evaluation_source", "llm"),
        model_version=getattr(task, "model_version", None),
        prompt_version=getattr(task, "prompt_version", None),
        ai_evaluation=ai_eval,
        review_status=task.review_status,
        user_is_defect=getattr(task, "user_is_defect", None),
        user_defect_description=getattr(task, "user_defect_description", None),
        user_category=getattr(task, "user_category", None),
        user_notes=getattr(task, "user_notes", None),
        reviewed_by=getattr(task, "reviewed_by", None),
        reviewed_at=getattr(task, "reviewed_at", None),
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def map_tasks_to_responses(tasks: Iterable[InspectionTask | Any]) -> List[InspectionTaskResponse]:
    """Birden fazla InspectionTask model listesini API yanıt listesine dönüştürür."""
    return [map_task_to_response(task) for task in tasks]
