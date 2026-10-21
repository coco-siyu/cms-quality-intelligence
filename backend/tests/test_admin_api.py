from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import hash_admin_password
from app.commands.seed_verified import seed_verified_drafts
from app.config import Settings, get_settings
from app.database import get_db
from app.main import create_app


@pytest.fixture
def admin_client(session: Session) -> Generator[TestClient]:
    seed_verified_drafts(session)
    session.commit()
    settings = Settings(
        admin_username="reviewer",
        admin_password_hash=hash_admin_password(
            "correct horse battery staple", salt=b"test-salt-16byte"
        ),
        admin_session_secret="test-session-secret-with-sufficient-entropy",
        admin_session_secure=False,
    )
    app = create_app()

    def override_database() -> Generator[Session]:
        yield session

    app.dependency_overrides[get_db] = override_database
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as test_client:
        yield test_client


def test_admin_session_reports_missing_configuration(client: TestClient) -> None:
    status = client.get("/api/admin/session")
    login = client.post(
        "/api/admin/session", json={"username": "admin", "password": "anything"}
    )

    assert status.json() == {
        "configured": False,
        "authenticated": False,
        "username": None,
    }
    assert login.status_code == 503
    assert login.json()["code"] == "admin_authentication_not_configured"


def test_private_review_data_requires_a_valid_admin_session(
    admin_client: TestClient,
) -> None:
    unauthorized = admin_client.get("/api/admin/review-summary")
    invalid_login = admin_client.post(
        "/api/admin/session",
        json={"username": "reviewer", "password": "incorrect password"},
    )

    assert unauthorized.status_code == 401
    assert unauthorized.json()["code"] == "admin_authentication_required"
    assert invalid_login.status_code == 401
    assert invalid_login.json()["code"] == "invalid_admin_credentials"


def test_admin_can_inspect_private_staged_records_without_publishing_them(
    admin_client: TestClient,
) -> None:
    login = admin_client.post(
        "/api/admin/session",
        json={"username": "reviewer", "password": "correct horse battery staple"},
    )

    assert login.status_code == 200
    assert login.json() == {
        "configured": True,
        "authenticated": True,
        "username": "reviewer",
    }
    assert "HttpOnly" in login.headers["set-cookie"]
    assert "SameSite=lax" in login.headers["set-cookie"]

    summary = admin_client.get("/api/admin/review-summary")
    measures = admin_client.get("/api/admin/measures")
    detail = admin_client.get("/api/admin/measures/001")

    assert summary.json() == {
        "private_measures": 8,
        "draft_versions": 46,
        "pending_candidates": 352,
        "decided_candidates": 0,
        "source_revisions": 16,
        "newer_revision_flags": 0,
    }
    assert measures.json()["pagination"]["total_items"] == 8
    assert all(item["measure_id"] != "DEMO-001" for item in measures.json()["items"])
    assert detail.status_code == 200
    assert detail.json()["is_public"] is False
    assert detail.json()["memberships"][0]["publication_state"] == "draft"
    candidates = [
        candidate
        for version in detail.json()["versions"]
        for candidate in version["candidates"]
    ]
    assert candidates
    assert all(candidate["review_decision"] == "pending" for candidate in candidates)
    assert candidates[0]["official_url"].startswith("https://")

    public = admin_client.get("/api/measures")
    assert public.status_code == 200
    assert public.json()["items"] == []


def test_logout_revokes_the_browser_session(admin_client: TestClient) -> None:
    admin_client.post(
        "/api/admin/session",
        json={"username": "reviewer", "password": "correct horse battery staple"},
    )
    assert admin_client.get("/api/admin/review-summary").status_code == 200

    logout = admin_client.delete("/api/admin/session")

    assert logout.json()["authenticated"] is False
    assert admin_client.get("/api/admin/review-summary").status_code == 401
