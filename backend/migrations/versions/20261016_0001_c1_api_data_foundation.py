"""Create the C1 public measure and evidence schema.

Revision ID: 20261016_0001
Revises:
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261016_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

publication_state = sa.Enum(
    "draft",
    "published",
    "withdrawn",
    name="publication_state",
    native_enum=False,
    create_constraint=True,
)
verification_status = sa.Enum(
    "verified",
    "partially_verified",
    "source_update_detected",
    name="public_verification_status",
    native_enum=False,
    create_constraint=True,
)
field_availability = sa.Enum(
    "available",
    "unavailable",
    "unresolved",
    name="field_availability",
    native_enum=False,
    create_constraint=True,
)
affected_field = sa.Enum(
    "measure_set",
    "definition",
    "numerator",
    "denominator",
    "exclusions",
    "eligibility",
    "calculation_logic",
    name="affected_field",
    native_enum=False,
    create_constraint=True,
)
change_status = sa.Enum(
    "added",
    "removed",
    "modified",
    "unchanged",
    "unknown",
    name="change_status",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "measures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("measure_id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("measure_id"),
    )
    op.create_index("ix_measures_measure_id", "measures", ["measure_id"])
    op.create_index("ix_measures_is_public", "measures", ["is_public"])

    op.create_table(
        "source_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("official_url", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("official_url"),
        sa.UniqueConstraint("source_id"),
    )
    op.create_index("ix_source_documents_source_id", "source_documents", ["source_id"])

    op.create_table(
        "program_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "measure_id",
            sa.Integer(),
            sa.ForeignKey("measures.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("program", sa.String(length=120), nullable=False),
        sa.Column("performance_year", sa.Integer(), nullable=False),
        sa.Column("is_program_member", sa.Boolean(), nullable=False),
        sa.Column("publication_state", publication_state, nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("performance_year >= 2000 AND performance_year <= 2100"),
        sa.UniqueConstraint("measure_id", "program", "performance_year"),
    )
    op.create_index(
        "ix_program_memberships_performance_year", "program_memberships", ["performance_year"]
    )
    op.create_index(
        "ix_program_memberships_publication_state", "program_memberships", ["publication_state"]
    )

    op.create_table(
        "source_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("revision_id", sa.String(length=120), nullable=False),
        sa.Column(
            "source_document_id",
            sa.Integer(),
            sa.ForeignKey("source_documents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_source_check_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("publication_state", publication_state, nullable=False),
        sa.Column("verification_status", verification_status, nullable=False),
        sa.UniqueConstraint("revision_id"),
        sa.UniqueConstraint("source_document_id", "revision_number"),
        sa.UniqueConstraint("source_document_id", "content_hash"),
    )
    op.create_index("ix_source_revisions_revision_id", "source_revisions", ["revision_id"])
    op.create_index(
        "ix_source_revisions_publication_state", "source_revisions", ["publication_state"]
    )

    op.create_table(
        "measure_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version_id", sa.String(length=120), nullable=False),
        sa.Column(
            "measure_id",
            sa.Integer(),
            sa.ForeignKey("measures.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("program", sa.String(length=120), nullable=False),
        sa.Column("performance_year", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("is_program_member", sa.Boolean(), nullable=False),
        sa.Column("publication_state", publication_state, nullable=False),
        sa.Column("verification_status", verification_status, nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_source_check_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("newer_revision_detected", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("performance_year >= 2000 AND performance_year <= 2100"),
        sa.UniqueConstraint("version_id"),
        sa.UniqueConstraint("measure_id", "program", "performance_year", "version_number"),
    )
    op.create_index("ix_measure_versions_version_id", "measure_versions", ["version_id"])
    op.create_index(
        "ix_measure_versions_performance_year", "measure_versions", ["performance_year"]
    )
    op.create_index(
        "ix_measure_versions_publication_state", "measure_versions", ["publication_state"]
    )

    op.create_table(
        "measure_comparisons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "measure_id",
            sa.Integer(),
            sa.ForeignKey("measures.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("program", sa.String(length=120), nullable=False),
        sa.Column("from_year", sa.Integer(), nullable=False),
        sa.Column("to_year", sa.Integer(), nullable=False),
        sa.Column("status", change_status, nullable=False),
        sa.Column("publication_state", publication_state, nullable=False),
        sa.CheckConstraint("from_year >= 2000 AND from_year <= 2100"),
        sa.CheckConstraint("to_year >= 2000 AND to_year <= 2100"),
        sa.UniqueConstraint("measure_id", "program", "from_year", "to_year"),
    )
    op.create_index("ix_comparison_year_pair", "measure_comparisons", ["from_year", "to_year"])
    op.create_index("ix_measure_comparisons_status", "measure_comparisons", ["status"])
    op.create_index(
        "ix_measure_comparisons_publication_state", "measure_comparisons", ["publication_state"]
    )

    op.create_table(
        "specification_fields",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "measure_version_id",
            sa.Integer(),
            sa.ForeignKey("measure_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field", affected_field, nullable=False),
        sa.Column("availability", field_availability, nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "(availability = 'available' AND value IS NOT NULL) OR "
            "(availability IN ('unavailable', 'unresolved') AND value IS NULL)",
            name="ck_field_availability_value",
        ),
        sa.UniqueConstraint("measure_version_id", "field"),
    )

    op.create_table(
        "measure_comparison_fields",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "comparison_id",
            sa.Integer(),
            sa.ForeignKey("measure_comparisons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field", affected_field, nullable=False),
        sa.UniqueConstraint("comparison_id", "field"),
    )

    op.create_table(
        "evidence_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("evidence_id", sa.String(length=120), nullable=False),
        sa.Column(
            "specification_field_id",
            sa.Integer(),
            sa.ForeignKey("specification_fields.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_revision_id",
            sa.Integer(),
            sa.ForeignKey("source_revisions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("locator", sa.String(length=500), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.UniqueConstraint("evidence_id"),
    )
    op.create_index("ix_evidence_references_evidence_id", "evidence_references", ["evidence_id"])


def downgrade() -> None:
    op.drop_table("evidence_references")
    op.drop_table("measure_comparison_fields")
    op.drop_table("specification_fields")
    op.drop_table("measure_comparisons")
    op.drop_table("measure_versions")
    op.drop_table("source_revisions")
    op.drop_table("program_memberships")
    op.drop_table("source_documents")
    op.drop_table("measures")
