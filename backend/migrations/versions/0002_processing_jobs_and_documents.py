"""Add durable documents and asynchronous processing jobs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_jobs_storage"
down_revision: str | None = "0001_postgresql_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("object_key", sa.String(1024), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
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
    )
    op.create_index("ix_documents_sha256", "documents", ["sha256"])
    op.add_column("invoices", sa.Column("document_id", sa.Integer()))
    op.create_unique_constraint("uq_invoices_document_id", "invoices", ["document_id"])
    op.create_foreign_key(
        "fk_invoices_document_id",
        "invoices",
        "documents",
        ["document_id"],
        ["id"],
    )
    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(64)),
        sa.Column(
            "invoice_id",
            sa.Integer(),
            sa.ForeignKey("invoices.id", ondelete="SET NULL"),
            unique=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
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
            "status IN ('queued', 'processing', 'completed', 'failed')",
            name="ck_processing_jobs_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("processing_jobs")
    op.drop_constraint("fk_invoices_document_id", "invoices", type_="foreignkey")
    op.drop_constraint("uq_invoices_document_id", "invoices", type_="unique")
    op.drop_column("invoices", "document_id")
    op.drop_table("documents")
