from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_admin_password
from app.config import Settings, get_settings
from app.domain import MeasureReviewStatus, ReviewRole
from app.models import MeasureComparison, MeasureReview
from app.repositories.admin_review_dashboard import list_admin_review_dashboard
from app.schemas import AdminReviewChecklistItemCreateRequest
from app.services.review_checklists import add_checklist_item


def _comparison(session: Session) -> MeasureComparison:
    comparison = session.scalar(select(MeasureComparison))
    assert comparison is not None
    return comparison


def test_dashboard_projects_private_progress_and_status_filters(
    seeded_session: Session,
) -> None:
    comparison = _comparison(seeded_session)
    pending = list_admin_review_dashboard(seeded_session)
    assert pending.summary.model_dump() == {
        "total": 1,
        "pending": 1,
        "in_review": 0,
        "completed": 0,
        "needs_re_review": 0,
    }
    assert pending.items[0].dashboard_status == "pending"
    assert pending.items[0].progress.model_dump() == {
        "total": 0,
        "open": 0,
        "resolved": 0,
    }

    add_checklist_item(
        seeded_session,
        comparison_id=comparison.id,
        request=AdminReviewChecklistItemCreateRequest(
            role=ReviewRole.BOTH,
            title="Confirm the reviewed measure workflow",
        ),
        actor="reviewer",
    )
    seeded_session.commit()

    active = list_admin_review_dashboard(seeded_session)
    assert active.summary.in_review == 1
    assert active.items[0].dashboard_status == "in_review"
    assert active.items[0].remaining_tasks == 1
    assert active.items[0].progress.total == 1
    assert active.items[0].progress.resolved == 0

    review = seeded_session.scalar(select(MeasureReview))
    assert review is not None
    review.status = MeasureReviewStatus.NEEDS_RE_REVIEW
    seeded_session.commit()

    filtered = list_admin_review_dashboard(
        seeded_session, status="needs_re_review"
    )
    assert filtered.summary.needs_re_review == 1
    assert len(filtered.items) == 1
    assert filtered.items[0].review_status == "needs_re_review"
    assert list_admin_review_dashboard(
        seeded_session, status="completed"
    ).items == []


def test_dashboard_api_is_authenticated_and_never_returns_task_notes(
    client: TestClient,
    seeded_session: Session,
) -> None:
    comparison = _comparison(seeded_session)
    add_checklist_item(
        seeded_session,
        comparison_id=comparison.id,
        request=AdminReviewChecklistItemCreateRequest(
            role=ReviewRole.DATA_ANALYST,
            title="Validate the approved mapping",
            notes="Private working note that must stay out of the dashboard.",
        ),
        actor="reviewer",
    )
    seeded_session.commit()

    assert client.get("/api/admin/review-dashboard").status_code == 401
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        admin_username="reviewer",
        admin_password_hash=hash_admin_password(
            "correct horse battery staple", salt=b"test-salt-16byte"
        ),
        admin_session_secret="test-session-secret-with-sufficient-entropy",
    )
    login = client.post(
        "/api/admin/session",
        json={
            "username": "reviewer",
            "password": "correct horse battery staple",
        },
    )
    assert login.status_code == 200

    response = client.get("/api/admin/review-dashboard?status=in_review")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["in_review"] == 1
    assert body["items"][0]["remaining_tasks"] == 1
    assert body["items"][0]["progress"] == {
        "total": 1,
        "open": 1,
        "resolved": 0,
    }
    assert "Private working note" not in response.text
