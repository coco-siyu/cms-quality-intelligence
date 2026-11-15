"""Add bounded retry state to private ingestion items.

Revision ID: 20261115_0019
Revises: 20261110_0018
Create Date: 2026-11-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261115_0019"
down_revision: str | None = "20261110_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table(
        "ingestion_run_items",
        table_args=(sa.CheckConstraint("sequence >= 1"),),
    ) as batch_op:
        batch_op.add_column(
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3")
        )
        batch_op.add_column(
            sa.Column(
                "retry_exhausted", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
        batch_op.add_column(
            sa.Column(
                "requires_attention", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
        batch_op.create_check_constraint(
            "ck_ingestion_run_item_attempt_count", "attempt_count >= 0"
        )
        batch_op.create_check_constraint(
            "ck_ingestion_run_item_max_attempts", "max_attempts >= 1"
        )
        batch_op.create_check_constraint(
            "ck_ingestion_run_item_max_attempts_ceiling", "max_attempts <= 5"
        )
        batch_op.create_check_constraint(
            "ck_ingestion_run_item_attempt_limit", "attempt_count <= max_attempts"
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "ingestion_run_items",
        table_args=(sa.CheckConstraint("sequence >= 1"),),
    ) as batch_op:
        batch_op.drop_constraint(
            "ck_ingestion_run_item_attempt_limit", type_="check"
        )
        batch_op.drop_constraint(
            "ck_ingestion_run_item_max_attempts_ceiling", type_="check"
        )
        batch_op.drop_constraint(
            "ck_ingestion_run_item_max_attempts", type_="check"
        )
        batch_op.drop_constraint(
            "ck_ingestion_run_item_attempt_count", type_="check"
        )
        batch_op.drop_column("requires_attention")
        batch_op.drop_column("retry_exhausted")
        batch_op.drop_column("max_attempts")
        batch_op.drop_column("attempt_count")
