import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db, AsyncSessionLocal
from app.seed.seeder import seed_database


# Testler başlamadan önce veritabanı tablolarını ve seed verisini hazırla
@pytest.fixture(autouse=True, scope="session")
async def setup_test_database():
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_database(session, force=False)


@pytest.mark.asyncio
async def test_root():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "VisionQC" in data["message"]


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert data["database"] == "healthy"


@pytest.mark.asyncio
async def test_get_categories_and_defects():
    """Tanımlı kategori ve kusur listesini döndüren endpoint testi."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/inspections/categories")
        assert res.status_code == 200
        data = res.json()
        assert "categories" in data
        assert "primary_defects" in data
        assert "Optik Lens Grupları" in data["categories"]
        assert "Termal Kamera Modülleri" in data["categories"]
        assert "Gözetleme Üniteleri" in data["categories"]
        assert "Yüzey Çizikleri" in data["primary_defects"]
        assert "Kaplama Kusurları" in data["primary_defects"]
        assert "Optik Eksen Hizalama Hataları" in data["primary_defects"]
        assert "Konektör Gevşekliği" in data["primary_defects"]


@pytest.mark.asyncio
async def test_langgraph_relevant_defect_analysis():
    """
    LangGraph Akışı - 1. Düğüm: Alakalı parça görseli
    2. Düğüm: LLM kusur ve kategori değerlendirmesi
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "product_id": "PRD-OPT-LENS-01",
            "image_url": "https://industrial-samples.com/parts/optical_lens_scratch.jpg"
        }
        res = await client.post("/api/v1/inspections/analyze", json=payload)
        assert res.status_code == 201
        data = res.json()

        # 1. Alakalılık Kontrolü
        assert data["is_relevant"] is True
        assert data["workflow_status"] == "COMPLETED"

        # 2. LLM Değerlendirme JSON çıktısı doğrulaması (Kategori dahil)
        ai_eval = data["ai_evaluation"]
        assert ai_eval["product_id"] == "PRD-OPT-LENS-01"
        assert "timestamp" in ai_eval and ai_eval["timestamp"] is not None
        assert "is_product_defect" in ai_eval
        assert "confidence_score" in ai_eval
        assert "defect_description" in ai_eval
        assert ai_eval["category"] in ["Optik Lens Grupları", "Termal Kamera Modülleri", "Gözetleme Üniteleri"]
        assert ai_eval["is_product_defect"] is True  # 'scratch' kelimesinden dolayı kusurlu tespit edildi
        assert "Yüzey Çizikleri" in ai_eval["defect_description"]

        # 3. İnsan onayı durumu
        assert data["review_status"] == "PENDING_REVIEW"


@pytest.mark.asyncio
async def test_langgraph_irrelevant_image_rejection():
    """
    LangGraph Akışı - 1. Düğüm: Alakasız görsel kontrolü.
    Alakasız ise 2. düğüme geçmeden akışı kapatıp otomatik uyarı mesajı döndürür.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "product_id": "PRD-INVALID-99",
            "image_url": "https://random-memes.com/cat_funny_meme.png"
        }
        res = await client.post("/api/v1/inspections/analyze", json=payload)
        assert res.status_code == 201
        data = res.json()

        # 1. Düğümde reddedildiğini doğrula
        assert data["is_relevant"] is False
        assert data["workflow_status"] == "REJECTED_IRRELEVANT"
        assert "Alakasız görsel tespit edildi" in data["relevance_message"]

        # 2. Düğüme geçmediğinden kusur ve kategori değerleri None olmalı
        assert data["ai_evaluation"]["is_product_defect"] is None
        assert data["ai_evaluation"]["defect_description"] is None
        assert data["review_status"] == "REJECTED"


@pytest.mark.asyncio
async def test_human_review_and_labeling():
    """
    Kullanıcı onayı ile etiketleme (Human Annotation) testi:
    Operatör görevi inceler ve etiket durumunu günceller.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Yeni bir görev oluştur
        create_res = await client.post(
            "/api/v1/inspections/analyze",
            json={
                "product_id": "PRD-LABEL-TEST",
                "image_url": "https://industrial-samples.com/parts/clean_optical_lens.jpg"
            }
        )
        task_id = create_res.json()["id"]

        # Operatör onayı / düzeltme gönder (Kategori dahil)
        review_payload = {
            "user_is_defect": True,
            "user_defect_description": "Kaplama Kusurları: Yansıma önleyici kaplamada bölgesel soyulma var.",
            "user_category": "Optik Lens Grupları",
            "user_notes": "Etiket ve kategori operatör tarafından düzeltildi.",
            "review_status": "CORRECTED",
            "reviewed_by": "test_operator"
        }
        review_res = await client.post(
            f"/api/v1/inspections/tasks/{task_id}/review",
            json=review_payload
        )
        assert review_res.status_code == 200
        reviewed_data = review_res.json()

        assert reviewed_data["review_status"] == "CORRECTED"
        assert reviewed_data["user_is_defect"] is True
        assert "Kaplama Kusurları" in reviewed_data["user_defect_description"]
        assert reviewed_data["user_category"] == "Optik Lens Grupları"
        assert reviewed_data["reviewed_by"] == "test_operator"
        assert reviewed_data["reviewed_at"] is not None


@pytest.mark.asyncio
async def test_analytics_dashboard():
    """Etiketleme metrikleri ve KPI dashboard testi."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/analytics/dashboard")
        assert res.status_code == 200
        stats = res.json()

        assert stats["total_tasks"] > 0
        assert "relevant_count" in stats
        assert "irrelevant_count" in stats
        assert "ai_defect_rate" in stats
        assert "approved_count" in stats
        assert "corrected_count" in stats
        assert len(stats["recent_tasks"]) > 0
