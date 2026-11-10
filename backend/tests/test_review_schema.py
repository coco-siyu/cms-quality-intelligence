from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain import (
    ChecklistTaskStatus,
    MeasureReviewStatus,
    ReviewEventType,
    ReviewRole,
    TaskProposalStatus,
)
from app.models import (
    ImpactExplanationDraft,
    MeasureComparison,
    MeasureReview,
    ReviewChecklistItem,
    ReviewEvent,
    ReviewSignOff,
    ReviewTaskProposal,
)

REVIEWED_AT = datetime(2026, 11, 10, 12, tzinfo=UTC)


def _comparison(session: Session) -> MeasureComparison:
    comparison = session.scalar(
        select(MeasureComparison).where(MeasureComparison.measure.has(measure_id="DEMO-001"))
    )
    assert comparison is not None
    return comparison


def _draft(comparison: MeasureComparison, *, sequence: int) -> ImpactExplanationDraft:
    return ImpactExplanationDraft(
        draft_id=f"REVIEW-SCHEMA-DRAFT-{sequence}",
        comparison=comparison,
        provider="test-provider",
        model=f"test-model-{sequence}",
        prompt_version="review-schema-v1",
        input_digest=f"digest-{sequence}",
        output_payload={"fixture": True, "sequence": sequence},
        provider_response_id=f"response-{sequence}",
        created_by="schema-test",
    )


def test_regeneration_and_reopening_preserve_tasks_signoffs_and_events(
    seeded_session: Session,
) -> None:
    comparison = _comparison(seeded_session)
    first_draft = _draft(comparison, sequence=1)
    review = MeasureReview(
        review_id="REVIEW-DEMO-001",
        comparison=comparison,
        status=MeasureReviewStatus.COMPLETED,
        completed_at=REVIEWED_AT,
        completed_by="admin",
        created_by="admin",
    )
    first_proposal = ReviewTaskProposal(
        proposal_id="PROPOSAL-DEMO-001-1",
        review=review,
        impact_explanation_draft=first_draft,
        sequence=1,
        role=ReviewRole.DATA_ANALYST,
        title="Validate the controlled year mapping",
        description="Fictional review task for schema testing only.",
        provider="test-provider",
        model="test-model",
        prompt_version="task-proposal-v1",
        input_digest="digest-1",
        provider_response_id="task-response-1",
        status=TaskProposalStatus.ACCEPTED,
        decided_at=REVIEWED_AT,
        decided_by="admin",
        created_by="generator",
    )
    completed_item = ReviewChecklistItem(
        checklist_item_id="CHECKLIST-DEMO-001-1",
        review=review,
        accepted_from_proposal=first_proposal,
        role=ReviewRole.DATA_ANALYST,
        title=first_proposal.title,
        description=first_proposal.description,
        status=ChecklistTaskStatus.COMPLETED,
        notes="Controlled completion note.",
        resolved_at=REVIEWED_AT,
        resolved_by="admin",
        created_by="admin",
    )
    first_signoff = ReviewSignOff(
        signoff_id="SIGNOFF-DEMO-001-1",
        review=review,
        sequence=1,
        accepted_task_count=1,
        resolved_task_count=1,
        note="Controlled sign-off.",
        signed_at=REVIEWED_AT,
        signed_by="admin",
    )
    review.events.extend(
        [
            ReviewEvent(
                event_id="EVENT-DEMO-001-1",
                sequence=1,
                event_type=ReviewEventType.REVIEW_CREATED,
                actor="admin",
                payload={},
            ),
            ReviewEvent(
                event_id="EVENT-DEMO-001-2",
                sequence=2,
                event_type=ReviewEventType.PROPOSAL_ACCEPTED,
                subject_type="task_proposal",
                subject_id=first_proposal.proposal_id,
                actor="admin",
                payload={"role": ReviewRole.DATA_ANALYST.value},
            ),
            ReviewEvent(
                event_id="EVENT-DEMO-001-3",
                sequence=3,
                event_type=ReviewEventType.TASK_STATUS_CHANGED,
                subject_type="checklist_item",
                subject_id=completed_item.checklist_item_id,
                actor="admin",
                payload={"status": ChecklistTaskStatus.COMPLETED.value},
            ),
            ReviewEvent(
                event_id="EVENT-DEMO-001-4",
                sequence=4,
                event_type=ReviewEventType.SIGNED_OFF,
                subject_type="signoff",
                subject_id=first_signoff.signoff_id,
                actor="admin",
                payload={"resolved_task_count": 1},
            ),
        ]
    )
    seeded_session.add_all([review, completed_item, first_signoff])
    seeded_session.commit()

    second_draft = _draft(comparison, sequence=2)
    second_proposal = ReviewTaskProposal(
        proposal_id="PROPOSAL-DEMO-001-2",
        review=review,
        impact_explanation_draft=second_draft,
        sequence=1,
        role=ReviewRole.ACO_QUALITY_MANAGER,
        title="Inspect the controlled workflow impact",
        provider="test-provider",
        model="test-model",
        prompt_version="task-proposal-v1",
        input_digest="digest-2",
        provider_response_id="task-response-2",
        status=TaskProposalStatus.PENDING,
        created_by="generator",
    )
    review.status = MeasureReviewStatus.REOPENED
    review.completed_at = None
    review.completed_by = None
    review.events.append(
        ReviewEvent(
            event_id="EVENT-DEMO-001-5",
            sequence=5,
            event_type=ReviewEventType.REOPENED,
            actor="admin",
            note="Reopened after a newer explanation was generated.",
            payload={"prior_signoff_id": first_signoff.signoff_id},
        )
    )
    seeded_session.add(second_proposal)
    seeded_session.commit()

    seeded_session.refresh(review)
    seeded_session.refresh(completed_item)
    assert review.status == MeasureReviewStatus.REOPENED
    assert completed_item.status == ChecklistTaskStatus.COMPLETED
    assert completed_item.resolved_at.replace(tzinfo=UTC) == REVIEWED_AT
    assert completed_item.accepted_from_proposal_id == first_proposal.id
    assert [signoff.signoff_id for signoff in review.signoffs] == [first_signoff.signoff_id]
    assert [event.sequence for event in review.events] == [1, 2, 3, 4, 5]
    assert first_proposal.status == TaskProposalStatus.ACCEPTED
    assert second_proposal.status == TaskProposalStatus.PENDING
    assert len(review.task_proposals) == 2


