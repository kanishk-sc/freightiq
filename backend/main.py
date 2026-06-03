from dotenv import load_dotenv
load_dotenv()
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from auditor import audit_invoice
from database import create_db_and_tables, get_session
from extractor import extract_invoice_fields, extract_text_from_pdf
from models import AuditFlag, Invoice, LineItem

app = FastAPI(title="FreightIQ API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()


def _invoice_to_dict(invoice: Invoice, session: Session) -> dict[str, Any]:
    line_items = session.exec(
        select(LineItem).where(LineItem.invoice_id == invoice.id)
    ).all()
    flags = session.exec(
        select(AuditFlag).where(AuditFlag.invoice_id == invoice.id)
    ).all()
    return {
        "id": invoice.id,
        "carrier_name": invoice.carrier_name,
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date,
        "due_date": invoice.due_date,
        "origin": invoice.origin,
        "destination": invoice.destination,
        "load_id": invoice.load_id,
        "subtotal": invoice.subtotal,
        "taxes": invoice.taxes,
        "total_amount": invoice.total_amount,
        "audited": invoice.audited,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "line_items": [
            {
                "id": li.id,
                "description": li.description,
                "quantity": li.quantity,
                "unit_price": li.unit_price,
                "total": li.total,
            }
            for li in line_items
        ],
        "audit_flags": [
            {
                "id": f.id,
                "field": f.field,
                "severity": f.severity,
                "description": f.description,
            }
            for f in flags
        ],
        "flag_counts": {
            "errors": sum(1 for f in flags if f.severity == "error"),
            "warnings": sum(1 for f in flags if f.severity == "warning"),
            "total": len(flags),
        },
    }


def _save_invoice(
    session: Session, extracted: dict[str, Any], raw_text: str
) -> Invoice:
    invoice = Invoice(
        carrier_name=extracted.get("carrier_name"),
        invoice_number=extracted.get("invoice_number"),
        invoice_date=extracted.get("invoice_date"),
        due_date=extracted.get("due_date"),
        origin=extracted.get("origin"),
        destination=extracted.get("destination"),
        load_id=extracted.get("load_id"),
        subtotal=extracted.get("subtotal"),
        taxes=extracted.get("taxes"),
        total_amount=extracted.get("total_amount"),
        raw_text=raw_text,
        audited=False,
    )
    session.add(invoice)
    session.commit()
    session.refresh(invoice)

    for item in extracted.get("line_items") or []:
        if not isinstance(item, dict):
            continue
        line = LineItem(
            invoice_id=invoice.id,
            description=item.get("description"),
            quantity=item.get("quantity"),
            unit_price=item.get("unit_price"),
            total=item.get("total"),
        )
        session.add(line)
    session.commit()
    session.refresh(invoice)
    return invoice


@app.post("/upload")
async def upload_invoice(
    session: Annotated[Session, Depends(get_session)],
    file: UploadFile = File(...),
) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        raw_text = extract_text_from_pdf(pdf_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Failed to parse PDF: {exc}"
        ) from exc

    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="No text found in PDF")

    try:
        extracted = extract_invoice_fields(raw_text)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Failed to extract invoice fields: {exc}"
        ) from exc

    invoice = _save_invoice(session, extracted, raw_text)
    return _invoice_to_dict(invoice, session)


@app.post("/audit/{invoice_id}")
def run_audit(
    invoice_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice_data = _invoice_to_dict(invoice, session)
    audit_payload = {k: v for k, v in invoice_data.items() if k != "audit_flags"}

    try:
        flags = audit_invoice(audit_payload)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Audit failed: {exc}"
        ) from exc

    existing = session.exec(
        select(AuditFlag).where(AuditFlag.invoice_id == invoice_id)
    ).all()
    for flag in existing:
        session.delete(flag)

    for flag in flags:
        session.add(
            AuditFlag(
                invoice_id=invoice_id,
                field=flag["field"],
                severity=flag["severity"],
                description=flag["description"],
            )
        )

    invoice.audited = True
    session.add(invoice)
    session.commit()
    session.refresh(invoice)

    result = _invoice_to_dict(invoice, session)
    return {
        "invoice_id": invoice_id,
        "audit_flags": result["audit_flags"],
        "flag_counts": result["flag_counts"],
    }


@app.get("/invoices")
def list_invoices(
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, Any]]:
    invoices = session.exec(
        select(Invoice).order_by(Invoice.created_at.desc())
    ).all()
    summaries: list[dict[str, Any]] = []
    for inv in invoices:
        flags = session.exec(
            select(AuditFlag).where(AuditFlag.invoice_id == inv.id)
        ).all()
        summaries.append(
            {
                "id": inv.id,
                "carrier_name": inv.carrier_name,
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date,
                "total_amount": inv.total_amount,
                "audited": inv.audited,
                "flag_counts": {
                    "errors": sum(1 for f in flags if f.severity == "error"),
                    "warnings": sum(1 for f in flags if f.severity == "warning"),
                    "total": len(flags),
                },
            }
        )
    return summaries


@app.get("/invoices/{invoice_id}")
def get_invoice(
    invoice_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _invoice_to_dict(invoice, session)


@app.get("/dashboard")
def dashboard_stats(
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    invoices = session.exec(select(Invoice)).all()
    all_flags = session.exec(select(AuditFlag)).all()
    return {
        "total_invoices": len(invoices),
        "total_audited": sum(1 for i in invoices if i.audited),
        "total_errors": sum(1 for f in all_flags if f.severity == "error"),
        "total_warnings": sum(1 for f in all_flags if f.severity == "warning"),
    }
