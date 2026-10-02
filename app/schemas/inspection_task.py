from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, model_validator


class LLMEvaluationOutput(BaseModel):
    """
    Kullanıcının talep ettiği standart LangGraph LLM Çıktı JSON Şeması:
    {
      "product_id": ...,
      "timestamp": ...,
      "is_product_defect": ...,
      "confidence_score": ...,
      "defect_description": ...
    }
    """
    product_id: str = Field(..., description="Ürün kimliği")
    timestamp: str = Field(..., description="Analiz zaman damgası (ISO format)")
    is_product_defect: Optional[bool] = Field(None, description="Üründe kusur olup olmadığı")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Model güven skoru")
    defect_description: Optional[str] = Field(None, description="Kusur türü ve açıklaması")
    category: Optional[str] = Field(None, description="Tespit edilen parça/ürün kategorisi (örn: Talaşlı İmalat, Vana, Dişli vb.)")


class InspectionTaskCreate(BaseModel):
    product_id: str = Field(..., description="İncelenecek ürün kodu / seri numarası")
    image_base64: Optional[str] = Field(None, description="Görselin Base64 kodlanmış verisi (data:image/... veya raw)")
    image_url: Optional[str] = Field(None, description="Görsel Base64 verisi veya URL")

    @model_validator(mode="after")
    def validate_image_input(self):
        if not self.image_base64 and not self.image_url:
            raise ValueError("image_base64 veya image_url alanlarından en az biri sağlanmalıdır.")
        if self.image_base64 and not self.image_url:
            self.image_url = self.image_base64
        elif self.image_url and not self.image_base64:
            self.image_base64 = self.image_url
        return self


class InspectionTaskReviewSubmit(BaseModel):
    """
    Kullanıcı onayı ile etiketleme (Human-in-the-Loop review) modeli.
    Operatör, AI tahminini onaylar ya da doğrusuyla etiketler.
    """
    user_is_defect: bool = Field(..., description="Operatörün kesinleştirdiği kusur kararı (True: Kusurlu, False: Kusursuz)")
    user_defect_description: Optional[str] = Field(None, description="Operatörün düzelttiği veya eklediği kusur açıklaması")
    user_category: Optional[str] = Field(None, description="Operatörün belirlediği/düzelttiği ürün kategorisi")
    user_notes: Optional[str] = Field(None, description="Operatör inceleme notları")
    review_status: str = Field(
        default="APPROVED",
        description="Onay durumu: APPROVED (AI onaylandı), CORRECTED (Etiket düzeltildi), REJECTED (Hatalı görsel/reddedildi)"
    )
    reviewed_by: Optional[str] = Field(default="operatör", description="İncelemeyi yapan kullanıcı/etiketleyici adı")


class InspectionTaskResponse(BaseModel):
    id: int
    product_id: str
    image_base64: Optional[str] = None
    image_url: str
    category: Optional[str] = None
    is_relevant: bool
    relevance_message: Optional[str]
    workflow_status: str
    
    # Kullanıcının istediği formatta LLM değerlendirmesi
    ai_evaluation: LLMEvaluationOutput

    # İnsan doğrulaması / Etiketleme durumu
    review_status: str
    user_is_defect: Optional[bool]
    user_defect_description: Optional[str]
    user_category: Optional[str] = None
    user_notes: Optional[str]
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedTaskResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: List[InspectionTaskResponse]
