import csv
from pathlib import Path

import pytest

from app.commands.verify_sources import (
    DownloadResult,
    _extension,
    load_inventory,
    write_manifest,
)


def test_load_inventory_rejects_duplicate_source_ids(tmp_path: Path) -> None:
    inventory = tmp_path / "inventory.csv"
    inventory.write_text(
        "source_id,official_url\n"
        "CMS-ONE,https://www.cms.gov/one\n"
        "CMS-ONE,https://www.cms.gov/two\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate source_id"):
        load_inventory(inventory)


def test_extension_prefers_supported_url_suffix() -> None:
    assert (
        _extension("https://www.cms.gov/source.PDF?version=1", "application/octet-stream")
        == ".pdf"
    )
    assert _extension("https://www.cms.gov/source", "application/pdf") == ".pdf"


def test_write_manifest_preserves_hash_and_review_state(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    result = DownloadResult(
        source_id="CMS-ONE",
        official_url="https://www.cms.gov/one.pdf",
        retrieved_at="2026-10-16T18:00:00+00:00",
        final_url="https://www.cms.gov/one.pdf",
        http_status="200",
        mime_type="application/pdf",
        byte_length="3",
        sha256="abc123",
        cache_path="var/cms-sources/CMS-ONE.pdf",
        verification_state="downloaded_unreviewed",
        error="",
    )

    write_manifest([result], manifest)

    with manifest.open(newline="", encoding="utf-8") as manifest_file:
        rows = list(csv.DictReader(manifest_file))
    assert rows == [
        {
            "source_id": "CMS-ONE",
            "official_url": "https://www.cms.gov/one.pdf",
            "retrieved_at": "2026-10-16T18:00:00+00:00",
            "final_url": "https://www.cms.gov/one.pdf",
            "http_status": "200",
            "mime_type": "application/pdf",
            "byte_length": "3",
            "sha256": "abc123",
            "cache_path": "var/cms-sources/CMS-ONE.pdf",
            "verification_state": "downloaded_unreviewed",
            "error": "",
        }
    ]
