from typing import Dict, Any
from app.workflows.state import QCState
from app.workflows.builders.graph_builder import build_qc_workflow
from app.utils.date_utils import format_iso_timestamp

# Derlenmiş tekil iş akışı örneği
qc_graph = build_qc_workflow()


async def run_qc_pipeline(product_id: str, image_url: str) -> Dict[str, Any]:
    """
    LangGraph iş akışını asenkron olarak çalıştırır ve
    standart çıktı JSON formatını üretir:
    {
      "product_id": ...,
      "timestamp": ...,
      "is_product_defect": ...,
      "confidence_score": ...,
      "defect_description": ...
    }
    """
    iso_timestamp = format_iso_timestamp()

    initial_state: QCState = {
        "product_id": product_id,
        "image_url": image_url,
        "timestamp": iso_timestamp,
        "is_relevant": None,
        "workflow_status": "PENDING"
    }

    # LangGraph ainvoke
    final_state: QCState = await qc_graph.ainvoke(initial_state)

    return {
        "product_id": final_state.get("product_id"),
        "timestamp": final_state.get("timestamp", iso_timestamp),
        "is_relevant": final_state.get("is_relevant"),
        "relevance_message": final_state.get("relevance_message"),
        "workflow_status": final_state.get("workflow_status"),
        "is_product_defect": final_state.get("is_product_defect"),
        "confidence_score": final_state.get("confidence_score"),
        "defect_description": final_state.get("defect_description"),
        "category": final_state.get("category"),
        "raw_json_output": {
            "product_id": final_state.get("product_id"),
            "timestamp": final_state.get("timestamp", iso_timestamp),
            "category": final_state.get("category"),
            "is_product_defect": final_state.get("is_product_defect"),
            "confidence_score": final_state.get("confidence_score"),
            "defect_description": final_state.get("defect_description"),
        }
    }
