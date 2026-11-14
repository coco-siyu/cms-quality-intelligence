from pathlib import Path

import yaml
from openapi_spec_validator import validate

from app.main import app


def test_root_openapi_contract_is_valid() -> None:
    contract_path = Path(__file__).parents[2] / "openapi.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))

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


def test_runtime_openapi_exposes_contract_operation_ids_and_error_models() -> None:
    schema = app.openapi()
    operations = {
        "/health": "getHealth",
        "/api/performance-years": "listPerformanceYears",
        "/api/measures": "listMeasures",
        "/api/measures/{measure_id}": "getMeasure",
        "/api/measures/{measure_id}/navigation": "getMeasureNavigation",
        "/api/measures/{measure_id}/versions": "listMeasureVersions",
        "/api/changes": "listChanges",
        "/api/changes/export.csv": "exportChangesCsv",
        "/api/changes/{measure_id}": "getChange",
        "/api/changes/{measure_id}/impact-explanation": "getImpactExplanation",
    }

    for path, operation_id in operations.items():
        assert schema["paths"][path]["get"]["operationId"] == operation_id
    assert set(
        schema["paths"]["/api/changes/export.csv"]["get"]["responses"]["200"]["content"]
    ) == {"text/csv"}

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
