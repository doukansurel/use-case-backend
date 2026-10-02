from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.inspection_task import (
    InspectionTaskCreate,
    InspectionTaskReviewSubmit,
    InspectionTaskResponse,
    PaginatedTaskResponse,
)
from app.services.inspection_service import inspection_service

router = APIRouter()


@router.post(
    "/analyze",
    response_model=InspectionTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="LangGraph Kalite Kontrol Analizi & Görev Oluştur"
)
async def analyze_and_create_task(
    payload: InspectionTaskCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    **LangGraph İş Akışını Başlatır:**
    1. **1. Düğüm:** Görsel alakalılık kontrolü yapılır (alakasız ise akış otomatik kapatılır ve mesaj döner).
    2. **2. Düğüm:** Alakalı ise LLM kusur tespit düğümüne geçer:
       - `product_id`
       - `timestamp`
       - `is_product_defect`
       - `confidence_score`
       - `defect_description`
       bilgilerini üretir ve veritabanına kullanıcı onayına (`PENDING_REVIEW`) hazır bir etiketleme görevi olarak kaydeder.
    """
    return await inspection_service.execute_and_create(db, payload=payload)


@router.post(
    "/quality-check",
    response_model=InspectionTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Kalite Kontrol Analizi (Alias)",
    include_in_schema=False
)
async def quality_check_alias(
    payload: InspectionTaskCreate,
    db: AsyncSession = Depends(get_db)
):
    """Frontend uyumluluğu için /analyze rotasının alias'ı."""
    return await inspection_service.execute_and_create(db, payload=payload)


@router.get(
    "/categories",
    summary="Tanımlı Kategori ve Başlıca Kusur Listesini Getir"
)
async def get_categories_and_defects():
    """
    Sistemin desteklediği hedef ürün kategorilerini ve tespit edilen başlıca kusur listesini döndürür.
    """
    from app.workflows.builders.llm_node_builder import SUPPORTED_CATEGORIES, PRIMARY_DEFECT_TYPES
    return {
        "categories": SUPPORTED_CATEGORIES,
        "primary_defects": PRIMARY_DEFECT_TYPES
    }


@router.get(
    "/tasks",
    response_model=PaginatedTaskResponse,
    summary="Etiketleme & Kontrol Görevlerini Listele"
)
async def list_inspection_tasks(
    review_status: Optional[str] = Query(None, description="Onay durumu: PENDING_REVIEW, APPROVED, CORRECTED, REJECTED"),
    workflow_status: Optional[str] = Query(None, description="İş akışı durumu: PENDING, PROCESSING, COMPLETED, REJECTED_IRRELEVANT, FAILED"),
    is_relevant: Optional[bool] = Query(None, description="Görsel alakalılık filtresi"),
    is_product_defect: Optional[bool] = Query(None, description="Kusur durumu filtresi"),
    product_id: Optional[str] = Query(None, description="Ürün kodu filtresi"),
    category: Optional[str] = Query(None, description="Ürün kategorisi filtresi (örn: Vana, Dişli)"),
    page: int = Query(1, ge=1, description="Sayfa no"),
    limit: int = Query(20, ge=1, le=100, description="Sayfa başı kayıt"),
    db: AsyncSession = Depends(get_db)
):
    """
    Tüm kalite kontrol ve etiketleme görevlerini sayfalı ve filtreli olarak listeler.
    """
    return await inspection_service.list_tasks(
        db,
        review_status=review_status,
        workflow_status=workflow_status,
        is_relevant=is_relevant,
        is_product_defect=is_product_defect,
        product_id=product_id,
        category=category,
        page=page,
        limit=limit
    )


@router.get(
    "/tasks/{task_id}",
    response_model=InspectionTaskResponse,
    summary="Görev Detayını Getir"
)
async def get_task_detail(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Tek bir kalite kontrol görevinin detaylarını ve AI çıktısını getirir."""
    return await inspection_service.get_by_id(db, task_id=task_id)


@router.post(
    "/tasks/{task_id}/review",
    response_model=InspectionTaskResponse,
    summary="Kullanıcı Onayı ile Etiketle (Human-in-the-Loop)"
)
async def submit_human_review(
    task_id: int,
    payload: InspectionTaskReviewSubmit,
    db: AsyncSession = Depends(get_db)
):
    """
    Operatör / etiketleyici, AI modelinin tahminini inceler:
    - **APPROVED:** AI tahminini doğrular.
    - **CORRECTED:** AI'ın hatalı bildiği kusur durumunu / açıklamasını düzeltip kaydeder.
    - **REJECTED:** Hatalı veya incelenemez görsel olarak işaretler.
    """
    return await inspection_service.submit_review(db, task_id=task_id, review=payload)


@router.post(
    "/tasks/{task_id}/retry",
    response_model=InspectionTaskResponse,
    summary="Görevi Yeniden Dene (Retry FAILED / Re-evaluate)"
)
async def retry_inspection_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Özellikle LLM hatası nedeniyle FAILED durumuna düşmüş veya yeniden
    analiz edilmesi istenen görevi LangGraph iş akışından tekrar geçirir.
    """
    return await inspection_service.retry_task(db, task_id=task_id)


@router.delete(
    "/tasks/{task_id}",
    summary="Görevi Sil"
)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Görevi veritabanından siler."""
    return await inspection_service.delete_task(db, task_id=task_id)
