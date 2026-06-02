import json
import os
import re
from typing import Any

import anthropic

AUDIT_SYSTEM_PROMPT = (
    "You are a freight billing auditor. Given this structured invoice JSON, "
    "identify anomalies. For each issue return: field, severity (warning|error), "
    "description. Common issues: line item totals that don't add up, missing "
    "required fields, duplicate line items, charges that seem unusually high, "
    "due date before invoice date. Return ONLY a JSON array of objects with keys: "
    "field, severity, description. If no issues found, return an empty array []."
)

MODEL = "claude-sonnet-4-5"


def _parse_json_response(content: str) -> list[dict[str, Any]]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    data = json.loads(cleaned)
    if not isinstance(data, list):
        raise ValueError("Expected JSON array from auditor")
    return data


def audit_invoice(invoice_data: dict[str, Any]) -> list[dict[str, Any]]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

    client = anthropic.Anthropic(api_key=api_key)
    invoice_json = json.dumps(invoice_data, indent=2)

    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=AUDIT_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Audit this freight invoice:\n\n{invoice_json}",
            }
        ],
    )

    text_block = next(
        (block.text for block in message.content if block.type == "text"),
        None,
    )
    if not text_block:
        raise ValueError("No text response from Claude")

    flags = _parse_json_response(text_block)
    validated: list[dict[str, Any]] = []
    for flag in flags:
        severity = flag.get("severity", "warning")
        if severity not in ("warning", "error"):
            severity = "warning"
        validated.append(
            {
                "field": str(flag.get("field", "unknown")),
                "severity": severity,
                "description": str(flag.get("description", "No description")),
            }
        )
    return validated
