import argparse
import csv
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, selectinload

from app.database import SessionLocal
from app.domain import CandidateReviewDecision
from app.models import (
    SourceRevision,
    SpecificationFieldCandidate,
    SpecificationFieldCandidateReview,
)
from app.services.reviews import record_candidate_review, review_event_key

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = REPOSITORY_ROOT / "docs/sources/field-review-crosswalk.csv"
REQUIRED_COLUMNS = {
    "review_item_id",
    "candidate_value",
    "source_id",
    "source_sha256",
    "evidence_locator",
    "review_decision",
    "reviewer_name",
    "reviewed_at",
    "reviewer_notes",
}
HEADER_ALIASES = {
    "Review item ID": "review_item_id",
    "Variant ID": "variant_id",
    "Quality ID": "quality_id",
    "Performance year": "performance_year",
    "Collection type": "collection_type",
    "Specification ID": "specification_identifier",
    "Field": "field_name",
    "Candidate value": "candidate_value",
    "Source ID": "source_id",
    "Source SHA-256": "source_sha256",
    "Evidence locator": "evidence_locator",
    "Extraction status": "extraction_status",
    "Review decision": "review_decision",
    "Reviewer": "reviewer_name",
    "Reviewed date": "reviewed_at",
    "Reviewer notes": "reviewer_notes",
}


@dataclass(frozen=True)
class ReviewPlan:
    candidate: SpecificationFieldCandidate
    decision: CandidateReviewDecision
    reviewed_value: str | None
    reviewer_name: str
    reviewed_at: datetime
    reviewer_notes: str | None
    event_key: str


@dataclass(frozen=True)
class ReviewImportResult:
    decided_rows: int
    pending_rows: int
    imported_events: int
    existing_events: int


def _parse_reviewed_at(value: str, review_item_id: str) -> datetime:
    if len(value) == 10:
        try:
            return datetime.combine(date.fromisoformat(value), time.min, tzinfo=UTC)
        except ValueError:
            pass
    try:
        reviewed_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(
            f"{review_item_id}: reviewed_at must be an ISO 8601 timestamp."
        ) from error
    if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
        raise ValueError(f"{review_item_id}: reviewed_at must include a UTC offset.")
    return reviewed_at.astimezone(UTC)


def _read_rows(path: Path) -> list[dict[str, str]]:
    if path.suffix.lower() != ".csv":
        raise ValueError("Review decisions must be exported as a CSV file.")
    with path.open(newline="", encoding="utf-8-sig") as review_file:
        raw_rows = list(csv.reader(review_file))
    header_index: int | None = None
    fieldnames: list[str] = []
    for index, row in enumerate(raw_rows[:10]):
        normalized = [HEADER_ALIASES.get(value.strip(), value.strip()) for value in row]
        if REQUIRED_COLUMNS <= set(normalized):
            header_index = index
            fieldnames = normalized
            break
    if header_index is None:
        raise ValueError(
            "Review CSV is missing required columns: "
            + ", ".join(sorted(REQUIRED_COLUMNS))
        )
    rows = []
    for raw_row in raw_rows[header_index + 1 :]:
        padded = raw_row + [""] * (len(fieldnames) - len(raw_row))
        row = dict(zip(fieldnames, padded, strict=False))
        if any(value.strip() for value in row.values()):
            rows.append(row)
    if not rows:
        raise ValueError("Review CSV contains no rows.")
    return rows


def _candidate_map(session: Session) -> dict[str, SpecificationFieldCandidate]:
    candidates = session.scalars(
        select(SpecificationFieldCandidate).options(
            selectinload(SpecificationFieldCandidate.source_revision).selectinload(
                SourceRevision.source_document
            ),
            selectinload(SpecificationFieldCandidate.measure_version),
        )
    )
    return {candidate.review_item_id: candidate for candidate in candidates}


