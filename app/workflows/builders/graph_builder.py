from langgraph.graph import StateGraph, END
from app.workflows.state import QCState
from app.workflows.nodes import (
    check_image_relevance,
    should_continue,
    defect_evaluation_node,
)


class WorkflowGraphBuilder:
    """
    LangGraph İş Akışı Oluşturucu (Graph Builder Pattern):
    StateGraph'ı düğümler (nodes), koşullu kenarlar (conditional edges)
    ve başlangıç noktası ile bir araya getirerek derler (compile).
    """
    def __init__(self):
        self.workflow = StateGraph(QCState)

    def build(self):
        """İş akışını kurar ve derlenmiş grafı (CompiledGraph) döner."""
        # 1. Düğümleri Ekle
        self.workflow.add_node("check_relevance", check_image_relevance)
        self.workflow.add_node("evaluate_defect", defect_evaluation_node)

        # 2. Başlangıç Noktası (Entry Point)
        self.workflow.set_entry_point("check_relevance")

        # 3. Koşullu Geçiş: Alakasız ise akışı kapat, alakalı ise LLM düğümüne geç
        self.workflow.add_conditional_edges(
            "check_relevance",
            should_continue,
            {
                "evaluate_defect": "evaluate_defect",
                END: END
            }
        )

        # 4. LLM Değerlendirmesi sonrası bitişe git
        self.workflow.add_edge("evaluate_defect", END)

        return self.workflow.compile()


def build_qc_workflow():
    """Grafiği kurup derleyen yardımcı fabrika fonksiyonu."""
    builder = WorkflowGraphBuilder()
    return builder.build()
