"""Add Node-owned review tasks and transactional history."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_review_workflow"
down_revision: str | None = "0002_jobs_storage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("resolution", sa.Text(), nullable=False, server_default=""),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("in_review_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'in_review', 'resolved')", name="ck_review_status"
        ),
        sa.CheckConstraint("version > 0", name="ck_review_version"),
        sa.CheckConstraint(
            "status != 'resolved' OR "
            "(resolved_at IS NOT NULL AND length(trim(resolution)) > 0)",
            name="ck_review_resolution",
        ),
    )
    op.create_index(
        "ix_review_status_created", "review_tasks", ["status", "created_at", "id"]
    )
    op.create_table(
        "review_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "task_id", sa.Integer(), sa.ForeignKey("review_tasks.id"), nullable=False
        ),
        sa.Column("from_status", sa.String(16)),
        sa.Column("to_status", sa.String(16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_review_history_task_id", "review_history", ["task_id", "id"])


def downgrade() -> None:
    op.drop_table("review_history")
    op.drop_table("review_tasks")
