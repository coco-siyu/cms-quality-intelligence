from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate

from app.main import app

CONTRACT_PATH = Path(__file__).parents[2] / "openapi.yaml"


def _contract() -> dict[str, Any]:
    return yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))


def _assert_json_response_matches_contract(
    contract: dict[str, Any],
    *,
    path: str,
    status_code: int,
    payload: object,
) -> None:
    response = contract["paths"][path]["get"]["responses"][str(status_code)]
    if "$ref" in response:
        reference = response["$ref"]
        response = contract
        for part in reference.removeprefix("#/").split("/"):
            response = response[part]
    schema = response["content"]["application/json"]["schema"]
    validation_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "components": contract["components"],
        **schema,
    }
    Draft202012Validator(validation_schema).validate(payload)


def test_root_openapi_contract_is_valid() -> None:
    contract = _contract()

    validate(contract)

    schemas = contract["components"]["schemas"]
    assert "wording_only" in schemas["ChangeStatus"]["enum"]
    assert schemas["ChangeField"]["properties"]["evidence"]["items"]["$ref"].endswith(
        "/ChangeFieldEvidence"
    )
    assert "PublicChangeRecord" in schemas
    assert "PublicChangePage" in schemas
    assert schemas["PublicChangePage"]["properties"]["items"]["items"]["$ref"].endswith(
        "/PublicChangeRecord"
    )
    assert "collection_type" in schemas["PublicChangeRecord"]["required"]
    assert "evidence_status" in schemas["PublicChangeRecord"]["required"]
    assert "measure_name" in schemas["PublicChangeRecord"]["required"]
    assert "approved_at" in schemas["PublicChangeRecord"]["required"]
    assert "published_at" in schemas["PublicChangeRecord"]["required"]
    assert "publication_date" in schemas["EvidenceReference"]["required"]
    assert "effective_date" in schemas["EvidenceReference"]["required"]
    assert schemas["ComparisonEvidenceStatus"]["enum"] == [
        "pending",
        "verified",
        "incomplete",
    ]
    assert schemas["ImpactStatementType"]["enum"] == [
        "source_fact",
        "possible_impact",
    ]
    impact_output = schemas["ImpactExplanationOutput"]
    assert impact_output["additionalProperties"] is False
    assert set(impact_output["required"]) == {
        "plain_language_summary",
        "data_analyst",
        "aco_quality_manager",
        "uncertainty_caveats",
    }
    assert impact_output["properties"]["data_analyst"]["$ref"].endswith("/DataAnalystImpact")
    assert impact_output["properties"]["aco_quality_manager"]["$ref"].endswith(
        "/ACOQualityManagerImpact"
    )
    assert "PublicImpactExplanation" in schemas
    assert schemas["PublicImpactExplanation"]["properties"]["output"]["$ref"].endswith(
        "/ImpactExplanationOutput"
    )
    assert "AdminImpactTaskProposal" in schemas
    assert schemas["AdminImpactTaskProposal"]["properties"]["evidence"]["items"]["$ref"].endswith(
        "/ChangeFieldEvidence"
    )
    assert "AdminReviewChecklist" in schemas
    assert schemas["AdminReviewChecklist"]["properties"]["items"]["items"]["$ref"].endswith(
        "/AdminReviewChecklistItem"
    )
    assert schemas["AdminReviewChecklist"]["properties"]["signoffs"]["items"]["$ref"].endswith(
        "/AdminReviewSignOff"
    )
    assert schemas["AdminMeasureReviewActivity"]["properties"]["reviews"]["items"]["$ref"].endswith(
        "/AdminReviewActivityReview"
    )
    assert schemas["ReviewDashboardStatus"]["enum"] == [
        "pending",
        "in_review",
        "completed",
        "needs_re_review",
    ]
    assert schemas["AdminReviewDashboard"]["properties"]["items"]["items"]["$ref"].endswith(
        "/AdminReviewDashboardItem"
    )
    export_operation = contract["paths"]["/api/changes/export.csv"]["get"]
    export_parameter_refs = {
        parameter["$ref"].rsplit("/", 1)[-1]
        for parameter in export_operation["parameters"]
        if "$ref" in parameter
    }
    assert export_parameter_refs >= {
        "SearchQuery",
        "PerformanceYear",
        "FromYear",
        "ToYear",
        "ChangeStatus",
        "AffectedField",
        "VerificationStatus",
    }
    assert "text/csv" in export_operation["responses"]["200"]["content"]
    xlsx_export_operation = contract["paths"]["/api/changes/export.xlsx"]["get"]
    xlsx_export_parameter_refs = {
        parameter["$ref"].rsplit("/", 1)[-1]
        for parameter in xlsx_export_operation["parameters"]
        if "$ref" in parameter
    }
    assert xlsx_export_parameter_refs >= export_parameter_refs
    assert (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in xlsx_export_operation["responses"]["200"]["content"]
    )


