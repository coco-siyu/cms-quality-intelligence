"""Add review and publication state for impact explanation drafts.

Revision ID: 20261106_0016
Revises: 20261106_0015
Create Date: 2026-11-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261106_0016"
down_revision: str | None = "20261106_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

impact_review_decision = sa.Enum(
    "pending",
    "approve",
    "reject",
    name="impact_explanation_review_decision",
    native_enum=False,
    create_constraint=True,
)
publication_state = sa.Enum(
    "draft",
    "published",
    "withdrawn",
    name="publication_state",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    with op.batch_alter_table("impact_explanation_drafts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "review_decision",
                impact_review_decision,
                nullable=False,
                server_default="pending",
            )
        )
        batch_op.add_column(sa.Column("approved_output_payload", sa.JSON()))
        batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column("reviewed_by", sa.String(length=200)))
        batch_op.add_column(
            sa.Column(
                "publication_state",
                publication_state,
                nullable=False,
                server_default="draft",
            )
        )
        batch_op.add_column(sa.Column("published_at", sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column("published_by", sa.String(length=200)))
        batch_op.add_column(sa.Column("outdated_at", sa.DateTime(timezone=True)))
        batch_op.create_index(
            "ix_impact_explanation_drafts_review_decision", ["review_decision"]
        )
        batch_op.create_index(
            "ix_impact_explanation_drafts_publication_state", ["publication_state"]
        )
        batch_op.create_index(
            "ix_impact_explanation_drafts_outdated_at", ["outdated_at"]
        )
        batch_op.create_check_constraint(
            "ck_impact_explanation_review_state",
            "(review_decision = 'pending' AND reviewed_at IS NULL "
            "AND reviewed_by IS NULL AND approved_output_payload IS NULL) OR "
            "(review_decision = 'approve' AND reviewed_at IS NOT NULL "
            "AND reviewed_by IS NOT NULL AND approved_output_payload IS NOT NULL) OR "
            "(review_decision = 'reject' AND reviewed_at IS NOT NULL "
            "AND reviewed_by IS NOT NULL AND approved_output_payload IS NULL)",
        )
        batch_op.create_check_constraint(
            "ck_impact_explanation_publication_state",
            "(publication_state = 'draft' AND published_at IS NULL "
            "AND published_by IS NULL) OR "
            "(publication_state IN ('published', 'withdrawn') "
            "AND published_at IS NOT NULL AND published_by IS NOT NULL "
            "AND review_decision = 'approve')",
        )


def downgrade() -> None:
    with op.batch_alter_table("impact_explanation_drafts") as batch_op:
        batch_op.drop_constraint(
            "ck_impact_explanation_publication_state", type_="check"
        )
        batch_op.drop_constraint("ck_impact_explanation_review_state", type_="check")
        batch_op.drop_constraint("impact_explanation_review_decision", type_="check")
        batch_op.drop_constraint("publication_state", type_="check")
        batch_op.drop_index("ix_impact_explanation_drafts_outdated_at")
        batch_op.drop_index("ix_impact_explanation_drafts_publication_state")
        batch_op.drop_index("ix_impact_explanation_drafts_review_decision")
        batch_op.drop_column("outdated_at")
        batch_op.drop_column("published_by")
        batch_op.drop_column("published_at")
        batch_op.drop_column("publication_state")
        batch_op.drop_column("reviewed_by")
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("approved_output_payload")
        batch_op.drop_column("review_decision")
