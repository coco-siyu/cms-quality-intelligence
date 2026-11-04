import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import ComparisonEvidenceStatus, PublicationState
from app.models import MeasureComparison

DETAIL_PARAMETERS = {
    "program": "Fictional Quality Program",
    "collection_type": "program_roster",
    "from_year": 2025,
    "to_year": 2026,
}


def test_change_list_returns_only_public_evidence_backed_comparisons(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/changes",
        params={"from_year": 2025, "to_year": 2026},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"] == {
        "page": 1,
        "page_size": 25,
        "total_items": 1,
        "total_pages": 1,
    }
    assert [item["measure_id"] for item in payload["items"]] == ["DEMO-001"]
    record = payload["items"][0]
    assert record["status"] == "modified"
    assert record["evidence_status"] == "verified"
    assert record["collection_type"] == "program_roster"
    assert record["fields"][0]["field"] == "definition"
    assert {item["side"] for item in record["fields"][0]["evidence"]} == {
        "from_version",
        "to_version",
    }
    assert "DEMO-PRIVATE" not in response.text


@pytest.mark.parametrize(
    ("parameters", "expected_total"),
    [
        ({"change_status": "modified"}, 1),
        ({"change_status": "unchanged"}, 0),
        ({"affected_field": "definition"}, 1),
        ({"affected_field": "numerator"}, 0),
        ({"from_year": 2024, "to_year": 2026}, 0),
        ({"from_year": 2025, "to_year": 2026}, 1),
        ({"collection_type": "ecqm"}, 0),
        ({"collection_type": "program_roster"}, 1),
    ],
)
def test_change_list_filters_public_records(
    client: TestClient,
    parameters: dict[str, object],
    expected_total: int,
) -> None:
    response = client.get("/api/changes", params=parameters)

    assert response.status_code == 200
    assert response.json()["pagination"]["total_items"] == expected_total


def test_change_list_paginates_after_fresh_public_validation(client: TestClient) -> None:
    response = client.get("/api/changes", params={"page": 2, "page_size": 1})

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "pagination": {
            "page": 2,
            "page_size": 1,
            "total_items": 1,
            "total_pages": 1,
        },
    }


def test_change_detail_returns_exact_side_by_side_record(client: TestClient) -> None:
    response = client.get("/api/changes/DEMO-001", params=DETAIL_PARAMETERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["measure_id"] == "DEMO-001"
    assert payload["from_year"] == 2025
    assert payload["to_year"] == 2026
    assert payload["fields"][0]["from_value"] == "Fictional definition for 2025."
    assert payload["fields"][0]["to_value"] == "Fictional definition for 2026."


@pytest.mark.parametrize(
    "parameters",
    [
        {**DETAIL_PARAMETERS, "from_year": 2024},
        {**DETAIL_PARAMETERS, "collection_type": "ecqm"},
        {**DETAIL_PARAMETERS, "program": "Another Program"},
    ],
)
def test_change_detail_requires_exact_public_identity(
    client: TestClient,
    parameters: dict[str, object],
) -> None:
    response = client.get("/api/changes/DEMO-001", params=parameters)

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


@pytest.mark.parametrize(
    ("publication_state", "evidence_status"),
    [
        (PublicationState.DRAFT, ComparisonEvidenceStatus.VERIFIED),
        (PublicationState.PUBLISHED, ComparisonEvidenceStatus.INCOMPLETE),
    ],
)
def test_draft_or_incomplete_comparison_never_crosses_public_api(
    client: TestClient,
    seeded_session: Session,
    publication_state: PublicationState,
    evidence_status: ComparisonEvidenceStatus,
) -> None:
    comparison = seeded_session.scalar(select(MeasureComparison))
    assert comparison is not None
    comparison.publication_state = publication_state
    if publication_state == PublicationState.DRAFT:
        comparison.published_at = None
        comparison.published_by = None
    comparison.evidence_status = evidence_status
    seeded_session.commit()

    listing = client.get("/api/changes")
    detail = client.get("/api/changes/DEMO-001", params=DETAIL_PARAMETERS)

    assert listing.status_code == 200
    assert listing.json()["items"] == []
    assert detail.status_code == 404


def test_fresh_validation_withholds_stale_published_comparison(
    client: TestClient,
    seeded_session: Session,
) -> None:
    comparison = seeded_session.scalar(select(MeasureComparison))
    assert comparison is not None
    source = (
        comparison.affected_fields[0]
        .evidence_links[0]
        .evidence_reference.source_revision.source_document
    )
    source.is_active = False
    seeded_session.commit()

    response = client.get("/api/changes")

    assert response.status_code == 200
    assert response.json()["pagination"]["total_items"] == 0


def test_change_routes_validate_year_pair_and_required_identity(client: TestClient) -> None:
    same_year = client.get(
        "/api/changes",
        params={"from_year": 2025, "to_year": 2025},
    )
    missing_identity = client.get(
        "/api/changes/DEMO-001",
        params={"from_year": 2025, "to_year": 2026},
    )

    assert same_year.status_code == 422
    assert same_year.json()["code"] == "validation_error"
    assert missing_identity.status_code == 422
    assert missing_identity.json()["code"] == "validation_error"
