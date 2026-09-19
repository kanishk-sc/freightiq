import uuid

import pytest
from sqlalchemy import func, select

import processing
import tasks
from database import SessionLocal
from models import Document, Invoice, ProcessingJob
from processing import PermanentProcessingError, process_job
from schemas import ExtractedInvoice


def create_job() -> str:
    with SessionLocal.begin() as session:
        document = Document(
            object_key=f"invoices/{uuid.uuid4()}/source.pdf",
            original_filename="invoice.pdf",
            content_type="application/pdf",
            size_bytes=100,
            sha256="a" * 64,
        )
        session.add(document)
        session.flush()
        job = ProcessingJob(idempotency_key=str(uuid.uuid4()), document_id=document.id)
        session.add(job)
        session.flush()
        return str(job.id)


def test_processing_is_idempotent_across_task_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = create_job()
    extracted = ExtractedInvoice(
        carrier_name="North Freight",
        invoice_number="INV-20",
        invoice_date="2026-09-18",
        line_items=[],
        total_amount="10.00",
    )

    class FakeStorage:
        def get_bytes(self, key: str) -> bytes:
            assert key.endswith("source.pdf")
            return b"%PDF-fixture"

    monkeypatch.setattr(processing, "DocumentStorage", FakeStorage)
    monkeypatch.setattr(processing, "extract_text_from_pdf", lambda value: "invoice")
    monkeypatch.setattr(processing, "extract_invoice_fields", lambda value: extracted)

    invoice_id = process_job(job_id)
    assert invoice_id is not None
    assert process_job(job_id) is None

    with SessionLocal() as session:
        assert session.scalar(select(func.count(Invoice.id))) == 1
        job = session.get(ProcessingJob, uuid.UUID(job_id))
        assert job is not None
        assert job.status == "completed"
        assert job.attempt_count == 1
        assert job.invoice_id == invoice_id


def test_permanent_worker_failure_persists_safe_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = create_job()

    def fail(_: str) -> None:
        raise PermanentProcessingError("pdf_has_no_text")

    monkeypatch.setattr(tasks, "process_job", fail)
    assert tasks.process_invoice.run(job_id) is None

    with SessionLocal() as session:
        job = session.get(ProcessingJob, uuid.UUID(job_id))
        assert job is not None
        assert job.status == "failed"
        assert job.error_code == "pdf_has_no_text"
