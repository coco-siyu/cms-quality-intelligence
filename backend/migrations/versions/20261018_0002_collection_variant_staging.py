"""Add collection variants and private field-candidate staging.

Revision ID: 20261018_0002
Revises: 20261016_0001
Create Date: 2026-10-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261018_0002"
down_revision: str | None = "20261016_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLLECTION_TYPES = (
    "program_roster",
    "ecqm",
    "mips_cqm",
    "medicare_cqm",
    "cahps_survey",
    "administrative_claims",
)

collection_type = sa.Enum(
    *COLLECTION_TYPES,
    name="collection_type",
    native_enum=False,
    create_constraint=True,
)
candidate_review_decision = sa.Enum(
    "pending",
    "approve",
    "needs_revision",
    "not_applicable",
    name="candidate_review_decision",
    native_enum=False,
    create_constraint=True,
)


def _version_identity_constraint() -> str:
    inspector = sa.inspect(op.get_bind())
    expected_columns = {
        "measure_id",
        "program",
        "performance_year",
        "version_number",
    }
    for constraint in inspector.get_unique_constraints("measure_versions"):
        if set(constraint["column_names"]) == expected_columns:
            return constraint["name"] or (
                "uq_measure_versions_measure_id_program_performance_year_version_number"
            )
    raise RuntimeError("Could not locate the legacy measure-version identity constraint.")


def upgrade() -> None:
    legacy_constraint = _version_identity_constraint()
    naming_convention = {
        "uq": "uq_%(table_name)s_%(column_0_name)s_%(column_1_name)s_"
        "%(column_2_name)s_%(column_3_name)s"
    }
    with op.batch_alter_table(
        "measure_versions",
        naming_convention=naming_convention,
        table_args=(
            sa.CheckConstraint(
                "performance_year >= 2000 AND performance_year <= 2100",
                name="ck_measure_versions_performance_year",
            ),
        ),
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "collection_type",
                collection_type,
                nullable=False,
                server_default="program_roster",
            )
        )
        batch_op.add_column(
            sa.Column("specification_identifier", sa.String(length=120), nullable=True)
        )
        batch_op.drop_constraint(legacy_constraint, type_="unique")
        batch_op.create_unique_constraint(
            "uq_measure_version_variant_revision",
            [
                "measure_id",
                "program",
                "performance_year",
                "collection_type",
                "version_number",
            ],
        )
        batch_op.create_index(
            "ix_measure_versions_collection_type", ["collection_type"], unique=False
        )

    op.create_table(
        "specification_field_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_item_id", sa.String(length=180), nullable=False),
        sa.Column(
            "measure_version_id",
            sa.Integer(),
            sa.ForeignKey("measure_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(length=80), nullable=False),
        sa.Column("candidate_value", sa.Text(), nullable=False),
        sa.Column("extraction_status", sa.String(length=80), nullable=False),
        sa.Column(
            "source_revision_id",
            sa.Integer(),
            sa.ForeignKey("source_revisions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("evidence_locator", sa.String(length=1000), nullable=False),
        sa.Column(
            "review_decision",
            candidate_review_decision,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("reviewed_value", sa.Text(), nullable=True),
        sa.Column("reviewer_name", sa.String(length=200), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(review_decision = 'pending' AND reviewed_at IS NULL) OR "
            "(review_decision != 'pending' AND reviewed_at IS NOT NULL)",
            name="ck_candidate_review_timestamp",
        ),
        sa.UniqueConstraint("review_item_id"),
        sa.UniqueConstraint("measure_version_id", "field_name"),
    )
    op.create_index(
        "ix_specification_field_candidates_review_item_id",
        "specification_field_candidates",
        ["review_item_id"],
    )
    op.create_index(
        "ix_specification_field_candidates_review_decision",
        "specification_field_candidates",
        ["review_decision"],
    )


def downgrade() -> None:
    op.drop_table("specification_field_candidates")
    with op.batch_alter_table(
        "measure_versions",
        table_args=(
            sa.CheckConstraint(
                "performance_year >= 2000 AND performance_year <= 2100",
                name="ck_measure_versions_performance_year",
            ),
        ),
    ) as batch_op:
        batch_op.drop_index("ix_measure_versions_collection_type")
        batch_op.drop_constraint("uq_measure_version_variant_revision", type_="unique")
        batch_op.drop_constraint("collection_type", type_="check")
        batch_op.create_unique_constraint(
            "uq_measure_versions_legacy_identity",
            ["measure_id", "program", "performance_year", "version_number"],
        )
        batch_op.drop_column("specification_identifier")
        batch_op.drop_column("collection_type")
