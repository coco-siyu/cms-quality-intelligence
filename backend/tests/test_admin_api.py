from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import hash_admin_password
from app.commands.seed_verified import seed_verified_drafts
from app.config import Settings, get_settings
from app.database import get_db
from app.domain import (
    CandidateReviewDecision,
    ClarificationOutcome,
    PublicationState,
    PublicVerificationStatus,
    SourceExtractionStatus,
)
from app.main import create_app
from app.models import (
    AIClarificationProposal,
    EvidenceReference,
    MeasureVersion,
    SourceDocument,
    SourceExtraction,
    SourceRevision,
    SourceTextSegment,
    SpecificationField,
    SpecificationFieldCandidate,
    SpecificationFieldCandidateReview,
)
from app.services.ai_clarification import (
    ClarificationOutput,
    EvidenceAssessment,
    ProviderResult,
)
from app.services.publication import build_public_explanation_context


@pytest.fixture
def admin_client(session: Session) -> Generator[TestClient]:
    seed_verified_drafts(session)
    unrelated_source = SourceDocument(
        source_id="DEMO-UNRELATED",
        title="Unrelated fictional published source",
        official_url="https://example.invalid/unrelated",
        mime_type="text/html",
    )
    unrelated_source.revisions.append(
        SourceRevision(
            revision_id="DEMO-UNRELATED-R1",
            revision_number=1,
            content_hash="unrelated-demo-hash",
            publication_date=None,
            effective_date=None,
            retrieved_at=datetime(2026, 10, 21, tzinfo=UTC),
            last_source_check_at=datetime(2026, 10, 21, tzinfo=UTC),
            publication_state=PublicationState.PUBLISHED,
            verification_status=PublicVerificationStatus.VERIFIED,
        )
    )
    session.add(unrelated_source)
    session.commit()
    settings = Settings(
        admin_username="reviewer",
        admin_password_hash=hash_admin_password(
            "correct horse battery staple", salt=b"test-salt-16byte"
        ),
        admin_session_secret="test-session-secret-with-sufficient-entropy",
        admin_session_secure=False,
    )
    app = create_app()

    def override_database() -> Generator[Session]:
        yield session

    app.dependency_overrides[get_db] = override_database
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as test_client:
        yield test_client


def test_admin_session_reports_missing_configuration(client: TestClient) -> None:
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        admin_username=None,
        admin_password_hash=None,
        admin_session_secret=None,
    )
    status = client.get("/api/admin/session")
    login = client.post(
        "/api/admin/session", json={"username": "admin", "password": "anything"}
    )

    assert status.json() == {
        "configured": False,
        "authenticated": False,
        "username": None,
    }
    assert login.status_code == 503
    assert login.json()["code"] == "admin_authentication_not_configured"


def test_private_review_data_requires_a_valid_admin_session(
    admin_client: TestClient,
) -> None:
    unauthorized = admin_client.get("/api/admin/review-summary")
    invalid_login = admin_client.post(
        "/api/admin/session",
        json={"username": "reviewer", "password": "incorrect password"},
    )

    assert unauthorized.status_code == 401
    assert unauthorized.json()["code"] == "admin_authentication_required"
    assert invalid_login.status_code == 401
    assert invalid_login.json()["code"] == "invalid_admin_credentials"


