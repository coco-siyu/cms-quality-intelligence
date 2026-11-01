from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain import (
    AffectedField,
    ChangeEvidenceSide,
    ChangeStatus,
    CollectionType,
    FieldAvailability,
    PublicationState,
)
from app.models import (
    Measure,
    MeasureComparison,
    MeasureComparisonEvidence,
    MeasureComparisonField,
    MeasureVersion,
    SourceDocument,
    SourceRevision,
    SpecificationField,
)


def test_unavailable_field_cannot_carry_a_value(session: Session) -> None:
    measure = Measure(
        measure_id="DEMO-CONSTRAINT",
        name="Constraint test",
        description="Synthetic test record.",
        is_public=False,
        versions=[
            MeasureVersion(
                version_id="DEMO-CONSTRAINT-V1",
                program="Fictional Quality Program",
                performance_year=2026,
                version_number=1,
                is_program_member=True,
                last_source_check_at=datetime(2026, 10, 1, 12, tzinfo=UTC),
                fields=[
                    SpecificationField(
                        field=AffectedField.DEFINITION,
                        availability=FieldAvailability.UNAVAILABLE,
                        value="This invalid value must be rejected.",
                    )
                ],
            )
        ],
    )
    session.add(measure)

    with pytest.raises(IntegrityError):
        session.commit()


def test_historical_measure_versions_and_source_revisions_are_retained(session: Session) -> None:
    checked_at = datetime(2026, 10, 1, 12, tzinfo=UTC)
    document = SourceDocument(
        source_id="DEMO-HISTORY-SOURCE",
        title="Fictional revision history source",
        official_url="https://example.invalid/history-source",
        mime_type="text/html",
        revisions=[
            SourceRevision(
                revision_id="DEMO-HISTORY-R1",
                revision_number=1,
                content_hash="history-hash-1",
                retrieved_at=checked_at,
                last_source_check_at=checked_at,
            ),
            SourceRevision(
                revision_id="DEMO-HISTORY-R2",
                revision_number=2,
                content_hash="history-hash-2",
                retrieved_at=checked_at,
                last_source_check_at=checked_at,
            ),
        ],
    )
    measure = Measure(
        measure_id="DEMO-HISTORY",
        name="Version history test",
        description="Synthetic history record.",
        is_public=False,
        versions=[
            MeasureVersion(
                version_id=f"DEMO-HISTORY-V{version_number}",
                program="Fictional Quality Program",
                performance_year=2026,
                version_number=version_number,
                is_program_member=True,
                last_source_check_at=checked_at,
            )
            for version_number in (1, 2)
        ],
    )
    session.add_all([document, measure])
    session.commit()

    assert [revision.revision_number for revision in document.revisions] == [1, 2]
    assert [version.version_number for version in measure.versions] == [1, 2]


def test_collection_variants_have_independent_version_streams(session: Session) -> None:
    checked_at = datetime(2026, 10, 1, 12, tzinfo=UTC)
    measure = Measure(
        measure_id="DEMO-VARIANTS",
        name="Collection variant test",
        description="Synthetic collection-variant record.",
        is_public=False,
        versions=[
            MeasureVersion(
                version_id=f"DEMO-VARIANT-{collection_type.value}",
                program="Fictional Quality Program",
                performance_year=2026,
                collection_type=collection_type,
                specification_identifier=identifier,
                version_number=1,
                is_program_member=True,
                last_source_check_at=checked_at,
            )
            for collection_type, identifier in (
                (CollectionType.ECQM, "DEMO1v1"),
                (CollectionType.MIPS_CQM, "Quality ID DEMO1"),
            )
        ],
    )
    session.add(measure)
    session.commit()

    assert {version.collection_type for version in measure.versions} == {
        CollectionType.ECQM,
        CollectionType.MIPS_CQM,
    }


def test_unresolved_comparison_side_cannot_be_claimed_as_removed(session: Session) -> None:
    measure = Measure(
        measure_id="DEMO-UNRESOLVED-COMPARISON",
        name="Unresolved comparison constraint test",
        description="Synthetic test record.",
        is_public=False,
        comparisons=[
            MeasureComparison(
                program="Fictional Quality Program",
                from_year=2025,
                to_year=2026,
                status=ChangeStatus.REMOVED,
                publication_state=PublicationState.DRAFT,
                affected_fields=[
                    MeasureComparisonField(
                        field=AffectedField.MEASURE_SET,
                        status=ChangeStatus.REMOVED,
                        from_availability=FieldAvailability.AVAILABLE,
                        from_value="true",
                        to_availability=FieldAvailability.UNRESOLVED,
                        to_value=None,
                    )
                ],
            )
        ],
    )
    session.add(measure)

    with pytest.raises(IntegrityError):
        session.commit()


def test_change_field_links_evidence_to_each_year_side(seeded_session: Session) -> None:
    measure = seeded_session.scalar(
        select(Measure).where(Measure.measure_id == "DEMO-001")
    )
    assert measure is not None
    comparison_field = measure.comparisons[0].affected_fields[0]
    evidence_by_year = {
        version.performance_year: version.fields[0].evidence[0]
        for version in measure.versions
    }
    comparison_field.evidence_links.extend(
        [
            MeasureComparisonEvidence(
                evidence_reference=evidence_by_year[2025],
                side=ChangeEvidenceSide.FROM_VERSION,
            ),
            MeasureComparisonEvidence(
                evidence_reference=evidence_by_year[2026],
                side=ChangeEvidenceSide.TO_VERSION,
            ),
        ]
    )
    seeded_session.commit()

    assert {link.side for link in comparison_field.evidence_links} == {
        ChangeEvidenceSide.FROM_VERSION,
        ChangeEvidenceSide.TO_VERSION,
    }


def test_initial_migration_builds_and_reverts_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "migration-test.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path}"
    monkeypatch.setenv("CMSQI_DATABASE_URL", database_url)

    from app.config import get_settings

    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "head")

    from sqlalchemy import create_engine

    engine = create_engine(database_url)
    assert {
        "measures",
        "program_memberships",
        "measure_versions",
        "specification_field_candidates",
        "specification_field_candidate_reviews",
        "specification_fields",
        "source_documents",
        "source_revisions",
        "evidence_references",
        "measure_comparisons",
        "measure_comparison_fields",
        "measure_comparison_evidence",
        "source_checks",
        "source_extractions",
        "source_text_segments",
        "source_normalizations",
        "normalized_measure_candidates",
        "normalized_field_candidates",
        "ai_clarification_proposals",
        "ai_clarification_evidence",
        "ingestion_runs",
        "ingestion_run_items",
        "ingestion_run_events",
    }.issubset(inspect(engine).get_table_names())
    candidate_columns = {
        column["name"]
        for column in inspect(engine).get_columns("specification_field_candidates")
    }
    assert {
        "source_excerpt",
        "publication_state",
        "published_field_id",
        "published_at",
        "published_by",
    }.issubset(candidate_columns)
    comparison_field_columns = {
        column["name"]
        for column in inspect(engine).get_columns("measure_comparison_fields")
    }
    assert {
        "status",
        "from_availability",
        "to_availability",
        "from_value",
        "to_value",
    }.issubset(comparison_field_columns)
    comparison_checks = {
        constraint["name"]
        for constraint in inspect(engine).get_check_constraints("measure_comparisons")
    }
    assert {
        "ck_comparison_from_year_range",
        "ck_comparison_to_year_range",
        "change_status",
    }.issubset(comparison_checks)

    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    get_settings.cache_clear()
