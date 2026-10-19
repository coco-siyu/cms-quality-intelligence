import csv
import json
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCES_DIR = REPOSITORY_ROOT / "docs/sources"
SEED_PATH = REPOSITORY_ROOT / "backend/app/data/cms_app_plus_2025_2026.seed.json"


def _csv_rows(filename: str) -> list[dict[str, str]]:
    with (SOURCES_DIR / filename).open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def test_verified_seed_matches_membership_reconciliation() -> None:
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    candidates = _csv_rows("measure-membership-candidates.csv")
    measures = {measure["measure_id"]: measure for measure in seed["measures"]}

    assert seed["publication_state"] == "draft"
    assert seed["is_public"] is False
    assert set(measures) == {candidate["quality_id"] for candidate in candidates}

    for candidate in candidates:
        expected_years = {
            year
            for year in (2025, 2026)
            if candidate[f"py{year}_candidate_member"] == "true"
        }
        measure = measures[candidate["quality_id"]]
        assert set(measure["memberships"]) == expected_years
        assert measure["membership_verification_status"] == "verified"


def test_evidence_hashes_match_retrieved_source_revisions() -> None:
    revisions = {row["source_id"]: row for row in _csv_rows("source-revisions.csv")}
    evidence = _csv_rows("evidence-locators.csv")

    assert len(revisions) == 24
    assert all(row["verification_state"] == "downloaded_unreviewed" for row in revisions.values())
    assert all(row["review_status"] == "verified_membership" for row in evidence)
    for row in evidence:
        assert row["source_id"] in revisions
        assert row["source_sha256"] == revisions[row["source_id"]]["sha256"]

    assert (
        revisions["CMS-APPPLUS-PY2026-QPS-2025-12"]["sha256"]
        == revisions["CMS-APPPLUS-PY2026-QPS-ALIAS"]["sha256"]
    )


def test_every_seed_variant_has_a_located_source() -> None:
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    variants = {row["variant_id"]: row for row in _csv_rows("collection-variants.csv")}
    source_ids = {row["source_id"] for row in _csv_rows("source-inventory.csv")}

    assert len(variants) == 32
    for variant in variants.values():
        assert variant["source_id"] in source_ids
        assert variant["verification_status"] == "located_not_field_verified"

    for measure in seed["measures"]:
        for variant_id in measure["specification_variant_ids"]:
            variant = variants[variant_id]
            assert variant["quality_id"] == measure["measure_id"]
            assert int(variant["performance_year"]) in measure["memberships"]

    excluded = seed["excluded_variant_candidates"]
    assert excluded == [
        {
            "performance_year": 2025,
            "quality_ids": ["001", "112", "134", "236"],
            "collection_type": "Medicare Part B Claims",
            "status": "excluded_not_app_plus_collection_type",
            "reason": excluded[0]["reason"],
        }
    ]
