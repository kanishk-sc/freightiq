# Engineering Conventions

**Analysis Date:** 2026-09-18

## Python

- Modules use snake_case and models use PascalCase.
- Type hints are present on most backend functions.
- API responses are annotated as broad dictionaries rather than Pydantic response models.
- Imports in `backend/main.py` and `backend/extractor.py` intentionally execute `load_dotenv` before later imports, violating configured Ruff rules.
- No formatter configuration or strict type checker is configured.

## TypeScript

- The frontend uses strict TypeScript settings and typed API interfaces.
- Functional components and React hooks are used consistently.
- Async errors are normalized through `ApiError` at the API boundary.
- Views are represented as a string union rather than a router.
- Tailwind utility classes are the primary styling convention.

## Error handling

- User-facing HTTP errors often include raw exception strings from PDF parsing, extraction, and audit calls.
- Missing API keys become HTTP 500 responses.
- Provider parse failures are inconsistently mapped to 422 or 500.
- There is no structured logging, request ID, or stable error schema.
- Database transaction rollback is not explicitly handled.

## Data correctness

- Provider fields are accessed with `.get` and persisted without schema validation.
- Invalid line item entries are silently skipped.
- Money uses `float`, and date strings have no validation.
- Audit severity is coerced to warning when unknown, but field and description accept arbitrary values.

## Configuration

- CORS origins and database URL are hard-coded.
- The Anthropic key is environment-driven.
- The selected Claude model is a module constant.
- No maximum upload size, provider timeout, retry count, or object-storage setting exists.

## Documentation

- The README lists implemented technologies but gives no honest in-progress/planned section.
- Setup path for the environment example is currently incorrect.

*Convention analysis: 2026-09-18*
