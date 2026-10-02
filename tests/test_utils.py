import pytest
from datetime import datetime, timezone
from app.models.inspection_task import InspectionTask
from app.utils.mappers import map_task_to_response, map_tasks_to_responses
from app.utils.image_utils import ensure_image_data_uri, is_base64_data_uri
from app.utils.json_utils import clean_json_output
from app.utils.date_utils import utc_now, format_iso_timestamp


def test_utc_now():
    now = utc_now()
    assert isinstance(now, datetime)
    assert now.tzinfo is not None
    assert now.tzinfo == timezone.utc


def test_format_iso_timestamp():
    iso_str = format_iso_timestamp()
    assert isinstance(iso_str, str)
    # Parse back to verify valid ISO 8601
    dt = datetime.fromisoformat(iso_str)
    assert dt is not None

    fixed_dt = datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc)
    assert format_iso_timestamp(fixed_dt) == "2026-10-02T12:00:00+00:00"


def test_ensure_image_data_uri():
    # URL should be kept intact
    http_url = "http://example.com/image.jpg"
    assert ensure_image_data_uri(http_url) == http_url

    https_url = "https://example.com/image.png"
    assert ensure_image_data_uri(https_url) == https_url

    # Data URI should be kept intact
    data_uri = "data:image/png;base64,iVBORw0KGgoAAAANS..."
    assert ensure_image_data_uri(data_uri) == data_uri

    # Raw base64 should be prefixed
    raw_b64 = "iVBORw0KGgoAAAANS..."
    assert ensure_image_data_uri(raw_b64) == f"data:image/jpeg;base64,{raw_b64}"

    # Empty string
    assert ensure_image_data_uri("") == ""
    assert ensure_image_data_uri(None) == ""


def test_is_base64_data_uri():
    assert is_base64_data_uri("data:image/jpeg;base64,12345") is True
    assert is_base64_data_uri("https://example.com/pic.jpg") is False
    assert is_base64_data_uri("") is False
    assert is_base64_data_uri(None) is False


def test_clean_json_output():
    # Standard ```json codeblock
    json_block = "```json\n{\"category\": \"Optik Lens Grupları\", \"is_product_defect\": true}\n```"
    parsed = clean_json_output(json_block)
    assert parsed["category"] == "Optik Lens Grupları"
    assert parsed["is_product_defect"] is True

    # Generic ``` codeblock
    generic_block = "```\n{\"confidence_score\": 0.95}\n```"
    parsed_generic = clean_json_output(generic_block)
    assert parsed_generic["confidence_score"] == 0.95

    # Raw clean JSON string
    raw_json = "{\"message\": \"success\"}"
    assert clean_json_output(raw_json) == {"message": "success"}


def test_map_task_to_response():
    now = utc_now()
    task = InspectionTask(
        id=42,
        product_id="PRD-TEST-001",
        image_url="https://example.com/test.jpg",
        image_base64="data:image/jpeg;base64,testdata",
        category="Optik Lens Grupları",
        is_relevant=True,
        relevance_message="Uygun",
        workflow_status="COMPLETED",
        is_product_defect=True,
        confidence_score=0.98,
        defect_description="Yüzey Çizikleri: Test hatası",
        ai_timestamp=now.isoformat(),
        evaluation_source="llm",
        model_version="gemini-2.5-flash-lite",
        prompt_version="v2.1",
        error=None,
        review_status="PENDING_REVIEW",
        created_at=now,
        updated_at=now,
    )

    response = map_task_to_response(task)

    assert response.id == 42
    assert response.product_id == "PRD-TEST-001"
    assert response.image_url == "https://example.com/test.jpg"
    assert response.image_base64 == "data:image/jpeg;base64,testdata"
    assert response.category == "Optik Lens Grupları"
    assert response.is_relevant is True
    assert response.workflow_status == "COMPLETED"
    assert response.evaluation_source == "llm"
    assert response.model_version == "gemini-2.5-flash-lite"
    assert response.prompt_version == "v2.1"
    assert response.error is None

    # AI evaluation sub-schema
    assert response.ai_evaluation.product_id == "PRD-TEST-001"
    assert response.ai_evaluation.category == "Optik Lens Grupları"
    assert response.ai_evaluation.is_product_defect is True
    assert response.ai_evaluation.confidence_score == 0.98
    assert response.ai_evaluation.defect_description == "Yüzey Çizikleri: Test hatası"
    assert response.ai_evaluation.evaluation_source == "llm"
    assert response.ai_evaluation.model_version == "gemini-2.5-flash-lite"
    assert response.ai_evaluation.prompt_version == "v2.1"

    # Multiple mapping helper
    tasks_list = [task, task]
    responses = map_tasks_to_responses(tasks_list)
    assert len(responses) == 2
    assert responses[0].id == 42
    assert responses[1].id == 42
