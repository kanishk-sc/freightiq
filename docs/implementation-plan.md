# FreightIQ implementation checklist

Checkmarks mean the feature has been executed or tested, not merely configured.

## 1. PostgreSQL foundation

- [x] Replace the SQLite runtime with environment-driven PostgreSQL
- [x] Add SQLAlchemy models with monetary precision, foreign keys and useful indexes
- [x] Add and execute an Alembic migration against local PostgreSQL
- [x] Add database health checking and a reproducible Compose service

## 2. Asynchronous processing and object storage

- [x] Persist uploaded documents to S3-compatible storage
- [x] Create idempotent processing jobs with explicit state transitions
- [x] Process extraction and auditing in a Redis-backed Celery worker
- [x] Return 202 from upload and expose job/invoice retrieval endpoints

## 3. Extraction and deterministic audit reliability

- [x] Validate Claude output with strict Pydantic contracts
- [x] Bound model timeouts and retry only transient failures
- [x] Calculate totals, duplicates, dates and required fields deterministically
- [x] Ensure logs never contain document text or credentials

## 4. Tests and frontend

- [x] Cover parsing, validation, arithmetic, duplicate charges and malformed model output
- [x] Cover worker failure, retry idempotency and API error behavior without paid calls
- [x] Add typed upload/job polling and complete/error states to the React interface
- [x] Run backend and frontend verification in GitHub Actions

## 5. Operational evidence

- [ ] Add bounded low-cardinality API and worker metrics
- [x] Run a real local PDF → object → Celery worker failure-path demonstration
- [ ] Run a successful live extraction with a configured Anthropic API key
- [ ] Record only observed functional or performance results