def _review_plans(
    session: Session, rows: list[dict[str, str]]
) -> tuple[list[ReviewPlan], int]:
    candidates = _candidate_map(session)
    plans: list[ReviewPlan] = []
    pending_rows = 0
    seen_review_items: set[str] = set()

    for row in rows:
        review_item_id = row["review_item_id"].strip()
        if not review_item_id:
            raise ValueError("Every review row must have a review_item_id.")
        if review_item_id in seen_review_items:
            raise ValueError(f"Duplicate review_item_id in CSV: {review_item_id}")
        seen_review_items.add(review_item_id)

        candidate = candidates.get(review_item_id)
        if candidate is None:
            raise ValueError(f"Unknown review_item_id: {review_item_id}")

        source_revision = candidate.source_revision
        immutable_values = {
            "candidate_value": candidate.candidate_value,
            "source_id": source_revision.source_document.source_id,
            "source_sha256": source_revision.content_hash,
            "evidence_locator": candidate.evidence_locator,
        }
        for field_name, expected in immutable_values.items():
            if row[field_name] != expected:
                raise ValueError(
                    f"{review_item_id}: {field_name} differs from private staging."
                )

        try:
            decision = CandidateReviewDecision(row["review_decision"].strip())
        except ValueError as error:
            allowed = ", ".join(value.value for value in CandidateReviewDecision)
            raise ValueError(
                f"{review_item_id}: review_decision must be one of {allowed}."
            ) from error

        reviewer_name = row["reviewer_name"].strip()
        reviewed_at_text = row["reviewed_at"].strip()
        reviewer_notes = row["reviewer_notes"].strip() or None

        if decision == CandidateReviewDecision.PENDING:
            if reviewer_name or reviewed_at_text or reviewer_notes:
                raise ValueError(
                    f"{review_item_id}: pending rows cannot contain reviewer metadata."
                )
            pending_rows += 1
            continue

        if not reviewer_name:
            raise ValueError(f"{review_item_id}: reviewer_name is required.")
        if not reviewed_at_text:
            raise ValueError(f"{review_item_id}: reviewed_at is required.")
        if decision != CandidateReviewDecision.APPROVE and not reviewer_notes:
            raise ValueError(
                f"{review_item_id}: reviewer_notes are required for {decision.value}."
            )
        if (
            decision == CandidateReviewDecision.APPROVE
            and candidate.measure_version.newer_revision_detected
        ):
            raise ValueError(
                f"{review_item_id}: approval is blocked because a newer source revision "
                "was detected."
            )

        reviewed_at = _parse_reviewed_at(reviewed_at_text, review_item_id)
        reviewed_value = (
            candidate.candidate_value
            if decision == CandidateReviewDecision.APPROVE
            else None
        )
        plans.append(
            ReviewPlan(
                candidate=candidate,
                decision=decision,
                reviewed_value=reviewed_value,
                reviewer_name=reviewer_name,
                reviewed_at=reviewed_at,
                reviewer_notes=reviewer_notes,
                event_key=review_event_key(
                    review_item_id,
                    decision,
                    reviewed_value,
                    reviewer_name,
                    reviewed_at,
                    reviewer_notes,
                ),
            )
        )

    return plans, pending_rows


def import_review_decisions(
    session: Session, path: Path, *, apply: bool = False
) -> ReviewImportResult:
    rows = _read_rows(path)
    plans, pending_rows = _review_plans(session, rows)
    existing_keys = set(
        session.scalars(
            select(SpecificationFieldCandidateReview.event_key).where(
                SpecificationFieldCandidateReview.event_key.in_(
                    [plan.event_key for plan in plans]
                )
            )
        )
    ) if plans else set()
    new_plans = [plan for plan in plans if plan.event_key not in existing_keys]

    if apply:
        for plan in new_plans:
            record_candidate_review(
                plan.candidate,
                decision=plan.decision,
                reviewed_value=plan.reviewed_value,
                reviewer_name=plan.reviewer_name,
                reviewed_at=plan.reviewed_at,
                reviewer_notes=plan.reviewer_notes,
            )
        session.flush()

    return ReviewImportResult(
        decided_rows=len(plans),
        pending_rows=pending_rows,
        imported_events=len(new_plans) if apply else 0,
        existing_events=len(existing_keys),
    )


def _assert_safe_target() -> None:
    if os.getenv("CMSQI_ALLOW_REVIEW_IMPORT") != "true":
        raise RuntimeError(
            "Set CMSQI_ALLOW_REVIEW_IMPORT=true to import private review decisions."
        )
    database_name = make_url(str(SessionLocal.kw["bind"].url)).database or ""
    if not any(marker in database_name.lower() for marker in ("demo", "dev")):
        raise RuntimeError(
            "Refusing to import reviews into a database whose name does not contain "
            "'demo' or 'dev'."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate or import private CMS field-review decisions without publishing data."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist valid decisions as private current state and append-only audit events.",
    )
    args = parser.parse_args()

    if args.apply:
        _assert_safe_target()

    with SessionLocal.begin() as session:
        result = import_review_decisions(session, args.input, apply=args.apply)

    print(
        f"Validated {result.decided_rows} decided rows and "
        f"{result.pending_rows} pending rows."
    )
    if args.apply:
        print(
            f"Imported {result.imported_events} new private review events; "
            f"{result.existing_events} were already present."
        )
        print("No fields or measures were published.")
    else:
        print("Dry run only. No database records were changed.")


if __name__ == "__main__":
    main()
