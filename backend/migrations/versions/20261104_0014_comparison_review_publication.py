"""Add audited comparison review and publication state.

Revision ID: 20261104_0014
Revises: 20261102_0013
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261104_0014"
down_revision: str | None = "20261102_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

comparison_review_decision = sa.Enum(
    "pending",
    "approve",
    "needs_revision",
    name="comparison_review_decision",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    with op.batch_alter_table("measure_comparisons") as batch_op:
        batch_op.add_column(
            sa.Column(
                "review_decision",
                comparison_review_decision,
                nullable=False,
                server_default="pending",
            )
        )
        batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column("reviewer_name", sa.String(length=200)))
        batch_op.add_column(sa.Column("reviewer_notes", sa.Text()))
        batch_op.add_column(sa.Column("published_at", sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column("published_by", sa.String(length=200)))
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            )
        )

    op.execute(
        sa.text(
            "UPDATE measure_comparisons "
            "SET review_decision = 'approve', reviewed_at = CURRENT_TIMESTAMP, "
            "reviewer_name = 'legacy_migration', "
            "reviewer_notes = 'Backfilled for a comparison published before the review workflow.', "
            "published_at = CURRENT_TIMESTAMP, published_by = 'legacy_migration' "
            "WHERE publication_state = 'published'"
        )
    )

    with op.batch_alter_table("measure_comparisons") as batch_op:
        batch_op.create_index(
            "ix_measure_comparisons_review_decision", ["review_decision"]
        )
        batch_op.create_check_constraint(
            "ck_comparison_review_state",
            "(review_decision = 'pending' AND reviewed_at IS NULL "
            "AND reviewer_name IS NULL) OR "
            "(review_decision != 'pending' AND reviewed_at IS NOT NULL "
            "AND reviewer_name IS NOT NULL)",
        )
        batch_op.create_check_constraint(
            "ck_comparison_publication_state",
            "(publication_state = 'draft' AND published_at IS NULL "
            "AND published_by IS NULL) OR "
            "(publication_state IN ('published', 'withdrawn') "
            "AND published_at IS NOT NULL AND published_by IS NOT NULL "
            "AND review_decision = 'approve')",
        )

    op.create_table(
        "measure_comparison_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_key", sa.String(length=64), nullable=False),
        sa.Column(
            "comparison_id",
            sa.Integer(),
            sa.ForeignKey("measure_comparisons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("decision", comparison_review_decision, nullable=False),
        sa.Column("reviewer_name", sa.String(length=200), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewer_notes", sa.Text()),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "decision != 'pending'", name="ck_comparison_review_event_is_decided"
        ),
        sa.UniqueConstraint("event_key"),
    )
    op.create_index(
        "ix_measure_comparison_reviews_event_key",
        "measure_comparison_reviews",
        ["event_key"],
    )
    op.create_index(
        "ix_measure_comparison_reviews_decision",
        "measure_comparison_reviews",
        ["decision"],
    )


def downgrade() -> None:
    op.drop_table("measure_comparison_reviews")
    with op.batch_alter_table("measure_comparisons") as batch_op:
        batch_op.drop_constraint("ck_comparison_publication_state", type_="check")
        batch_op.drop_constraint("ck_comparison_review_state", type_="check")
        batch_op.drop_constraint("comparison_review_decision", type_="check")
        batch_op.drop_index("ix_measure_comparisons_review_decision")
        batch_op.drop_column("created_at")
        batch_op.drop_column("published_by")
        batch_op.drop_column("published_at")
        batch_op.drop_column("reviewer_notes")
        batch_op.drop_column("reviewer_name")
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("review_decision")
