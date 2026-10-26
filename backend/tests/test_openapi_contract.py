from pathlib import Path

import yaml
from openapi_spec_validator import validate

from app.main import app


def test_root_openapi_contract_is_valid() -> None:
    contract_path = Path(__file__).parents[2] / "openapi.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))

    validate(contract)


def test_runtime_openapi_exposes_contract_operation_ids_and_error_models() -> None:
    schema = app.openapi()
    operations = {
        "/health": "getHealth",
        "/api/performance-years": "listPerformanceYears",
        "/api/measures": "listMeasures",
        "/api/measures/{measure_id}": "getMeasure",
        "/api/measures/{measure_id}/versions": "listMeasureVersions",
    }

    for path, operation_id in operations.items():
        assert schema["paths"][path]["get"]["operationId"] == operation_id

    admin_operations = {
        ("/api/admin/session", "get"): "getAdminSession",
        ("/api/admin/session", "post"): "createAdminSession",
        ("/api/admin/session", "delete"): "deleteAdminSession",
        ("/api/admin/review-summary", "get"): "getAdminReviewSummary",
        ("/api/admin/measures", "get"): "listAdminMeasures",
        ("/api/admin/measures/{measure_id}", "get"): "getAdminMeasure",
        ("/api/admin/review-items/{review_item_id}", "patch"): (
            "reviewAdminFieldCandidate"
        ),
        ("/api/admin/review-items/{review_item_id}/publish", "post"): (
            "publishAdminFieldCandidate"
        ),
        ("/api/admin/sources", "get"): "listAdminSources",
        ("/api/admin/sources", "post"): "createAdminSource",
        ("/api/admin/sources/{source_id}", "get"): "getAdminSource",
        ("/api/admin/sources/{source_id}", "patch"): "updateAdminSource",
        ("/api/admin/sources/{source_id}/check", "post"): "checkAdminSource",
        ("/api/admin/source-extractions/{extraction_id}", "get"): (
            "getAdminSourceExtraction"
        ),
    }
    for (path, method), operation_id in admin_operations.items():
        assert schema["paths"][path][method]["operationId"] == operation_id

    list_responses = schema["paths"]["/api/measures"]["get"]["responses"]
    detail_responses = schema["paths"]["/api/measures/{measure_id}"]["get"]["responses"]
    assert list_responses["422"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/ApiError"
    )
    assert detail_responses["404"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/ApiError"
    )
