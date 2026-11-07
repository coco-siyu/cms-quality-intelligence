"""Add private, versioned impact explanation drafts.

Revision ID: 20261106_0015
Revises: 20261104_0014
Create Date: 2026-11-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261106_0015"
down_revision: str | None = "20261104_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "impact_explanation_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_id", sa.String(length=120), nullable=False),
        sa.Column(
            "comparison_id",
            sa.Integer(),
            sa.ForeignKey("measure_comparisons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("prompt_version", sa.String(length=120), nullable=False),
        sa.Column("input_digest", sa.String(length=128), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=False),
        sa.Column("provider_response_id", sa.String(length=200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.UniqueConstraint("draft_id"),
        sa.UniqueConstraint(
            "comparison_id",
            "provider",
            "model",
            "prompt_version",
            "input_digest",
            name="uq_impact_explanation_input",
        ),
    )
    op.create_index(
        "ix_impact_explanation_drafts_draft_id",
        "impact_explanation_drafts",
        ["draft_id"],
    )
    op.create_table(
        "impact_explanation_citations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "impact_explanation_draft_id",
            sa.Integer(),
            sa.ForeignKey("impact_explanation_drafts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "comparison_evidence_id",
            sa.Integer(),
            sa.ForeignKey("measure_comparison_evidence.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "impact_explanation_draft_id",
            "comparison_evidence_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("impact_explanation_citations")
    op.drop_table("impact_explanation_drafts")
