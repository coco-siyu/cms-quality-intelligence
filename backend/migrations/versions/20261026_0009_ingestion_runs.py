"""Add persisted, private source ingestion runs.

Revision ID: 20261026_0009
Revises: 20261026_0008
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261026_0009"
down_revision: str | None = "20261026_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

run_status = sa.Enum(
    "running",
    "completed",
    "completed_with_errors",
    "interrupted",
    name="ingestion_run_status",
    native_enum=False,
    create_constraint=True,
)
item_stage = sa.Enum(
    "pending",
    "downloading",
    "extracting",
    "comparing",
    "awaiting_verification",
    "unchanged",
    "failed",
    name="ingestion_item_stage",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=120), nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("completed_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index("ix_ingestion_runs_run_id", "ingestion_runs", ["run_id"])
    op.create_index("ix_ingestion_runs_status", "ingestion_runs", ["status"])

    op.create_table(
        "ingestion_run_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.String(length=160), nullable=False),
        sa.Column(
            "ingestion_run_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_document_id",
            sa.Integer(),
            sa.ForeignKey("source_documents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "source_check_id",
            sa.Integer(),
            sa.ForeignKey("source_checks.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("stage", item_stage, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.CheckConstraint("sequence >= 1"),
        sa.UniqueConstraint("item_id"),
        sa.UniqueConstraint("ingestion_run_id", "sequence"),
        sa.UniqueConstraint("ingestion_run_id", "source_document_id"),
    )
    op.create_index(
        "ix_ingestion_run_items_item_id", "ingestion_run_items", ["item_id"]
    )
    op.create_index(
        "ix_ingestion_run_items_stage", "ingestion_run_items", ["stage"]
    )

    op.create_table(
        "ingestion_run_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(length=180), nullable=False),
        sa.Column(
            "ingestion_run_item_id",
            sa.Integer(),
            sa.ForeignKey("ingestion_run_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("stage", item_stage, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.UniqueConstraint("event_id"),
        sa.UniqueConstraint("ingestion_run_item_id", "sequence"),
    )
    op.create_index(
        "ix_ingestion_run_events_event_id", "ingestion_run_events", ["event_id"]
    )


def downgrade() -> None:
    op.drop_table("ingestion_run_events")
    op.drop_table("ingestion_run_items")
    op.drop_table("ingestion_runs")
