from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.commands.bootstrap_preview import _assert_preview_target
from app.commands.seed_demo import clear_demo_records_in_session
from app.commands.seed_verified import seed_verified_drafts
from app.database import get_db
from app.domain import CollectionType, PublicationState, PublicVerificationStatus
from app.main import create_app
from app.models import (
    EvidenceReference,
    Measure,
    MeasureVersion,
    ProgramMembership,
    SourceDocument,
    SourceRevision,
    SpecificationFieldCandidate,
)
from app.repositories.admin_reviews import review_summary
from app.repositories.measures import MeasureFilters, get_measure, list_measures
from app.services.roster_publication import (
    RosterPublicationError,
    RosterPublicationResult,
    publish_verified_roster_baseline,
)


def _count(session: Session, model: type, *criteria: object) -> int:
    statement = select(func.count()).select_from(model)
    if criteria:
        statement = statement.where(*criteria)
    return session.scalar(statement) or 0


def test_roster_publication_populates_public_and_private_workspaces(
    session: Session,
) -> None:
    seed_verified_drafts(session)

    result = publish_verified_roster_baseline(session)
    session.commit()

    assert result == RosterPublicationResult(
        published_measures=8,
        published_memberships=14,
        published_roster_versions=14,
        published_source_revisions=3,
    )
    assert _count(session, Measure, Measure.is_public.is_(True)) == 8
    assert (
        _count(
            session,
            ProgramMembership,
            ProgramMembership.publication_state == PublicationState.PUBLISHED,
        )
        == 14
    )
    assert (
        _count(
            session,
            MeasureVersion,
            MeasureVersion.collection_type == CollectionType.PROGRAM_ROSTER,
            MeasureVersion.publication_state == PublicationState.PUBLISHED,
            MeasureVersion.verification_status == PublicVerificationStatus.VERIFIED,
        )
        == 14
    )
    assert (
        _count(
            session,
            MeasureVersion,
            MeasureVersion.collection_type != CollectionType.PROGRAM_ROSTER,
            MeasureVersion.publication_state == PublicationState.DRAFT,
        )
        == 32
    )
    assert (
        _count(
            session,
            SpecificationFieldCandidate,
            SpecificationFieldCandidate.publication_state == PublicationState.DRAFT,
        )
        == 352
    )

    public_page = list_measures(session, MeasureFilters(page_size=100))
    assert public_page.pagination.total_items == 8
    assert {item.measure_id for item in public_page.items} == {
        "001",
        "112",
        "113",
        "134",
        "236",
        "321",
        "479",
        "484",
    }
    assert all(
        item.description
        == (
            "Official program-year roster membership is verified; detailed "
            "specification fields remain under review."
        )
        for item in public_page.items
    )
    detail = get_measure(session, "001", 2025, 2026)
    assert detail is not None
    assert len(detail.versions) == 2
    assert all(
        [field.field.value for field in version.fields] == ["measure_set"]
        and len(version.fields[0].evidence) == 2
        for version in detail.versions
    )

    admin = review_summary(session)
    assert admin.private_measures == 8
    assert admin.draft_versions == 32
    assert admin.pending_candidates == 352
    assert admin.decided_candidates == 0
    assert admin.source_revisions == 16

    assert publish_verified_roster_baseline(session) == RosterPublicationResult(0, 0, 0, 0)


def test_verified_roster_seed_reaches_public_http_contract(session: Session) -> None:
    seed_verified_drafts(session)
    publish_verified_roster_baseline(session)
    session.commit()

    app = create_app()

    def override_database() -> Generator[Session]:
        yield session

    app.dependency_overrides[get_db] = override_database
    with TestClient(app) as client:
        years_response = client.get("/api/performance-years")
        list_response = client.get("/api/measures?from_year=2025&to_year=2026&page_size=100")
        detail_response = client.get("/api/measures/001?from_year=2025&to_year=2026")
        navigation_response = client.get(
            "/api/measures/001/navigation?from_year=2025&to_year=2026"
        )
    app.dependency_overrides.clear()

    assert years_response.status_code == 200
    assert years_response.json()["years"] == [2025, 2026]

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["pagination"]["total_items"] == 8
    assert {item["measure_id"] for item in payload["items"]} == {
        "001",
        "112",
        "113",
        "134",
        "236",
        "321",
        "479",
        "484",
    }

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert [version["performance_year"] for version in detail["versions"]] == [2025, 2026]
    for version in detail["versions"]:
        assert [field["field"] for field in version["fields"]] == ["measure_set"]
        evidence = version["fields"][0]["evidence"]
        assert len(evidence) == 2
        assert all(
            reference["official_url"].startswith("https://www.cms.gov/")
            for reference in evidence
        )

    assert navigation_response.status_code == 200
    assert navigation_response.json() == {
        "measure_id": "001",
        "position": 1,
        "total_items": 8,
        "previous_measure_id": None,
        "next_measure_id": "112",
    }


def test_roster_publication_refuses_incomplete_evidence(session: Session) -> None:
    seed_verified_drafts(session)
    evidence = session.scalar(
        select(EvidenceReference).where(
            EvidenceReference.evidence_id == "CMS-EVIDENCE-001-2025-1"
        )
    )
    assert evidence is not None
    session.delete(evidence)
    session.flush()
    session.expire_all()

    with pytest.raises(RosterPublicationError, match="Two distinct official CMS sources"):
        publish_verified_roster_baseline(session)

    assert _count(session, Measure, Measure.is_public.is_(True)) == 0
    assert (
        _count(
            session,
            SourceRevision,
            SourceRevision.publication_state == PublicationState.PUBLISHED,
        )
        == 0
    )


def test_preview_bootstrap_requires_explicit_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CMSQI_DEPLOYMENT_ENVIRONMENT", raising=False)
    monkeypatch.delenv("CMSQI_BOOTSTRAP_PREVIEW", raising=False)
    with pytest.raises(RuntimeError, match="outside CMSQI_DEPLOYMENT_ENVIRONMENT=preview"):
        _assert_preview_target()

    monkeypatch.setenv("CMSQI_DEPLOYMENT_ENVIRONMENT", "preview")
    with pytest.raises(RuntimeError, match="CMSQI_BOOTSTRAP_PREVIEW=true"):
        _assert_preview_target()

    monkeypatch.setenv("CMSQI_BOOTSTRAP_PREVIEW", "true")
    _assert_preview_target()


def test_preview_cleanup_removes_only_explicit_demo_fixtures(session: Session) -> None:
    session.add_all(
        [
            Measure(
                measure_id="DEMO-001",
                name="Fictional fixture",
                description="Synthetic test data.",
                is_public=True,
            ),
            Measure(
                measure_id="001",
                name="Source-backed measure",
                description="Retained record.",
                is_public=False,
            ),
            SourceDocument(
                source_id="DEMO-SOURCE-001",
                title="Fictional source",
                official_url="https://example.invalid/demo",
                mime_type="text/html",
            ),
            SourceDocument(
                source_id="CMS-SOURCE-001",
                title="Official source",
                official_url="https://www.cms.gov/example",
                mime_type="text/html",
            ),
        ]
    )
    session.flush()

    assert clear_demo_records_in_session(session) == (1, 1)
    assert set(session.scalars(select(Measure.measure_id))) == {"001"}
    assert set(session.scalars(select(SourceDocument.source_id))) == {"CMS-SOURCE-001"}
