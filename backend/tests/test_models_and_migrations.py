from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain import AffectedField, FieldAvailability
from app.models import Measure, MeasureVersion, SpecificationField


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
        "specification_fields",
        "source_documents",
        "source_revisions",
        "evidence_references",
        "measure_comparisons",
        "measure_comparison_fields",
    }.issubset(inspect(engine).get_table_names())

    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    get_settings.cache_clear()
