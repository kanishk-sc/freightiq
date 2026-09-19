FROM python:3.11-slim AS base

WORKDIR /app

COPY pyproject.toml requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN groupadd --gid 10001 freightiq && useradd --uid 10001 --gid freightiq --no-create-home freightiq

COPY --chown=freightiq:freightiq . .

FROM base AS runtime
USER freightiq
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn main:app --host 0.0.0.0 --port 8000"]

FROM base AS test
RUN pip install --no-cache-dir -r requirements-dev.txt
USER freightiq
CMD ["pytest"]
