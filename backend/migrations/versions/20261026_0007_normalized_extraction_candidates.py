"""Add append-only normalized extraction candidates.

Revision ID: 20261026_0007
Revises: 20261026_0006
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261026_0007"
down_revision: str | None = "20261026_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

normalization_status = sa.Enum(
    "normalized",
    "needs_review",
    "no_candidates",
    name="source_normalization_status",
    native_enum=False,
    create_constraint=True,
)
identity_status = sa.Enum(
    "matched",
    "unresolved",
    "ambiguous",
    name="normalized_identity_status",
    native_enum=False,
    create_constraint=True,
)
field_status = sa.Enum(
    "extracted",
    "unresolved",
    name="normalized_field_status",
    native_enum=False,
    create_constraint=True,
)
staging_status = sa.Enum(
    "staged",
    "existing",
    "blocked_newer_revision",
    "unmatched",
    name="normalized_staging_status",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "source_normalizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("normalization_id", sa.String(length=120), nullable=False),
        sa.Column(
            "source_extraction_id",
            sa.Integer(),
            sa.ForeignKey("source_extractions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("parser_version", sa.String(length=120), nullable=False),
        sa.Column("status", normalization_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.UniqueConstraint("normalization_id"),
        sa.UniqueConstraint("source_extraction_id", "parser_version"),
    )
    op.create_index(
        "ix_source_normalizations_normalization_id",
        "source_normalizations",
        ["normalization_id"],
    )
    op.create_index(
        "ix_source_normalizations_status", "source_normalizations", ["status"]
    )

    op.create_table(
        "normalized_measure_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.String(length=120), nullable=False),
        sa.Column(
            "source_normalization_id",
            sa.Integer(),
            sa.ForeignKey("source_normalizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("identity_status", identity_status, nullable=False),
        sa.Column("measure_id_candidate", sa.String(length=80), nullable=True),
        sa.Column("performance_year_candidate", sa.Integer(), nullable=True),
        sa.Column("collection_type_candidate", sa.String(length=80), nullable=True),
        sa.Column(
            "specification_identifier_candidate",
            sa.String(length=120),
            nullable=True,
        ),
        sa.Column(
            "matched_measure_version_id",
            sa.Integer(),
            sa.ForeignKey("measure_versions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("issues", sa.Text(), nullable=True),
        sa.CheckConstraint("sequence >= 1"),
        sa.CheckConstraint(
            "performance_year_candidate IS NULL OR "
            "(performance_year_candidate >= 2000 AND performance_year_candidate <= 2100)"
        ),
        sa.UniqueConstraint("candidate_id"),
        sa.UniqueConstraint("source_normalization_id", "sequence"),
    )
    op.create_index(
        "ix_normalized_measure_candidates_candidate_id",
        "normalized_measure_candidates",
        ["candidate_id"],
    )
    op.create_index(
        "ix_normalized_measure_candidates_identity_status",
        "normalized_measure_candidates",
        ["identity_status"],
    )

    op.create_table(
        "normalized_field_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("field_candidate_id", sa.String(length=120), nullable=False),
        sa.Column(
            "normalized_measure_candidate_id",
            sa.Integer(),
            sa.ForeignKey("normalized_measure_candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(length=80), nullable=False),
        sa.Column("candidate_value", sa.Text(), nullable=True),
        sa.Column("status", field_status, nullable=False),
        sa.Column(
            "source_text_segment_id",
            sa.Integer(),
            sa.ForeignKey("source_text_segments.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("evidence_locator", sa.String(length=1000), nullable=True),
        sa.Column("source_excerpt", sa.Text(), nullable=True),
        sa.Column("staging_status", staging_status, nullable=False),
        sa.Column(
            "staged_field_candidate_id",
            sa.Integer(),
            sa.ForeignKey("specification_field_candidates.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "(status = 'extracted' AND candidate_value IS NOT NULL "
            "AND source_text_segment_id IS NOT NULL AND evidence_locator IS NOT NULL "
            "AND source_excerpt IS NOT NULL) OR "
            "(status = 'unresolved' AND candidate_value IS NULL)",
            name="ck_normalized_field_evidence",
        ),
        sa.UniqueConstraint("field_candidate_id"),
        sa.UniqueConstraint("normalized_measure_candidate_id", "field_name"),
    )
    op.create_index(
        "ix_normalized_field_candidates_field_candidate_id",
        "normalized_field_candidates",
        ["field_candidate_id"],
    )
    op.create_index(
        "ix_normalized_field_candidates_status",
        "normalized_field_candidates",
        ["status"],
    )
    op.create_index(
        "ix_normalized_field_candidates_staging_status",
        "normalized_field_candidates",
        ["staging_status"],
    )


def downgrade() -> None:
    op.drop_table("normalized_field_candidates")
    op.drop_table("normalized_measure_candidates")
    op.drop_table("source_normalizations")
