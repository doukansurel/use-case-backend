from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.inspection_task import InspectionTask


async def seed_database(db: AsyncSession, force: bool = False) -> dict:
    """
    Kalite Kontrol ve Etiketleme Programı için gerçekçi örnek verileri oluşturur.
    """
    count = await db.scalar(select(func.count(InspectionTask.id))) or 0
    if count > 0 and not force:
        return {"status": "skipped", "message": "Veritabanı zaten etiketleme verisi içeriyor."}

    if force and count > 0:
        await db.execute(InspectionTask.__table__.delete())
        await db.commit()

    now = datetime.now(timezone.utc)

    sample_tasks = [
        # 1. Alakalı, Kusurlu ve Henüz Operatör Onayı Bekleyen (PENDING_REVIEW)
        {
            "product_id": "PRD-OPT-LENS-101",
            "image_url": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=600&q=80",
            "category": "Optik Lens Grupları",
            "is_relevant": True,
            "relevance_message": "Görsel elektro-optik kalite kontrol incelemesi için uygundur.",
            "workflow_status": "COMPLETED",
            "is_product_defect": True,
            "confidence_score": 0.942,
            "defect_description": "Yüzey Çizikleri: Ön optik mercek yüzeyinde 0.8mm uzunluğunda mikro çizik tespit edildi.",
            "ai_timestamp": (now - timedelta(minutes=15)).isoformat(),
            "review_status": "PENDING_REVIEW",
            "created_at": now - timedelta(minutes=15),
            "updated_at": now - timedelta(minutes=15),
        },
        # 2. Alakalı, Kusursuz ve Operatör Tarafından Onaylanmış (APPROVED)
        {
            "product_id": "PRD-THM-CAM-42",
            "image_url": "https://images.unsplash.com/photo-1581092335397-9583fe92d232?auto=format&fit=crop&w=600&q=80",
            "category": "Termal Kamera Modülleri",
            "is_relevant": True,
            "relevance_message": "Görsel elektro-optik kalite kontrol incelemesi için uygundur.",
            "workflow_status": "COMPLETED",
            "is_product_defect": False,
            "confidence_score": 0.985,
            "defect_description": "Herhangi bir anomali tespit edilmedi. Termal sensör yuvası ve kızılötesi optik toleransları tam uygundur.",
            "ai_timestamp": (now - timedelta(hours=1)).isoformat(),
            "review_status": "APPROVED",
            "user_is_defect": False,
            "user_defect_description": None,
            "user_category": "Termal Kamera Modülleri",
            "user_notes": "AI tespiti doğru; kızılötesi filtre ve sensör merkezlemesi standartlara uygun.",
            "reviewed_by": "kemal_uzman",
            "reviewed_at": now - timedelta(minutes=45),
            "created_at": now - timedelta(hours=1),
            "updated_at": now - timedelta(minutes=45),
        },
        # 3. Alakalı, AI Kusursuz Dedi Ama Operatör Düzeltti (CORRECTED)
        {
            "product_id": "PRD-SURV-UNIT-07",
            "image_url": "https://images.unsplash.com/photo-1581092580497-e0d23cbdf1dc?auto=format&fit=crop&w=600&q=80",
            "category": "Gözetleme Üniteleri",
            "is_relevant": True,
            "relevance_message": "Görsel elektro-optik kalite kontrol incelemesi için uygundur.",
            "workflow_status": "COMPLETED",
            "is_product_defect": False,
            "confidence_score": 0.760,
            "defect_description": "Ünite genel görünümü temiz, dış gövdede belirgin kusur bulunamadı.",
            "ai_timestamp": (now - timedelta(hours=2)).isoformat(),
            "review_status": "CORRECTED",
            "user_is_defect": True,
            "user_defect_description": "Konektör Gevşekliği ve Optik Eksen Hizalama Hatası: Arka panel veri konektör soketinde 0.5mm boşluk ve kamera ekseninde açısal kayma var.",
            "user_category": "Gözetleme Üniteleri",
            "user_notes": "Etiket düzeltildi: Konektör kilit tırnakları yeniden sıkılmalı ve eksen kalibrasyonuna alınmalı.",
            "reviewed_by": "ayse_kalite",
            "reviewed_at": now - timedelta(hours=1, minutes=30),
            "created_at": now - timedelta(hours=2),
            "updated_at": now - timedelta(hours=1, minutes=30),
        },
        # 4. Alakasız Görsel - LangGraph 1. Düğümde Otomatik Kapatılan (REJECTED_IRRELEVANT)
        {
            "product_id": "PRD-UNKNOWN-99",
            "image_url": "https://images.unsplash.com/photo-1543610892-0b1f7e6d8ac1?auto=format&fit=crop&w=600&q=80&cat=avatar",
            "category": None,
            "is_relevant": False,
            "relevance_message": "Alakasız görsel tespit edildi: Yüklenen görsel Optik Lens Grupları, Termal Kamera Modülleri ve Gözetleme Üniteleri kalite kontrolü için uygun değildir. İşlem sonlandırıldı.",
            "workflow_status": "REJECTED_IRRELEVANT",
            "is_product_defect": None,
            "confidence_score": None,
            "defect_description": None,
            "ai_timestamp": (now - timedelta(hours=3)).isoformat(),
            "review_status": "REJECTED",
            "user_notes": "Otomatik sistem tarafından alakasız görsel olarak işaretlendi.",
            "created_at": now - timedelta(hours=3),
            "updated_at": now - timedelta(hours=3),
        },
        # 5. Alakalı, Kusurlu ve Operatör Tarafından Onaylanmış (APPROVED)
        {
            "product_id": "PRD-OPT-LENS-88",
            "image_url": "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=600&q=80",
            "category": "Optik Lens Grupları",
            "is_relevant": True,
            "relevance_message": "Görsel elektro-optik kalite kontrol incelemesi için uygundur.",
            "workflow_status": "COMPLETED",
            "is_product_defect": True,
            "confidence_score": 0.965,
            "defect_description": "Kaplama Kusurları: Antirefle (AR) kaplamasında çevresel soyulma ve gökkuşağı rengi dalgalanma tespit edildi.",
            "ai_timestamp": (now - timedelta(hours=4)).isoformat(),
            "review_status": "APPROVED",
            "user_is_defect": True,
            "user_defect_description": "AI tespiti teyit edildi: Kaplama kusuru geçirgenlik kaybına sebep olduğu için mercek grubu yeniden kaplamaya gönderildi.",
            "user_category": "Optik Lens Grupları",
            "user_notes": "Kaplama fırını parametreleri kontrol edilmeli.",
            "reviewed_by": "mehmet_denetmen",
            "reviewed_at": now - timedelta(hours=3, minutes=15),
            "created_at": now - timedelta(hours=4),
            "updated_at": now - timedelta(hours=3, minutes=15),
        },
        # 6. Alakalı, Kusurlu (Optik Eksen Sapması), İnceleme Bekleyen (PENDING_REVIEW)
        {
            "product_id": "PRD-THM-MOD-15",
            "image_url": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=600&q=80",
            "category": "Termal Kamera Modülleri",
            "is_relevant": True,
            "relevance_message": "Görsel elektro-optik kalite kontrol incelemesi için uygundur.",
            "workflow_status": "COMPLETED",
            "is_product_defect": True,
            "confidence_score": 0.912,
            "defect_description": "Optik Eksen Hizalama Hataları: Termal dedektör ile odaklama lens grubu arasında 0.4° açısal eksen sapması tespit edildi.",
            "ai_timestamp": (now - timedelta(minutes=5)).isoformat(),
            "review_status": "PENDING_REVIEW",
            "created_at": now - timedelta(minutes=5),
            "updated_at": now - timedelta(minutes=5),
        },
        # 7. LLM Hatası Nedeniyle Başarısız Olan ve Yeniden Denenmeyi Bekleyen (FAILED)
        {
            "product_id": "PRD-FAIL-SAMPLE-01",
            "image_url": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=600&q=80",
            "category": None,
            "is_relevant": False,
            "relevance_message": "LLM API hatası nedeniyle analiz tamamlanamadı.",
            "workflow_status": "FAILED",
            "error": "LLM çağrısı başarısız oldu (gemini / gemini-2.5-flash-lite): 429 Resource Exhausted / Timeout. Yeniden deneme bekleniyor.",
            "is_product_defect": None,
            "confidence_score": None,
            "defect_description": None,
            "evaluation_source": "llm",
            "model_version": "gemini-2.5-flash-lite",
            "prompt_version": "v2.1",
            "ai_timestamp": (now - timedelta(minutes=2)).isoformat(),
            "review_status": "PENDING_REVIEW",
            "created_at": now - timedelta(minutes=2),
            "updated_at": now - timedelta(minutes=2),
        }
    ]

    for item in sample_tasks:
        item.setdefault("evaluation_source", "llm")
        item.setdefault("model_version", "gemini-2.5-flash-lite")
        item.setdefault("prompt_version", "v2.1")
        item.setdefault("error", None)
        task = InspectionTask(**item)
        db.add(task)

    await db.commit()

    return {
        "status": "success",
        "message": "Örnek kalite kontrol ve etiketleme görevleri yüklendi.",
        "tasks_created": len(sample_tasks)
    }
