import os

import pytest
from sqlalchemy import text

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://freightiq:freightiq@localhost:5433/freightiq"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")
os.environ.setdefault("S3_ENDPOINT_URL", "http://localhost:9100")
os.environ.setdefault("S3_ACCESS_KEY", "freightiq")
os.environ.setdefault("S3_SECRET_KEY", "freightiq-local-only")

from database import engine  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database():
    with engine.begin() as connection:
        tables = "audit_flags, line_items, processing_jobs, invoices, documents"
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    yield
