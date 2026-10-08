"""Upload a real PDF through the running API for a local review demonstration.

The default blank PDF exercises the unreadable-document path without an AI key.
Use --file sample_invoice.pdf to exercise extraction and deterministic audit.
"""

import argparse
import json
import time
import uuid
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

from reportlab.pdfgen import canvas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--file", type=Path)
    args = parser.parse_args()
    if args.file:
        content = args.file.read_bytes()
        filename = args.file.name
    else:
        stream = BytesIO()
        pdf = canvas.Canvas(stream)
        pdf.showPage()
        pdf.save()
        content = stream.getvalue()
        filename = "demo-unreadable-invoice.pdf"
    boundary = uuid.uuid4().hex
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            f'filename="{filename}"\r\nContent-Type: application/pdf\r\n\r\n'
        ).encode()
        + content
        + f"\r\n--{boundary}--\r\n".encode()
    )
    request = Request(
        args.api_url.rstrip("/") + "/api/invoices",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Idempotency-Key": str(uuid.uuid4()),
        },
    )
    with urlopen(request, timeout=10) as response:
        job = json.load(response)
    print(f"Uploaded {filename}; job {job['job_id']}")
    for _ in range(60):
        if job["status"] in {"completed", "failed"}:
            print(f"Outcome: {job['status']}; error_code={job['error_code']}")
            print("Open Review Queue in React and refresh to inspect the document.")
            return
        time.sleep(1)
        with urlopen(
            f"{args.api_url.rstrip('/')}/api/jobs/{job['job_id']}", timeout=5
        ) as response:
            job = json.load(response)
    raise SystemExit(
        "Processing is still pending; check worker logs and refresh later."
    )


if __name__ == "__main__":
    main()
