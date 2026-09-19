from collections import Counter
from decimal import Decimal

from schemas import AuditFinding, ExtractedInvoice, ExtractedLineItem

CENT = Decimal("0.01")


def _finding(field: str, severity: str, description: str) -> AuditFinding:
    return AuditFinding(
        field=field,
        severity=severity,
        description=description,
    )


def _money_equal(left: Decimal, right: Decimal) -> bool:
    return abs(left - right) <= CENT


def _line_key(
    item: ExtractedLineItem,
) -> tuple[str, Decimal | None, Decimal | None, Decimal | None]:
    return (
        (item.description or "").strip().casefold(),
        item.quantity,
        item.unit_price,
        item.total,
    )


def audit_invoice(invoice: ExtractedInvoice) -> list[dict[str, str]]:
    findings: list[AuditFinding] = []
    for field, value in (
        ("carrier_name", invoice.carrier_name),
        ("invoice_number", invoice.invoice_number),
        ("invoice_date", invoice.invoice_date),
        ("total_amount", invoice.total_amount),
    ):
        if value is None:
            findings.append(
                _finding(field, "error", f"Required field {field} is missing")
            )

    if (
        invoice.invoice_date
        and invoice.due_date
        and invoice.due_date < invoice.invoice_date
    ):
        findings.append(
            _finding("due_date", "error", "Due date is earlier than the invoice date")
        )

    counts = Counter(_line_key(item) for item in invoice.line_items)
    for key, count in counts.items():
        if count > 1:
            label = key[0] or "unnamed charge"
            findings.append(
                _finding(
                    "line_items",
                    "warning",
                    f"Possible duplicate charge: {label} appears {count} times",
                )
            )

    stated_line_totals: list[Decimal] = []
    for index, item in enumerate(invoice.line_items):
        if item.total is not None:
            stated_line_totals.append(item.total)
        if item.quantity is None or item.unit_price is None or item.total is None:
            continue
        calculated = item.quantity * item.unit_price
        if not _money_equal(calculated, item.total):
            description = (
                f"Stated {item.total:.2f}; quantity × unit price is {calculated:.2f}"
            )
            findings.append(
                _finding(
                    f"line_items[{index}].total",
                    "error",
                    description,
                )
            )

    if invoice.subtotal is not None and stated_line_totals:
        calculated_subtotal = sum(stated_line_totals, start=Decimal("0"))
        if not _money_equal(calculated_subtotal, invoice.subtotal):
            description = (
                f"Stated {invoice.subtotal:.2f}; "
                f"line items sum to {calculated_subtotal:.2f}"
            )
            findings.append(
                _finding(
                    "subtotal",
                    "error",
                    description,
                )
            )

    if (
        invoice.subtotal is not None
        and invoice.taxes is not None
        and invoice.total_amount is not None
    ):
        calculated_total = invoice.subtotal + invoice.taxes
        if not _money_equal(calculated_total, invoice.total_amount):
            description = (
                f"Stated {invoice.total_amount:.2f}; "
                f"subtotal plus taxes is {calculated_total:.2f}"
            )
            findings.append(
                _finding(
                    "total_amount",
                    "error",
                    description,
                )
            )
    return [finding.model_dump() for finding in findings]
