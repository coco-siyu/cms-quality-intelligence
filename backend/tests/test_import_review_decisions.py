import csv
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.commands.import_review_decisions import import_review_decisions
from app.commands.seed_verified import seed_verified_drafts
from app.domain import CandidateReviewDecision
from app.models import Measure, SpecificationFieldCandidate, SpecificationFieldCandidateReview

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CROSSWALK_PATH = REPOSITORY_ROOT / "docs/sources/field-review-crosswalk.csv"


def _review_csv(tmp_path: Path) -> Path:
    with CROSSWALK_PATH.open(newline="", encoding="utf-8") as crosswalk_file:
        rows = list(csv.DictReader(crosswalk_file))
        fieldnames = list(rows[0])

    approve_row = rows[0]
    needs_revision_row = rows[1]
    not_applicable_row = next(
        row
        for row in rows
        if row["extraction_status"]
        == "not_applicable_candidate_needs_sme_confirmation"
    )
    reviewed_at = "2026-10-19T12:00:00-04:00"
    approve_row.update(
        review_decision="approve",
        reviewer_name="Qualified Reviewer",
        reviewed_at=reviewed_at,
    )
    needs_revision_row.update(
        review_decision="needs_revision",
        reviewer_name="Qualified Reviewer",
        reviewed_at=reviewed_at,
        reviewer_notes="The source section needs a corrected interpretation.",
    )
    not_applicable_row.update(
        review_decision="not_applicable",
        reviewer_name="Qualified Reviewer",
        reviewed_at=reviewed_at,
        reviewer_notes="Confirmed that this field does not apply to the collection model.",
    )

    output = tmp_path / "review-decisions.csv"
    with output.open("w", newline="", encoding="utf-8") as review_file:
        writer = csv.DictWriter(review_file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return output


def test_review_import_is_dry_run_by_default_and_idempotent(
    session: Session, tmp_path: Path
) -> None:
    assert seed_verified_drafts(session) == (8, 14, 32, 352)
    session.commit()
    review_path = _review_csv(tmp_path)

    dry_run = import_review_decisions(session, review_path)
    assert dry_run.decided_rows == 3
    assert dry_run.pending_rows == 349
    assert dry_run.imported_events == 0
    assert session.scalar(
        select(func.count()).select_from(SpecificationFieldCandidateReview)
    ) == 0

    first_import = import_review_decisions(session, review_path, apply=True)
    session.commit()
    assert first_import.imported_events == 3
    assert first_import.existing_events == 0

    second_import = import_review_decisions(session, review_path, apply=True)
    session.commit()
    assert second_import.imported_events == 0
    assert second_import.existing_events == 3

    reviewed = list(
        session.scalars(
            select(SpecificationFieldCandidate).where(
                SpecificationFieldCandidate.review_decision
                != CandidateReviewDecision.PENDING
            )
        )
    )
    assert {candidate.review_decision for candidate in reviewed} == {
        CandidateReviewDecision.APPROVE,
        CandidateReviewDecision.NEEDS_REVISION,
        CandidateReviewDecision.NOT_APPLICABLE,
    }
    approved = next(
        candidate
        for candidate in reviewed
        if candidate.review_decision == CandidateReviewDecision.APPROVE
    )
    assert approved.reviewed_value == approved.candidate_value
    assert all(measure.is_public is False for measure in session.scalars(select(Measure)))
    assert session.scalar(
        select(func.count()).select_from(SpecificationFieldCandidateReview)
    ) == 3


def test_review_import_rejects_changed_source_evidence(
    session: Session, tmp_path: Path
) -> None:
    seed_verified_drafts(session)
    session.commit()
    review_path = _review_csv(tmp_path)

    with review_path.open(newline="", encoding="utf-8") as review_file:
        rows = list(csv.DictReader(review_file))
        fieldnames = list(rows[0])
    rows[0]["source_sha256"] = "tampered-source-hash"
    with review_path.open("w", newline="", encoding="utf-8") as review_file:
        writer = csv.DictWriter(review_file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="source_sha256 differs from private staging"):
        import_review_decisions(session, review_path, apply=True)

    assert session.scalar(
        select(func.count()).select_from(SpecificationFieldCandidateReview)
    ) == 0


def test_review_import_requires_identity_timestamp_and_notes(
    session: Session, tmp_path: Path
) -> None:
    seed_verified_drafts(session)
    session.commit()
    review_path = _review_csv(tmp_path)

    with review_path.open(newline="", encoding="utf-8") as review_file:
        rows = list(csv.DictReader(review_file))
        fieldnames = list(rows[0])
    rows[0]["reviewer_name"] = ""
    with review_path.open("w", newline="", encoding="utf-8") as review_file:
        writer = csv.DictWriter(review_file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="reviewer_name is required"):
        import_review_decisions(session, review_path, apply=True)


def test_review_import_accepts_field_evidence_csv_export(
    session: Session, tmp_path: Path
) -> None:
    seed_verified_drafts(session)
    session.commit()
    review_path = _review_csv(tmp_path)
    with review_path.open(newline="", encoding="utf-8") as review_file:
        rows = list(csv.DictReader(review_file))
        canonical_headers = list(rows[0])

    friendly_headers = {
        "review_item_id": "Review item ID",
        "variant_id": "Variant ID",
        "quality_id": "Quality ID",
        "performance_year": "Performance year",
        "collection_type": "Collection type",
        "specification_identifier": "Specification ID",
        "field_name": "Field",
        "candidate_value": "Candidate value",
        "source_id": "Source ID",
        "source_sha256": "Source SHA-256",
        "evidence_locator": "Evidence locator",
        "extraction_status": "Extraction status",
        "review_decision": "Review decision",
        "reviewer_name": "Reviewer",
        "reviewed_at": "Reviewed date",
        "reviewer_notes": "Reviewer notes",
    }
    for row in rows:
        if row["review_decision"] != "pending":
            row["reviewed_at"] = "2026-10-19"

    with review_path.open("w", newline="", encoding="utf-8") as review_file:
        writer = csv.writer(review_file, lineterminator="\n")
        writer.writerows(
            [
                [],
                ["Field evidence and reviewer decisions"],
                ["Candidate text is not approved until reviewed."],
                [],
                [friendly_headers[header] for header in canonical_headers],
            ]
        )
        writer.writerows([[row[header] for header in canonical_headers] for row in rows])

    result = import_review_decisions(session, review_path)
    assert result.decided_rows == 3
    assert result.pending_rows == 349
