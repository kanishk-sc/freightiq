import hashlib
import uuid
from typing import Annotated, Any

import redis
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import get_settings
from database import get_session
from metrics import metrics_response, observe_request
from models import AuditFlag, Document, Invoice, LineItem, ProcessingJob
from storage import DocumentStorage
from tasks import process_invoice

settings = get_settings()
app = FastAPI(title="FreightIQ API", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Idempotency-Key"],
)
app.middleware("http")(observe_request)


def _flag_counts(flags: list[AuditFlag]) -> dict[str, int]:
    return {
        "errors": sum(flag.severity == "error" for flag in flags),
        "warnings": sum(flag.severity == "warning" for flag in flags),
        "total": len(flags),
    }


def _invoice_to_dict(invoice: Invoice, session: Session) -> dict[str, Any]:
    line_items = list(
        session.scalars(
            select(LineItem)
            .where(LineItem.invoice_id == invoice.id)
            .order_by(LineItem.id)
        ).all()
    )
    flags = list(
        session.scalars(
            select(AuditFlag)
            .where(AuditFlag.invoice_id == invoice.id)
            .order_by(AuditFlag.id)
        ).all()
    )
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
        "flag_counts": _flag_counts(flags),
    }


def _job_to_dict(job: ProcessingJob, *, replayed: bool = False) -> dict[str, Any]:
    return {
        "job_id": str(job.id),
        "status": job.status,
        "invoice_id": job.invoice_id,
        "attempt_count": job.attempt_count,
        "error_code": job.error_code,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "replayed": replayed,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def readiness(session: Annotated[Session, Depends(get_session)]) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
        redis.Redis.from_url(settings.redis_url, socket_timeout=2).ping()
        DocumentStorage().check()
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="A dependency is unavailable"
        ) from exc
    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
def metrics() -> Any:
    return metrics_response()


@app.post("/api/invoices", status_code=status.HTTP_202_ACCEPTED)
async def create_invoice_job(
    session: Annotated[Session, Depends(get_session)],
    file: UploadFile = File(...),
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", max_length=255)
    ] = None,
) -> dict[str, Any]:
    key = idempotency_key or str(uuid.uuid4())
    existing = session.scalar(
        select(ProcessingJob).where(ProcessingJob.idempotency_key == key)
    )
    if existing is not None:
        return _job_to_dict(existing, replayed=True)

    if file.content_type != "application/pdf" or not file.filename:
        raise HTTPException(status_code=415, detail="A PDF document is required")
    pdf_bytes = await file.read(settings.max_upload_bytes + 1)
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(pdf_bytes) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="PDF exceeds the upload limit")
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="File content is not a PDF")

    job_id = uuid.uuid4()
    object_key = f"invoices/{job_id}/source.pdf"
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    safe_name = file.filename.replace("\\", "/").rsplit("/", 1)[-1][:255]
    storage = DocumentStorage()
    try:
        storage.put_pdf(object_key, pdf_bytes, digest)
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="Document storage is unavailable"
        ) from exc

    document = Document(
        object_key=object_key,
        original_filename=safe_name,
        content_type="application/pdf",
        size_bytes=len(pdf_bytes),
        sha256=digest,
    )
    session.add(document)
    session.flush()
    job = ProcessingJob(
        id=job_id,
        idempotency_key=key,
        document_id=document.id,
        status="queued",
    )
    session.add(job)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        storage.delete(object_key)
        replay = session.scalar(
            select(ProcessingJob).where(ProcessingJob.idempotency_key == key)
        )
        if replay is None:
            raise HTTPException(status_code=409, detail="Upload could not be recorded")
        return _job_to_dict(replay, replayed=True)
    session.refresh(job)

    try:
        process_invoice.delay(str(job.id))
    except Exception as exc:
        job.status = "failed"
        job.error_code = "queue_unavailable"
        session.commit()
        raise HTTPException(
            status_code=503, detail="Processing queue is unavailable"
        ) from exc
    return _job_to_dict(job)


@app.get("/api/jobs/{job_id}")
def get_job(
    job_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    job = session.get(ProcessingJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_dict(job)


@app.get("/api/invoices")
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
            if key not in {"line_items", "audit_flags"}
        }
        for invoice in invoices
    ]


@app.get("/api/invoices/{invoice_id}")
def get_invoice(
    invoice_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    invoice = session.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _invoice_to_dict(invoice, session)


@app.get("/api/dashboard")
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
