import pytest

from extractor import ExtractionValidationError, parse_extraction_response


def test_validates_and_normalizes_model_output() -> None:
    invoice = parse_extraction_response(
        '{"carrier_name":"  North Freight ","invoice_number":"INV-1",'
        '"invoice_date":"2026-09-18","due_date":null,"origin":null,'
        '"destination":null,"load_id":null,"line_items":[],"subtotal":10.10,'
        '"taxes":0.90,"total_amount":11.00}'
    )
    assert invoice.carrier_name == "North Freight"
    assert str(invoice.total_amount) == "11.0"


@pytest.mark.parametrize(
    "response",
    [
        "not json",
        "[]",
        '{"unknown":"field"}',
        '{"carrier_name":null,"invoice_number":null,"invoice_date":null,'
        '"due_date":null,"origin":null,"destination":null,"load_id":null,'
        '"line_items":[{"description":"Fuel","quantity":-1,'
        '"unit_price":2,"total":-2}],"subtotal":null,"taxes":null,'
        '"total_amount":null}',
    ],
)
def test_rejects_malformed_or_out_of_contract_output(response: str) -> None:
    with pytest.raises(ExtractionValidationError):
        parse_extraction_response(response)
