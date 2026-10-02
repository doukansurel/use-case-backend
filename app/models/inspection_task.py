from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Boolean, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import TimestampMixin


class InspectionTask(Base, TimestampMixin):
    """
    Kalite Kontrol & Etiketleme Görevi (Inspection Task).
    LangGraph iş akışı çıktısını ve operatörün nihai onay/etiketleme kararlarını saklar.
    """
    __tablename__ = "inspection_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    image_base64: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Base64 görsel verisi (data:image/... veya raw)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)  # Geriye dönük uyumluluk (Base64 veya URL)

    # 1. Aşama: Görsel İnceleme & Alakalılık (LangGraph 1. Düğüm)
    is_relevant: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    relevance_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    workflow_status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        index=True
    )  # PENDING, REJECTED_IRRELEVANT, COMPLETED, FAILED
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # LLM veya sistem hata mesajı

    # 2. Aşama: LLM Kusur Değerlendirmesi (LangGraph 2. Düğüm Çıktısı)
    is_product_defect: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    defect_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    ai_timestamp: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Denetim & Model Meta Verileri (Audit & Evaluation Metadata)
    evaluation_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="llm")  # "llm" veya "fallback"
    model_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # örn: gemini-2.5-flash-lite, gpt-4o-mini
    prompt_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="v2.1")

    # 3. Aşama: Kullanıcı Onayı ile Etiketleme (Human-in-the-Loop Annotation)
    review_status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING_REVIEW",
        nullable=False,
        index=True
    )  # PENDING_REVIEW, APPROVED, REJECTED, CORRECTED
    user_is_defect: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    user_defect_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<InspectionTask(id={self.id}, product='{self.product_id}', defect={self.is_product_defect}, status='{self.review_status}')>"
