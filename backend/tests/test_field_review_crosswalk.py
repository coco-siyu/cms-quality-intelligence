import csv
from collections import Counter
from pathlib import Path

from app.commands.prepare_review_crosswalk import FIELD_NAMES

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCES_DIR = REPOSITORY_ROOT / "docs/sources"


def _csv_rows(filename: str) -> list[dict[str, str]]:
    with (SOURCES_DIR / filename).open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def test_review_crosswalk_covers_every_variant_and_field() -> None:
    variants = _csv_rows("collection-variants.csv")
    rows = _csv_rows("field-review-crosswalk.csv")
    variant_ids = {variant["variant_id"] for variant in variants}

    assert len(variant_ids) == 32
    assert len(rows) == len(variant_ids) * len(FIELD_NAMES)
    assert len({row["review_item_id"] for row in rows}) == len(rows)
    assert {row["variant_id"] for row in rows} == variant_ids
    assert Counter(row["field_name"] for row in rows) == {
        field_name: len(variant_ids) for field_name in FIELD_NAMES
    }


def test_review_crosswalk_remains_pending_and_source_backed() -> None:
    rows = _csv_rows("field-review-crosswalk.csv")
    revisions = {
        revision["source_id"]: revision
        for revision in _csv_rows("source-revisions.csv")
    }
    allowed_statuses = {
        "candidate_extracted_needs_sme_review",
        "manual_extraction_or_policy_review_required",
        "not_applicable_candidate_needs_sme_confirmation",
        "source_detail_not_snapshotted",
    }

    assert all(row["review_decision"] == "pending" for row in rows)
    assert all(row["reviewer_name"] == "" for row in rows)
    assert all(row["reviewed_at"] == "" for row in rows)
    assert all(row["extraction_status"] in allowed_statuses for row in rows)
    assert all(row["candidate_value"] for row in rows)
    assert all(row["evidence_locator"] for row in rows)
    for row in rows:
        assert row["source_id"] in revisions
        assert row["source_sha256"] == revisions[row["source_id"]]["sha256"]


def test_unsnapshotted_2026_ecqm_details_are_not_silently_filled() -> None:
    rows = _csv_rows("field-review-crosswalk.csv")
    unavailable = [
        row
        for row in rows
        if row["performance_year"] == "2026"
        and row["collection_type"] == "eCQM"
        and row["field_name"]
        not in {"measure_title", "specification_identifier", "data_collection"}
    ]

    assert len(unavailable) == 40
    assert all(
        row["extraction_status"] == "source_detail_not_snapshotted"
        for row in unavailable
    )
