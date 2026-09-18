# Architecture

**Analysis Date:** 2026-09-18

## Current pattern

- FreightIQ is a two-directory full-stack application with a single-file backend service and component-based React UI.
- The backend mixes transport, orchestration, persistence mapping, and error translation in `backend/main.py`.
- Extraction and audit provider calls are split into `backend/extractor.py` and `backend/auditor.py`.
- Persistence models and engine setup are separate but still tightly coupled to SQLite.

## Upload flow

1. The browser posts a PDF to `/upload`.
2. FastAPI checks only the filename extension and non-empty body.
3. pdfplumber extracts all available text in memory.
4. Claude returns untyped JSON extraction data.
5. `_save_invoice` commits the invoice before adding line items in a second transaction.
6. The full saved invoice is returned synchronously.

## Audit flow

1. The browser explicitly posts to `/audit/{invoice_id}`.
2. The backend materializes invoice, line items, and current flags.
3. Claude is asked to identify both deterministic and subjective anomalies.
4. Existing flags are deleted and response flags are inserted.
5. The invoice is marked audited and returned.

## Data model

- `Invoice` is the aggregate root.
- `LineItem` and `AuditFlag` use integer foreign-key fields but no ORM relationships or cascade rules.
- Monetary values are floats, which is unsafe for exact invoice math.
- Dates are strings and timestamps are naive UTC datetimes.
- Invoice number uniqueness and retry idempotency are not represented.

## Required target boundary

- POST `/api/invoices` should validate/store the document, create one invoice/job transaction, enqueue work, and return 202.
- A Celery worker should own extraction, deterministic audit, optional model-assisted review, and result persistence.
- Object storage should own PDF bytes while PostgreSQL stores keys and metadata.
- Job state transitions should be explicit and safe under retries.

## Architectural risks

- Request-bound model calls cause timeout and concurrency problems.
- Two-commit invoice creation can leave partial aggregates.
- Retried requests can create duplicate invoices.
- Database models accept unvalidated provider data directly.

*Architecture analysis: 2026-09-18*
