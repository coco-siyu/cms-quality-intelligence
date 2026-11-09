"""Allow append-only impact explanation regeneration.

Revision ID: 20261108_0017
Revises: 20261106_0016
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261108_0017"
down_revision: str | None = "20261106_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("impact_explanation_drafts") as batch_op:
        batch_op.drop_constraint("uq_impact_explanation_input", type_="unique")
        batch_op.add_column(
            sa.Column(
                "generation_sequence",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )
        batch_op.create_unique_constraint(
            "uq_impact_explanation_input",
            [
                "comparison_id",
                "provider",
                "model",
                "prompt_version",
                "input_digest",
                "generation_sequence",
            ],
        )
        batch_op.create_check_constraint(
            "ck_impact_explanation_generation_sequence",
            "generation_sequence >= 1",
        )


def downgrade() -> None:
    # Refuse to discard historical versions merely to satisfy the former
    # uniqueness rule.
    connection = op.get_bind()
    regenerated_count = connection.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM impact_explanation_drafts
            WHERE generation_sequence > 1
            """
        )
    ).scalar_one()
    if regenerated_count:
        raise RuntimeError(
            "Cannot downgrade without discarding regenerated impact explanation history."
        )

    with op.batch_alter_table("impact_explanation_drafts") as batch_op:
        batch_op.drop_constraint(
            "ck_impact_explanation_generation_sequence", type_="check"
        )
        batch_op.drop_constraint("uq_impact_explanation_input", type_="unique")
        batch_op.drop_column("generation_sequence")
        batch_op.create_unique_constraint(
            "uq_impact_explanation_input",
            ["comparison_id", "provider", "model", "prompt_version", "input_digest"],
        )
