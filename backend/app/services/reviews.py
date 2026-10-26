import hashlib
import json
from datetime import UTC, datetime

from app.domain import CandidateReviewDecision
from app.models import SpecificationFieldCandidate, SpecificationFieldCandidateReview


def review_event_key(
    review_item_id: str,
    decision: CandidateReviewDecision,
    reviewed_value: str | None,
    reviewer_name: str,
    reviewed_at: datetime,
    reviewer_notes: str | None,
) -> str:
    payload = json.dumps(
        {
            "decision": decision.value,
            "review_item_id": review_item_id,
            "reviewed_at": reviewed_at.isoformat(),
            "reviewed_value": reviewed_value,
            "reviewer_name": reviewer_name,
            "reviewer_notes": reviewer_notes,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_candidate_review(
    candidate: SpecificationFieldCandidate,
    *,
    decision: CandidateReviewDecision,
    reviewed_value: str | None,
    reviewer_name: str,
    reviewer_notes: str | None,
    reviewed_at: datetime | None = None,
) -> SpecificationFieldCandidateReview:
    decision_time = reviewed_at or datetime.now(UTC)
    event = SpecificationFieldCandidateReview(
        event_key=review_event_key(
            candidate.review_item_id,
            decision,
            reviewed_value,
            reviewer_name,
            decision_time,
            reviewer_notes,
        ),
        decision=decision,
        reviewed_value=reviewed_value,
        reviewer_name=reviewer_name,
        reviewed_at=decision_time,
        reviewer_notes=reviewer_notes,
    )
    candidate.review_decision = decision
    candidate.reviewed_value = reviewed_value
    candidate.reviewer_name = reviewer_name
    candidate.reviewed_at = decision_time
    candidate.reviewer_notes = reviewer_notes
    candidate.reviews.append(event)
    return event
