from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class LineItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoice.id")
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None


class Invoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    carrier_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    load_id: Optional[str] = None
    subtotal: Optional[float] = None
    taxes: Optional[float] = None
    total_amount: Optional[float] = None
    raw_text: Optional[str] = None
    audited: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditFlag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoice.id")
    field: str
    severity: str
    description: str
