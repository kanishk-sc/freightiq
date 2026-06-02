"""Generate a sample freight invoice PDF with intentional audit issues."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUTPUT = Path(__file__).parent / "sample_invoice.pdf"


def build_pdf() -> None:
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>ACME FREIGHT LOGISTICS</b>", styles["Title"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Freight Invoice", styles["Heading2"]))
    story.append(Spacer(1, 0.3 * inch))

    meta = [
        ["Invoice Number:", "INV-2025-78432"],
        ["Invoice Date:", "2025-05-15"],
        ["Due Date:", "2025-06-14"],
        ["Load ID:", "LD-908877"],
        ["Origin:", "Chicago, IL"],
        ["Destination:", "Dallas, TX"],
    ]
    meta_table = Table(meta, colWidths=[1.5 * inch, 3 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 0.4 * inch))

    # Line items: 5 rows — one math error, one duplicate description
    line_data = [
        ["Description", "Qty", "Unit Price", "Total"],
        ["Linehaul - Full Truckload", "1", "$2,450.00", "$2,450.00"],
        ["Fuel Surcharge", "1", "$385.00", "$385.00"],
        ["Detention - Origin (2 hrs)", "2", "$75.00", "$150.00"],
        # Intentional math error: 3 × 120 should be 360, not 400
        ["Lumper Fee - Destination", "3", "$120.00", "$400.00"],
        # Duplicate of fuel surcharge line
        ["Fuel Surcharge", "1", "$385.00", "$385.00"],
    ]

    line_table = Table(
        line_data,
        colWidths=[3 * inch, 0.8 * inch, 1.2 * inch, 1.2 * inch],
    )
    line_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f8fafc")],
                ),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(line_table)
    story.append(Spacer(1, 0.3 * inch))

    totals = [
        ["Subtotal:", "$3,770.00"],
        ["Taxes:", "$301.60"],
        ["Total Amount Due:", "$4,071.60"],
    ]
    totals_table = Table(totals, colWidths=[4.5 * inch, 1.5 * inch])
    totals_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(totals_table)
    story.append(Spacer(1, 0.5 * inch))
    story.append(
        Paragraph(
            "Payment terms: Net 30. Remit to ACME Freight Logistics, "
            "PO Box 4400, Chicago IL 60601.",
            styles["Normal"],
        )
    )

    doc.build(story)
    print(f"Sample invoice written to {OUTPUT}")


if __name__ == "__main__":
    build_pdf()
