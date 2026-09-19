from decimal import Decimal

from auditor import audit_invoice
from schemas import ExtractedInvoice, ExtractedLineItem


def invoice_with(items: list[ExtractedLineItem], **overrides) -> ExtractedInvoice:
    values = {
        "carrier_name": "North Freight",
        "invoice_number": "INV-10",
        "invoice_date": "2026-09-01",
        "due_date": "2026-09-30",
        "line_items": items,
        "subtotal": "20.00",
        "taxes": "2.00",
        "total_amount": "22.00",
    }
    values.update(overrides)
    return ExtractedInvoice.model_validate(values)


def test_detects_line_subtotal_and_invoice_math_errors() -> None:
    invoice = invoice_with(
        [
            ExtractedLineItem(
                description="Fuel", quantity="2", unit_price="10.00", total="19.00"
            )
        ],
        subtotal="25.00",
        total_amount="30.00",
    )
    fields = {finding["field"] for finding in audit_invoice(invoice)}
    assert fields == {"line_items[0].total", "subtotal", "total_amount"}


def test_allows_one_cent_rounding_tolerance() -> None:
    invoice = invoice_with(
        [
            ExtractedLineItem(
                description="Fuel",
                quantity=Decimal("3"),
                unit_price=Decimal("6.67"),
                total=Decimal("20.00"),
            )
        ]
    )
    assert audit_invoice(invoice) == []


def test_due_date_and_missing_required_fields_are_deterministic() -> None:
    invoice = ExtractedInvoice(
        invoice_date="2026-09-18",
        due_date="2026-09-01",
        line_items=[],
    )
    fields = {finding["field"] for finding in audit_invoice(invoice)}
    assert {"carrier_name", "invoice_number", "total_amount", "due_date"} <= fields
