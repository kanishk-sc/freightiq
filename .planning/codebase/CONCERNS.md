# Technical Concerns

**Analysis Date:** 2026-09-18

## Correctness

- Claude performs audit math and duplicate detection that should be deterministic code.
- Unvalidated JSON can persist wrong types or fail midway through a request.
- Monetary floats can introduce rounding errors.
- Invoice creation uses two commits and can leave an invoice without line items.
- Duplicate invoice numbers and request retries are not constrained.

## Reliability

- PDF parsing and two separate Claude calls run synchronously inside HTTP requests.
- No explicit SDK timeout, bounded retry, circuit behavior, or job failure state exists.
- A worker retry could duplicate data because there is no job or idempotency key.
- Startup `create_all` is not a migration strategy.

## Security and privacy

- File validation trusts filename extension and does not verify content type or PDF magic bytes.
- Upload size is unbounded and the full document is read into memory.
- Raw invoice text is stored in SQLite and sent to Claude without a documented privacy boundary.
- Raw exception messages may disclose parser/provider internals to clients.
- The backend Docker image runs as root.
- There is no authentication, so production deployment would expose sensitive invoice data.

## Operations

- No structured logs, metrics, traces, health endpoint, or readiness endpoint exist.
- There is no Compose stack for the claimed full application.
- The frontend production API base is fixed to `/api` but no production reverse proxy is supplied.
- Dependency installation is loosely versioned.

## Repository hygiene

- CI is red because Ruff fails.
- Frontend build outputs are not ignored.
- The README points to a non-existent `backend/.env.example`.
- The README omits the absence of tests and background processing.
- Five npm audit findings need triage before adding more frontend dependencies.

## Hiring-manager risk

- The current project demonstrates a prototype, not production AI reliability.
- A senior reviewer will immediately question LLM-based arithmetic, synchronous uploads, SQLite, no tests, and unsafe upload limits.
- The strongest next proof is a transactional PostgreSQL job model plus deterministic audit tests before adding observability polish.

*Concern analysis: 2026-09-18*