def test_admin_can_inspect_private_staged_records_without_publishing_them(
    admin_client: TestClient,
) -> None:
    login = admin_client.post(
        "/api/admin/session",
        json={"username": "reviewer", "password": "correct horse battery staple"},
    )

    assert login.status_code == 200
    assert login.json() == {
        "configured": True,
        "authenticated": True,
        "username": "reviewer",
    }
    assert "HttpOnly" in login.headers["set-cookie"]
    assert "SameSite=lax" in login.headers["set-cookie"]

    summary = admin_client.get("/api/admin/review-summary")
    measures = admin_client.get("/api/admin/measures")
    detail = admin_client.get("/api/admin/measures/001")

    assert summary.json() == {
        "private_measures": 8,
        "draft_versions": 46,
        "pending_candidates": 352,
        "decided_candidates": 0,
        "source_revisions": 16,
        "newer_revision_flags": 0,
    }
    assert measures.json()["pagination"]["total_items"] == 8
    assert all(item["measure_id"] != "DEMO-001" for item in measures.json()["items"])
    assert detail.status_code == 200
    assert detail.json()["is_public"] is False
    assert detail.json()["memberships"][0]["publication_state"] == "draft"
    candidates = [
        candidate
        for version in detail.json()["versions"]
        for candidate in version["candidates"]
    ]
    assert candidates
    assert all(candidate["review_decision"] == "pending" for candidate in candidates)
    assert all("source_excerpt" in candidate for candidate in candidates)
    assert any(candidate["source_excerpt"] for candidate in candidates)
    assert candidates[0]["official_url"].startswith("https://")

    public = admin_client.get("/api/measures")
    assert public.status_code == 200
    assert public.json()["items"] == []


def test_logout_revokes_the_browser_session(admin_client: TestClient) -> None:
    admin_client.post(
        "/api/admin/session",
        json={"username": "reviewer", "password": "correct horse battery staple"},
    )
    assert admin_client.get("/api/admin/review-summary").status_code == 200

    logout = admin_client.delete("/api/admin/session")

    assert logout.json()["authenticated"] is False
    assert admin_client.get("/api/admin/review-summary").status_code == 401


def _login_admin(admin_client: TestClient) -> None:
    response = admin_client.post(
        "/api/admin/session",
        json={"username": "reviewer", "password": "correct horse battery staple"},
    )
    assert response.status_code == 200


