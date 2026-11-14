"""Formal review completion and reopening transitions."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domain import ChecklistTaskStatus, MeasureReviewStatus, ReviewEventType
from app.models import MeasureReview, ReviewSignOff
from app.services.review_checklists import append_review_event


class ReviewLifecycleError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _now() -> datetime:
    return datetime.now(UTC)


def _review(session: Session, review_id: str) -> MeasureReview:
    review = session.scalar(
        select(MeasureReview)
        .where(MeasureReview.review_id == review_id)
        .options(
            selectinload(MeasureReview.checklist_items),
            selectinload(MeasureReview.signoffs),
        )
    )
    if review is None:
        raise ReviewLifecycleError(
            "review_not_found", f"Review '{review_id}' was not found."
        )
    return review


def sign_off_review(
    session: Session,
    *,
    review_id: str,
    actor: str,
    note: str | None,
) -> MeasureReview:
    review = _review(session, review_id)
    if review.status == MeasureReviewStatus.COMPLETED:
        raise ReviewLifecycleError(
            "review_already_completed", "The review is already signed off."
        )

    open_items = [
        item
        for item in review.checklist_items
        if item.status == ChecklistTaskStatus.OPEN
    ]
    if open_items:
        raise ReviewLifecycleError(
            "review_has_open_tasks",
            f"Resolve all accepted tasks before sign-off; {len(open_items)} remain open.",
        )

    signed_at = _now()
    sequence = (
        session.scalar(
            select(func.max(ReviewSignOff.sequence)).where(
                ReviewSignOff.review_id == review.id
            )
        )
        or 0
    ) + 1
    resolved_count = len(review.checklist_items)
    signoff = ReviewSignOff(
        signoff_id=f"CMS-SIGNOFF-{uuid4().hex}",
        review=review,
        sequence=sequence,
        accepted_task_count=resolved_count,
        resolved_task_count=resolved_count,
        note=note,
        signed_at=signed_at,
        signed_by=actor,
    )
    session.add(signoff)
    session.flush()
    review.status = MeasureReviewStatus.COMPLETED
    review.completed_at = signed_at
    review.completed_by = actor
    append_review_event(
        session,
        review,
        event_type=ReviewEventType.SIGNED_OFF,
        subject_type="signoff",
        subject_id=signoff.signoff_id,
        actor=actor,
        note=note,
        payload={
            "sequence": sequence,
            "accepted_task_count": resolved_count,
            "resolved_task_count": resolved_count,
        },
    )
    return review


def reopen_review(
    session: Session,
    *,
    review_id: str,
    actor: str,
    note: str | None,
) -> MeasureReview:
    review = _review(session, review_id)
    if review.status != MeasureReviewStatus.COMPLETED:
        raise ReviewLifecycleError(
            "review_not_completed", "Only a completed review can be reopened."
        )
    if not review.signoffs:
        raise ReviewLifecycleError(
            "review_signoff_missing",
            "The completed review has no sign-off snapshot to reopen.",
        )
    prior_signoff = max(review.signoffs, key=lambda item: item.sequence)
    review.status = MeasureReviewStatus.REOPENED
    review.completed_at = None
    review.completed_by = None
    append_review_event(
        session,
        review,
        event_type=ReviewEventType.REOPENED,
        subject_type="signoff",
        subject_id=prior_signoff.signoff_id,
        actor=actor,
        note=note,
        payload={"prior_signoff_id": prior_signoff.signoff_id},
    )
    session.flush()
    return review


def require_re_review_for_new_source(
    session: Session,
    review: MeasureReview,
    *,
    actor: str,
    note: str,
) -> None:
    if review.status != MeasureReviewStatus.COMPLETED:
        return
    prior_signoff = (
        max(review.signoffs, key=lambda item: item.sequence)
        if review.signoffs
        else None
    )
    review.status = MeasureReviewStatus.NEEDS_RE_REVIEW
    review.completed_at = None
    review.completed_by = None
    append_review_event(
        session,
        review,
        event_type=ReviewEventType.NEEDS_RE_REVIEW,
        subject_type="signoff" if prior_signoff is not None else "comparison",
        subject_id=(
            prior_signoff.signoff_id
            if prior_signoff is not None
            else str(review.comparison_id)
        ),
        actor=actor,
        note=note,
        payload={
            "prior_signoff_id": (
                prior_signoff.signoff_id if prior_signoff is not None else None
            )
        },
    )
    session.flush()
