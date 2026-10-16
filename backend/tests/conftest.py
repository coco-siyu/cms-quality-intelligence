from collections.abc import Generator
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.domain import (
    AffectedField,
    ChangeStatus,
    FieldAvailability,
    PublicationState,
    PublicVerificationStatus,
)
from app.main import create_app
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


@pytest.fixture
def session() -> Generator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as database_session:
        yield database_session
    Base.metadata.drop_all(engine)


def _add_version(
    measure: Measure,
    year: int,
    source_revision: SourceRevision,
    *,
    availability: FieldAvailability = FieldAvailability.AVAILABLE,
    publication_state: PublicationState = PublicationState.PUBLISHED,
) -> MeasureVersion:
    checked_at = datetime(2026, 10, 1, 12, tzinfo=UTC)
    field = SpecificationField(
        field=AffectedField.DEFINITION,
        availability=availability,
        value=f"Fictional definition for {year}."
        if availability == FieldAvailability.AVAILABLE
        else None,
    )
    field.evidence.append(
        EvidenceReference(
            evidence_id=f"DEMO-EVIDENCE-{measure.measure_id}-{year}",
            source_revision=source_revision,
            locator=f"Demo section {year}",
            excerpt="Fictional evidence excerpt for automated testing only.",
        )
    )
    version = MeasureVersion(
        version_id=f"DEMO-VERSION-{measure.measure_id}-{year}",
        program="Fictional Quality Program",
        performance_year=year,
        version_number=1,
        is_program_member=True,
        publication_state=publication_state,
        verification_status=PublicVerificationStatus.PARTIALLY_VERIFIED,
        verified_at=checked_at,
        last_source_check_at=checked_at,
        newer_revision_detected=False,
        fields=[field],
    )
    measure.versions.append(version)
    return version


@pytest.fixture
def seeded_session(session: Session) -> Session:
    checked_at = datetime(2026, 10, 1, 12, tzinfo=UTC)
    document = SourceDocument(
        source_id="DEMO-SOURCE-001",
        title="Fictional C1 Test Source",
        official_url="https://example.invalid/cms-quality-intelligence/demo-source",
        mime_type="text/html",
    )
    published_revision = SourceRevision(
        revision_id="DEMO-SOURCE-001-R1",
        revision_number=1,
        content_hash="demo-hash-r1",
        publication_date=date(2026, 9, 1),
        effective_date=date(2026, 9, 1),
        retrieved_at=checked_at,
        last_source_check_at=checked_at,
        publication_state=PublicationState.PUBLISHED,
        verification_status=PublicVerificationStatus.PARTIALLY_VERIFIED,
    )
    document.revisions.append(published_revision)

    public_measure = Measure(
        measure_id="DEMO-001",
        name="Fictional Follow-up Measure",
        description="Synthetic measure for C1 tests; not a CMS record.",
        is_public=True,
    )
    for year in (2025, 2026):
        public_measure.memberships.append(
            ProgramMembership(
                program="Fictional Quality Program",
                performance_year=year,
                is_program_member=True,
                publication_state=PublicationState.PUBLISHED,
                verified_at=checked_at,
            )
        )
        _add_version(public_measure, year, published_revision)
    public_measure.comparisons.append(
        MeasureComparison(
            program="Fictional Quality Program",
            from_year=2025,
            to_year=2026,
            status=ChangeStatus.MODIFIED,
            publication_state=PublicationState.PUBLISHED,
            affected_fields=[MeasureComparisonField(field=AffectedField.DEFINITION)],
        )
    )

    unknown_measure = Measure(
        measure_id="DEMO-002",
        name="Fictional Unresolved Measure",
        description="Synthetic record with unresolved evidence.",
        is_public=True,
    )
    unknown_measure.memberships.append(
        ProgramMembership(
            program="Fictional Quality Program",
            performance_year=2026,
            is_program_member=True,
            publication_state=PublicationState.PUBLISHED,
            verified_at=None,
        )
    )
    _add_version(
        unknown_measure,
        2026,
        published_revision,
        availability=FieldAvailability.UNRESOLVED,
    )

    private_measure = Measure(
        measure_id="DEMO-PRIVATE",
        name="Private Draft Measure",
        description="Must never cross the public API boundary.",
        is_public=False,
    )
    _add_version(private_measure, 2026, published_revision)

    session.add_all([document, public_measure, unknown_measure, private_measure])
    session.commit()
    return session


@pytest.fixture
def client(seeded_session: Session) -> Generator[TestClient]:
    app = create_app()

    def override_database() -> Generator[Session]:
        yield seeded_session

    app.dependency_overrides[get_db] = override_database
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
