import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

import main
from database import SessionLocal
from main import app
from models import Document, ProcessingJob


class FakeStorage:
    uploads: list[tuple[str, bytes, str]] = []
    deletes: list[str] = []

    def put_pdf(self, key: str, content: bytes, sha256: str) -> None:
        self.uploads.append((key, content, sha256))

    def delete(self, key: str) -> None:
        self.deletes.append(key)

    def check(self) -> None:
        return None


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    FakeStorage.uploads.clear()
    FakeStorage.deletes.clear()
    monkeypatch.setattr(main, "DocumentStorage", FakeStorage)
    monkeypatch.setattr(main.process_invoice, "delay", lambda job_id: None)
    return TestClient(app)


def upload(
    client: TestClient,
    *,
    key: str = "test-idempotency-key",
    content: bytes = b"%PDF-fixture",
    content_type: str = "application/pdf",
) -> object:
    return client.post(
        "/api/invoices",
        files={"file": ("../unsafe.pdf", content, content_type)},
        headers={"Idempotency-Key": key},
    )


def test_upload_returns_202_and_replays_idempotently(client: TestClient) -> None:
    first = upload(client)
    second = upload(client)

    assert first.status_code == 202
    assert first.json()["status"] == "queued"
    assert second.status_code == 202
    assert second.json()["job_id"] == first.json()["job_id"]
    assert second.json()["replayed"] is True
    assert len(FakeStorage.uploads) == 1

    with SessionLocal() as session:
        assert session.scalar(select(func.count(Document.id))) == 1
        assert session.scalar(select(func.count(ProcessingJob.id))) == 1
        document = session.scalar(select(Document))
        assert document is not None
        assert document.original_filename == "unsafe.pdf"
        assert len(document.sha256) == 64


@pytest.mark.parametrize(
    ("content", "content_type", "expected"),
    [
        (b"", "application/pdf", 400),
        (b"not-pdf", "application/pdf", 422),
        (b"%PDF-fixture", "text/plain", 415),
    ],
)
def test_upload_validation(
    client: TestClient,
    content: bytes,
    content_type: str,
    expected: int,
) -> None:
    assert (
        upload(client, content=content, content_type=content_type).status_code
        == expected
    )


def test_queue_failure_is_persisted(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(_: str) -> None:
        raise OSError("broker details must not escape")

    monkeypatch.setattr(main.process_invoice, "delay", unavailable)
    response = upload(client, key="queue-failure")

    assert response.status_code == 503
    assert response.json()["detail"] == "Processing queue is unavailable"
    with SessionLocal() as session:
        job = session.scalar(select(ProcessingJob))
        assert job is not None
        assert job.status == "failed"
        assert job.error_code == "queue_unavailable"


def test_missing_resources_return_404(client: TestClient) -> None:
    assert (
        client.get("/api/jobs/00000000-0000-0000-0000-000000000000").status_code == 404
    )
    assert client.get("/api/invoices/999").status_code == 404
