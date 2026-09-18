# Testing Strategy

**Analysis Date:** 2026-09-18

## Current state

- No backend test files exist.
- No frontend test framework or test files exist.
- pytest is not in `backend/requirements.txt`.
- External Anthropic calls have no mocks or contract fixtures.
- SQLite persistence and FastAPI endpoints have no automated behavior checks.

## CI checks

- Backend CI installs requirements and runs `ruff check .`.
- The backend lint job currently fails with 17 errors.
- Frontend CI runs `npm install` rather than deterministic `npm ci`.
- Frontend CI runs `npm run typecheck` but does not build the application.
- Docker images are not built in CI.
- No database or object-storage service is started.

## Baseline results

- Backend imports and exposes `FreightIQ API` on Python 3.12.
- Local backend Ruff check failed on import layout in `extractor.py` and `main.py`.
- Frontend type-check and production build both passed.
- `npm ci` completed but reported five dependency vulnerabilities.

## Critical test targets

- PDF parsing should cover empty, malformed, encrypted, and textless files.
- Pydantic extraction validation should cover malformed JSON, missing fields, invalid decimals, and invalid dates.
- Deterministic audit tests should cover line math, invoice totals, duplicate charges, and decimal rounding.
- Worker tests should cover failure state, bounded retries, and retry idempotency.
- API tests should cover 202 responses, job polling, file validation, 404s, and safe errors.
- Storage tests should mock S3 for unit scope and use MinIO for an integration scope.

## Test architecture recommendation

- Provider clients should be injected behind small interfaces so tests never spend API credits.
- PostgreSQL integration tests should run migrations rather than metadata `create_all`.
- Celery eager mode can test workflow logic while a Compose integration test proves Redis broker behavior.
- Factories should use `Decimal` and deterministic fixture PDFs.

*Testing analysis: 2026-09-18*
