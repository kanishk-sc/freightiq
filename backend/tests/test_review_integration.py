import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest
from sqlalchemy import text
from test_jobs import create_job

import processing
import review_client
import tasks
from database import SessionLocal
from extractor import ExtractionValidationError
from schemas import ExtractedInvoice


def test_unavailable_review_service_does_not_break_processing(monkeypatch):
    job_id = create_job()

    class FakeStorage:
        def get_bytes(self, _key):
            return b"%PDF-fixture"

    monkeypatch.setattr(processing, "DocumentStorage", FakeStorage)
    monkeypatch.setattr(processing, "extract_text_from_pdf", lambda _: "invoice")
    monkeypatch.setattr(
        processing, "extract_invoice_fields", lambda _: ExtractedInvoice()
    )
    monkeypatch.setattr(
        review_client,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(URLError("private details")),
    )
    assert tasks.process_invoice.run(job_id) is not None
    with SessionLocal() as session:
        assert (
            session.execute(
                text("SELECT status FROM processing_jobs WHERE id = :id"),
                {"id": job_id},
            ).scalar_one()
            == "completed"
        )


def test_schema_failure_has_a_distinct_durable_review_signal(monkeypatch):
    job_id = create_job()

    class FakeStorage:
        def get_bytes(self, _key):
            return b"%PDF-fixture"

    def invalid(_text):
        raise ExtractionValidationError("invalid output")

    monkeypatch.setattr(processing, "DocumentStorage", FakeStorage)
    monkeypatch.setattr(processing, "extract_text_from_pdf", lambda _: "invoice")
    monkeypatch.setattr(processing, "extract_invoice_fields", invalid)
    monkeypatch.setattr(tasks, "notify_review", lambda _: None)
    tasks.process_invoice.run(job_id)
    with SessionLocal() as session:
        assert (
            session.execute(
                text("SELECT error_code FROM processing_jobs WHERE id = :id"),
                {"id": job_id},
            ).scalar_one()
            == "extraction_validation_failed"
        )


@pytest.mark.skipif(
    not os.getenv("REVIEW_INTEGRATION_URL"),
    reason="Requires running Node review service",
)
def test_flagged_document_creates_real_node_task_and_persists_resolution(monkeypatch):
    job_id = create_job()

    class FakeStorage:
        def get_bytes(self, _key):
            return b"%PDF-fixture"

    monkeypatch.setattr(processing, "DocumentStorage", FakeStorage)
    monkeypatch.setattr(
        processing, "extract_text_from_pdf", lambda _: "invoice missing required fields"
    )
    monkeypatch.setattr(
        processing, "extract_invoice_fields", lambda _: ExtractedInvoice()
    )
    assert tasks.process_invoice.run(job_id) is not None
    base = os.environ["REVIEW_INTEGRATION_URL"].rstrip("/")
    with SessionLocal() as session:
        row = session.execute(
            text(
                "SELECT r.id, r.version FROM review_tasks r "
                "JOIN processing_jobs j ON j.document_id = r.document_id "
                "WHERE j.id = :id"
            ),
            {"id": job_id},
        ).one()
        task_id, version = row.id, row.version
    for status, resolution in [
        ("in_review", ""),
        ("resolved", "Carrier contacted; corrected invoice requested"),
    ]:
        request = Request(
            f"{base}/api/review-tasks/{task_id}",
            method="PATCH",
            data=json.dumps(
                {"status": status, "version": version, "resolution": resolution}
            ).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=5) as response:
            updated = json.load(response)
        version = updated["version"]
    with SessionLocal() as session:
        task = session.execute(
            text(
                "SELECT status, resolution, resolved_at FROM review_tasks "
                "WHERE id = :id"
            ),
            {"id": task_id},
        ).one()
        assert task.status == "resolved"
        assert task.resolved_at is not None
        assert task.resolution == "Carrier contacted; corrected invoice requested"
        assert (
            session.execute(
                text("SELECT count(*) FROM review_history WHERE task_id = :id"),
                {"id": task_id},
            ).scalar_one()
            == 3
        )
