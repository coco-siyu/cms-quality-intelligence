"""Spreadsheet serialization for the allowlisted public comparison projection."""

import csv
import io
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from openpyxl import Workbook
from openpyxl.cell import Cell
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo

from app.domain import AffectedField, ChangeStatus, FieldAvailability
from app.schemas import PublicChangeRecord

CSV_COLUMNS = (
    "measure_id",
    "measure_name",
    "program",
    "collection_type",
    "from_year",
    "to_year",
    "comparison_status",
    "evidence_status",
    "affected_field",
    "field_change_status",
    "from_availability",
    "from_value",
    "to_availability",
    "to_value",
    "evidence_ids",
    "evidence_urls",
    "approved_at",
    "published_at",
)

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

DATA_DICTIONARY = {
    "measure_id": ("text", "Stable public measure identifier."),
    "measure_name": ("text", "Public measure name."),
    "program": ("text", "CMS program or collection program name."),
    "collection_type": ("text", "Comparison collection type."),
    "from_year": ("integer", "Earlier performance year in the comparison."),
    "to_year": ("integer", "Later performance year in the comparison."),
    "comparison_status": ("text", "Approved overall comparison status."),
    "evidence_status": ("text", "Public evidence-validation status."),
    "affected_field": ("text", "Verified field represented by this row."),
    "field_change_status": ("text", "Approved change status for the field."),
    "from_availability": ("text", "Availability of the earlier-year value."),
    "from_value": ("text", "Approved earlier-year field value, when available."),
    "to_availability": ("text", "Availability of the later-year value."),
    "to_value": ("text", "Approved later-year field value, when available."),
    "evidence_ids": ("text", "Pipe-separated immutable public evidence identifiers."),
    "evidence_urls": ("text", "Pipe-separated official source URLs supporting the row."),
    "approved_at": ("datetime", "UTC timestamp when the comparison was approved."),
    "published_at": ("datetime", "UTC timestamp when the comparison became public."),
}

_COLUMN_WIDTHS = {
    "measure_id": 16,
    "measure_name": 38,
    "program": 34,
    "collection_type": 20,
    "from_year": 12,
    "to_year": 12,
    "comparison_status": 20,
    "evidence_status": 18,
    "affected_field": 20,
    "field_change_status": 22,
    "from_availability": 20,
    "from_value": 48,
    "to_availability": 20,
    "to_value": 48,
    "evidence_ids": 42,
    "evidence_urls": 56,
    "approved_at": 22,
    "published_at": 22,
}


def _iso_datetime(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _spreadsheet_safe(value: object | None) -> str | int:
    """Keep exported text from being interpreted as a spreadsheet formula."""

    if value is None:
        return ""
    if isinstance(value, int):
        return value
    text = str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return f"'{text}"
    return text


def _public_change_rows(
    records: Iterable[PublicChangeRecord],
    *,
    affected_field: AffectedField | None = None,
) -> list[dict[str, Any]]:
    """Project public comparison fields into the shared CSV/XLSX row shape."""

    rows: list[dict[str, Any]] = []
    for record in records:
        for field in record.fields:
            if (
                (affected_field is not None and field.field != affected_field)
                or field.status == ChangeStatus.UNKNOWN
                or field.from_availability == FieldAvailability.UNRESOLVED
                or field.to_availability == FieldAvailability.UNRESOLVED
                or not field.evidence
            ):
                continue
            evidence_ids = sorted({item.evidence_id for item in field.evidence})
            evidence_urls = sorted({str(item.official_url) for item in field.evidence})
            rows.append(
                {
                    "measure_id": record.measure_id,
                    "measure_name": record.measure_name,
                    "program": record.program,
                    "collection_type": record.collection_type.value,
                    "from_year": record.from_year,
                    "to_year": record.to_year,
                    "comparison_status": record.status.value,
                    "evidence_status": record.evidence_status.value,
                    "affected_field": field.field.value,
                    "field_change_status": field.status.value,
                    "from_availability": field.from_availability.value,
                    "from_value": field.from_value,
                    "to_availability": field.to_availability.value,
                    "to_value": field.to_value,
                    "evidence_ids": " | ".join(evidence_ids),
                    "evidence_urls": " | ".join(evidence_urls),
                    "approved_at": record.approved_at,
                    "published_at": record.published_at,
                }
            )
    return rows


def build_public_change_csv(
    records: Iterable[PublicChangeRecord],
    *,
    affected_field: AffectedField | None = None,
) -> str:
    """Write one row per verified public comparison field."""

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\r\n")
    writer.writeheader()
    for row in _public_change_rows(records, affected_field=affected_field):
        csv_row = {
            key: _iso_datetime(value) if isinstance(value, datetime) else value
            for key, value in row.items()
        }
        writer.writerow({key: _spreadsheet_safe(value) for key, value in csv_row.items()})
    return output.getvalue()


def _xlsx_value(value: object | None) -> object:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value
    return _spreadsheet_safe(value)


def _style_header(cells: Iterable[Cell]) -> None:
    for cell in cells:
        cell.fill = PatternFill("solid", fgColor="243B5A")
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(vertical="center", wrap_text=True)


def build_public_change_xlsx(
    records: Iterable[PublicChangeRecord],
    *,
    affected_field: AffectedField | None = None,
) -> bytes:
    """Build a two-sheet XLSX workbook without formulas or private fields."""

    rows = _public_change_rows(records, affected_field=affected_field)
    workbook = Workbook()
    changes = workbook.active
    changes.title = "Changes"
    changes.sheet_view.showGridLines = False
    changes.freeze_panes = "A2"
    changes.append(list(CSV_COLUMNS))
    _style_header(changes[1])
    changes.row_dimensions[1].height = 28

    for row in rows:
        changes.append([_xlsx_value(row[column]) for column in CSV_COLUMNS])

    for column_index, column_name in enumerate(CSV_COLUMNS, start=1):
        letter = changes.cell(row=1, column=column_index).column_letter
        changes.column_dimensions[letter].width = _COLUMN_WIDTHS[column_name]
        for cell in changes[letter][1:]:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        if column_name in {"approved_at", "published_at"}:
            for cell in changes[letter][1:]:
                cell.number_format = "yyyy-mm-dd hh:mm"

    if rows:
        changes_table = Table(displayName="PublicChanges", ref=f"A1:R{changes.max_row}")
        changes_table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        changes.add_table(changes_table)
    else:
        changes.auto_filter.ref = "A1:R1"

    dictionary = workbook.create_sheet("Data Dictionary")
    dictionary.sheet_view.showGridLines = False
    dictionary.freeze_panes = "A2"
    dictionary.append(["column", "type", "description"])
    _style_header(dictionary[1])
    dictionary.row_dimensions[1].height = 28
    for column_name in CSV_COLUMNS:
        value_type, description = DATA_DICTIONARY[column_name]
        dictionary.append([column_name, value_type, description])
    dictionary.column_dimensions["A"].width = 26
    dictionary.column_dimensions["B"].width = 16
    dictionary.column_dimensions["C"].width = 82
    for row in dictionary.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    dictionary_table = Table(
        displayName="ExportDataDictionary",
        ref=f"A1:C{dictionary.max_row}",
    )
    dictionary_table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    dictionary.add_table(dictionary_table)

    workbook.properties.creator = "CMS Quality Intelligence"
    workbook.properties.title = "Verified public measure changes"
    workbook.properties.subject = "One row per verified public comparison field"
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()
