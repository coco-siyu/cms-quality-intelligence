import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_admin_password
from app.config import Settings, get_settings
from app.domain import (
    ChecklistTaskStatus,
    MeasureReviewStatus,
    ReviewEventType,
    ReviewRole,
)
from app.models import MeasureComparison, MeasureReview, ReviewEvent
from app.schemas import (
    AdminReviewChecklistItemCreateRequest,
    AdminReviewChecklistItemUpdateRequest,
)
from app.services.review_checklists import (
    ReviewChecklistError,
    add_checklist_item,
    update_checklist_item,
)
from app.services.review_lifecycle import (
    ReviewLifecycleError,
    reopen_review,
    require_re_review_for_new_source,
    sign_off_review,
)


def _comparison(session: Session) -> MeasureComparison:
    comparison = session.scalar(select(MeasureComparison))
    assert comparison is not None
    return comparison


def _resolved_review(session: Session) -> MeasureReview:
    comparison = _comparison(session)
    item = add_checklist_item(
        session,
        comparison_id=comparison.id,
        request=AdminReviewChecklistItemCreateRequest(
            role=ReviewRole.BOTH,
            title="Confirm the approved workflow",
        ),
        actor="reviewer",
    )
    update_checklist_item(
        session,
        checklist_item_id=item.checklist_item_id,
        request=AdminReviewChecklistItemUpdateRequest(
            status=ChecklistTaskStatus.COMPLETED
        ),
        actor="reviewer",
    )
    session.commit()
    return item.review


def test_signoff_requires_resolution_and_reopening_preserves_history(
    seeded_session: Session,
) -> None:
    comparison = _comparison(seeded_session)
    open_item = add_checklist_item(
        seeded_session,
        comparison_id=comparison.id,
        request=AdminReviewChecklistItemCreateRequest(
            role=ReviewRole.DATA_ANALYST,
            title="Validate the year mapping",
        ),
        actor="reviewer",
    )
    seeded_session.commit()

    with pytest.raises(ReviewLifecycleError) as blocked:
        sign_off_review(
            seeded_session,
            review_id=open_item.review.review_id,
            actor="reviewer",
            note=None,
        )
    assert blocked.value.code == "review_has_open_tasks"

    update_checklist_item(
        seeded_session,
        checklist_item_id=open_item.checklist_item_id,
        request=AdminReviewChecklistItemUpdateRequest(
            status=ChecklistTaskStatus.NOT_APPLICABLE
        ),
        actor="reviewer",
    )
    first = sign_off_review(
        seeded_session,
        review_id=open_item.review.review_id,
        actor="reviewer",
        note="All accepted work is resolved.",
    )
    seeded_session.commit()

    assert first.status == MeasureReviewStatus.COMPLETED
    assert first.completed_by == "reviewer"
    assert len(first.signoffs) == 1
    assert first.signoffs[0].sequence == 1
    assert first.signoffs[0].accepted_task_count == 1

    with pytest.raises(ReviewChecklistError) as locked:
        update_checklist_item(
            seeded_session,
            checklist_item_id=open_item.checklist_item_id,
            request=AdminReviewChecklistItemUpdateRequest(title="Changed after completion"),
            actor="reviewer",
        )
    assert locked.value.code == "review_completed_reopen_required"

    reopened = reopen_review(
        seeded_session,
        review_id=first.review_id,
        actor="reviewer",
        note="A second review pass is required.",
    )
    second = sign_off_review(
        seeded_session,
        review_id=first.review_id,
        actor="reviewer",
        note="Second review pass complete.",
    )
    seeded_session.commit()

    assert reopened is second
    assert second.status == MeasureReviewStatus.COMPLETED
    assert [item.sequence for item in second.signoffs] == [1, 2]
    assert [item.note for item in second.signoffs] == [
        "All accepted work is resolved.",
        "Second review pass complete.",
    ]
    event_types = seeded_session.scalars(
        select(ReviewEvent.event_type).order_by(ReviewEvent.sequence)
    ).all()
    assert event_types[-3:] == [
        ReviewEventType.SIGNED_OFF,
        ReviewEventType.REOPENED,
        ReviewEventType.SIGNED_OFF,
    ]


def test_new_source_moves_completed_review_to_needs_re_review(
    seeded_session: Session,
) -> None:
    review = _resolved_review(seeded_session)
    sign_off_review(
        seeded_session,
        review_id=review.review_id,
        actor="reviewer",
        note=None,
    )
    seeded_session.commit()

    require_re_review_for_new_source(
        seeded_session,
        review,
        actor="system:source-revision",
        note="A newer official source revision was detected.",
    )
    seeded_session.commit()

    assert review.status == MeasureReviewStatus.NEEDS_RE_REVIEW
    assert review.completed_at is None
    assert review.completed_by is None
    assert len(review.signoffs) == 1
    assert review.events[-1].event_type == ReviewEventType.NEEDS_RE_REVIEW


def test_review_lifecycle_api_is_private_and_requires_explicit_action(
    client: TestClient,
    seeded_session: Session,
) -> None:
    review = _resolved_review(seeded_session)
    path = f"/api/admin/reviews/{review.review_id}"
    assert client.post(f"{path}/sign-off", json={"note": None}).status_code == 401

    client.app.dependency_overrides[get_settings] = lambda: Settings(
        admin_username="reviewer",
        admin_password_hash=hash_admin_password(
            "correct horse battery staple", salt=b"test-salt-16byte"
        ),
        admin_session_secret="test-session-secret-with-sufficient-entropy",
    )
    assert client.post(
        "/api/admin/session",
        json={
            "username": "reviewer",
            "password": "correct horse battery staple",
        },
    ).status_code == 200

    wrong_header = client.post(
        f"{path}/sign-off",
        headers={"X-CMSQI-Admin-Action": "manage-review-checklist"},
        json={"note": None},
    )
    assert wrong_header.status_code == 403

    signed = client.post(
        f"{path}/sign-off",
        headers={"X-CMSQI-Admin-Action": "manage-review-lifecycle"},
        json={"note": "Confirmed for final sign-off."},
    )
    assert signed.status_code == 200
    assert signed.json()["review_status"] == "completed"
    assert signed.json()["can_sign_off"] is False
    assert len(signed.json()["signoffs"]) == 1

    reopened = client.post(
        f"{path}/reopen",
        headers={"X-CMSQI-Admin-Action": "manage-review-lifecycle"},
        json={"note": "Reopen for an additional review pass."},
    )
    assert reopened.status_code == 200
    assert reopened.json()["review_status"] == "reopened"
    assert reopened.json()["can_sign_off"] is True
    assert len(reopened.json()["signoffs"]) == 1
