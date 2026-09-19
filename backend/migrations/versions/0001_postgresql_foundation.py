"""Create PostgreSQL invoice tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_postgresql_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("carrier_name", sa.String(255)),
        sa.Column("invoice_number", sa.String(128)),
        sa.Column("invoice_date", sa.String(32)),
        sa.Column("due_date", sa.String(32)),
        sa.Column("origin", sa.String(512)),
        sa.Column("destination", sa.String(512)),
        sa.Column("load_id", sa.String(128)),
        sa.Column("subtotal", sa.Numeric(14, 2)),
        sa.Column("taxes", sa.Numeric(14, 2)),
        sa.Column("total_amount", sa.Numeric(14, 2)),
        sa.Column("raw_text", sa.Text()),
        sa.Column("audited", sa.Boolean(), nullable=False, server_default=sa.false()),
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
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"])
    op.create_index("ix_invoices_load_id", "invoices", ["load_id"])
    op.create_index(
        "ix_invoices_carrier_number",
        "invoices",
        ["carrier_name", "invoice_number"],
    )
    op.create_table(
        "line_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "invoice_id",
            sa.Integer(),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("description", sa.String(512)),
        sa.Column("quantity", sa.Numeric(12, 3)),
        sa.Column("unit_price", sa.Numeric(14, 2)),
        sa.Column("total", sa.Numeric(14, 2)),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity >= 0", name="ck_line_quantity"
        ),
    )
    op.create_index("ix_line_items_invoice_id", "line_items", ["invoice_id"])
    op.create_table(
        "audit_flags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "invoice_id",
            sa.Integer(),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field", sa.String(128), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "source",
            sa.String(32),
            nullable=False,
            server_default="deterministic",
        ),
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
            "severity IN ('warning', 'error')", name="ck_audit_flags_severity"
        ),
    )
    op.create_index("ix_audit_flags_invoice_id", "audit_flags", ["invoice_id"])


def downgrade() -> None:
    op.drop_table("audit_flags")
    op.drop_table("line_items")
    op.drop_table("invoices")