def test_resolved_checklist_item_requires_resolver_metadata(
    seeded_session: Session,
) -> None:
    review = MeasureReview(
        review_id="REVIEW-INVALID-TASK",
        comparison=_comparison(seeded_session),
        status=MeasureReviewStatus.IN_REVIEW,
        created_by="admin",
    )
    review.checklist_items.append(
        ReviewChecklistItem(
            checklist_item_id="CHECKLIST-INVALID-TASK",
            role=ReviewRole.BOTH,
            title="Invalid completed task",
            status=ChecklistTaskStatus.COMPLETED,
            created_by="admin",
        )
    )
    seeded_session.add(review)

    with pytest.raises(IntegrityError):
        seeded_session.commit()


def test_signoff_snapshot_requires_resolved_count_to_match_accepted_count(
    seeded_session: Session,
) -> None:
    review = MeasureReview(
        review_id="REVIEW-INVALID-SIGNOFF",
        comparison=_comparison(seeded_session),
        status=MeasureReviewStatus.IN_REVIEW,
        created_by="admin",
    )
    review.signoffs.append(
        ReviewSignOff(
            signoff_id="SIGNOFF-INVALID-COUNT",
            sequence=1,
            accepted_task_count=2,
            resolved_task_count=1,
            signed_by="admin",
        )
    )
    seeded_session.add(review)

    with pytest.raises(IntegrityError):
        seeded_session.commit()
