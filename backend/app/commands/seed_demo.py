import argparse
import os
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.domain import (
    AffectedField,
    ChangeStatus,
    FieldAvailability,
    PublicationState,
    PublicVerificationStatus,
)
from app.models import (
    EvidenceReference,
    Measure,
    MeasureComparison,
    MeasureComparisonField,
    MeasureVersion,
    ProgramMembership,
    SourceDocument,
    SourceRevision,
    SpecificationField,
)

DEMO_PREFIX = "DEMO-"


def _assert_demo_target() -> None:
    if os.getenv("CMSQI_ALLOW_DEMO_SEED") != "true":
        raise RuntimeError("Set CMSQI_ALLOW_DEMO_SEED=true to confirm demo-data seeding.")
    database_name = make_url(str(SessionLocal.kw["bind"].url)).database or ""
    if "demo" not in database_name.lower():
        raise RuntimeError("Refusing to seed a database whose name does not contain 'demo'.")


def clear_demo_records_in_session(session: Session) -> tuple[int, int]:
    measures = list(
        session.scalars(select(Measure).where(Measure.measure_id.startswith(DEMO_PREFIX)))
    )
    for measure in measures:
        session.delete(measure)
    session.flush()
    documents = list(
        session.scalars(
            select(SourceDocument).where(SourceDocument.source_id.startswith(DEMO_PREFIX))
        )
    )
    for document in documents:
        session.delete(document)
    session.flush()
    return len(measures), len(documents)


def clear_demo_records() -> None:
    with SessionLocal.begin() as session:
        clear_demo_records_in_session(session)


def _field(
    measure_id: str,
    year: int,
    field_name: AffectedField,
    value: str | None,
    revision: SourceRevision,
) -> SpecificationField:
    availability = (
        FieldAvailability.AVAILABLE if value is not None else FieldAvailability.UNRESOLVED
    )
    return SpecificationField(
        field=field_name,
        availability=availability,
        value=value,
        evidence=[
            EvidenceReference(
                evidence_id=f"DEMO-EVIDENCE-{measure_id}-{year}-{field_name.value}",
                source_revision=revision,
                locator=f"Fictional section {year}-{field_name.value}",
                excerpt="Synthetic evidence text for interface and contract testing only.",
            )
        ],
    )


def _version(
    measure_id: str,
    year: int,
    revision: SourceRevision,
    fields: list[SpecificationField],
) -> MeasureVersion:
    return MeasureVersion(
        version_id=f"DEMO-VERSION-{measure_id.removeprefix(DEMO_PREFIX)}-{year}",
        program="Fictional Quality Program",
        performance_year=year,
        version_number=1,
        is_program_member=True,
        publication_state=PublicationState.PUBLISHED,
        verification_status=PublicVerificationStatus.PARTIALLY_VERIFIED,
        verified_at=None,
        last_source_check_at=revision.last_source_check_at,
        newer_revision_detected=False,
        fields=fields,
    )


def seed_demo_records() -> None:
    checked_at = datetime(2026, 10, 1, 12, tzinfo=UTC)
    with SessionLocal.begin() as session:
        if session.scalar(select(Measure).where(Measure.measure_id == "DEMO-001")):
            raise RuntimeError("Demo records already exist. Run with --reset to recreate them.")

        document = SourceDocument(
            source_id="DEMO-SOURCE-001",
            title="Fictional CMS Quality Intelligence Prototype Source",
            official_url="https://example.invalid/cms-quality-intelligence/demo-source",
            mime_type="text/html",
        )
        revision = SourceRevision(
            revision_id="DEMO-SOURCE-001-R1",
            revision_number=1,
            content_hash="demo-only-not-a-source-document-hash",
            publication_date=date(2026, 9, 1),
            effective_date=date(2026, 9, 1),
            retrieved_at=checked_at,
            last_source_check_at=checked_at,
            publication_state=PublicationState.PUBLISHED,
            verification_status=PublicVerificationStatus.PARTIALLY_VERIFIED,
        )
        document.revisions.append(revision)

        first = Measure(
            measure_id="DEMO-001",
            name="Fictional Follow-up Quality Measure",
            description="Synthetic prototype record; not a CMS measure or verified claim.",
            is_public=True,
        )
        for year, definition in (
            (2025, "Fictional baseline definition for interface testing."),
            (2026, "Fictional revised definition for interface testing."),
        ):
            first.memberships.append(_membership(year))
            first.versions.append(
                _version(
                    first.measure_id,
                    year,
                    revision,
                    [
                        _field(
                            first.measure_id, year, AffectedField.DEFINITION, definition, revision
                        ),
                        _field(
                            first.measure_id,
                            year,
                            AffectedField.DENOMINATOR,
                            "Synthetic denominator; no patient-level data.",
                            revision,
                        ),
                    ],
                )
            )
        first.comparisons.append(
            MeasureComparison(
                program="Fictional Quality Program",
                from_year=2025,
                to_year=2026,
                status=ChangeStatus.MODIFIED,
                publication_state=PublicationState.PUBLISHED,
                affected_fields=[MeasureComparisonField(field=AffectedField.DEFINITION)],
            )
        )

        second = Measure(
            measure_id="DEMO-002",
            name="Fictional Evidence Review Measure",
            description="Synthetic unresolved example; not a verified removal or CMS claim.",
            is_public=True,
            memberships=[_membership(2026)],
            versions=[
                _version(
                    "DEMO-002",
                    2026,
                    revision,
                    [_field("DEMO-002", 2026, AffectedField.ELIGIBILITY, None, revision)],
                )
            ],
        )
        session.add_all([document, first, second])


def _membership(year: int) -> ProgramMembership:
    return ProgramMembership(
        program="Fictional Quality Program",
        performance_year=year,
        is_program_member=True,
        publication_state=PublicationState.PUBLISHED,
        verified_at=None,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed explicitly fictional C1 demo records.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete only DEMO-* records, then recreate the fixture set.",
    )
    args = parser.parse_args()
    _assert_demo_target()
    if args.reset:
        clear_demo_records()
    seed_demo_records()
    print("Seeded 2 fictional DEMO-* measures; no CMS or patient data was loaded.")


if __name__ == "__main__":
    main()
