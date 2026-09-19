from io import BytesIO

import pytest
from reportlab.pdfgen import canvas

from extractor import extract_text_from_pdf


def make_pdf(text: str = "Invoice INV-100") -> bytes:
    stream = BytesIO()
    document = canvas.Canvas(stream)
    if text:
        document.drawString(72, 720, text)
    document.save()
    return stream.getvalue()


def test_extracts_text_from_pdf() -> None:
    assert "INV-100" in extract_text_from_pdf(make_pdf())


def test_empty_page_returns_empty_text() -> None:
    assert extract_text_from_pdf(make_pdf("")) == ""


def test_malformed_pdf_is_rejected() -> None:
    with pytest.raises(Exception):
        extract_text_from_pdf(b"%PDF-not-a-real-document")
