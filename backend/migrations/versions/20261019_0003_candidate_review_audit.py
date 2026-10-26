"""Add append-only candidate review audit events.

Revision ID: 20261019_0003
Revises: 20261018_0002
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261019_0003"
down_revision: str | None = "20261018_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

candidate_review_decision = sa.Enum(
    "pending",
    "approve",
    "needs_revision",
    "not_applicable",
    name="candidate_review_decision",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "specification_field_candidate_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_key", sa.String(length=64), nullable=False),
        sa.Column(
            "specification_field_candidate_id",
            sa.Integer(),
            sa.ForeignKey("specification_field_candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("decision", candidate_review_decision, nullable=False),
        sa.Column("reviewed_value", sa.Text(), nullable=True),
        sa.Column("reviewer_name", sa.String(length=200), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "decision != 'pending'",
            name="ck_candidate_review_event_is_decided",
        ),
        sa.CheckConstraint(
            "(decision = 'approve' AND reviewed_value IS NOT NULL) OR "
            "(decision != 'approve' AND reviewed_value IS NULL)",
            name="ck_candidate_review_event_value",
        ),
        sa.UniqueConstraint("event_key"),
    )
    op.create_index(
        "ix_specification_field_candidate_reviews_event_key",
        "specification_field_candidate_reviews",
        ["event_key"],
    )
    op.create_index(
        "ix_specification_field_candidate_reviews_decision",
        "specification_field_candidate_reviews",
        ["decision"],
    )


def downgrade() -> None:
    op.drop_table("specification_field_candidate_reviews")
