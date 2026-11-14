from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_admin_password
from app.config import Settings, get_settings
from app.domain import ChecklistTaskStatus, ReviewEventType, ReviewRole
from app.models import MeasureComparison
from app.repositories.admin_review_activity import get_measure_review_activity
from app.schemas import (
    AdminReviewChecklistItemCreateRequest,
    AdminReviewChecklistItemUpdateRequest,
)
from app.services.review_checklists import add_checklist_item, update_checklist_item
from app.services.review_lifecycle import reopen_review, sign_off_review


def _comparison(session: Session) -> MeasureComparison:
    comparison = session.scalar(select(MeasureComparison))
    assert comparison is not None
    return comparison


def _build_activity(session: Session) -> tuple[str, str]:
    comparison = _comparison(session)
    item = add_checklist_item(
        session,
        comparison_id=comparison.id,
        request=AdminReviewChecklistItemCreateRequest(
            role=ReviewRole.DATA_ANALYST,
            title="Validate the reviewed mapping",
            notes="Initial private note.",
        ),
        actor="reviewer",
    )
    update_checklist_item(
        session,
        checklist_item_id=item.checklist_item_id,
        request=AdminReviewChecklistItemUpdateRequest(
            title="Validate the final mapping",
            notes="Updated private note.",
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
    sign_off_review(
        session,
        review_id=item.review.review_id,
        actor="reviewer",
        note="All follow-up work was checked.",
    )
    reopen_review(
        session,
        review_id=item.review.review_id,
        actor="reviewer",
        note="Reopened for a second review pass.",
    )
    session.commit()
    return comparison.measure.measure_id, item.review.review_id


def test_activity_read_model_is_append_only_human_readable_and_newest_first(
    seeded_session: Session,
) -> None:
    measure_id, review_id = _build_activity(seeded_session)

    activity = get_measure_review_activity(seeded_session, measure_id=measure_id)
    assert activity is not None
    assert activity.measure_id == measure_id
    assert len(activity.reviews) == 1
    review = activity.reviews[0]
    assert review.review_id == review_id
    assert review.review_status == "reopened"
    assert [event.event_type for event in review.events] == [
        ReviewEventType.REOPENED,
        ReviewEventType.SIGNED_OFF,
        ReviewEventType.TASK_STATUS_CHANGED,
        ReviewEventType.TASK_EDITED,
        ReviewEventType.TASK_ADDED,
        ReviewEventType.REVIEW_CREATED,
    ]
    assert review.events[0].note == "Reopened for a second review pass."
    assert review.events[1].note == "All follow-up work was checked."
    edited = next(
        event for event in review.events if event.event_type == ReviewEventType.TASK_EDITED
    )
    assert edited.note == "Updated private note."
    assert "Title, private notes updated" in edited.detail
    assert "Validate the final mapping" in edited.detail


def test_activity_endpoint_is_private_and_public_responses_exclude_internal_history(
    client: TestClient,
    seeded_session: Session,
) -> None:
    measure_id, _review_id = _build_activity(seeded_session)
    path = f"/api/admin/measures/{measure_id}/review-activity"
    assert client.get(path).status_code == 401

    public_response = client.get("/api/measures")
    assert public_response.status_code == 200
    assert "Updated private note" not in public_response.text
    assert "review_activity" not in public_response.text

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

    response = client.get(path)
    assert response.status_code == 200
    assert response.json()["reviews"][0]["events"][0]["event_type"] == "reopened"
    assert "Reopened for a second review pass." in response.text
