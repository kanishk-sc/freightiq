from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExtractedLineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str | None = Field(default=None, max_length=512)
    quantity: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=3
    )
    unit_price: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=2
    )
    total: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class ExtractedInvoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    carrier_name: str | None = Field(default=None, max_length=255)
    invoice_number: str | None = Field(default=None, max_length=128)
    invoice_date: date | None = None
    due_date: date | None = None
    origin: str | None = Field(default=None, max_length=512)
    destination: str | None = Field(default=None, max_length=512)
    load_id: str | None = Field(default=None, max_length=128)
    line_items: list[ExtractedLineItem] = Field(default_factory=list, max_length=500)
    subtotal: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=2
    )
    taxes: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    total_amount: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=2
    )

    @field_validator(
        "carrier_name",
        "invoice_number",
        "origin",
        "destination",
        "load_id",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class AuditFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    severity: str
    description: str
    source: str = "deterministic"
