"""Invalidate reviewable records that depend on an older source revision."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.domain import (
    CandidateReviewDecision,
    ComparisonEvidenceStatus,
    ComparisonReviewDecision,
    PublicationState,
)
from app.models import (
    EvidenceReference,
    MeasureComparison,
    MeasureComparisonEvidence,
    MeasureComparisonField,
    MeasureVersion,
    SourceRevision,
    SpecificationField,
    SpecificationFieldCandidate,
)
from app.services.comparison_publication import record_comparison_review
from app.services.reviews import record_candidate_review

SYSTEM_REVIEWER = "system:source-revision"
OUTDATED_EXTRACTION_STATUS = "candidate_outdated_newer_source_revision"


@dataclass(frozen=True)
class SourceStalenessResult:
    affected_versions: int
    pending_reviews_outdated: int
    completed_reviews_reopened: int
    comparisons_invalidated: int
    explanations_outdated: int


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _candidate_note(revision: SourceRevision) -> str:
    return (
        f"New source revision {revision.revision_id} was detected; "
        "the previous decision requires re-review."
    )


def _comparison_note(revision: SourceRevision) -> str:
    return (
        f"New source revision {revision.revision_id} invalidated comparison evidence; "
        "the comparison requires re-review."
    )


def mark_source_dependents_stale(
    session: Session,
    revision: SourceRevision,
    *,
    detected_at: datetime | None = None,
) -> SourceStalenessResult:
    """Fail closed for records citing older revisions of the same CMS source.

    Prior review and publication events remain intact. Draft decisions receive an
    append-only needs-revision event, while immutable published records retain their
    historical decision and are withheld by their stale evidence/version markers.
    """

    prior_revision_ids = tuple(
        session.scalars(
            select(SourceRevision.id).where(
                SourceRevision.source_document_id == revision.source_document_id,
                SourceRevision.revision_number < revision.revision_number,
            )
        )
    )
    if not prior_revision_ids:
        return SourceStalenessResult(0, 0, 0, 0, 0)

    stale_time = detected_at or revision.retrieved_at or datetime.now(UTC)
    candidate_note = _candidate_note(revision)
    comparison_note = _comparison_note(revision)

    versions = list(
        session.scalars(
            select(MeasureVersion)
            .where(
                or_(
                    MeasureVersion.id.in_(
                        select(SpecificationFieldCandidate.measure_version_id).where(
                            SpecificationFieldCandidate.source_revision_id.in_(
                                prior_revision_ids
                            )
                        )
                    ),
                    MeasureVersion.id.in_(
                        select(SpecificationField.measure_version_id)
                        .join(EvidenceReference)
                        .where(
                            EvidenceReference.source_revision_id.in_(
                                prior_revision_ids
                            )
                        )
                    ),
                )
            )
            .options(
                selectinload(MeasureVersion.field_candidates).selectinload(
                    SpecificationFieldCandidate.reviews
                )
            )
        ).unique()
    )

    pending_outdated = 0
    completed_reopened = 0
    for version in versions:
        version.newer_revision_detected = True
        if _as_utc(version.last_source_check_at) < _as_utc(stale_time):
            version.last_source_check_at = stale_time
        for candidate in version.field_candidates:
            if candidate.source_revision_id not in prior_revision_ids:
                continue
            if candidate.review_decision == CandidateReviewDecision.PENDING:
                if candidate.extraction_status != OUTDATED_EXTRACTION_STATUS:
                    candidate.extraction_status = OUTDATED_EXTRACTION_STATUS
                    pending_outdated += 1
                continue
            if candidate.publication_state != PublicationState.DRAFT:
                continue
            already_recorded = any(
                review.reviewer_name == SYSTEM_REVIEWER
                and review.reviewer_notes == candidate_note
                for review in candidate.reviews
            )
            if already_recorded:
                continue
            record_candidate_review(
                candidate,
                decision=CandidateReviewDecision.NEEDS_REVISION,
                reviewed_value=None,
                reviewer_name=SYSTEM_REVIEWER,
                reviewer_notes=candidate_note,
                reviewed_at=stale_time,
            )
            candidate.extraction_status = OUTDATED_EXTRACTION_STATUS
            completed_reopened += 1

    comparisons = list(
        session.scalars(
            select(MeasureComparison)
            .join(MeasureComparison.affected_fields)
            .join(MeasureComparisonField.evidence_links)
            .join(MeasureComparisonEvidence.evidence_reference)
            .where(EvidenceReference.source_revision_id.in_(prior_revision_ids))
            .options(
                selectinload(MeasureComparison.reviews),
                selectinload(MeasureComparison.impact_explanation_drafts),
            )
        ).unique()
    )

    explanations_outdated = 0
    for comparison in comparisons:
        comparison.evidence_status = ComparisonEvidenceStatus.INCOMPLETE
        if (
            comparison.publication_state == PublicationState.DRAFT
            and comparison.review_decision == ComparisonReviewDecision.APPROVE
            and not any(
                review.reviewer_name == SYSTEM_REVIEWER
                and review.reviewer_notes == comparison_note
                for review in comparison.reviews
            )
        ):
            record_comparison_review(
                comparison,
                decision=ComparisonReviewDecision.NEEDS_REVISION,
                reviewer_name=SYSTEM_REVIEWER,
                reviewer_notes=comparison_note,
                reviewed_at=stale_time,
            )
        for explanation in comparison.impact_explanation_drafts:
            if explanation.outdated_at is None:
                explanation.outdated_at = stale_time
                explanations_outdated += 1

    session.flush()
    return SourceStalenessResult(
        affected_versions=len(versions),
        pending_reviews_outdated=pending_outdated,
        completed_reviews_reopened=completed_reopened,
        comparisons_invalidated=len(comparisons),
        explanations_outdated=explanations_outdated,
    )
