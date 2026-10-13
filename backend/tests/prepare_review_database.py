"""Prepare a disposable Node-test database using the canonical migrations."""

import os
import subprocess

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

url = make_url(os.environ["DATABASE_URL"])
if not url.database or not url.database.endswith("_test"):
    raise RuntimeError("Refusing to prepare a database without a _test suffix")
admin_url = url.set(drivername="postgresql", database="postgres")
with psycopg.connect(
    admin_url.render_as_string(hide_password=False), autocommit=True
) as conn:
    if not conn.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s", (url.database,)
    ).fetchone():
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(url.database)))
subprocess.run(["alembic", "upgrade", "head"], check=True)
