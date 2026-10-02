from typing import Dict, Any
from app.workflows.state import QCState
from app.workflows.builders.llm_node_builder import default_llm_builder


def defect_evaluation_node(state: QCState) -> Dict[str, Any]:
    """
    2. DÜĞÜM (Node 2): LLM Kusur Değerlendirmesi.
    Alakalı görseller için parçada kusur olup olmadığını (is_product_defect),
    varsa kusur türünü ve açıklamasını (defect_description) ve güven skorunu (confidence_score) hesaplar.
    """
    image_url = state.get("image_url", "")
    product_id = state.get("product_id", "UNKNOWN")

    eval_res = default_llm_builder.evaluate_defect(
        image_url=image_url,
        product_id=product_id
    )

    return {
        "category": eval_res.get("category"),
        "is_product_defect": eval_res["is_product_defect"],
        "confidence_score": eval_res["confidence_score"],
        "defect_description": eval_res["defect_description"],
        "workflow_status": "COMPLETED",
    }
