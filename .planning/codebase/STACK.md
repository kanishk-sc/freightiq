# Technology Stack

**Analysis Date:** 2026-09-18

## Backend

- Python is executed as loose modules from `backend/`; there is no installable package definition.
- FastAPI provides synchronous upload, audit, list, detail, and dashboard endpoints.
- SQLModel combines Pydantic-style models with SQLAlchemy persistence.
- SQLite is hard-coded in `backend/database.py`.
- Anthropic's Python SDK calls Claude for both extraction and auditing.
- pdfplumber extracts text from uploaded PDFs.

## Frontend

- React 19 and TypeScript 5.7 are built with Vite 6.
- Tailwind CSS 3 provides styling.
- A hand-written typed client in `frontend/src/api.ts` wraps Fetch.
- State is local React state; there is no router or server-state library.

## Tooling

- Ruff is installed through production `requirements.txt` and configured in `backend/pyproject.toml`.
- npm has a committed lock file.
- GitHub Actions runs backend lint and frontend type-check only.
- `backend/Dockerfile` containerizes only the API.
- There is no root Docker Compose configuration despite the README's container language.

## Baseline verification

- Frontend `npm run typecheck` passed on 2026-09-18.
- Frontend `npm run build` passed on 2026-09-18.
- Backend import smoke test passed on Python 3.12.
- Backend Ruff check failed with 17 import-order and module-import-position errors.
- No pytest tests or test dependencies exist.
- `npm ci` reported five dependency vulnerabilities: one low, one moderate, and three high.

## Target gaps

- PostgreSQL, Alembic, Redis, Celery, S3/MinIO, OpenTelemetry, and Prometheus are not implemented.
- No worker, retry policy, job state model, object-storage adapter, or asynchronous upload workflow exists.

*Stack analysis: 2026-09-18*