def test_runtime_openapi_exposes_contract_operation_ids_and_error_models() -> None:
    contract = _contract()
    schema = app.openapi()
    http_methods = {"get", "post", "put", "patch", "delete"}
    contract_operations = {
        (path, method, operation["operationId"])
        for path, path_item in contract["paths"].items()
        for method, operation in path_item.items()
        if method in http_methods
    }
    runtime_operations = {
        (path, method, operation["operationId"])
        for path, path_item in schema["paths"].items()
        for method, operation in path_item.items()
        if method in http_methods
    }
    assert runtime_operations == contract_operations

    operations = {
        "/health": "getHealth",
        "/api/performance-years": "listPerformanceYears",
        "/api/measures": "listMeasures",
        "/api/measures/{measure_id}": "getMeasure",
        "/api/measures/{measure_id}/navigation": "getMeasureNavigation",
        "/api/measures/{measure_id}/versions": "listMeasureVersions",
        "/api/changes": "listChanges",
        "/api/changes/export.csv": "exportChangesCsv",
        "/api/changes/export.xlsx": "exportChangesXlsx",
        "/api/changes/{measure_id}": "getChange",
        "/api/changes/{measure_id}/impact-explanation": "getImpactExplanation",
    }

    for path, operation_id in operations.items():
        assert schema["paths"][path]["get"]["operationId"] == operation_id
    assert set(
        schema["paths"]["/api/changes/export.csv"]["get"]["responses"]["200"]["content"]
    ) == {"text/csv"}
    assert set(
        schema["paths"]["/api/changes/export.xlsx"]["get"]["responses"]["200"]["content"]
    ) == {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}

    admin_operations = {
        ("/api/admin/session", "get"): "getAdminSession",
        ("/api/admin/session", "post"): "createAdminSession",
        ("/api/admin/session", "delete"): "deleteAdminSession",
        ("/api/admin/review-summary", "get"): "getAdminReviewSummary",
        ("/api/admin/review-dashboard", "get"): "getAdminReviewDashboard",
        ("/api/admin/measures", "get"): "listAdminMeasures",
        ("/api/admin/measures/{measure_id}", "get"): "getAdminMeasure",
        ("/api/admin/measures/{measure_id}/review-activity", "get"): (
            "getAdminMeasureReviewActivity"
        ),
        ("/api/admin/review-items/{review_item_id}", "patch"): ("reviewAdminFieldCandidate"),
        ("/api/admin/review-items/{review_item_id}/publish", "post"): (
            "publishAdminFieldCandidate"
        ),
        ("/api/admin/sources", "get"): "listAdminSources",
        ("/api/admin/sources", "post"): "createAdminSource",
        ("/api/admin/ingestion-runs", "get"): "listAdminIngestionRuns",
        ("/api/admin/ingestion-runs", "post"): "createAdminIngestionRun",
        ("/api/admin/ingestion-runs/{run_id}", "get"): "getAdminIngestionRun",
        ("/api/admin/sources/{source_id}", "get"): "getAdminSource",
        ("/api/admin/sources/{source_id}", "patch"): "updateAdminSource",
        ("/api/admin/sources/{source_id}/check", "post"): "checkAdminSource",
        ("/api/admin/source-extractions/{extraction_id}", "get"): ("getAdminSourceExtraction"),
        ("/api/admin/source-extractions/{extraction_id}/normalize", "post"): (
            "normalizeAdminSourceExtraction"
        ),
        ("/api/admin/source-normalizations/{normalization_id}", "get"): (
            "getAdminSourceNormalization"
        ),
        ("/api/admin/normalized-fields/{field_candidate_id}/clarifications", "post"): (
            "clarifyAdminNormalizedField"
        ),
        ("/api/admin/comparisons/{comparison_id}/impact-explanations", "get"): (
            "listAdminImpactExplanationDrafts"
        ),
        (
            "/api/admin/comparisons/{comparison_id}/impact-explanations/generate",
            "post",
        ): "generateAdminImpactExplanationDraft",
        (
            "/api/admin/comparisons/{comparison_id}/impact-explanations/regenerate",
            "post",
        ): "regenerateAdminImpactExplanationDraft",
        ("/api/admin/impact-explanations/{draft_id}", "patch"): (
            "reviewAdminImpactExplanationDraft"
        ),
        ("/api/admin/impact-explanations/{draft_id}/publish", "post"): (
            "publishAdminImpactExplanationDraft"
        ),
        ("/api/admin/impact-explanations/{draft_id}/task-proposals", "get"): (
            "listAdminImpactTaskProposals"
        ),
        (
            "/api/admin/impact-explanations/{draft_id}/task-proposals/generate",
            "post",
        ): "generateAdminImpactTaskProposals",
        ("/api/admin/comparisons/{comparison_id}/review-checklist", "get"): (
            "getAdminReviewChecklist"
        ),
        ("/api/admin/comparisons/{comparison_id}/review-checklist/items", "post"): (
            "createAdminReviewChecklistItem"
        ),
        ("/api/admin/review-checklist/items/{checklist_item_id}", "patch"): (
            "updateAdminReviewChecklistItem"
        ),
        ("/api/admin/reviews/{review_id}/sign-off", "post"): "signOffAdminReview",
        ("/api/admin/reviews/{review_id}/reopen", "post"): "reopenAdminReview",
        ("/api/admin/task-proposals/{proposal_id}/accept", "post"): (
            "acceptAdminImpactTaskProposal"
        ),
        ("/api/admin/task-proposals/{proposal_id}/dismiss", "post"): (
            "dismissAdminImpactTaskProposal"
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


@pytest.mark.parametrize(
    ("request_path", "contract_path", "parameters", "expected_status"),
    [
        ("/health", "/health", {}, 200),
        ("/api/performance-years", "/api/performance-years", {}, 200),
        (
            "/api/measures",
            "/api/measures",
            {"from_year": 2025, "to_year": 2026, "page_size": 100},
            200,
        ),
        (
            "/api/measures/DEMO-001",
            "/api/measures/{measure_id}",
            {"from_year": 2025, "to_year": 2026},
            200,
        ),
        (
            "/api/measures/DEMO-001/navigation",
            "/api/measures/{measure_id}/navigation",
            {"from_year": 2025, "to_year": 2026},
            200,
        ),
        (
            "/api/measures/DEMO-001/versions",
            "/api/measures/{measure_id}/versions",
            {"performance_year": 2025},
            200,
        ),
        (
            "/api/changes",
            "/api/changes",
            {"from_year": 2025, "to_year": 2026},
            200,
        ),
        (
            "/api/changes/DEMO-001",
            "/api/changes/{measure_id}",
            {
                "program": "Fictional Quality Program",
                "collection_type": "program_roster",
                "from_year": 2025,
                "to_year": 2026,
            },
            200,
        ),
        (
            "/api/changes/DEMO-001/impact-explanation",
            "/api/changes/{measure_id}/impact-explanation",
            {
                "program": "Fictional Quality Program",
                "collection_type": "program_roster",
                "from_year": 2025,
                "to_year": 2026,
            },
            404,
        ),
        (
            "/api/measures/DOES-NOT-EXIST",
            "/api/measures/{measure_id}",
            {"from_year": 2025, "to_year": 2026},
            404,
        ),
        (
            "/api/changes",
            "/api/changes",
            {"from_year": 2025, "to_year": 2025},
            422,
        ),
    ],
)
def test_public_json_responses_match_checked_in_openapi_schemas(
    client: TestClient,
    request_path: str,
    contract_path: str,
    parameters: dict[str, object],
    expected_status: int,
) -> None:
    response = client.get(request_path, params=parameters)

    assert response.status_code == expected_status
    _assert_json_response_matches_contract(
        _contract(),
        path=contract_path,
        status_code=expected_status,
        payload=response.json(),
    )
