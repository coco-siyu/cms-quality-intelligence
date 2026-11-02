"""Add private semantic classification proposals.

Revision ID: 20261102_0013
Revises: 20261102_0012
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261102_0013"
down_revision: str | None = "20261102_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

semantic_classification = sa.Enum(
    "substantive",
    "wording_only",
    "needs_review",
    name="semantic_classification",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "semantic_classification_proposals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("proposal_id", sa.String(length=120), nullable=False),
        sa.Column(
            "comparison_field_id",
            sa.Integer(),
            sa.ForeignKey("measure_comparison_fields.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("prompt_version", sa.String(length=120), nullable=False),
        sa.Column("input_digest", sa.String(length=128), nullable=False),
        sa.Column("classification", semantic_classification, nullable=False),
        sa.Column("reasoning_summary", sa.Text(), nullable=False),
        sa.Column("uncertainty_summary", sa.Text(), nullable=True),
        sa.Column("validation_error_code", sa.String(length=120), nullable=True),
        sa.Column("provider_response_id", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.CheckConstraint(
            "(classification = 'needs_review' AND uncertainty_summary IS NOT NULL) OR "
            "(classification IN ('substantive', 'wording_only') "
            "AND uncertainty_summary IS NULL)",
            name="ck_semantic_classification_uncertainty",
        ),
        sa.CheckConstraint(
            "validation_error_code IS NULL OR classification = 'needs_review'",
            name="ck_semantic_validation_error_needs_review",
        ),
        sa.UniqueConstraint("proposal_id"),
        sa.UniqueConstraint(
            "comparison_field_id",
            "provider",
            "model",
            "prompt_version",
            "input_digest",
            name="uq_semantic_classification_input",
        ),
    )
    op.create_index(
        "ix_semantic_classification_proposals_proposal_id",
        "semantic_classification_proposals",
        ["proposal_id"],
    )
    op.create_index(
        "ix_semantic_classification_proposals_classification",
        "semantic_classification_proposals",
        ["classification"],
    )

    op.create_table(
        "semantic_classification_citations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "semantic_classification_proposal_id",
            sa.Integer(),
            sa.ForeignKey("semantic_classification_proposals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "comparison_evidence_id",
            sa.Integer(),
            sa.ForeignKey("measure_comparison_evidence.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "semantic_classification_proposal_id",
            "comparison_evidence_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("semantic_classification_citations")
    op.drop_table("semantic_classification_proposals")
