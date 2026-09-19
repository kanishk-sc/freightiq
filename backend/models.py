from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Invoice(TimestampMixin, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_carrier_number", "carrier_name", "invoice_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    carrier_name: Mapped[str | None] = mapped_column(String(255))
    invoice_number: Mapped[str | None] = mapped_column(String(128), index=True)
    invoice_date: Mapped[str | None] = mapped_column(String(32))
    due_date: Mapped[str | None] = mapped_column(String(32))
    origin: Mapped[str | None] = mapped_column(String(512))
    destination: Mapped[str | None] = mapped_column(String(512))
    load_id: Mapped[str | None] = mapped_column(String(128), index=True)
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    taxes: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    raw_text: Mapped[str | None] = mapped_column(Text)
    audited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    line_items: Mapped[list["LineItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )
    audit_flags: Mapped[list["AuditFlag"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class LineItem(Base):
    __tablename__ = "line_items"
    __table_args__ = (
        CheckConstraint("quantity IS NULL OR quantity >= 0", name="ck_line_quantity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str | None] = mapped_column(String(512))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))

    invoice: Mapped[Invoice] = relationship(back_populates="line_items")


class AuditFlag(TimestampMixin, Base):
    __tablename__ = "audit_flags"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('warning', 'error')", name="ck_audit_flags_severity"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    field: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(
        String(32), default="deterministic", nullable=False
    )

    invoice: Mapped[Invoice] = relationship(back_populates="audit_flags")
