"""Audited review and guarded publication for deterministic comparisons."""

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.domain import (
    ChangeStatus,
    ComparisonEvidenceStatus,
    ComparisonPublicationEligibility,
    ComparisonReviewDecision,
    PublicationState,
)
from app.models import MeasureComparison, MeasureComparisonReview
from app.services.comparison_evidence import refresh_comparison_evidence_status


class ComparisonPublicationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def comparison_publication_eligibility(
    comparison: MeasureComparison,
) -> ComparisonPublicationEligibility:
    refresh_comparison_evidence_status(comparison)
    if comparison.publication_state == PublicationState.PUBLISHED:
        return ComparisonPublicationEligibility.PUBLISHED
    if comparison.review_decision != ComparisonReviewDecision.APPROVE:
        return ComparisonPublicationEligibility.NOT_APPROVED
    if comparison.evidence_status != ComparisonEvidenceStatus.VERIFIED:
        return ComparisonPublicationEligibility.INCOMPLETE_EVIDENCE
    if comparison.status == ChangeStatus.UNKNOWN:
        return ComparisonPublicationEligibility.UNKNOWN_STATUS
    if not comparison.measure.is_public:
        return ComparisonPublicationEligibility.PRIVATE_MEASURE
    return ComparisonPublicationEligibility.ELIGIBLE


def comparison_publication_blocker(
    eligibility: ComparisonPublicationEligibility,
) -> str | None:
    return {
        ComparisonPublicationEligibility.NOT_APPROVED: (
            "Review and approve this evidence-backed comparison before publication."
        ),
        ComparisonPublicationEligibility.INCOMPLETE_EVIDENCE: (
            "Both year values require current, verified source excerpts and locators."
        ),
        ComparisonPublicationEligibility.UNKNOWN_STATUS: (
            "An unresolved comparison cannot be published as a confirmed finding."
        ),
        ComparisonPublicationEligibility.PRIVATE_MEASURE: (
            "The measure must have an approved public record before its comparison can publish."
        ),
    }.get(eligibility)


def _review_event_key(
    comparison: MeasureComparison,
    decision: ComparisonReviewDecision,
    reviewer_name: str,
    reviewed_at: datetime,
    reviewer_notes: str | None,
) -> str:
    payload = json.dumps(
        {
            "comparison_id": comparison.id,
            "decision": decision.value,
            "reviewed_at": reviewed_at.isoformat(),
            "reviewer_name": reviewer_name,
            "reviewer_notes": reviewer_notes,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_comparison_review(
    comparison: MeasureComparison,
    *,
    decision: ComparisonReviewDecision,
    reviewer_name: str,
    reviewer_notes: str | None,
    reviewed_at: datetime | None = None,
) -> MeasureComparisonReview:
    if comparison.publication_state == PublicationState.PUBLISHED:
        raise ComparisonPublicationError(
            "published_comparison_locked",
            "A published comparison is immutable; create a new reviewed revision instead.",
        )
    if decision == ComparisonReviewDecision.PENDING:
        raise ComparisonPublicationError(
            "comparison_review_invalid",
            "A recorded comparison review must contain a final decision.",
        )
    if decision == ComparisonReviewDecision.NEEDS_REVISION and not reviewer_notes:
        raise ComparisonPublicationError(
            "comparison_review_notes_required",
            "Reviewer notes are required when a comparison needs revision.",
        )
    refresh_comparison_evidence_status(comparison)
    if decision == ComparisonReviewDecision.APPROVE:
        if comparison.evidence_status != ComparisonEvidenceStatus.VERIFIED:
            raise ComparisonPublicationError(
                "comparison_review_incomplete_evidence",
                "Approval requires verified evidence for both performance years.",
            )
        if comparison.status == ChangeStatus.UNKNOWN:
            raise ComparisonPublicationError(
                "comparison_review_unknown_status",
                "Resolve unknown comparison fields before approval.",
            )

    decision_time = reviewed_at or datetime.now(UTC)
    event = MeasureComparisonReview(
        event_key=_review_event_key(
            comparison,
            decision,
            reviewer_name,
            decision_time,
            reviewer_notes,
        ),
        decision=decision,
        reviewer_name=reviewer_name,
        reviewed_at=decision_time,
        reviewer_notes=reviewer_notes,
    )
    comparison.review_decision = decision
    comparison.reviewed_at = decision_time
    comparison.reviewer_name = reviewer_name
    comparison.reviewer_notes = reviewer_notes
    comparison.reviews.append(event)
    return event


def publish_approved_comparison(
    session: Session,
    comparison: MeasureComparison,
    *,
    publisher_name: str,
    published_at: datetime | None = None,
) -> MeasureComparison:
    eligibility = comparison_publication_eligibility(comparison)
    if eligibility == ComparisonPublicationEligibility.PUBLISHED:
        return comparison
    if eligibility != ComparisonPublicationEligibility.ELIGIBLE:
        raise ComparisonPublicationError(
            f"comparison_publication_{eligibility.value}",
            comparison_publication_blocker(eligibility)
            or "The comparison is not eligible for publication.",
        )
    publication_time = published_at or datetime.now(UTC)
    comparison.publication_state = PublicationState.PUBLISHED
    comparison.published_at = publication_time
    comparison.published_by = publisher_name
    session.flush()
    return comparison
