"""Add private AI clarification proposals and evidence.

Revision ID: 20261026_0008
Revises: 20261026_0007
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261026_0008"
down_revision: str | None = "20261026_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

clarification_outcome = sa.Enum(
    "proposed",
    "unresolved",
    "conflict",
    name="clarification_outcome",
    native_enum=False,
    create_constraint=True,
)
clarification_evidence_relation = sa.Enum(
    "supports",
    "conflicts",
    "context",
    name="clarification_evidence_relation",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "ai_clarification_proposals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clarification_id", sa.String(length=120), nullable=False),
        sa.Column(
            "normalized_field_candidate_id",
            sa.Integer(),
            sa.ForeignKey("normalized_field_candidates.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("prompt_version", sa.String(length=120), nullable=False),
        sa.Column("input_digest", sa.String(length=128), nullable=False),
        sa.Column("outcome", clarification_outcome, nullable=False),
        sa.Column("proposed_value", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("provider_response_id", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.CheckConstraint(
            "(outcome = 'proposed' AND proposed_value IS NOT NULL) OR "
            "(outcome IN ('unresolved', 'conflict') AND proposed_value IS NULL)",
            name="ck_ai_clarification_proposed_value",
        ),
        sa.UniqueConstraint("clarification_id"),
        sa.UniqueConstraint(
            "normalized_field_candidate_id",
            "provider",
            "model",
            "prompt_version",
            "input_digest",
            name="uq_ai_clarification_input",
        ),
    )
    op.create_index(
        "ix_ai_clarification_proposals_clarification_id",
        "ai_clarification_proposals",
        ["clarification_id"],
    )
    op.create_index(
        "ix_ai_clarification_proposals_outcome",
        "ai_clarification_proposals",
        ["outcome"],
    )

    op.create_table(
        "ai_clarification_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("evidence_key", sa.String(length=120), nullable=False),
        sa.Column(
            "ai_clarification_proposal_id",
            sa.Integer(),
            sa.ForeignKey("ai_clarification_proposals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_text_segment_id",
            sa.Integer(),
            sa.ForeignKey("source_text_segments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "source_revision_id",
            sa.Integer(),
            sa.ForeignKey("source_revisions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("locator", sa.String(length=1000), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("relation", clarification_evidence_relation, nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.UniqueConstraint("ai_clarification_proposal_id", "evidence_key"),
    )
    op.create_index(
        "ix_ai_clarification_evidence_evidence_key",
        "ai_clarification_evidence",
        ["evidence_key"],
    )


def downgrade() -> None:
    op.drop_table("ai_clarification_evidence")
    op.drop_table("ai_clarification_proposals")
