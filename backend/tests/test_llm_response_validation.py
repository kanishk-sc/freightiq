from types import SimpleNamespace

import pytest

import extractor
from config import get_settings
from extractor import ExtractionConfigurationError, extract_invoice_fields

VALID_RESPONSE = (
    '{"carrier_name":"Carrier","invoice_number":"INV-3",'
    '"invoice_date":"2026-09-18","due_date":null,"origin":null,'
    '"destination":null,"load_id":null,"line_items":[],"subtotal":null,'
    '"taxes":null,"total_amount":null}'
)


def test_missing_api_key_fails_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    get_settings.cache_clear()
    with pytest.raises(ExtractionConfigurationError):
        extract_invoice_fields("invoice text")


def test_client_is_bounded_and_response_is_validated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    class FakeMessages:
        def create(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text=VALID_RESPONSE)]
            )

    class FakeClient:
        def __init__(self, **kwargs):
            calls["client"] = kwargs
            self.messages = FakeMessages()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setattr(extractor.anthropic, "Anthropic", FakeClient)
    get_settings.cache_clear()
    result = extract_invoice_fields("x" * 60_000)

    assert result.invoice_number == "INV-3"
    assert calls["client"] == {
        "api_key": "test-key-not-real",
        "timeout": 30.0,
        "max_retries": 0,
    }
    user_text = calls["messages"][0]["content"]
    assert len(user_text) < 51_000
