"""Store source excerpts separately from candidate values.

Revision ID: 20261022_0004
Revises: 20261019_0003
Create Date: 2026-10-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261022_0004"
down_revision: str | None = "20261019_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "specification_field_candidates",
        sa.Column("source_excerpt", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("specification_field_candidates", "source_excerpt")
