import csv
from datetime import datetime
from io import BytesIO, StringIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import ChangeStatus, FieldAvailability
from app.models import Measure, MeasureComparison
from app.services.change_export import CSV_COLUMNS, XLSX_MEDIA_TYPE


def _rows(response_text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(StringIO(response_text)))


def _xlsx_rows(response_content: bytes) -> tuple[object, list[dict[str, object]]]:
    workbook = load_workbook(BytesIO(response_content), data_only=False)
    sheet = workbook["Changes"]
    headers = [cell.value for cell in sheet[1]]
    rows = [
        dict(zip(headers, values, strict=True))
        for values in sheet.iter_rows(min_row=2, values_only=True)
    ]
    return workbook, rows


def test_csv_export_returns_public_field_rows_and_evidence_urls(client: TestClient) -> None:
    response = client.get(
        "/api/changes/export.csv",
        params={
            "from_year": 2025,
            "to_year": 2026,
            "collection_type": "program_roster",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == (
        'attachment; filename="cms-quality-changes-2025-2026.csv"'
    )
    rows = _rows(response.text)
    assert len(rows) == 1
    assert list(rows[0]) == list(CSV_COLUMNS)
    assert rows[0] == {
        "measure_id": "DEMO-001",
        "measure_name": "Fictional Follow-up Measure",
        "program": "Fictional Quality Program",
        "collection_type": "program_roster",
        "from_year": "2025",
        "to_year": "2026",
        "comparison_status": "modified",
        "evidence_status": "verified",
        "affected_field": "definition",
        "field_change_status": "modified",
        "from_availability": "available",
        "from_value": "Fictional definition for 2025.",
        "to_availability": "available",
        "to_value": "Fictional definition for 2026.",
        "evidence_ids": (
            "DEMO-EVIDENCE-DEMO-001-2025 | DEMO-EVIDENCE-DEMO-001-2026"
        ),
        "evidence_urls": "https://example.invalid/cms-quality-intelligence/demo-source",
        "approved_at": "2026-10-01T12:00:00Z",
        "published_at": "2026-10-01T12:00:00Z",
    }
    assert "DEMO-PRIVATE" not in response.text
    assert "fixture-reviewer" not in response.text


@pytest.mark.parametrize(
    ("parameters", "expected_rows"),
    [
        ({"q": "Follow-up"}, 1),
        ({"q": "no matching measure"}, 0),
        ({"performance_year": 2025}, 1),
        ({"performance_year": 2024}, 0),
        ({"change_status": "modified"}, 1),
        ({"change_status": "unchanged"}, 0),
        ({"affected_field": "definition"}, 1),
        ({"affected_field": "numerator"}, 0),
        ({"verification_status": "partially_verified"}, 1),
        ({"verification_status": "verified"}, 0),
    ],
)
def test_csv_export_reuses_public_measure_filters(
    client: TestClient,
    parameters: dict[str, object],
    expected_rows: int,
) -> None:
    response = client.get(
        "/api/changes/export.csv",
        params={"from_year": 2025, "to_year": 2026, **parameters},
    )

    assert response.status_code == 200
    assert len(_rows(response.text)) == expected_rows


def test_csv_export_escapes_csv_text_and_neutralizes_formula_cells(
    client: TestClient,
    seeded_session: Session,
) -> None:
    measure = seeded_session.scalar(select(Measure).where(Measure.measure_id == "DEMO-001"))
    comparison = seeded_session.scalar(select(MeasureComparison))
    assert measure is not None
    assert comparison is not None
    measure.name = 'Fictional, "quoted"\nmeasure'
    comparison.affected_fields[0].from_value = "=SUM(1, 1)"
    seeded_session.commit()

    response = client.get("/api/changes/export.csv")

    assert response.status_code == 200
    rows = _rows(response.text)
    assert len(rows) == 1
    assert rows[0]["measure_name"] == 'Fictional, "quoted"\nmeasure'
    assert rows[0]["from_value"] == "'=SUM(1, 1)"


def test_csv_export_withholds_unresolved_fields(
    client: TestClient,
    seeded_session: Session,
) -> None:
    comparison = seeded_session.scalar(select(MeasureComparison))
    assert comparison is not None
    comparison.status = ChangeStatus.UNKNOWN
    comparison.affected_fields[0].status = ChangeStatus.UNKNOWN
    comparison.affected_fields[0].to_availability = FieldAvailability.UNRESOLVED
    comparison.affected_fields[0].to_value = None
    seeded_session.commit()

    response = client.get("/api/changes/export.csv")

    assert response.status_code == 200
    assert _rows(response.text) == []


def test_csv_export_validates_year_pair(client: TestClient) -> None:
    response = client.get(
        "/api/changes/export.csv",
        params={"from_year": 2025, "to_year": 2025},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_xlsx_export_opens_with_public_rows_and_data_dictionary(client: TestClient) -> None:
    response = client.get(
        "/api/changes/export.xlsx",
        params={
            "from_year": 2025,
            "to_year": 2026,
            "collection_type": "program_roster",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(XLSX_MEDIA_TYPE)
    assert response.headers["content-disposition"] == (
        'attachment; filename="cms-quality-changes-2025-2026.xlsx"'
    )
    workbook, rows = _xlsx_rows(response.content)
    assert workbook.sheetnames == ["Changes", "Data Dictionary"]
    assert len(rows) == 1
    assert list(rows[0]) == list(CSV_COLUMNS)
    assert rows[0]["measure_id"] == "DEMO-001"
    assert rows[0]["affected_field"] == "definition"
    assert rows[0]["from_year"] == 2025
    assert rows[0]["to_year"] == 2026
    assert isinstance(rows[0]["approved_at"], datetime)
    assert rows[0]["evidence_urls"] == (
        "https://example.invalid/cms-quality-intelligence/demo-source"
    )
    changes_sheet = workbook["Changes"]
    assert changes_sheet.freeze_panes == "A2"
    assert changes_sheet.auto_filter.ref is None
    assert changes_sheet.tables["PublicChanges"].ref == "A1:R2"
    dictionary_rows = list(
        workbook["Data Dictionary"].iter_rows(min_row=2, values_only=True)
    )
    assert len(dictionary_rows) == len(CSV_COLUMNS)
    assert (
        "evidence_urls",
        "text",
        "Pipe-separated official source URLs supporting the row.",
    ) in dictionary_rows
    all_values = " ".join(
        str(cell.value)
        for sheet in workbook.worksheets
        for row in sheet.iter_rows()
        for cell in row
        if cell.value is not None
    )
    assert "DEMO-PRIVATE" not in all_values
    assert "fixture-reviewer" not in all_values


@pytest.mark.parametrize(
    ("parameters", "expected_rows"),
    [
        ({"q": "Follow-up"}, 1),
        ({"q": "no matching measure"}, 0),
        ({"change_status": "modified"}, 1),
        ({"change_status": "unchanged"}, 0),
        ({"affected_field": "definition"}, 1),
        ({"affected_field": "numerator"}, 0),
        ({"verification_status": "partially_verified"}, 1),
        ({"verification_status": "verified"}, 0),
    ],
)
def test_xlsx_export_reuses_public_measure_filters(
    client: TestClient,
    parameters: dict[str, object],
    expected_rows: int,
) -> None:
    response = client.get(
        "/api/changes/export.xlsx",
        params={"from_year": 2025, "to_year": 2026, **parameters},
    )

    assert response.status_code == 200
    _, rows = _xlsx_rows(response.content)
    assert len(rows) == expected_rows


def test_xlsx_export_neutralizes_formula_cells(
    client: TestClient,
    seeded_session: Session,
) -> None:
    measure = seeded_session.scalar(select(Measure).where(Measure.measure_id == "DEMO-001"))
    comparison = seeded_session.scalar(select(MeasureComparison))
    assert measure is not None
    assert comparison is not None
    measure.name = "=HYPERLINK(\"https://example.invalid\")"
    comparison.affected_fields[0].from_value = "+SUM(1, 1)"
    seeded_session.commit()

    response = client.get("/api/changes/export.xlsx")

    assert response.status_code == 200
    workbook, rows = _xlsx_rows(response.content)
    assert rows[0]["measure_name"] == "'=HYPERLINK(\"https://example.invalid\")"
    assert rows[0]["from_value"] == "'+SUM(1, 1)"
    assert all(
        cell.data_type != "f"
        for sheet in workbook.worksheets
        for row in sheet.iter_rows()
        for cell in row
    )
