import json
import os
import re
from io import BytesIO
from typing import Any

import anthropic
import pdfplumber

EXTRACTION_SYSTEM_PROMPT = (
    "You are a freight invoice parser. Extract the following fields as JSON: "
    "carrier_name, invoice_number, invoice_date, due_date, origin, destination, "
    "load_id, line_items (array of: description, quantity, unit_price, total), "
    "subtotal, taxes, total_amount. If a field is missing, use null. "
    "Return ONLY valid JSON with no markdown or explanation."
)

MODEL = "claude-sonnet-4-5"


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    text_parts: list[str] = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def _parse_json_response(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def extract_invoice_fields(raw_text: str) -> dict[str, Any]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract invoice fields from this freight invoice text:\n\n"
                    f"{raw_text}"
                ),
            }
        ],
    )

    text_block = next(
        (block.text for block in message.content if block.type == "text"),
        None,
    )
    if not text_block:
        raise ValueError("No text response from Claude")

    return _parse_json_response(text_block)
