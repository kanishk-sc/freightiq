# Repository Structure

**Analysis Date:** 2026-09-18

## Root

- `README.md` is a short setup note and omits architecture, status boundaries, tests, and environment details.
- `.env.example` contains only the Anthropic key placeholder and is located at root while setup references `backend/.env.example`.
- `.gitignore` covers local backend databases, virtual environments, environment files, and node modules.
- `.github/workflows/ci.yml` defines separate backend and frontend jobs.

## Backend

- `backend/main.py` owns FastAPI routes, CORS, persistence mapping, and workflow orchestration.
- `backend/database.py` owns the hard-coded SQLite engine and session dependency.
- `backend/models.py` defines invoice, line item, and audit flag SQLModel tables.
- `backend/extractor.py` owns PDF parsing and Claude extraction.
- `backend/auditor.py` owns Claude-driven anomaly review.
- `backend/generate_sample.py` creates the committed demonstration PDF.
- `backend/requirements.txt` combines runtime, development, and sample-generation dependencies.
- `backend/Dockerfile` builds the API image as root.

## Frontend

- `frontend/src/App.tsx` implements manual view switching and top-level workflow state.
- `frontend/src/api.ts` defines interfaces and endpoint wrappers.
- `frontend/src/components/UploadZone.tsx` handles PDF selection and loading feedback.
- `frontend/src/components/InvoiceTable.tsx` renders extracted fields and line items.
- `frontend/src/components/AuditPanel.tsx` renders model-generated flags.
- `frontend/src/components/Dashboard.tsx` loads summary counts and invoice history.
- `frontend/vite.config.ts` provides only a development proxy.

## Missing structure

- There is no `tests/`, `alembic/`, service layer, repository layer, worker module, storage adapter, or schema module.
- There is no root `docker-compose.yml`, frontend Dockerfile, migration command, or Make/task runner.
- Generated frontend `dist/` and `tsconfig.tsbuildinfo` are not ignored.

## Naming and API shape

- Backend endpoints are unversioned and do not use the README-requested `/api` prefix directly.
- Frontend interfaces mirror ad hoc dictionary responses rather than generated or shared schemas.

*Structure analysis: 2026-09-18*
