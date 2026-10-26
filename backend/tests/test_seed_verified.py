from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.commands.seed_verified import seed_verified_drafts
from app.domain import (
    AffectedField,
    CandidateReviewDecision,
    CollectionType,
    PublicationState,
    PublicVerificationStatus,
)
from app.models import (
    EvidenceReference,
    Measure,
    MeasureVersion,
    ProgramMembership,
    SourceDocument,
    SourceRevision,
    SpecificationField,
    SpecificationFieldCandidate,
)


def _count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_verified_seed_is_idempotent_and_non_public(session: Session) -> None:
    assert seed_verified_drafts(session) == (8, 14, 32, 352)
    session.commit()
    backfill_candidate = session.scalar(
        select(SpecificationFieldCandidate).where(
            SpecificationFieldCandidate.source_excerpt.is_not(None)
        )
    )
    assert backfill_candidate is not None
    expected_excerpt = backfill_candidate.source_excerpt
    backfill_candidate.source_excerpt = None
    session.commit()
    assert seed_verified_drafts(session) == (0, 0, 0, 0)
    session.commit()
    session.refresh(backfill_candidate)
    assert backfill_candidate.source_excerpt == expected_excerpt

    assert _count(session, Measure) == 8
    assert _count(session, ProgramMembership) == 14
    assert _count(session, MeasureVersion) == 46
    assert _count(session, SpecificationField) == 14
    assert _count(session, SpecificationFieldCandidate) == 352
    assert _count(session, EvidenceReference) == 28
    assert _count(session, SourceDocument) == 16
    assert _count(session, SourceRevision) == 16

    assert all(measure.is_public is False for measure in session.scalars(select(Measure)))
    assert all(
        membership.publication_state == PublicationState.DRAFT
        for membership in session.scalars(select(ProgramMembership))
    )
    versions = list(session.scalars(select(MeasureVersion)))
    assert all(version.publication_state == PublicationState.DRAFT for version in versions)
    assert all(
        version.verification_status == PublicVerificationStatus.PARTIALLY_VERIFIED
        for version in versions
    )
    assert all(
        field.field == AffectedField.MEASURE_SET
        for field in session.scalars(select(SpecificationField))
    )
    roster_versions = [
        version
        for version in versions
        if version.collection_type == CollectionType.PROGRAM_ROSTER
    ]
    variant_versions = [
        version
        for version in versions
        if version.collection_type != CollectionType.PROGRAM_ROSTER
    ]
    assert len(roster_versions) == 14
    assert len(variant_versions) == 32
    assert all(version.specification_identifier for version in variant_versions)
    candidates = list(session.scalars(select(SpecificationFieldCandidate)))
    assert all(
        candidate.review_decision == CandidateReviewDecision.PENDING
        and candidate.reviewed_at is None
        for candidate in candidates
    )
    assert sum(candidate.source_excerpt is not None for candidate in candidates) == 182
    assert all(
        candidate.source_excerpt is None
        for candidate in candidates
        if candidate.extraction_status
        in {
            "manual_extraction_or_policy_review_required",
            "not_applicable_candidate_needs_sme_confirmation",
        }
    )
