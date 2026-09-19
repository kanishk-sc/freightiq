import hashlib
import uuid

from storage import DocumentStorage


def test_minio_pdf_round_trip() -> None:
    content = b"%PDF-1.4\nfreightiq-storage-test\n%%EOF"
    digest = hashlib.sha256(content).hexdigest()
    key = f"tests/{uuid.uuid4()}.pdf"
    storage = DocumentStorage()

    storage.put_pdf(key, content, digest)
    try:
        assert storage.get_bytes(key) == content
        metadata = storage.client.head_object(Bucket=storage.bucket, Key=key)
        assert metadata["ContentType"] == "application/pdf"
        assert metadata["Metadata"]["sha256"] == digest
    finally:
        storage.delete(key)
