from typing import Dict, Any
from langgraph.graph import END
from app.workflows.state import QCState
from app.workflows.builders.llm_node_builder import default_llm_builder


def check_image_relevance(state: QCState) -> Dict[str, Any]:
    """
    1. DÜĞÜM (Node 1): Görsel Alakalılık İncelemesi.
    Yüklenen görselin endüstriyel kalite kontrol ile ilgili olup olmadığını denetler.
    - LLM hatası durumunda: workflow_status='FAILED', error detayları ile kaydedilir.
    - Alakasız ise: workflow_status='REJECTED_IRRELEVANT' olarak akış sonlanır.
    - Alakalı ise: workflow_status='PROCESSING' olarak kusur değerlendirme düğümüne geçer.
    """
    image_url = state.get("image_url", "")
    res = default_llm_builder.evaluate_relevance(image_url)

    workflow_status = res.get("workflow_status", "PROCESSING")
    error = res.get("error")
    evaluation_source = res.get("evaluation_source", "llm")
    model_version = res.get("model_version")
    prompt_version = res.get("prompt_version")

    # LLM veya API hatası oluşmuşsa
    if workflow_status == "FAILED":
        return {
            "is_relevant": False,
            "relevance_message": res.get("reason") or error,
            "workflow_status": "FAILED",
            "error": error,
            "evaluation_source": evaluation_source,
            "model_version": model_version,
            "prompt_version": prompt_version,
            "is_product_defect": None,
            "confidence_score": None,
            "defect_description": None,
            "category": None,
        }

    is_relevant = res.get("is_relevant", False)
    reason = res.get("reason", "")

    if not is_relevant:
        return {
            "is_relevant": False,
            "relevance_message": reason,
            "workflow_status": "REJECTED_IRRELEVANT",
            "error": None,
            "evaluation_source": evaluation_source,
            "model_version": model_version,
            "prompt_version": prompt_version,
            "is_product_defect": None,
            "confidence_score": None,
            "defect_description": None,
            "category": None,
        }

    return {
        "is_relevant": True,
        "relevance_message": reason,
        "workflow_status": "PROCESSING",
        "error": None,
        "evaluation_source": evaluation_source,
        "model_version": model_version,
        "prompt_version": prompt_version,
    }


def should_continue(state: QCState) -> str:
    """
    KOŞULLU YÖNLENDİRİCİ (Conditional Edge Router):
    - Hata (FAILED) durumunda: Akışı derhal sonlandırarak END düğümüne gider.
    - Görsel alakalı ise (is_relevant == True): 2. düğüm olan 'evaluate_defect' düğümüne dallanır.
    - Görsel alakasız ise (is_relevant == False): Akışı derhal sonlandırarak END düğümüne gider.
    """
    if state.get("workflow_status") == "FAILED":
        return END

    if state.get("is_relevant") is True:
        return "evaluate_defect"

    return END
