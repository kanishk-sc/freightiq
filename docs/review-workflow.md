# Document review implementation plan

## Repository audit (2026-10-08)

The existing React 19/Vite/Tailwind app uses a typed fetch client and local view
state. FastAPI exposes upload, jobs, invoices, dashboard, health and readiness
under `/api` (except health endpoints). There is no authentication or review queue.
PDFs live in MinIO/S3; PostgreSQL stores document metadata, one processing job and
at most one invoice per document, line items, and deterministic audit flags.
Celery/Redis handles extraction; Pydantic rejects malformed model output before
invoice persistence. Alembic owns schema changes. pytest uses real PostgreSQL and
MinIO; the frontend previously had type/build checks only. Compose binds local
services to loopback. Existing CI runs Python checks and the frontend build.

## Implementation sequence

1. Add review tasks and history through the existing Alembic migration chain.
2. Add `review-service/`: strict TypeScript, Fastify, Zod, node-postgres, Vitest.
3. Notify Node after durable Python processing outcomes; reconcile persisted
   flags/failures in Node after missed notifications or downtime.
4. Add a typed React queue/detail flow reusing invoice and audit components.
5. Wire migrations and services into Compose and checks into CI; exercise the
   workflow against real PostgreSQL and document verification evidence.

## Ownership and invariants

- Python continues to own extraction, validation, invoices and audit flags.
- Node alone writes review tasks/history. Python models describe their schema
  solely so Alembic has one complete metadata registry and migration history.
- One task per document, including resolved tasks. Notifications and periodic
  reconciliation are idempotent and never reset operator work.
- Pending → In Review → Resolved. Resolution requires nonblank resolution notes.
  Notes may be edited in any state. Every actual edit records an immutable history
  snapshot in the same transaction. Row locks and a version precondition prevent
  concurrent operators from silently overwriting changes.
- Node reads existing document/invoice/audit data; no extracted values or model
  behavior are rewritten. Missing required fields and arithmetic/date/duplicate
  flags all qualify. Unreadable PDFs and schema-invalid model output also qualify;
  configuration/network failures do not masquerade as document issues.
- Python notifications have a short timeout and never change processing results.
  Node sweeps at most 100 untracked candidates per interval. The durable source
  signals survive service downtime; no new broker or outbox is needed.
- Local unauthenticated access matches the repository boundary. Both APIs and
  Vite bind to loopback on the host. A hosted version still needs authentication
  and tenant isolation across both APIs.

## Tradeoffs

Reconciliation is eventually consistent (default 30 seconds per batch), not an
exactly-once message bus. Already-existing flagged documents are included. A task
groups all exceptions for one document rather than creating separate assignments
per flag. Resolved tasks are terminal; correction of source invoices and reopening
are outside this feature. Audit history identifies a local operator or pipeline
origin, not an authenticated user identity.

Local execution results and limitations are recorded in
[review-verification.md](review-verification.md).
