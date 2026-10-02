from typing import Optional, TypedDict


class QCState(TypedDict, total=False):
    """
    LangGraph Kalite Kontrol ve Etiketleme İş Akışı Durum Modeli (State).
    Akıştaki tüm düğümler (Nodes) bu paylaşılan durumu günceller.
    """
    product_id: str
    image_url: str
    timestamp: str
    
    # 1. Düğüm: Görsel Alakalılık Çıktıları
    is_relevant: Optional[bool]
    relevance_message: Optional[str]
    
    # 2. Düğüm: LLM Kusur Değerlendirme Çıktıları
    is_product_defect: Optional[bool]
    confidence_score: Optional[float]
    defect_description: Optional[str]
    category: Optional[str]
    
    # Genel İş Akışı Durumu
    workflow_status: str  # PENDING, PROCESSING, REJECTED_IRRELEVANT, COMPLETED, FAILED
    error: Optional[str]
