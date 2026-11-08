from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import (
    CandidateReviewDecision,
    ComparisonEvidenceStatus,
    ComparisonReviewDecision,
    ImpactExplanationReviewDecision,
    PublicationState,
    PublicVerificationStatus,
)
from app.models import (
    ImpactExplanationCitation,
    ImpactExplanationDraft,
    MeasureComparison,
    MeasureVersion,
    SourceDocument,
    SourceRevision,
    SpecificationFieldCandidate,
)
from app.services.comparison_publication import record_comparison_review
from app.services.reviews import record_candidate_review
from app.services.source_staleness import (
    OUTDATED_EXTRACTION_STATUS,
    SYSTEM_REVIEWER,
    mark_source_dependents_stale,
)


def _new_revision(
    document: SourceDocument,
    *,
    detected_at: datetime,
) -> SourceRevision:
    revision = SourceRevision(
        revision_id=f"{document.source_id}-R2-new-content",
        revision_number=2,
        content_hash="new-source-content-hash",
        publication_date=None,
        effective_date=None,
        retrieved_at=detected_at,
        last_source_check_at=detected_at,
        publication_state=PublicationState.DRAFT,
        verification_status=PublicVerificationStatus.PARTIALLY_VERIFIED,
    )
    document.revisions.append(revision)
    return revision


def test_new_revision_reopens_draft_reviews_and_outdates_explanations(
    seeded_session: Session,
    client: TestClient,
) -> None:
    comparison = seeded_session.scalar(select(MeasureComparison))
    document = seeded_session.scalar(select(SourceDocument))
    version = seeded_session.scalar(
        select(MeasureVersion).where(MeasureVersion.performance_year == 2025)
    )
    assert comparison is not None
    assert document is not None
    assert version is not None

    old_revision = document.revisions[0]
    candidate = SpecificationFieldCandidate(
        review_item_id="STALE-REVIEWED-CANDIDATE",
        measure_version=version,
        field_name="numerator_or_outcome",
        candidate_value="Prior candidate value",
        source_excerpt="Prior official excerpt",
        extraction_status="candidate_extracted_needs_sme_review",
        source_revision=old_revision,
        evidence_locator="HTML section: prior",
        publication_state=PublicationState.DRAFT,
    )
    record_candidate_review(
        candidate,
        decision=CandidateReviewDecision.APPROVE,
        reviewed_value="Prior reviewed value",
        reviewer_name="human-reviewer",
        reviewer_notes=None,
        reviewed_at=datetime(2026, 11, 6, 12, tzinfo=UTC),
    )
    comparison_evidence = comparison.affected_fields[0].evidence_links[0]
    explanation = ImpactExplanationDraft(
        draft_id="STALE-IMPACT-DRAFT",
        comparison=comparison,
        provider="stored",
        model="stored-test-model",
        prompt_version="test-v1",
        input_digest="a" * 64,
        output_payload={},
        review_decision=ImpactExplanationReviewDecision.APPROVE,
        approved_output_payload={},
        reviewed_at=datetime(2026, 11, 6, 13, tzinfo=UTC),
        reviewed_by="human-reviewer",
        publication_state=PublicationState.PUBLISHED,
        published_at=datetime(2026, 11, 6, 14, tzinfo=UTC),
        published_by="human-reviewer",
        created_by="generator",
        citations=[
            ImpactExplanationCitation(comparison_evidence=comparison_evidence)
        ],
    )
    seeded_session.add_all([candidate, explanation])
    detected_at = datetime(2026, 11, 8, 9, tzinfo=UTC)
    revision = _new_revision(document, detected_at=detected_at)
    seeded_session.flush()

    result = mark_source_dependents_stale(
        seeded_session,
        revision,
        detected_at=detected_at,
    )
    seeded_session.commit()

    assert result.affected_versions == 4
    assert result.completed_reviews_reopened == 1
    assert result.comparisons_invalidated == 1
    assert result.explanations_outdated == 1
    assert version.newer_revision_detected is True
    assert candidate.review_decision == CandidateReviewDecision.NEEDS_REVISION
    assert candidate.reviewed_value is None
    assert candidate.extraction_status == OUTDATED_EXTRACTION_STATUS
    assert [event.decision for event in candidate.reviews] == [
        CandidateReviewDecision.APPROVE,
        CandidateReviewDecision.NEEDS_REVISION,
    ]
    assert candidate.reviews[-1].reviewer_name == SYSTEM_REVIEWER
    assert revision.revision_id in (candidate.reviews[-1].reviewer_notes or "")
    assert comparison.review_decision == ComparisonReviewDecision.APPROVE
    assert comparison.evidence_status == ComparisonEvidenceStatus.INCOMPLETE
    assert explanation.outdated_at == detected_at

    parameters = {
        "program": "Fictional Quality Program",
        "collection_type": "program_roster",
        "from_year": 2025,
        "to_year": 2026,
    }
    assert client.get("/api/changes/DEMO-001", params=parameters).status_code == 404
    assert (
        client.get(
            "/api/changes/DEMO-001/impact-explanation",
            params=parameters,
        ).status_code
        == 404
    )


def test_new_revision_flags_pending_review_without_inventing_a_decision(
    seeded_session: Session,
) -> None:
    document = seeded_session.scalar(select(SourceDocument))
    comparison = seeded_session.scalar(select(MeasureComparison))
    version = seeded_session.scalar(
        select(MeasureVersion).where(MeasureVersion.performance_year == 2026)
    )
    assert document is not None
    assert comparison is not None
    assert version is not None

    comparison.publication_state = PublicationState.DRAFT
    comparison.published_at = None
    comparison.published_by = None
    record_comparison_review(
        comparison,
        decision=ComparisonReviewDecision.APPROVE,
        reviewer_name="human-reviewer",
        reviewer_notes=None,
        reviewed_at=datetime(2026, 11, 7, 12, tzinfo=UTC),
    )

    candidate = SpecificationFieldCandidate(
        review_item_id="STALE-PENDING-CANDIDATE",
        measure_version=version,
        field_name="numerator_or_outcome",
        candidate_value="Pending candidate value",
        source_excerpt="Prior official excerpt",
        extraction_status="candidate_extracted_needs_sme_review",
        source_revision=document.revisions[0],
        evidence_locator="HTML section: prior",
        review_decision=CandidateReviewDecision.PENDING,
        publication_state=PublicationState.DRAFT,
    )
    seeded_session.add(candidate)
    detected_at = datetime(2026, 11, 8, 10, tzinfo=UTC)
    revision = _new_revision(document, detected_at=detected_at)
    seeded_session.flush()

    first = mark_source_dependents_stale(
        seeded_session,
        revision,
        detected_at=detected_at,
    )
    second = mark_source_dependents_stale(
        seeded_session,
        revision,
        detected_at=detected_at,
    )

    assert first.pending_reviews_outdated == 1
    assert second.pending_reviews_outdated == 0
    assert candidate.review_decision == CandidateReviewDecision.PENDING
    assert candidate.reviewed_at is None
    assert candidate.reviews == []
    assert candidate.extraction_status == OUTDATED_EXTRACTION_STATUS
    assert version.newer_revision_detected is True
    assert comparison.review_decision == ComparisonReviewDecision.NEEDS_REVISION
    assert [event.decision for event in comparison.reviews] == [
        ComparisonReviewDecision.APPROVE,
        ComparisonReviewDecision.NEEDS_REVISION,
    ]
    assert comparison.reviews[-1].reviewer_name == SYSTEM_REVIEWER
