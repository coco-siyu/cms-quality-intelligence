"""Private checklist mutations with append-only review audit events."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domain import (
    ChecklistTaskStatus,
    MeasureReviewStatus,
    ReviewEventType,
    TaskProposalStatus,
)
from app.models import (
    MeasureComparison,
    MeasureReview,
    ReviewChecklistItem,
    ReviewEvent,
    ReviewTaskProposal,
)
from app.schemas import (
    AdminReviewChecklistItemCreateRequest,
    AdminReviewChecklistItemUpdateRequest,
)


class ReviewChecklistError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _now() -> datetime:
    return datetime.now(UTC)


def _event_sequence(session: Session, review: MeasureReview) -> int:
    return (
        session.scalar(
            select(func.max(ReviewEvent.sequence)).where(ReviewEvent.review_id == review.id)
        )
        or 0
    ) + 1


def append_review_event(
    session: Session,
    review: MeasureReview,
    *,
    event_type: ReviewEventType,
    subject_type: str,
    subject_id: str,
    actor: str,
    note: str | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    review.events.append(
        ReviewEvent(
            event_id=f"CMS-REVIEW-EVENT-{uuid4().hex}",
            sequence=_event_sequence(session, review),
            event_type=event_type,
            subject_type=subject_type,
            subject_id=subject_id,
            actor=actor,
            note=note,
            payload=payload or {},
        )
    )
    session.flush()


def _start_review(review: MeasureReview) -> None:
    if review.status == MeasureReviewStatus.PENDING:
        review.status = MeasureReviewStatus.IN_REVIEW


def _ensure_review_editable(review: MeasureReview) -> None:
    if review.status == MeasureReviewStatus.COMPLETED:
        raise ReviewChecklistError(
            "review_completed_reopen_required",
            "Reopen the completed review before changing its checklist.",
        )


def _review_for_comparison(
    session: Session,
    *,
    comparison_id: int,
    actor: str,
) -> MeasureReview:
    comparison = session.scalar(
        select(MeasureComparison).where(MeasureComparison.id == comparison_id)
    )
    if comparison is None:
        raise ReviewChecklistError(
            "comparison_not_found", f"Comparison '{comparison_id}' was not found."
        )
    review = session.scalar(
        select(MeasureReview).where(MeasureReview.comparison_id == comparison_id)
    )
    if review is not None:
        return review
    review = MeasureReview(
        review_id=f"CMS-REVIEW-{uuid4().hex}",
        comparison=comparison,
        status=MeasureReviewStatus.PENDING,
        created_by=actor,
    )
    session.add(review)
    session.flush()
    append_review_event(
        session,
        review,
        event_type=ReviewEventType.REVIEW_CREATED,
        subject_type="comparison",
        subject_id=str(comparison_id),
        actor=actor,
        payload={"comparison_id": comparison_id},
    )
    return review


def add_checklist_item(
    session: Session,
    *,
    comparison_id: int,
    request: AdminReviewChecklistItemCreateRequest,
    actor: str,
) -> ReviewChecklistItem:
    review = _review_for_comparison(
        session, comparison_id=comparison_id, actor=actor
    )
    _ensure_review_editable(review)
    _start_review(review)
    item = ReviewChecklistItem(
        checklist_item_id=f"CMS-CHECKLIST-{uuid4().hex}",
        review=review,
        role=request.role,
        title=request.title,
        description=request.description,
        notes=request.notes,
        created_by=actor,
    )
    session.add(item)
    session.flush()
    append_review_event(
        session,
        review,
        event_type=ReviewEventType.TASK_ADDED,
        subject_type="checklist_item",
        subject_id=item.checklist_item_id,
        actor=actor,
        note=item.notes,
        payload={
            "origin": "manual",
            "role": item.role.value,
            "task_title": item.title,
        },
    )
    return item


def decide_task_proposal(
    session: Session,
    *,
    proposal_id: str,
    accept: bool,
    actor: str,
) -> MeasureReview:
    proposal = session.scalar(
        select(ReviewTaskProposal)
        .where(ReviewTaskProposal.proposal_id == proposal_id)
        .options(
            selectinload(ReviewTaskProposal.review),
            selectinload(ReviewTaskProposal.accepted_item),
        )
    )
    if proposal is None:
        raise ReviewChecklistError(
            "proposal_not_found", f"Task proposal '{proposal_id}' was not found."
        )
    if proposal.status != TaskProposalStatus.PENDING:
        if accept and proposal.status == TaskProposalStatus.ACCEPTED:
            return proposal.review
        if not accept and proposal.status == TaskProposalStatus.DISMISSED:
            return proposal.review
        raise ReviewChecklistError(
            "proposal_already_decided",
            "The task proposal already has a different decision.",
        )

    _ensure_review_editable(proposal.review)

    decided_at = _now()
    proposal.status = (
        TaskProposalStatus.ACCEPTED if accept else TaskProposalStatus.DISMISSED
    )
    proposal.decided_at = decided_at
    proposal.decided_by = actor
    event_type = (
        ReviewEventType.PROPOSAL_ACCEPTED
        if accept
        else ReviewEventType.PROPOSAL_DISMISSED
    )
    append_review_event(
        session,
        proposal.review,
        event_type=event_type,
        subject_type="task_proposal",
        subject_id=proposal.proposal_id,
        actor=actor,
        payload={"role": proposal.role.value, "task_title": proposal.title},
    )
    if not accept:
        return proposal.review

    _start_review(proposal.review)
    item = ReviewChecklistItem(
        checklist_item_id=f"CMS-CHECKLIST-{uuid4().hex}",
        review=proposal.review,
        accepted_from_proposal=proposal,
        role=proposal.role,
        title=proposal.title,
        description=proposal.description,
        created_by=actor,
    )
    session.add(item)
    session.flush()
    append_review_event(
        session,
        proposal.review,
        event_type=ReviewEventType.TASK_ADDED,
        subject_type="checklist_item",
        subject_id=item.checklist_item_id,
        actor=actor,
        payload={
            "origin": "proposal",
            "proposal_id": proposal.proposal_id,
            "role": item.role.value,
            "task_title": item.title,
        },
    )
    return proposal.review


def update_checklist_item(
    session: Session,
    *,
    checklist_item_id: str,
    request: AdminReviewChecklistItemUpdateRequest,
    actor: str,
) -> ReviewChecklistItem:
    item = session.scalar(
        select(ReviewChecklistItem)
        .where(ReviewChecklistItem.checklist_item_id == checklist_item_id)
        .options(selectinload(ReviewChecklistItem.review))
    )
    if item is None:
        raise ReviewChecklistError(
            "checklist_item_not_found",
            f"Checklist item '{checklist_item_id}' was not found.",
        )

    _ensure_review_editable(item.review)

    changed_fields: list[str] = []
    previous_title = item.title
    for field in ("role", "title", "description", "notes"):
        if field in request.model_fields_set:
            next_value = getattr(request, field)
            if getattr(item, field) != next_value:
                setattr(item, field, next_value)
                changed_fields.append(field)

    status_changed = (
        "status" in request.model_fields_set
        and request.status is not None
        and request.status != item.status
    )
    previous_status = item.status
    if status_changed:
        item.status = request.status
        if request.status == ChecklistTaskStatus.OPEN:
            item.resolved_at = None
            item.resolved_by = None
        else:
            item.resolved_at = _now()
            item.resolved_by = actor

    if changed_fields:
        append_review_event(
            session,
            item.review,
            event_type=ReviewEventType.TASK_EDITED,
            subject_type="checklist_item",
            subject_id=item.checklist_item_id,
            actor=actor,
            note=item.notes if "notes" in changed_fields else None,
            payload={
                "changed_fields": changed_fields,
                "task_title": item.title,
                "previous_title": previous_title,
            },
        )
    if status_changed:
        append_review_event(
            session,
            item.review,
            event_type=ReviewEventType.TASK_STATUS_CHANGED,
            subject_type="checklist_item",
            subject_id=item.checklist_item_id,
            actor=actor,
            payload={
                "from_status": previous_status.value,
                "to_status": item.status.value,
                "task_title": item.title,
            },
        )
    session.flush()
    return item