def test_admin_source_registry_is_private_validated_and_reversible(
    admin_client: TestClient,
) -> None:
    assert admin_client.get("/api/admin/sources").status_code == 401
    _login_admin(admin_client)

    rejected = admin_client.post(
        "/api/admin/sources",
        headers={"X-CMSQI-Admin-Action": "source-registry"},
        json={
            "source_id": "CMS-UNSAFE",
            "title": "Unsafe source must be rejected",
            "official_url": "https://example.com/source",
            "source_format": "html",
        },
    )
    missing_action = admin_client.post(
        "/api/admin/sources",
        json={
            "source_id": "CMS-MISSING-ACTION",
            "title": "Missing action header",
            "official_url": "https://www.cms.gov/source",
            "source_format": "html",
        },
    )
    created = admin_client.post(
        "/api/admin/sources",
        headers={"X-CMSQI-Admin-Action": "source-registry"},
        json={
            "source_id": "CMS-TEST-REGISTRY",
            "title": "Official CMS registry test source",
            "official_url": "https://www.cms.gov/quality/source",
            "source_format": "html",
            "notes": "Private registry test only.",
        },
    )

    assert rejected.status_code == 422
    assert rejected.json()["code"] == "source_url_domain_forbidden"
    assert missing_action.status_code == 422
    assert created.status_code == 201
    assert created.json()["created_by"] == "reviewer"
    assert created.json()["revision_count"] == 0

    deactivated = admin_client.patch(
        "/api/admin/sources/CMS-TEST-REGISTRY",
        headers={"X-CMSQI-Admin-Action": "source-registry"},
        json={"is_active": False, "notes": None},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert deactivated.json()["deactivated_at"] is not None
    assert deactivated.json()["notes"] is None

    blocked_check = admin_client.post(
        "/api/admin/sources/CMS-TEST-REGISTRY/check",
        headers={"X-CMSQI-Admin-Action": "source-check"},
        json={"force": False},
    )
    assert blocked_check.status_code == 409
    assert blocked_check.json()["code"] == "source_inactive"

    reactivated = admin_client.patch(
        "/api/admin/sources/CMS-TEST-REGISTRY",
        headers={"X-CMSQI-Admin-Action": "source-registry"},
        json={"is_active": True},
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True
    assert reactivated.json()["deactivated_at"] is None


def test_admin_ingestion_run_requires_explicit_action_and_stays_private(
    admin_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.api.sources.execute_ingestion_run_by_id", lambda *_args, **_kwargs: None
    )
    assert admin_client.get("/api/admin/ingestion-runs").status_code == 401
    _login_admin(admin_client)

    missing_action = admin_client.post("/api/admin/ingestion-runs")
    invalid_action = admin_client.post(
        "/api/admin/ingestion-runs",
        headers={"X-CMSQI-Admin-Action": "source-check"},
    )
    created = admin_client.post(
        "/api/admin/ingestion-runs",
        headers={"X-CMSQI-Admin-Action": "check-for-updates"},
    )

    assert missing_action.status_code == 422
    assert invalid_action.status_code == 403
    assert created.status_code == 202
    assert created.json()["status"] == "running"
    assert created.json()["completed_count"] == 0
    listed = admin_client.get("/api/admin/ingestion-runs")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["run_id"] == created.json()["run_id"]
    assert admin_client.get("/api/measures").json()["items"] == []


def test_admin_can_normalize_an_extraction_without_publishing_candidates(
    admin_client: TestClient,
    session: Session,
) -> None:
    revision = session.scalar(
        select(SourceRevision)
        .join(SourceDocument)
        .where(SourceDocument.source_id == "CMS-ECQI-PY2026-CMS122V14")
    )
    assert revision is not None
    extraction = SourceExtraction(
        extraction_id="CMS-ECQI-PY2026-CMS122V14-TEST-X1",
        source_revision=revision,
        sequence=1,
        status=SourceExtractionStatus.EXTRACTED,
        page_count=None,
        extractor_version="stdlib-html-v1",
        forced=False,
        created_by="reviewer",
        segments=[
            SourceTextSegment(
                sequence=1,
                locator="HTML section: Document body",
                text="CMS eCQM ID CMS122v14. Performance Year 2026. eCQM.",
            ),
            SourceTextSegment(
                sequence=2,
                locator="HTML heading: Description",
                text="Description",
            ),
            SourceTextSegment(
                sequence=3,
                locator="HTML section: Description",
                text="Source-derived wording requiring human review.",
            ),
        ],
    )
    session.add(extraction)
    session.commit()
    _login_admin(admin_client)
    path = f"/api/admin/source-extractions/{extraction.extraction_id}/normalize"

    missing_header = admin_client.post(path)
    normalized = admin_client.post(
        path, headers={"X-CMSQI-Admin-Action": "normalize-source"}
    )

    assert missing_header.status_code == 422
    assert normalized.status_code == 200
    body = normalized.json()
    assert body["status"] == "normalized"
    assert body["candidates"][0]["identity_status"] == "matched"
    assert body["candidates"][0]["matched_version_id"] == "CMS-001-PY2026-ECQM"
    description = next(
        field
        for field in body["candidates"][0]["fields"]
        if field["field_name"] == "description"
    )
    assert description["staging_status"] == "existing"
    assert description["source_excerpt"] == (
        "Source-derived wording requiring human review."
    )
    assert admin_client.get("/api/measures").json()["items"] == []


def test_ai_clarification_requires_configuration_and_never_publishes(
    admin_client: TestClient,
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = session.scalar(
        select(SourceRevision)
        .join(SourceDocument)
        .where(SourceDocument.source_id == "CMS-ECQI-PY2026-CMS122V14")
    )
    assert revision is not None
    extraction = SourceExtraction(
        extraction_id="CMS-CLARIFICATION-PRIMARY-X1",
        source_revision=revision,
        sequence=1,
        status=SourceExtractionStatus.EXTRACTED,
        page_count=None,
        extractor_version="stdlib-html-v1",
        forced=False,
        created_by="reviewer",
        segments=[
            SourceTextSegment(
                sequence=1,
                locator="HTML section: Document body",
                text="CMS eCQM ID CMS122v14. Performance Year 2026. eCQM.",
            )
        ],
    )
    corroborating = SourceDocument(
        source_id="CMS-CLARIFICATION-CORROBORATION",
        title="Additional official CMS exclusions source",
        official_url="https://www.cms.gov/test/clarification-corroboration.html",
        mime_type="text/html",
    )
    corroborating_revision = SourceRevision(
        revision_id="CMS-CLARIFICATION-CORROBORATION-R1",
        revision_number=1,
        content_hash="clarification-corroboration-hash",
        retrieved_at=datetime(2026, 10, 26, tzinfo=UTC),
        last_source_check_at=datetime(2026, 10, 26, tzinfo=UTC),
    )
    corroborating_revision.extractions.append(
        SourceExtraction(
            extraction_id="CMS-CLARIFICATION-CORROBORATION-X1",
            sequence=1,
            status=SourceExtractionStatus.EXTRACTED,
            page_count=None,
            extractor_version="stdlib-html-v1",
            forced=False,
            created_by="reviewer",
            segments=[
                SourceTextSegment(
                    sequence=1,
                    locator="HTML section: Exclusions",
                    text=(
                        "CMS122v14 Exclusions: Patients receiving hospice care are excluded."
                    ),
                )
            ],
        )
    )
    corroborating.revisions.append(corroborating_revision)
    session.add_all([extraction, corroborating])
    session.commit()
    _login_admin(admin_client)
    normalized = admin_client.post(
        f"/api/admin/source-extractions/{extraction.extraction_id}/normalize",
        headers={"X-CMSQI-Admin-Action": "normalize-source"},
    )
    assert normalized.status_code == 200
    unresolved = next(
        field
        for field in normalized.json()["candidates"][0]["fields"]
        if field["field_name"] == "exclusions"
    )
    path = (
        f"/api/admin/normalized-fields/{unresolved['field_candidate_id']}/clarifications"
    )

    missing_action = admin_client.post(path)
    unconfigured = admin_client.post(
        path, headers={"X-CMSQI-Admin-Action": "clarify-source"}
    )
    assert missing_action.status_code == 422
    assert unconfigured.status_code == 503
    assert unconfigured.json()["code"] == "clarification_provider_not_configured"

    class ApiFakeProvider:
        provider_name = "test-provider"
        model_name = "test-model"

        def propose(self, *, field_name, identity_context, evidence):
            return ProviderResult(
                output=ClarificationOutput(
                    outcome="proposed",
                    proposed_value="Patients receiving hospice care are excluded.",
                    summary="One additional official source supports this wording.",
                    evidence_assessments=[
                        EvidenceAssessment(
                            evidence_id=item.evidence_id,
                            relation="supports",
                            explanation="The excerpt directly labels the exclusion.",
                        )
                        for item in evidence
                    ],
                ),
                response_id="test-response-id",
            )

    monkeypatch.setattr(
        "app.api.sources.provider_from_settings", lambda _settings: ApiFakeProvider()
    )
    clarified = admin_client.post(
        path, headers={"X-CMSQI-Admin-Action": "clarify-source"}
    )

    assert clarified.status_code == 200
    body = clarified.json()
    assert body["outcome"] == ClarificationOutcome.PROPOSED
    assert body["proposed_value"] == "Patients receiving hospice care are excluded."
    assert body["evidence"][0]["source_id"] == "CMS-CLARIFICATION-CORROBORATION"
    assert body["evidence"][0]["official_url"].startswith("https://www.cms.gov/")
    assert session.query(AIClarificationProposal).count() == 1
    assert admin_client.get("/api/measures").json()["items"] == []


def _first_review_item(admin_client: TestClient) -> dict[str, object]:
    detail = admin_client.get("/api/admin/measures/001")
    assert detail.status_code == 200
    return detail.json()["versions"][0]["candidates"][0]


def _review_item(
    admin_client: TestClient,
    *,
    field_name: str,
    has_excerpt: bool,
) -> tuple[dict[str, object], dict[str, object]]:
    detail = admin_client.get("/api/admin/measures/001")
    assert detail.status_code == 200
    for version in detail.json()["versions"]:
        for candidate in version["candidates"]:
            if candidate["field_name"] == field_name and bool(
                candidate["source_excerpt"]
            ) == has_excerpt:
                return version, candidate
    raise AssertionError(f"No {field_name} candidate matched excerpt={has_excerpt}")


def test_admin_review_decisions_are_authenticated_audited_and_not_published(
    admin_client: TestClient,
    session: Session,
) -> None:
    _login_admin(admin_client)
    review_item = _first_review_item(admin_client)
    review_item_id = review_item["review_item_id"]

    approved = admin_client.patch(
        f"/api/admin/review-items/{review_item_id}",
        headers={"X-CMSQI-Admin-Action": "review-decision"},
        json={
            "decision": "approve",
            "reviewed_value": review_item["candidate_value"],
            "reviewer_notes": "Checked against the linked official source.",
        },
    )

    assert approved.status_code == 200
    approved_body = approved.json()
    assert approved_body["review_decision"] == "approve"
    assert approved_body["reviewer_name"] == "reviewer"
    assert approved_body["review_history"] == [
        {
            "decision": "approve",
            "reviewed_value": review_item["candidate_value"],
            "reviewer_name": "reviewer",
            "reviewed_at": approved_body["reviewed_at"],
            "reviewer_notes": "Checked against the linked official source.",
        }
    ]

    revised = admin_client.patch(
        f"/api/admin/review-items/{review_item_id}",
        headers={"X-CMSQI-Admin-Action": "review-decision"},
        json={
            "decision": "needs_revision",
            "reviewed_value": None,
            "reviewer_notes": "The locator needs a more precise page reference.",
        },
    )

    assert revised.status_code == 200
    revised_body = revised.json()
    assert revised_body["review_decision"] == "needs_revision"
    assert revised_body["reviewed_value"] is None
    assert len(revised_body["review_history"]) == 2
    assert [event["decision"] for event in revised_body["review_history"]] == [
        "approve",
        "needs_revision",
    ]

    candidate = session.query(SpecificationFieldCandidate).filter_by(
        review_item_id=review_item_id
    ).one()
    assert candidate.review_decision == CandidateReviewDecision.NEEDS_REVISION
    assert session.query(SpecificationFieldCandidateReview).filter_by(
        specification_field_candidate_id=candidate.id
    ).count() == 2

    public = admin_client.get("/api/measures")
    assert public.status_code == 200
    assert public.json()["items"] == []


def test_admin_review_mutation_enforces_action_header_and_decision_rules(
    admin_client: TestClient,
) -> None:
    _login_admin(admin_client)
    review_item = _first_review_item(admin_client)
    path = f"/api/admin/review-items/{review_item['review_item_id']}"

    missing_header = admin_client.patch(
        path,
        json={"decision": "approve", "reviewed_value": review_item["candidate_value"]},
    )
    invalid_header = admin_client.patch(
        path,
        headers={"X-CMSQI-Admin-Action": "publish"},
        json={"decision": "approve", "reviewed_value": review_item["candidate_value"]},
    )
    missing_value = admin_client.patch(
        path,
        headers={"X-CMSQI-Admin-Action": "review-decision"},
        json={"decision": "approve"},
    )
    missing_notes = admin_client.patch(
        path,
        headers={"X-CMSQI-Admin-Action": "review-decision"},
        json={"decision": "not_applicable"},
    )

    assert missing_header.status_code == 422
    assert invalid_header.status_code == 403
    assert invalid_header.json()["code"] == "invalid_admin_action_header"
    assert missing_value.status_code == 422
    assert missing_value.json()["code"] == "review_validation_error"
    assert missing_notes.status_code == 422
    assert missing_notes.json()["code"] == "review_validation_error"


def test_review_mutation_requires_an_authenticated_admin(
    admin_client: TestClient,
) -> None:
    response = admin_client.patch(
        "/api/admin/review-items/unknown",
        headers={"X-CMSQI-Admin-Action": "review-decision"},
        json={"decision": "not_applicable", "reviewer_notes": "Not applicable."},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "admin_authentication_required"


def test_admin_can_publish_one_evidenced_field_without_exposing_sibling_drafts(
    admin_client: TestClient,
    session: Session,
) -> None:
    _login_admin(admin_client)
    version, candidate = _review_item(
        admin_client, field_name="description", has_excerpt=True
    )
    review_item_id = str(candidate["review_item_id"])

    premature = admin_client.post(
        f"/api/admin/review-items/{review_item_id}/publish",
        headers={"X-CMSQI-Admin-Action": "publish-field"},
    )
    assert premature.status_code == 409
    assert premature.json()["code"] == "field_publication_not_approved"

    approved_value = "Reviewer-approved definition supported by the cited CMS excerpt."
    approved = admin_client.patch(
        f"/api/admin/review-items/{review_item_id}",
        headers={"X-CMSQI-Admin-Action": "review-decision"},
        json={
            "decision": "approve",
            "reviewed_value": approved_value,
            "reviewer_notes": "Confirmed for the cited year and collection type.",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["publication_eligibility"] == "eligible"

    invalid_header = admin_client.post(
        f"/api/admin/review-items/{review_item_id}/publish",
        headers={"X-CMSQI-Admin-Action": "review-decision"},
    )
    assert invalid_header.status_code == 403

    published = admin_client.post(
        f"/api/admin/review-items/{review_item_id}/publish",
        headers={"X-CMSQI-Admin-Action": "publish-field"},
    )
    assert published.status_code == 200
    publication = published.json()
    assert publication["publication_state"] == "published"
    assert publication["publication_eligibility"] == "published"
    assert publication["published_field"] == "definition"
    assert publication["published_by"] == "reviewer"

    public = admin_client.get("/api/measures/001")
    assert public.status_code == 200
    payload = public.json()
    assert payload["description"] == approved_value
    assert len(payload["versions"]) == 1
    assert payload["versions"][0]["version_id"] == version["version_id"]
    assert len(payload["versions"][0]["fields"]) == 1
    public_field = payload["versions"][0]["fields"][0]
    assert public_field["field"] == "definition"
    assert public_field["availability"] == "available"
    assert public_field["value"] == approved_value
    assert len(public_field["evidence"]) == 1
    public_evidence = public_field["evidence"][0]
    assert public_evidence["evidence_id"].startswith("CMS-PUBLISHED-FIELD-")
    assert public_evidence["source_revision_id"] == candidate["source_revision_id"]
    assert public_evidence["document_title"] == candidate["source_title"]
    assert public_evidence["official_url"] == candidate["official_url"]
    assert public_evidence["locator"] == candidate["evidence_locator"]
    assert public_evidence["excerpt"] == candidate["source_excerpt"]
    sibling = next(
        item
        for item in version["candidates"]
        if item["review_item_id"] != review_item_id
    )
    assert str(sibling["candidate_value"]) not in public.text

    still_reviewable = admin_client.get("/api/admin/measures/001")
    assert still_reviewable.status_code == 200
    assert still_reviewable.json()["is_public"] is True
    assert any(
        item["review_decision"] == "pending"
        for staged_version in still_reviewable.json()["versions"]
        for item in staged_version["candidates"]
    )

    repeated = admin_client.post(
        f"/api/admin/review-items/{review_item_id}/publish",
        headers={"X-CMSQI-Admin-Action": "publish-field"},
    )
    assert repeated.status_code == 200
    assert session.query(SpecificationField).count() == 15
    assert session.query(EvidenceReference).count() == 29
    assert seed_verified_drafts(session) == (0, 0, 0, 0)
    session.commit()
    assert admin_client.get("/api/measures/001").status_code == 200

    locked = admin_client.patch(
        f"/api/admin/review-items/{review_item_id}",
        headers={"X-CMSQI-Admin-Action": "review-decision"},
        json={"decision": "needs_revision", "reviewer_notes": "Try to change public data."},
    )
    assert locked.status_code == 409
    assert locked.json()["code"] == "published_review_locked"

    published_version = session.scalar(
        select(MeasureVersion)
        .where(MeasureVersion.version_id == version["version_id"])
        .options(
            selectinload(MeasureVersion.fields)
            .selectinload(SpecificationField.evidence)
            .selectinload(EvidenceReference.source_revision)
        )
    )
    assert published_version is not None
    context = build_public_explanation_context(published_version)
    assert [(item.field.value, item.value) for item in context] == [
        ("definition", approved_value)
    ]


def test_publication_rejects_approved_fields_without_a_literal_excerpt(
    admin_client: TestClient,
) -> None:
    _login_admin(admin_client)
    _version, candidate = _review_item(
        admin_client, field_name="exclusions", has_excerpt=False
    )
    review_item_id = str(candidate["review_item_id"])
    approved = admin_client.patch(
        f"/api/admin/review-items/{review_item_id}",
        headers={"X-CMSQI-Admin-Action": "review-decision"},
        json={
            "decision": "approve",
            "reviewed_value": "A reviewer-entered value that still lacks a stored excerpt.",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["publication_eligibility"] == "missing_source_excerpt"

    response = admin_client.post(
        f"/api/admin/review-items/{review_item_id}/publish",
        headers={"X-CMSQI-Admin-Action": "publish-field"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "field_publication_missing_source_excerpt"
    assert admin_client.get("/api/measures").json()["items"] == []


def test_partial_publication_uses_a_neutral_summary_until_definition_is_public(
    admin_client: TestClient,
) -> None:
    _login_admin(admin_client)
    _version, candidate = _review_item(
        admin_client, field_name="population_or_denominator", has_excerpt=True
    )
    review_item_id = str(candidate["review_item_id"])
    approved_value = "Reviewer-approved denominator for the test transaction."
    assert admin_client.patch(
        f"/api/admin/review-items/{review_item_id}",
        headers={"X-CMSQI-Admin-Action": "review-decision"},
        json={"decision": "approve", "reviewed_value": approved_value},
    ).status_code == 200
    assert admin_client.post(
        f"/api/admin/review-items/{review_item_id}/publish",
        headers={"X-CMSQI-Admin-Action": "publish-field"},
    ).status_code == 200

    public = admin_client.get("/api/measures/001")
    assert public.status_code == 200
    assert public.json()["description"] == (
        "Verified specification fields are partially available; unresolved fields are withheld."
    )
    assert public.json()["versions"][0]["fields"][0]["field"] == "denominator"
    assert public.json()["versions"][0]["fields"][0]["value"] == approved_value
    private_description = "Percentage of patients 18-75 years of age with diabetes"
    assert private_description not in public.text
    assert admin_client.get(
        "/api/measures", params={"q": private_description}
    ).json()["items"] == []


def test_publication_rejects_fields_without_an_exact_public_contract_mapping(
    admin_client: TestClient,
) -> None:
    _login_admin(admin_client)
    _version, candidate = _review_item(
        admin_client, field_name="measure_type", has_excerpt=True
    )
    review_item_id = str(candidate["review_item_id"])
    approved = admin_client.patch(
        f"/api/admin/review-items/{review_item_id}",
        headers={"X-CMSQI-Admin-Action": "review-decision"},
        json={"decision": "approve", "reviewed_value": candidate["candidate_value"]},
    )
    assert approved.status_code == 200
    assert approved.json()["publication_eligibility"] == "unsupported_field"

    response = admin_client.post(
        f"/api/admin/review-items/{review_item_id}/publish",
        headers={"X-CMSQI-Admin-Action": "publish-field"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "field_publication_unsupported_field"
    assert admin_client.get("/api/measures").json()["items"] == []
