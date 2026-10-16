from fastapi.testclient import TestClient


def test_list_measures_returns_only_public_published_records(client: TestClient) -> None:
    response = client.get("/api/measures", params={"from_year": 2025, "to_year": 2026})

    assert response.status_code == 200
    payload = response.json()
    assert [item["measure_id"] for item in payload["items"]] == ["DEMO-001", "DEMO-002"]
    assert payload["pagination"] == {
        "page": 1,
        "page_size": 25,
        "total_items": 2,
        "total_pages": 1,
    }
    assert payload["items"][0]["change_status"] == "modified"
    assert payload["items"][1]["change_status"] == "unknown"
    assert "content_hash" not in response.text
    assert "DEMO-PRIVATE" not in response.text


def test_measure_filters_and_pagination_follow_contract(client: TestClient) -> None:
    filtered = client.get(
        "/api/measures",
        params={
            "q": "Follow-up",
            "performance_year": 2025,
            "from_year": 2025,
            "to_year": 2026,
            "change_status": "modified",
            "affected_field": "definition",
            "verification_status": "partially_verified",
            "page": 1,
            "page_size": 1,
        },
    )

    assert filtered.status_code == 200
    payload = filtered.json()
    assert [item["measure_id"] for item in payload["items"]] == ["DEMO-001"]
    assert payload["pagination"]["total_items"] == 1


def test_measure_detail_exposes_explicit_availability_and_public_evidence(
    client: TestClient,
) -> None:
    response = client.get("/api/measures/DEMO-002")

    assert response.status_code == 200
    payload = response.json()
    field = payload["versions"][0]["fields"][0]
    assert field["availability"] == "unresolved"
    assert field["value"] is None
    assert field["evidence"][0]["document_title"] == "Fictional C1 Test Source"
    assert set(field["evidence"][0]) == {
        "evidence_id",
        "source_revision_id",
        "document_title",
        "official_url",
        "locator",
        "excerpt",
    }


def test_measure_versions_can_be_selected_by_year(client: TestClient) -> None:
    response = client.get("/api/measures/DEMO-001/versions", params={"performance_year": 2025})

    assert response.status_code == 200
    assert [item["performance_year"] for item in response.json()["versions"]] == [2025]


def test_not_found_and_validation_errors_match_public_error_shape(client: TestClient) -> None:
    not_found = client.get("/api/measures/DEMO-MISSING")
    invalid = client.get("/api/measures", params={"page_size": 101})

    assert not_found.status_code == 404
    assert not_found.json()["code"] == "not_found"
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "validation_error"
    assert invalid.json()["details"]


def test_performance_years_are_derived_from_published_memberships(client: TestClient) -> None:
    response = client.get("/api/performance-years")

    assert response.status_code == 200
    assert response.json() == {
        "years": [2025, 2026],
        "default_from_year": 2025,
        "default_to_year": 2026,
    }
