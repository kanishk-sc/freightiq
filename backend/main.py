from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from auditor import audit_invoice
from config import get_settings
from database import get_session
from extractor import extract_invoice_fields, extract_text_from_pdf
from models import AuditFlag, Invoice, LineItem

settings = get_settings()
app = FastAPI(title="FreightIQ API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def _invoice_to_dict(invoice: Invoice, session: Session) -> dict[str, Any]:
    line_items = session.scalars(
        select(LineItem).where(LineItem.invoice_id == invoice.id).order_by(LineItem.id)
    ).all()
    flags = session.scalars(
        select(AuditFlag)
        .where(AuditFlag.invoice_id == invoice.id)
        .order_by(AuditFlag.id)
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
        "created_at": invoice.created_at,
        "line_items": [
            {
                "id": item.id,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total": item.total,
            }
            for item in line_items
        ],
        "audit_flags": [
            {
                "id": flag.id,
                "field": flag.field,
                "severity": flag.severity,
                "description": flag.description,
                "source": flag.source,
            }
            for flag in flags
        ],
        "flag_counts": {
            "errors": sum(flag.severity == "error" for flag in flags),
            "warnings": sum(flag.severity == "warning" for flag in flags),
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
    )
    session.add(invoice)
    session.flush()
    for item in extracted.get("line_items") or []:
        if isinstance(item, dict):
            session.add(
                LineItem(
                    invoice_id=invoice.id,
                    description=item.get("description"),
                    quantity=item.get("quantity"),
                    unit_price=item.get("unit_price"),
                    total=item.get("total"),
                )
            )
    session.commit()
    session.refresh(invoice)
    return invoice


@app.get("/health")
def health(session: Annotated[Session, Depends(get_session)]) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/upload")
async def upload_invoice(
    session: Annotated[Session, Depends(get_session)],
    file: UploadFile = File(...),
) -> dict[str, Any]:
    if file.content_type != "application/pdf" or not file.filename:
        raise HTTPException(status_code=415, detail="A PDF document is required")
    pdf_bytes = await file.read(settings.max_upload_bytes + 1)
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(pdf_bytes) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="PDF exceeds the upload limit")
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="File content is not a PDF")

    try:
        raw_text = extract_text_from_pdf(pdf_bytes)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Unable to parse PDF") from exc
    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="PDF contains no extractable text")

    try:
        extracted = extract_invoice_fields(raw_text)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail="Invoice extraction failed"
        ) from exc

    return _invoice_to_dict(_save_invoice(session, extracted, raw_text), session)


@app.post("/audit/{invoice_id}")
def run_audit(
    invoice_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    flags = audit_invoice(_invoice_to_dict(invoice, session))
    for flag in session.scalars(
        select(AuditFlag).where(AuditFlag.invoice_id == invoice_id)
    ):
        session.delete(flag)
    for flag in flags:
        session.add(AuditFlag(invoice_id=invoice_id, **flag))
    invoice.audited = True
    session.commit()
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
    invoices = session.scalars(
        select(Invoice).order_by(Invoice.created_at.desc())
    ).all()
    return [
        {
            key: value
            for key, value in _invoice_to_dict(invoice, session).items()
            if key not in {"line_items", "audit_flags", "raw_text"}
        }
        for invoice in invoices
    ]


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
    invoices = session.scalars(select(Invoice)).all()
    flags = session.scalars(select(AuditFlag)).all()
    return {
        "total_invoices": len(invoices),
        "total_audited": sum(invoice.audited for invoice in invoices),
        "total_errors": sum(flag.severity == "error" for flag in flags),
        "total_warnings": sum(flag.severity == "warning" for flag in flags),
    }
