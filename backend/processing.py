import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from auditor import audit_invoice
from database import SessionLocal
from extractor import extract_invoice_fields, extract_text_from_pdf
from models import AuditFlag, Document, Invoice, LineItem, ProcessingJob
from storage import DocumentStorage


class PermanentProcessingError(RuntimeError):
    pass


class TransientProcessingError(RuntimeError):
    pass


def _begin_attempt(job_id: uuid.UUID) -> tuple[int, str] | None:
    with SessionLocal.begin() as session:
        job = session.get(ProcessingJob, job_id, with_for_update=True)
        if job is None:
            raise PermanentProcessingError("job_not_found")
        if job.status == "completed":
            return None
        if (
            job.status == "processing"
            and job.started_at
            and job.started_at > datetime.now(UTC) - timedelta(minutes=15)
        ):
            return None
        document = session.get(Document, job.document_id)
        if document is None:
            raise PermanentProcessingError("document_metadata_missing")
        job.status = "processing"
        job.attempt_count += 1
        job.error_code = None
        job.started_at = datetime.now(UTC)
        return document.id, document.object_key


def _persist_invoice(
    job_id: uuid.UUID,
    document_id: int,
    extracted: dict[str, Any],
    flags: list[dict[str, Any]],
) -> int:
    with SessionLocal.begin() as session:
        job = session.get(ProcessingJob, job_id, with_for_update=True)
        if job is None:
            raise PermanentProcessingError("job_not_found")
        if job.invoice_id is not None:
            job.status = "completed"
            return job.invoice_id
        existing = session.scalar(
            select(Invoice).where(Invoice.document_id == document_id)
        )
        if existing is not None:
            job.invoice_id = existing.id
            job.status = "completed"
            job.completed_at = datetime.now(UTC)
            return existing.id

        invoice = Invoice(
            document_id=document_id,
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
            audited=True,
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
        for flag in flags:
            session.add(
                AuditFlag(
                    invoice_id=invoice.id,
                    field=str(flag.get("field", "unknown")),
                    severity=str(flag.get("severity", "warning")),
                    description=str(flag.get("description", "Review required")),
                    source=str(flag.get("source", "model")),
                )
            )
        job.invoice_id = invoice.id
        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        return invoice.id


def process_job(job_id: str) -> int | None:
    parsed_job_id = uuid.UUID(job_id)
    attempt = _begin_attempt(parsed_job_id)
    if attempt is None:
        return None
    document_id, object_key = attempt
    try:
        pdf_bytes = DocumentStorage().get_bytes(object_key)
    except Exception as exc:
        raise TransientProcessingError("storage_read_failed") from exc
    try:
        raw_text = extract_text_from_pdf(pdf_bytes)
    except Exception as exc:
        raise PermanentProcessingError("pdf_parse_failed") from exc
    if not raw_text.strip():
        raise PermanentProcessingError("pdf_has_no_text")
    try:
        extracted = extract_invoice_fields(raw_text)
        flags = audit_invoice(extracted)
    except ValueError as exc:
        raise PermanentProcessingError("model_configuration_or_output_invalid") from exc
    except Exception as exc:
        raise TransientProcessingError("model_request_failed") from exc
    return _persist_invoice(
        parsed_job_id,
        document_id,
        extracted.model_dump(mode="json"),
        flags,
    )


def set_job_state(job_id: str, *, status: str, error_code: str) -> None:
    with SessionLocal.begin() as session:
        job = session.get(ProcessingJob, uuid.UUID(job_id), with_for_update=True)
        if job is None or job.status == "completed":
            return
        job.status = status
        job.error_code = error_code
