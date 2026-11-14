"""Private read model for one comparison's durable review checklist."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain import (
    ChecklistTaskStatus,
    ImpactExplanationReviewDecision,
    MeasureReviewStatus,
)
from app.models import (
    ImpactExplanationDraft,
    MeasureComparison,
    MeasureReview,
    ReviewChecklistItem,
    ReviewSignOff,
    ReviewTaskProposal,
)
from app.repositories.admin_task_proposals import (
    proposal_options,
    task_proposal_response,
)
from app.schemas import (
    AdminReviewChecklistItemResponse,
    AdminReviewChecklistProgress,
    AdminReviewChecklistResponse,
    AdminReviewSignOffResponse,
)


def checklist_item_response(item: ReviewChecklistItem) -> AdminReviewChecklistItemResponse:
    return AdminReviewChecklistItemResponse(
        checklist_item_id=item.checklist_item_id,
        review_id=item.review.review_id,
        accepted_from_proposal_id=(
            item.accepted_from_proposal.proposal_id
            if item.accepted_from_proposal is not None
            else None
        ),
        role=item.role,
        title=item.title,
        description=item.description,
        status=item.status,
        notes=item.notes,
        resolved_at=item.resolved_at,
        resolved_by=item.resolved_by,
        created_at=item.created_at,
        created_by=item.created_by,
        updated_at=item.updated_at,
    )


def signoff_response(signoff: ReviewSignOff) -> AdminReviewSignOffResponse:
    return AdminReviewSignOffResponse(
        signoff_id=signoff.signoff_id,
        sequence=signoff.sequence,
        accepted_task_count=signoff.accepted_task_count,
        resolved_task_count=signoff.resolved_task_count,
        note=signoff.note,
        signed_at=signoff.signed_at,
        signed_by=signoff.signed_by,
    )


def get_review_checklist(
    session: Session,
    *,
    comparison_id: int,
) -> AdminReviewChecklistResponse | None:
    comparison_exists = session.scalar(
        select(MeasureComparison.id).where(MeasureComparison.id == comparison_id)
    )
    if comparison_exists is None:
        return None

    eligible_draft_id = session.scalar(
        select(ImpactExplanationDraft.draft_id)
        .where(
            ImpactExplanationDraft.comparison_id == comparison_id,
            ImpactExplanationDraft.review_decision
            == ImpactExplanationReviewDecision.APPROVE,
            ImpactExplanationDraft.outdated_at.is_(None),
        )
        .order_by(ImpactExplanationDraft.generation_sequence.desc())
        .limit(1)
    )
    review = session.scalar(
        select(MeasureReview).where(MeasureReview.comparison_id == comparison_id)
    )
    if review is None:
        return AdminReviewChecklistResponse(
            comparison_id=comparison_id,
            review_id=None,
            review_status=None,
            eligible_impact_explanation_draft_id=eligible_draft_id,
            proposals=[],
            items=[],
            progress=AdminReviewChecklistProgress(total=0, open=0, resolved=0),
            signoffs=[],
            can_sign_off=False,
            signoff_blocker="Start the review before signing off.",
        )

    proposals = list(
        session.scalars(
            select(ReviewTaskProposal)
            .where(ReviewTaskProposal.review_id == review.id)
            .options(*proposal_options())
            .order_by(ReviewTaskProposal.created_at.desc(), ReviewTaskProposal.sequence)
        ).all()
    )
    items = list(
        session.scalars(
            select(ReviewChecklistItem)
            .where(ReviewChecklistItem.review_id == review.id)
            .options(
                selectinload(ReviewChecklistItem.review),
                selectinload(ReviewChecklistItem.accepted_from_proposal),
            )
            .order_by(ReviewChecklistItem.created_at, ReviewChecklistItem.id)
        ).all()
    )
    signoffs = list(
        session.scalars(
            select(ReviewSignOff)
            .where(ReviewSignOff.review_id == review.id)
            .order_by(ReviewSignOff.sequence)
        ).all()
    )
    open_count = sum(item.status == ChecklistTaskStatus.OPEN for item in items)
    if review.status == MeasureReviewStatus.COMPLETED:
        signoff_blocker = "This review is already signed off."
    elif open_count:
        task_label = "tasks" if open_count != 1 else "task"
        signoff_blocker = (
            f"Resolve {open_count} open {task_label} before signing off."
        )
    else:
        signoff_blocker = None
    return AdminReviewChecklistResponse(
        comparison_id=comparison_id,
        review_id=review.review_id,
        review_status=review.status,
        eligible_impact_explanation_draft_id=eligible_draft_id,
        proposals=[task_proposal_response(proposal) for proposal in proposals],
        items=[checklist_item_response(item) for item in items],
        progress=AdminReviewChecklistProgress(
            total=len(items),
            open=open_count,
            resolved=len(items) - open_count,
        ),
        signoffs=[signoff_response(signoff) for signoff in signoffs],
        can_sign_off=signoff_blocker is None,
        signoff_blocker=signoff_blocker,
    )
