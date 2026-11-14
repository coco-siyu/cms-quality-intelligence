"""CSV serialization for the allowlisted public comparison projection."""

import csv
import io
from collections.abc import Iterable
from datetime import datetime

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


def build_public_change_csv(
    records: Iterable[PublicChangeRecord],
    *,
    affected_field: AffectedField | None = None,
) -> str:
    """Write one row per verified public comparison field."""

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\r\n")
    writer.writeheader()
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
            row = {
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
                "approved_at": _iso_datetime(record.approved_at),
                "published_at": _iso_datetime(record.published_at),
            }
            writer.writerow({key: _spreadsheet_safe(value) for key, value in row.items()})
    return output.getvalue()
