from typing import Dict, Any
from langgraph.graph import END
from app.workflows.state import QCState
from app.workflows.builders.llm_node_builder import default_llm_builder


def check_image_relevance(state: QCState) -> Dict[str, Any]:
    """
    1. DÜĞÜM (Node 1): Görsel Alakalılık İncelemesi.
    Yüklenen görselin endüstriyel kalite kontrol ile ilgili olup olmadığını denetler.
    Alakasız ise akış kapatılacak şekilde durumu günceller.
    """
    image_url = state.get("image_url", "")
    res = default_llm_builder.evaluate_relevance(image_url)

    is_relevant = res["is_relevant"]
    reason = res["reason"]

    if not is_relevant:
        return {
            "is_relevant": False,
            "relevance_message": reason,
            "workflow_status": "REJECTED_IRRELEVANT",
            "is_product_defect": None,
            "confidence_score": None,
            "defect_description": None,
        }

    return {
        "is_relevant": True,
        "relevance_message": reason,
        "workflow_status": "PROCESSING",
    }


def should_continue(state: QCState) -> str:
    """
    KOŞULLU YÖNLENDİRİCİ (Conditional Edge Router):
    - Görsel alakalı ise (is_relevant == True): 2. düğüm olan 'evaluate_defect' düğümüne dallanır.
    - Görsel alakasız ise (is_relevant == False): Akışı derhal sonlandırarak END düğümüne gider.
    """
    if state.get("is_relevant") is True:
        return "evaluate_defect"
    return END
