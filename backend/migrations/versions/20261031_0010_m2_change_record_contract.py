"""Add the evidence-backed M2 change record contract.

Revision ID: 20261031_0010
Revises: 20261026_0009
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261031_0010"
down_revision: str | None = "20261026_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

old_change_status = sa.Enum(
    "added",
    "removed",
    "modified",
    "unchanged",
    "unknown",
    name="change_status",
    native_enum=False,
    create_constraint=True,
)
change_status = sa.Enum(
    "added",
    "removed",
    "modified",
    "wording_only",
    "unchanged",
    "unknown",
    name="change_status",
    native_enum=False,
    create_constraint=True,
)
field_change_status = sa.Enum(
    "added",
    "removed",
    "modified",
    "wording_only",
    "unchanged",
    "unknown",
    name="comparison_field_change_status",
    native_enum=False,
    create_constraint=True,
)
from_availability = sa.Enum(
    "available",
    "unavailable",
    "unresolved",
    name="comparison_from_availability",
    native_enum=False,
    create_constraint=True,
)
to_availability = sa.Enum(
    "available",
    "unavailable",
    "unresolved",
    name="comparison_to_availability",
    native_enum=False,
    create_constraint=True,
)
evidence_side = sa.Enum(
    "from_version",
    "to_version",
    "context",
    name="change_evidence_side",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    with op.batch_alter_table(
        "measure_comparisons",
        table_args=(
            sa.CheckConstraint(
                "from_year >= 2000 AND from_year <= 2100",
                name="ck_comparison_from_year_range",
            ),
            sa.CheckConstraint(
                "to_year >= 2000 AND to_year <= 2100",
                name="ck_comparison_to_year_range",
            ),
        ),
    ) as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=old_change_status,
            type_=change_status,
            existing_nullable=False,
        )

    with op.batch_alter_table("measure_comparison_fields") as batch_op:
        batch_op.add_column(
            sa.Column(
                "status",
                field_change_status,
                nullable=False,
                server_default="unknown",
            )
        )
        batch_op.add_column(
            sa.Column(
                "from_availability",
                from_availability,
                nullable=False,
                server_default="unresolved",
            )
        )
        batch_op.add_column(
            sa.Column(
                "to_availability",
                to_availability,
                nullable=False,
                server_default="unresolved",
            )
        )
        batch_op.add_column(sa.Column("from_value", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("to_value", sa.Text(), nullable=True))
        batch_op.create_check_constraint(
            "ck_comparison_from_availability_value",
            "(from_availability = 'available' AND from_value IS NOT NULL) OR "
            "(from_availability IN ('unavailable', 'unresolved') AND from_value IS NULL)",
        )
        batch_op.create_check_constraint(
            "ck_comparison_to_availability_value",
            "(to_availability = 'available' AND to_value IS NOT NULL) OR "
            "(to_availability IN ('unavailable', 'unresolved') AND to_value IS NULL)",
        )
        batch_op.create_check_constraint(
            "ck_unresolved_comparison_is_unknown",
            "(from_availability != 'unresolved' AND to_availability != 'unresolved') "
            "OR status = 'unknown'",
        )
        batch_op.create_index(
            "ix_measure_comparison_fields_status", ["status"], unique=False
        )

    op.create_table(
        "measure_comparison_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "comparison_field_id",
            sa.Integer(),
            sa.ForeignKey("measure_comparison_fields.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evidence_reference_id",
            sa.Integer(),
            sa.ForeignKey("evidence_references.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("side", evidence_side, nullable=False),
        sa.UniqueConstraint("comparison_field_id", "evidence_reference_id", "side"),
    )


def downgrade() -> None:
    op.drop_table("measure_comparison_evidence")

    with op.batch_alter_table("measure_comparison_fields") as batch_op:
        batch_op.drop_index("ix_measure_comparison_fields_status")
        batch_op.drop_constraint("ck_unresolved_comparison_is_unknown", type_="check")
        batch_op.drop_constraint("ck_comparison_to_availability_value", type_="check")
        batch_op.drop_constraint("ck_comparison_from_availability_value", type_="check")
        batch_op.drop_constraint("comparison_to_availability", type_="check")
        batch_op.drop_constraint("comparison_from_availability", type_="check")
        batch_op.drop_constraint("comparison_field_change_status", type_="check")
        batch_op.drop_column("to_value")
        batch_op.drop_column("from_value")
        batch_op.drop_column("to_availability")
        batch_op.drop_column("from_availability")
        batch_op.drop_column("status")

    op.execute(
        sa.text(
            "UPDATE measure_comparisons SET status = 'modified' "
            "WHERE status = 'wording_only'"
        )
    )
    with op.batch_alter_table(
        "measure_comparisons",
        table_args=(
            sa.CheckConstraint(
                "from_year >= 2000 AND from_year <= 2100",
                name="ck_comparison_from_year_range",
            ),
            sa.CheckConstraint(
                "to_year >= 2000 AND to_year <= 2100",
                name="ck_comparison_to_year_range",
            ),
        ),
    ) as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=change_status,
            type_=old_change_status,
            existing_nullable=False,
        )
