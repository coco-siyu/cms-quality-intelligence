"""Add durable review checklist and audit schemas.

Revision ID: 20261110_0018
Revises: 20261108_0017
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261110_0018"
down_revision: str | None = "20261108_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

measure_review_status = sa.Enum(
    "pending",
    "in_review",
    "completed",
    "reopened",
    "needs_re_review",
    name="measure_review_status",
    native_enum=False,
    create_constraint=True,
)
review_role = sa.Enum(
    "data_analyst",
    "aco_quality_manager",
    "both",
    name="review_role",
    native_enum=False,
    create_constraint=True,
)
task_proposal_status = sa.Enum(
    "pending",
    "accepted",
    "dismissed",
    name="task_proposal_status",
    native_enum=False,
    create_constraint=True,
)
checklist_task_status = sa.Enum(
    "open",
    "completed",
    "not_applicable",
    name="checklist_task_status",
    native_enum=False,
    create_constraint=True,
)
review_event_type = sa.Enum(
    "review_created",
    "proposal_created",
    "proposal_accepted",
    "proposal_dismissed",
    "task_added",
    "task_edited",
    "task_status_changed",
    "note_added",
    "signed_off",
    "reopened",
    "needs_re_review",
    name="review_event_type",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "measure_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_id", sa.String(length=120), nullable=False),
        sa.Column(
            "comparison_id",
            sa.Integer(),
            sa.ForeignKey("measure_comparisons.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "status",
            measure_review_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("completed_by", sa.String(length=200)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "(status = 'completed' AND completed_at IS NOT NULL "
            "AND completed_by IS NOT NULL) OR "
            "(status != 'completed' AND completed_at IS NULL "
            "AND completed_by IS NULL)",
            name="ck_measure_review_completion_state",
        ),
        sa.UniqueConstraint("review_id"),
    )
    op.create_index("ix_measure_reviews_review_id", "measure_reviews", ["review_id"])
    op.create_index("ix_measure_reviews_status", "measure_reviews", ["status"])

    op.create_table(
        "review_task_proposals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("proposal_id", sa.String(length=120), nullable=False),
        sa.Column(
            "review_id",
            sa.Integer(),
            sa.ForeignKey("measure_reviews.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "impact_explanation_draft_id",
            sa.Integer(),
            sa.ForeignKey("impact_explanation_drafts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", review_role, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("prompt_version", sa.String(length=120), nullable=False),
        sa.Column("input_digest", sa.String(length=128), nullable=False),
        sa.Column("provider_response_id", sa.String(length=200)),
        sa.Column(
            "status",
            task_proposal_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decided_by", sa.String(length=200)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.CheckConstraint("sequence >= 1", name="ck_review_task_proposal_sequence"),
        sa.CheckConstraint(
            "(status = 'pending' AND decided_at IS NULL AND decided_by IS NULL) OR "
            "(status IN ('accepted', 'dismissed') AND decided_at IS NOT NULL "
            "AND decided_by IS NOT NULL)",
            name="ck_review_task_proposal_decision_state",
        ),
        sa.UniqueConstraint("proposal_id"),
        sa.UniqueConstraint("impact_explanation_draft_id", "sequence"),
    )
    op.create_index(
        "ix_review_task_proposals_proposal_id",
        "review_task_proposals",
        ["proposal_id"],
    )
    op.create_index("ix_review_task_proposals_review_id", "review_task_proposals", ["review_id"])
    op.create_index(
        "ix_review_task_proposals_impact_explanation_draft_id",
        "review_task_proposals",
        ["impact_explanation_draft_id"],
    )
    op.create_index("ix_review_task_proposals_role", "review_task_proposals", ["role"])
    op.create_index("ix_review_task_proposals_status", "review_task_proposals", ["status"])

    op.create_table(
        "review_task_proposal_citations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "review_task_proposal_id",
            sa.Integer(),
            sa.ForeignKey("review_task_proposals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "comparison_evidence_id",
            sa.Integer(),
            sa.ForeignKey("measure_comparison_evidence.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.UniqueConstraint("review_task_proposal_id", "comparison_evidence_id"),
    )

    op.create_table(
        "review_checklist_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("checklist_item_id", sa.String(length=120), nullable=False),
        sa.Column(
            "review_id",
            sa.Integer(),
            sa.ForeignKey("measure_reviews.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "accepted_from_proposal_id",
            sa.Integer(),
            sa.ForeignKey("review_task_proposals.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column("role", review_role, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "status",
            checklist_task_status,
            nullable=False,
            server_default="open",
        ),
        sa.Column("notes", sa.Text()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by", sa.String(length=200)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "(status = 'open' AND resolved_at IS NULL AND resolved_by IS NULL) OR "
            "(status IN ('completed', 'not_applicable') AND resolved_at IS NOT NULL "
            "AND resolved_by IS NOT NULL)",
            name="ck_review_checklist_item_resolution_state",
        ),
        sa.UniqueConstraint("checklist_item_id"),
    )
    op.create_index(
        "ix_review_checklist_items_checklist_item_id",
        "review_checklist_items",
        ["checklist_item_id"],
    )
    op.create_index("ix_review_checklist_items_review_id", "review_checklist_items", ["review_id"])
    op.create_index("ix_review_checklist_items_role", "review_checklist_items", ["role"])
    op.create_index("ix_review_checklist_items_status", "review_checklist_items", ["status"])

    op.create_table(
        "review_signoffs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("signoff_id", sa.String(length=120), nullable=False),
        sa.Column(
            "review_id",
            sa.Integer(),
            sa.ForeignKey("measure_reviews.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("accepted_task_count", sa.Integer(), nullable=False),
        sa.Column("resolved_task_count", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column(
            "signed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("signed_by", sa.String(length=200), nullable=False),
        sa.CheckConstraint("sequence >= 1", name="ck_review_signoff_sequence"),
        sa.CheckConstraint(
            "accepted_task_count >= 0 AND resolved_task_count >= 0 "
            "AND accepted_task_count = resolved_task_count",
            name="ck_review_signoff_resolved_tasks",
        ),
        sa.UniqueConstraint("signoff_id"),
        sa.UniqueConstraint("review_id", "sequence"),
    )
    op.create_index("ix_review_signoffs_signoff_id", "review_signoffs", ["signoff_id"])
    op.create_index("ix_review_signoffs_review_id", "review_signoffs", ["review_id"])

    op.create_table(
        "review_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(length=120), nullable=False),
        sa.Column(
            "review_id",
            sa.Integer(),
            sa.ForeignKey("measure_reviews.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", review_event_type, nullable=False),
        sa.Column("subject_type", sa.String(length=80)),
        sa.Column("subject_id", sa.String(length=160)),
        sa.Column("actor", sa.String(length=200), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("note", sa.Text()),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.CheckConstraint("sequence >= 1", name="ck_review_event_sequence"),
        sa.CheckConstraint(
            "(subject_type IS NULL AND subject_id IS NULL) OR "
            "(subject_type IS NOT NULL AND subject_id IS NOT NULL)",
            name="ck_review_event_subject",
        ),
        sa.UniqueConstraint("event_id"),
        sa.UniqueConstraint("review_id", "sequence"),
    )
    op.create_index("ix_review_events_event_id", "review_events", ["event_id"])
    op.create_index("ix_review_events_review_id", "review_events", ["review_id"])
    op.create_index("ix_review_events_event_type", "review_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("review_events")
    op.drop_table("review_signoffs")
    op.drop_table("review_checklist_items")
    op.drop_table("review_task_proposal_citations")
    op.drop_table("review_task_proposals")
    op.drop_table("measure_reviews")
