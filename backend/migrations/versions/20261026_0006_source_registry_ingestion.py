"""Add managed source registry and append-only extraction history.

Revision ID: 20261026_0006
Revises: 20261026_0005
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261026_0006"
down_revision: str | None = "20261026_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

source_check_outcome = sa.Enum(
    "new_revision",
    "unchanged",
    "reprocessed",
    "failed",
    name="source_check_outcome",
    native_enum=False,
    create_constraint=True,
)
source_extraction_status = sa.Enum(
    "extracted",
    "manual_review",
    "failed",
    name="source_extraction_status",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    with op.batch_alter_table("source_documents") as batch_op:
        batch_op.add_column(
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.add_column(sa.Column("notes", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("created_by", sa.String(length=200), nullable=True))
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            )
        )
        batch_op.add_column(
            sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_index("ix_source_documents_is_active", ["is_active"])

    with op.batch_alter_table("source_revisions") as batch_op:
        batch_op.alter_column(
            "revision_id",
            existing_type=sa.String(length=120),
            type_=sa.String(length=180),
            existing_nullable=False,
        )
        batch_op.add_column(sa.Column("source_url", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("final_url", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("http_status", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("retrieved_mime_type", sa.String(length=120), nullable=True)
        )
        batch_op.add_column(sa.Column("byte_length", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("content_blob", sa.LargeBinary(), nullable=True))

    op.execute(
        sa.text(
            "UPDATE source_revisions SET source_url = "
            "(SELECT official_url FROM source_documents "
            "WHERE source_documents.id = source_revisions.source_document_id)"
        )
    )

    op.create_table(
        "source_extractions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("extraction_id", sa.String(length=200), nullable=False),
        sa.Column(
            "source_revision_id",
            sa.Integer(),
            sa.ForeignKey("source_revisions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", source_extraction_status, nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("extractor_version", sa.String(length=120), nullable=False),
        sa.Column("forced", sa.Boolean(), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.CheckConstraint("sequence >= 1"),
        sa.CheckConstraint("page_count IS NULL OR page_count >= 0"),
        sa.UniqueConstraint("extraction_id"),
        sa.UniqueConstraint("source_revision_id", "sequence"),
    )
    op.create_index(
        "ix_source_extractions_extraction_id", "source_extractions", ["extraction_id"]
    )
    op.create_index("ix_source_extractions_status", "source_extractions", ["status"])

    op.create_table(
        "source_text_segments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_extraction_id",
            sa.Integer(),
            sa.ForeignKey("source_extractions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("locator", sa.String(length=500), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.UniqueConstraint("source_extraction_id", "sequence"),
    )

    op.create_table(
        "source_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("check_id", sa.String(length=120), nullable=False),
        sa.Column(
            "source_document_id",
            sa.Integer(),
            sa.ForeignKey("source_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_revision_id",
            sa.Integer(),
            sa.ForeignKey("source_revisions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "extraction_id",
            sa.Integer(),
            sa.ForeignKey("source_extractions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outcome", source_check_outcome, nullable=False),
        sa.Column("requested_url", sa.Text(), nullable=False),
        sa.Column("final_url", sa.Text(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("byte_length", sa.Integer(), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("forced", sa.Boolean(), nullable=False),
        sa.Column("checked_by", sa.String(length=200), nullable=False),
        sa.UniqueConstraint("check_id"),
    )
    op.create_index("ix_source_checks_check_id", "source_checks", ["check_id"])
    op.create_index("ix_source_checks_outcome", "source_checks", ["outcome"])


def downgrade() -> None:
    op.drop_table("source_checks")
    op.drop_table("source_text_segments")
    op.drop_table("source_extractions")
    with op.batch_alter_table("source_revisions") as batch_op:
        batch_op.drop_column("content_blob")
        batch_op.drop_column("byte_length")
        batch_op.drop_column("retrieved_mime_type")
        batch_op.drop_column("http_status")
        batch_op.drop_column("final_url")
        batch_op.drop_column("source_url")
        batch_op.alter_column(
            "revision_id",
            existing_type=sa.String(length=180),
            type_=sa.String(length=120),
            existing_nullable=False,
        )
    with op.batch_alter_table("source_documents") as batch_op:
        batch_op.drop_index("ix_source_documents_is_active")
        batch_op.drop_column("deactivated_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_by")
        batch_op.drop_column("notes")
        batch_op.drop_column("is_active")
