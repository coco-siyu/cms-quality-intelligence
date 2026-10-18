import csv
import json
import os
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.domain import (
    AffectedField,
    FieldAvailability,
    PublicationState,
    PublicVerificationStatus,
)
from app.models import (
    EvidenceReference,
    Measure,
    MeasureVersion,
    ProgramMembership,
    SourceDocument,
    SourceRevision,
    SpecificationField,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SEED_PATH = REPOSITORY_ROOT / "backend/app/data/cms_app_plus_2025_2026.seed.json"
SOURCES_DIR = REPOSITORY_ROOT / "docs/sources"
PROGRAM = "Medicare Shared Savings Program — APP Plus"


def _csv_rows(filename: str) -> list[dict[str, str]]:
    with (SOURCES_DIR / filename).open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def _load_seed() -> dict[str, Any]:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def _full_date(value: str) -> date | None:
    return date.fromisoformat(value) if len(value) == 10 and value != "unknown" else None


def _source_revisions(session: Session) -> dict[str, SourceRevision]:
    inventory = {row["source_id"]: row for row in _csv_rows("source-inventory.csv")}
    manifests = {row["source_id"]: row for row in _csv_rows("source-revisions.csv")}
    evidence_source_ids = {row["source_id"] for row in _csv_rows("evidence-locators.csv")}
    revisions: dict[str, SourceRevision] = {}

    for source_id in sorted(evidence_source_ids):
        inventory_row = inventory[source_id]
        manifest = manifests[source_id]
        document = session.scalar(
            select(SourceDocument).where(SourceDocument.source_id == source_id)
        )
        if document is None:
            document = SourceDocument(
                source_id=source_id,
                title=inventory_row["title"],
                official_url=inventory_row["official_url"],
                mime_type=manifest["mime_type"],
            )
            session.add(document)
            session.flush()
        elif document.official_url != inventory_row["official_url"]:
            raise RuntimeError(f"Existing source URL conflicts with verified seed: {source_id}")

        revision = session.scalar(
            select(SourceRevision).where(
                SourceRevision.source_document_id == document.id,
                SourceRevision.content_hash == manifest["sha256"],
            )
        )
        if revision is None:
            checked_at = datetime.fromisoformat(manifest["retrieved_at"]).astimezone(UTC)
            revision = SourceRevision(
                revision_id=f"{source_id}-R-{manifest['sha256'][:12]}",
                revision_number=len(document.revisions) + 1,
                content_hash=manifest["sha256"],
                publication_date=_full_date(inventory_row["publication_or_revision_date"]),
                effective_date=None,
                retrieved_at=checked_at,
                last_source_check_at=checked_at,
                publication_state=PublicationState.DRAFT,
                verification_status=PublicVerificationStatus.VERIFIED,
            )
            document.revisions.append(revision)
            session.flush()
        revisions[source_id] = revision
    return revisions


def _membership_evidence(
    year: int,
    measure_id: str,
    source_revisions: dict[str, SourceRevision],
) -> list[EvidenceReference]:
    rows = [
        row
        for row in _csv_rows("evidence-locators.csv")
        if int(row["performance_year"]) == year
        and measure_id in row["quality_ids"].split("|")
    ]
    return [
        EvidenceReference(
            evidence_id=f"CMS-EVIDENCE-{measure_id}-{year}-{index}",
            source_revision=source_revisions[row["source_id"]],
            locator=row["locator"],
            excerpt=row["evidence_summary"],
        )
        for index, row in enumerate(rows, start=1)
    ]


def seed_verified_drafts(session: Session) -> tuple[int, int]:
    seed = _load_seed()
    if seed["is_public"] is not False or seed["publication_state"] != "draft":
        raise RuntimeError("Verified seed artifact must remain draft and non-public.")

    source_revisions = _source_revisions(session)
    created_measures = 0
    created_versions = 0
    checked_at = max(revision.retrieved_at for revision in source_revisions.values())

    for record in seed["measures"]:
        measure = session.scalar(
            select(Measure).where(Measure.measure_id == record["measure_id"])
        )
        if measure is None:
            measure = Measure(
                measure_id=record["measure_id"],
                name=record["name"],
                description=record["description"],
                is_public=False,
            )
            session.add(measure)
            session.flush()
            created_measures += 1
        elif measure.is_public or measure.name != record["name"]:
            raise RuntimeError(
                f"Existing measure conflicts with verified draft seed: {record['measure_id']}"
            )

        for year in record["memberships"]:
            membership = session.scalar(
                select(ProgramMembership).where(
                    ProgramMembership.measure_id == measure.id,
                    ProgramMembership.program == PROGRAM,
                    ProgramMembership.performance_year == year,
                )
            )
            if membership is None:
                measure.memberships.append(
                    ProgramMembership(
                        program=PROGRAM,
                        performance_year=year,
                        is_program_member=True,
                        publication_state=PublicationState.DRAFT,
                        verified_at=checked_at,
                    )
                )

            version_id = f"CMS-APPPLUS-{record['measure_id']}-PY{year}-ROSTER-R1"
            version = session.scalar(
                select(MeasureVersion).where(MeasureVersion.version_id == version_id)
            )
            if version is None:
                measure.versions.append(
                    MeasureVersion(
                        version_id=version_id,
                        program=PROGRAM,
                        performance_year=year,
                        version_number=1,
                        is_program_member=True,
                        publication_state=PublicationState.DRAFT,
                        verification_status=PublicVerificationStatus.PARTIALLY_VERIFIED,
                        verified_at=checked_at,
                        last_source_check_at=checked_at,
                        newer_revision_detected=False,
                        fields=[
                            SpecificationField(
                                field=AffectedField.MEASURE_SET,
                                availability=FieldAvailability.AVAILABLE,
                                value=f"Member of the PY{year} MSSP APP Plus quality measure set.",
                                evidence=_membership_evidence(
                                    year, record["measure_id"], source_revisions
                                ),
                            )
                        ],
                    )
                )
                created_versions += 1

    session.flush()
    return created_measures, created_versions


def _assert_safe_target() -> None:
    if os.getenv("CMSQI_ALLOW_VERIFIED_DRAFT_SEED") != "true":
        raise RuntimeError(
            "Set CMSQI_ALLOW_VERIFIED_DRAFT_SEED=true to prepare verified non-public drafts."
        )
    database_name = make_url(str(SessionLocal.kw["bind"].url)).database or ""
    if not any(marker in database_name.lower() for marker in ("demo", "dev")):
        raise RuntimeError(
            "Refusing to seed a database whose name does not contain 'demo' or 'dev'."
        )


def main() -> None:
    _assert_safe_target()
    with SessionLocal.begin() as session:
        created_measures, created_versions = seed_verified_drafts(session)
    print(
        f"Prepared {created_measures} new non-public measures and "
        f"{created_versions} new draft roster versions."
    )
    print("No records were published; running the command again is idempotent.")


if __name__ == "__main__":
    main()
