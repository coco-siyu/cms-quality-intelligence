import os
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILES = (
    REPOSITORY_ROOT / "compose.yaml",
    REPOSITORY_ROOT / "tests/integration/compose.test.yaml",
)
PRIVATE_RESPONSE_KEYS = {
    "candidate_value",
    "candidates",
    "checks",
    "clarifications",
    "created_by",
    "draft_versions",
    "private_measures",
    "review_history",
    "review_items",
    "reviewer_notes",
}


def _required_environment(name: str) -> str:
    value = os.getenv(name)
    if not value:
        pytest.fail(f"{name} must be set by scripts/test-compose.sh")
    return value


@pytest.fixture(scope="session")
def api_url() -> str:
    return _required_environment("CMSQI_INTEGRATION_API_URL")


@pytest.fixture(scope="session")
def frontend_url() -> str:
    return _required_environment("CMSQI_INTEGRATION_FRONTEND_URL")


@pytest.fixture
def frontend_client(frontend_url: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=frontend_url, timeout=10) as client:
        yield client


def _walk_keys(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def _login(client: httpx.Client) -> httpx.Response:
    return client.post(
        "/api/admin/session",
        json={"username": "compose-admin", "password": "compose-test-password"},
    )


def _compose_command(*arguments: str) -> list[str]:
    project_name = _required_environment("CMSQI_COMPOSE_PROJECT_NAME")
    command = ["docker", "compose", "--project-name", project_name]
    for compose_file in COMPOSE_FILES:
        command.extend(("--file", str(compose_file)))
    command.extend(arguments)
    return command


def _wait_for_stack(api_url: str, frontend_url: str, timeout_seconds: int = 90) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = "stack did not respond"
    while time.monotonic() < deadline:
        try:
            direct_health = httpx.get(f"{api_url}/health", timeout=2)
            proxy_health = httpx.get(f"{frontend_url}/health", timeout=2)
            public_years = httpx.get(f"{frontend_url}/api/performance-years", timeout=2)
            if (
                direct_health.status_code == 200
                and proxy_health.status_code == 200
                and public_years.status_code == 200
            ):
                return
            last_error = (
                f"status codes: direct={direct_health.status_code}, "
                f"proxy={proxy_health.status_code}, years={public_years.status_code}"
            )
        except httpx.HTTPError as error:
            last_error = str(error)
        time.sleep(1)
    pytest.fail(f"Compose stack did not recover within {timeout_seconds}s: {last_error}")


def test_health_is_available_directly_and_through_nginx(
    api_url: str, frontend_client: httpx.Client
) -> None:
    direct_response = httpx.get(f"{api_url}/health", timeout=10)
    proxied_response = frontend_client.get("/health")

    assert direct_response.status_code == 200
    assert direct_response.json() == {"status": "ok"}
    assert proxied_response.status_code == 200
    assert proxied_response.json() == direct_response.json()


def test_frontend_serves_the_app_shell_for_client_routes(
    frontend_client: httpx.Client,
) -> None:
    for path in ("/", "/measures", "/admin/sources"):
        response = frontend_client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert '<div id="root"></div>' in response.text

    api_not_found = frontend_client.get("/api/route-that-does-not-exist")
    assert api_not_found.status_code == 404
    assert api_not_found.headers["content-type"].startswith("application/json")


def test_migrations_and_preview_bootstrap_expose_only_the_public_roster(
    frontend_client: httpx.Client,
) -> None:
    years_response = frontend_client.get("/api/performance-years")
    measures_response = frontend_client.get("/api/measures", params={"page_size": 100})

    assert years_response.status_code == 200
    assert years_response.json() == {
        "years": [2025, 2026],
        "default_from_year": 2025,
        "default_to_year": 2026,
    }
    assert measures_response.status_code == 200

    payload = measures_response.json()
    assert payload["pagination"]["total_items"] == 8
    assert len(payload["items"]) == 8
    assert all(item["measure_id"] and item["name"] for item in payload["items"])
    assert PRIVATE_RESPONSE_KEYS.isdisjoint(_walk_keys(payload))

    measure_id = payload["items"][0]["measure_id"]
    detail_response = frontend_client.get(f"/api/measures/{measure_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["measure_id"] == measure_id
    assert PRIVATE_RESPONSE_KEYS.isdisjoint(_walk_keys(detail_response.json()))

    unpublished_changes = frontend_client.get(
        "/api/changes",
        params={
            "collection_type": "program_roster",
            "from_year": 2025,
            "to_year": 2026,
        },
    )
    assert unpublished_changes.status_code == 200
    assert unpublished_changes.json()["items"] == []


def test_admin_authentication_and_private_route_boundary(
    frontend_client: httpx.Client,
) -> None:
    unauthenticated = frontend_client.get("/api/admin/review-summary")
    assert unauthenticated.status_code == 401

    invalid_login = frontend_client.post(
        "/api/admin/session",
        json={"username": "compose-admin", "password": "wrong-password"},
    )
    assert invalid_login.status_code == 401

    login = _login(frontend_client)
    assert login.status_code == 200
    assert login.json() == {
        "configured": True,
        "authenticated": True,
        "username": "compose-admin",
    }
    cookie = login.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/api/admin" in cookie

    private_response = frontend_client.get("/api/admin/review-summary")
    assert private_response.status_code == 200
    assert private_response.json()["private_measures"] > 0

    logout = frontend_client.delete("/api/admin/session")
    assert logout.status_code == 200
    assert logout.json()["authenticated"] is False
    assert frontend_client.get("/api/admin/review-summary").status_code == 401


def test_admin_mutation_requires_authentication_and_explicit_action_header(
    frontend_client: httpx.Client,
) -> None:
    request_body = {
        "source_id": "COMPOSE-IT-GUARD",
        "title": "Compose integration guard fixture",
        "official_url": "https://www.cms.gov/compose-integration-guard-fixture",
        "source_format": "html",
        "notes": "Automated private test fixture; never fetched or published.",
    }
    unauthenticated = frontend_client.post(
        "/api/admin/sources",
        headers={"X-CMSQI-Admin-Action": "source-registry"},
        json=request_body,
    )
    assert unauthenticated.status_code == 401

    assert _login(frontend_client).status_code == 200
    wrong_action = frontend_client.post(
        "/api/admin/sources",
        headers={"X-CMSQI-Admin-Action": "not-authorized"},
        json=request_body,
    )
    assert wrong_action.status_code == 403
    assert frontend_client.get("/api/admin/sources/COMPOSE-IT-GUARD").status_code == 404


def test_postgres_data_survives_a_compose_restart(
    api_url: str, frontend_url: str, frontend_client: httpx.Client
) -> None:
    assert _login(frontend_client).status_code == 200
    create_response = frontend_client.post(
        "/api/admin/sources",
        headers={"X-CMSQI-Admin-Action": "source-registry"},
        json={
            "source_id": "COMPOSE-IT-PERSISTENCE",
            "title": "Compose integration persistence fixture",
            "official_url": "https://www.cms.gov/compose-integration-persistence-fixture",
            "source_format": "html",
            "notes": "Automated private test fixture; never fetched or published.",
        },
    )
    assert create_response.status_code == 201

    subprocess.run(
        _compose_command("restart", "postgres", "backend", "frontend"),
        cwd=REPOSITORY_ROOT,
        check=True,
        timeout=120,
    )
    _wait_for_stack(api_url, frontend_url)

    with httpx.Client(base_url=frontend_url, timeout=10) as restarted_client:
        assert _login(restarted_client).status_code == 200
        persisted = restarted_client.get("/api/admin/sources/COMPOSE-IT-PERSISTENCE")
        public_measures = restarted_client.get("/api/measures", params={"page_size": 100})

    assert persisted.status_code == 200
    assert persisted.json()["source_id"] == "COMPOSE-IT-PERSISTENCE"
    assert persisted.json()["revision_count"] == 0
    assert public_measures.status_code == 200
    assert public_measures.json()["pagination"]["total_items"] == 8
