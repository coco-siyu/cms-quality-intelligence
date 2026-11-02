"""Scope deterministic comparisons to one collection variant.

Revision ID: 20261102_0011
Revises: 20261031_0010
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261102_0011"
down_revision: str | None = "20261031_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

collection_type = sa.Enum(
    "program_roster",
    "ecqm",
    "mips_cqm",
    "medicare_cqm",
    "cahps_survey",
    "administrative_claims",
    name="collection_type",
    native_enum=False,
    create_constraint=True,
)


def _comparison_identity_constraint() -> str:
    inspector = sa.inspect(op.get_bind())
    expected_columns = {"measure_id", "program", "from_year", "to_year"}
    for constraint in inspector.get_unique_constraints("measure_comparisons"):
        if set(constraint["column_names"]) == expected_columns:
            return constraint["name"] or (
                "uq_measure_comparisons_measure_id_program_from_year_to_year"
            )
    raise RuntimeError("Could not locate the legacy comparison identity constraint.")


def upgrade() -> None:
    legacy_constraint = _comparison_identity_constraint()
    naming_convention = {
        "uq": "uq_%(table_name)s_%(column_0_name)s_%(column_1_name)s_"
        "%(column_2_name)s_%(column_3_name)s"
    }
    with op.batch_alter_table(
        "measure_comparisons",
        naming_convention=naming_convention,
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "collection_type",
                collection_type,
                nullable=False,
                server_default="program_roster",
            )
        )
        batch_op.drop_constraint(legacy_constraint, type_="unique")
        batch_op.create_unique_constraint(
            "uq_measure_comparison_variant_year_pair",
            [
                "measure_id",
                "program",
                "from_year",
                "to_year",
                "collection_type",
            ],
        )
        batch_op.create_index(
            "ix_measure_comparisons_collection_type",
            ["collection_type"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("measure_comparisons") as batch_op:
        batch_op.drop_index("ix_measure_comparisons_collection_type")
        batch_op.drop_constraint(
            "uq_measure_comparison_variant_year_pair", type_="unique"
        )
        batch_op.drop_constraint("collection_type", type_="check")
        batch_op.drop_column("collection_type")
        batch_op.create_unique_constraint(
            "uq_measure_comparison_year_pair",
            ["measure_id", "program", "from_year", "to_year"],
        )
