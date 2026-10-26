"""Track audited publication of individually approved fields.

Revision ID: 20261026_0005
Revises: 20261022_0004
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261026_0005"
down_revision: str | None = "20261022_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

publication_state = sa.Enum(
    "draft",
    "published",
    "withdrawn",
    name="publication_state",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    with op.batch_alter_table("specification_field_candidates") as batch_op:
        batch_op.add_column(
            sa.Column(
                "publication_state",
                publication_state,
                nullable=False,
                server_default="draft",
            )
        )
        batch_op.add_column(sa.Column("published_field_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("published_by", sa.String(length=200), nullable=True))
        batch_op.create_foreign_key(
            "fk_candidate_published_field",
            "specification_fields",
            ["published_field_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_unique_constraint(
            "uq_candidate_published_field_id", ["published_field_id"]
        )
        batch_op.create_check_constraint(
            "ck_candidate_publication_state",
            "(publication_state = 'draft' AND published_field_id IS NULL "
            "AND published_at IS NULL AND published_by IS NULL) OR "
            "(publication_state IN ('published', 'withdrawn') "
            "AND published_field_id IS NOT NULL AND published_at IS NOT NULL "
            "AND published_by IS NOT NULL AND review_decision = 'approve')",
        )
        batch_op.create_index(
            "ix_specification_field_candidates_publication_state",
            ["publication_state"],
        )


def downgrade() -> None:
    with op.batch_alter_table("specification_field_candidates") as batch_op:
        batch_op.drop_index("ix_specification_field_candidates_publication_state")
        batch_op.drop_constraint("ck_candidate_publication_state", type_="check")
        batch_op.drop_constraint("uq_candidate_published_field_id", type_="unique")
        batch_op.drop_constraint("fk_candidate_published_field", type_="foreignkey")
        batch_op.drop_constraint("publication_state", type_="check")
        batch_op.drop_column("published_by")
        batch_op.drop_column("published_at")
        batch_op.drop_column("published_field_id")
        batch_op.drop_column("publication_state")
