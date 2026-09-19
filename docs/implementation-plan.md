# FreightIQ implementation checklist

Checkmarks mean the feature has been executed or tested, not merely configured.

## 1. PostgreSQL foundation

- [x] Replace the SQLite runtime with environment-driven PostgreSQL
- [x] Add SQLAlchemy models with monetary precision, foreign keys and useful indexes
- [x] Add and execute an Alembic migration against local PostgreSQL
- [x] Add database health checking and a reproducible Compose service

## 2. Asynchronous processing and object storage

- [ ] Persist uploaded documents to S3-compatible storage
- [ ] Create idempotent processing jobs with explicit state transitions
- [ ] Process extraction and auditing in a Redis-backed Celery worker
- [ ] Return 202 from upload and expose job/invoice retrieval endpoints

## 3. Extraction and deterministic audit reliability

- [ ] Validate Claude output with strict Pydantic contracts
- [ ] Bound model timeouts and retry only transient failures
- [ ] Calculate totals, duplicates, dates and required fields deterministically
- [ ] Ensure logs never contain document text or credentials

## 4. Tests and frontend

- [ ] Cover parsing, validation, arithmetic, duplicate charges and malformed model output
- [ ] Cover worker failure, retry idempotency and API error behavior without paid calls
- [ ] Add typed upload/job polling and complete/error states to the React interface
- [ ] Run backend and frontend verification in GitHub Actions

## 5. Operational evidence

- [ ] Add bounded low-cardinality API and worker metrics
- [ ] Run a real local end-to-end PDF → object → worker → result demonstration
- [ ] Record only observed functional or performance results
