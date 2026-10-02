import asyncio
import json
import pytest
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db, AsyncSessionLocal
from app.seed.seeder import seed_database
from app.workflows.builders.llm_node_builder import default_llm_builder


class MockLLMResponse:
    def __init__(self, content: str):
        self.content = content


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
    evaluation_source='llm', model_version ve prompt_version doğrulama
    """
    mock_client = MagicMock()
    mock_client.invoke.side_effect = [
        # 1. Düğüm (Alakalılık kontrolü)
        MockLLMResponse(json.dumps({"is_relevant": True, "reason": "Optik lens inceleme için uygundur."})),
        # 2. Düğüm (Kusur değerlendirmesi)
        MockLLMResponse(json.dumps({
            "category": "Optik Lens Grupları",
            "is_product_defect": True,
            "confidence_score": 0.942,
            "defect_description": "Yüzey Çizikleri: Optik eleman yüzeyinde mikro çizik tespit edildi."
        }))
    ]

    with patch.object(default_llm_builder, "get_llm_client", return_value=mock_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "product_id": "PRD-OPT-LENS-01",
                "image_url": "https://industrial-samples.com/parts/optical_lens_scratch.jpg"
            }
            res = await client.post("/api/v1/inspections/analyze", json=payload)
            assert res.status_code == 201
            data = res.json()

            # 1. Alakalılık ve İş Akışı Kontrolü
            assert data["is_relevant"] is True
            assert data["workflow_status"] == "COMPLETED"
            assert data["evaluation_source"] == "llm"
            assert data["prompt_version"] is not None
            assert data["error"] is None

            # 2. LLM Değerlendirme Çıktısı Doğrulaması
            ai_eval = data["ai_evaluation"]
            assert ai_eval["product_id"] == "PRD-OPT-LENS-01"
            assert ai_eval["timestamp"] is not None
            assert ai_eval["is_product_defect"] is True
            assert ai_eval["confidence_score"] == 0.942
            assert ai_eval["category"] == "Optik Lens Grupları"
            assert "Yüzey Çizikleri" in ai_eval["defect_description"]
            assert ai_eval["evaluation_source"] == "llm"

            # 3. İnsan Onayı Durumu
            assert data["review_status"] == "PENDING_REVIEW"


@pytest.mark.asyncio
async def test_langgraph_irrelevant_image_rejection():
    """
    LangGraph Akışı - 1. Düğüm: Alakasız görsel kontrolü.
    Alakasız ise 2. düğüme geçmeden akışı kapatıp REJECTED_IRRELEVANT döndürür.
    """
    mock_client = MagicMock()
    mock_client.invoke.return_value = MockLLMResponse(
        json.dumps({
            "is_relevant": False,
            "reason": "Alakasız görsel tespit edildi: evcil hayvan görseli kalite kontrol için uygun değildir."
        })
    )

    with patch.object(default_llm_builder, "get_llm_client", return_value=mock_client):
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
            assert data["ai_evaluation"]["confidence_score"] is None
            assert data["ai_evaluation"]["defect_description"] is None
            assert data["review_status"] == "REJECTED"


@pytest.mark.asyncio
async def test_langgraph_llm_failure_records_failed_status():
    """
    Kullanıcı Talebi: Fallback motoru kaldırılmalı.
    LLM hata verirse sahte sonuç uydurmak yerine workflow_status=FAILED olarak kaydedilmeli,
    hata mesajı error alanına yazılmalı ve kusursuz/0.985 gibi sahte değerler üretilmemelidir.
    """
    mock_client = MagicMock()
    mock_client.invoke.side_effect = RuntimeError("API quota exceeded or network connection reset")

    # default_llm_builder._invoke_with_retry içinde 1 retry yapıp hata fırlatacak
    with patch.object(default_llm_builder, "get_llm_client", return_value=mock_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "product_id": "PRD-FAIL-TEST-01",
                "image_url": "https://industrial-samples.com/parts/unknown_part.jpg"
            }
            res = await client.post("/api/v1/inspections/analyze", json=payload)
            assert res.status_code == 201
            data = res.json()

            # FAILED durumu ve hata alanı doğrulaması
            assert data["workflow_status"] == "FAILED"
            assert data["error"] is not None
            assert "API quota exceeded" in data["error"] or "LLM" in data["error"]
            assert data["evaluation_source"] == "llm"

            # Kusurlu veya kusursuz uydurma veri girilmediğini doğrula
            assert data["ai_evaluation"]["is_product_defect"] is None
            assert data["ai_evaluation"]["confidence_score"] is None
            assert data["ai_evaluation"]["defect_description"] is None
            assert data["ai_evaluation"]["category"] is None

            # Operatörün müdahalesi ve retry için PENDING_REVIEW olarak tutulmalıdır
            assert data["review_status"] == "PENDING_REVIEW"


@pytest.mark.asyncio
async def test_retry_failed_inspection_task():
    """
    Kullanıcı Talebi: Üretimde LLM hatası workflow_status=FAILED olarak kaydedilmeli ve tekrar denenmeli.
    POST /tasks/{task_id}/retry endpoint'i FAILED görevi yeniden LangGraph akışından geçirerek günceller.
    """
    # 1. Önce hata alan bir görev yarat
    mock_fail_client = MagicMock()
    mock_fail_client.invoke.side_effect = RuntimeError("Temporary 503 Service Unavailable")

    with patch.object(default_llm_builder, "get_llm_client", return_value=mock_fail_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create_res = await client.post(
                "/api/v1/inspections/analyze",
                json={
                    "product_id": "PRD-RETRY-TEST",
                    "image_url": "https://industrial-samples.com/parts/thermal_sensor.jpg"
                }
            )
            assert create_res.status_code == 201
            task_id = create_res.json()["id"]
            assert create_res.json()["workflow_status"] == "FAILED"

    # 2. Şimdi API düzeldiğinde tekrar dene (Retry)
    mock_success_client = MagicMock()
    mock_success_client.invoke.side_effect = [
        MockLLMResponse(json.dumps({"is_relevant": True, "reason": "Termal kamera modülü parçası."})),
        MockLLMResponse(json.dumps({
            "category": "Termal Kamera Modülleri",
            "is_product_defect": False,
            "confidence_score": 0.910,
            "defect_description": "Sensör ekseni standartlara uygundur."
        }))
    ]

    with patch.object(default_llm_builder, "get_llm_client", return_value=mock_success_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            retry_res = await client.post(f"/api/v1/inspections/tasks/{task_id}/retry")
            assert retry_res.status_code == 200
            retried_data = retry_res.json()

            assert retried_data["id"] == task_id
            assert retried_data["workflow_status"] == "COMPLETED"
            assert retried_data["error"] is None
            assert retried_data["ai_evaluation"]["category"] == "Termal Kamera Modülleri"
            assert retried_data["ai_evaluation"]["is_product_defect"] is False
            assert retried_data["ai_evaluation"]["confidence_score"] == 0.910


@pytest.mark.asyncio
async def test_confidence_score_no_arbitrary_default():
    """
    Kullanıcı Talebi: Değer gelmezse kod varsayılan olarak 0.95 ATAMAMALI (None kalmalı).
    """
    mock_client = MagicMock()
    mock_client.invoke.side_effect = [
        MockLLMResponse(json.dumps({"is_relevant": True, "reason": "Uygun görsel"})),
        MockLLMResponse(json.dumps({
            "category": "Optik Lens Grupları",
            "is_product_defect": False,
            "confidence_score": None,  # Model skor döndürmedi
            "defect_description": "Parça temiz."
        }))
    ]

    with patch.object(default_llm_builder, "get_llm_client", return_value=mock_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/inspections/analyze",
                json={
                    "product_id": "PRD-NO-SCORE",
                    "image_url": "https://industrial-samples.com/parts/clean_lens.jpg"
                }
            )
            assert res.status_code == 201
            data = res.json()
            assert data["ai_evaluation"]["confidence_score"] is None  # 0.95 uydurulmamalı!


@pytest.mark.asyncio
async def test_unrecognized_category_not_defaulted_to_optik_lens():
    """
    Kullanıcı Talebi: Kategori eşleşmezse sessizce 'Optik Lens Grupları' ATANMAMALI.
    """
    mock_client = MagicMock()
    mock_client.invoke.side_effect = [
        MockLLMResponse(json.dumps({"is_relevant": True, "reason": "Endüstriyel parça"})),
        MockLLMResponse(json.dumps({
            "category": "Plastik Gövde ve Kovan",  # Desteklenen 3 kategori dışı
            "is_product_defect": False,
            "confidence_score": 0.85,
            "defect_description": "Kusur yok."
        }))
    ]

    with patch.object(default_llm_builder, "get_llm_client", return_value=mock_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/inspections/analyze",
                json={
                    "product_id": "PRD-CUSTOM-CAT",
                    "image_url": "https://industrial-samples.com/parts/housing.jpg"
                }
            )
            assert res.status_code == 201
            data = res.json()
            # Sessizce Optik Lens Grupları atanmadığını, orijinal tespitin korunduğunu doğrula
            assert data["ai_evaluation"]["category"] == "Plastik Gövde ve Kovan"


@pytest.mark.asyncio
async def test_human_review_and_labeling():
    """
    Kullanıcı onayı ile etiketleme (Human Annotation) testi:
    Operatör görevi inceler ve etiket durumunu günceller.
    """
    mock_client = MagicMock()
    mock_client.invoke.side_effect = [
        MockLLMResponse(json.dumps({"is_relevant": True, "reason": "Optik parça"})),
        MockLLMResponse(json.dumps({
            "category": "Optik Lens Grupları",
            "is_product_defect": False,
            "confidence_score": 0.90,
            "defect_description": "Temiz görünüyor."
        }))
    ]

    with patch.object(default_llm_builder, "get_llm_client", return_value=mock_client):
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
        assert "failed_count" in stats
        assert "approved_count" in stats
        assert "corrected_count" in stats
        assert len(stats["recent_tasks"]) > 0
