"""Track structural evidence coverage for comparison publication.

Revision ID: 20261102_0012
Revises: 20261102_0011
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261102_0012"
down_revision: str | None = "20261102_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

evidence_status = sa.Enum(
    "pending",
    "verified",
    "incomplete",
    name="comparison_evidence_status",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    with op.batch_alter_table("measure_comparisons") as batch_op:
        batch_op.add_column(
            sa.Column(
                "evidence_status",
                evidence_status,
                nullable=False,
                server_default="incomplete",
            )
        )
        batch_op.create_index(
            "ix_measure_comparisons_evidence_status",
            ["evidence_status"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("measure_comparisons") as batch_op:
        batch_op.drop_index("ix_measure_comparisons_evidence_status")
        batch_op.drop_constraint("comparison_evidence_status", type_="check")
        batch_op.drop_column("evidence_status")
