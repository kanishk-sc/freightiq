# External Integrations

**Analysis Date:** 2026-09-18

## Anthropic Claude

- `backend/extractor.py` sends raw invoice text to `claude-sonnet-4-5` for JSON extraction.
- `backend/auditor.py` sends the structured invoice back to Claude for anomaly detection.
- Both calls use a direct synchronous SDK request with no explicit timeout or retry policy.
- Responses are parsed with `json.loads` after optional Markdown fence stripping.
- The API key comes from `ANTHROPIC_API_KEY` loaded from dotenv.
- Paid calls are not mocked because no tests exist.

## Database

- SQLite is opened through a process-local SQLModel engine.
- Tables are created from metadata during FastAPI startup.
- There are no migrations, database environment variables, indexes, explicit constraints, or PostgreSQL support.
- Raw invoice text, extracted records, line items, and audit flags are stored in the database.

## Browser/API boundary

- Vite proxies `/api` to the backend in development.
- FastAPI allows the two local Vite origins with credentials.
- The frontend calls `/upload`, `/audit/{id}`, `/invoices`, `/invoices/{id}`, and `/dashboard`.
- All long-running Claude work happens inside HTTP requests.

## File storage

- Uploaded PDF bytes are never persisted after parsing.
- There is no S3/MinIO integration or document metadata model.
- A generated sample invoice PDF is committed for demonstration.

## CI and deployment

- GitHub Actions uses public setup actions and requires no secrets.
- Docker builds only the backend image and is not validated in CI.
- No container registry, hosting provider, AWS API, telemetry backend, or deployed URL is configured.

## Absent integrations

- Redis and Celery are absent.
- PostgreSQL and Alembic are absent.
- Prometheus and OpenTelemetry are absent.
- No email, auth, webhooks, payment provider, or third-party document service is present.

*Integration analysis: 2026-09-18*
