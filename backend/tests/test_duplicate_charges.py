from auditor import audit_invoice
from schemas import ExtractedInvoice, ExtractedLineItem


def test_duplicate_charge_detection_normalizes_description_case() -> None:
    item = {
        "quantity": "1",
        "unit_price": "15.00",
        "total": "15.00",
    }
    invoice = ExtractedInvoice(
        carrier_name="Carrier",
        invoice_number="INV-2",
        invoice_date="2026-09-18",
        line_items=[
            ExtractedLineItem(description="Liftgate", **item),
            ExtractedLineItem(description=" liftGATE ", **item),
        ],
        subtotal="30.00",
        taxes="0",
        total_amount="30.00",
    )
    duplicates = [
        finding
        for finding in audit_invoice(invoice)
        if finding["field"] == "line_items"
    ]
    assert len(duplicates) == 1
    assert duplicates[0]["source"] == "deterministic"
