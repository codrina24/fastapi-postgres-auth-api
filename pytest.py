"""
Shared pytest setup.

The app talks to Postgres in production (see .env), but tests run against an
isolated SQLite file instead. This keeps the test suite fast, makes it runnable
without a Postgres server, and — most importantly — guarantees tests can never
touch or corrupt real data. The env vars are set here, before any app module is
imported, because db.py reads DATABASE_URL at import time.
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from db import Base, engine
from fastapi_config import app

_tmp_dir = tempfile.mkdtemp(prefix="app_test_db_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_dir}/test.db"
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ALGORITHM", "HS256")

@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    # SQLite ignores foreign key constraints unless you turn them on per
    # connection. Postgres enforces them by default, so without this pragma
    # the tests would pass in a way that doesn't reflect production behavior.
    if engine.dialect.name == "sqlite":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    """Create every table once for the whole test session, drop them at the end."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    """
    Wipe all rows after every test, so tests never see data left over from a
    previous one. Deleting in reverse dependency order avoids foreign key
    violations (guests reference events, events reference users, and so on).
    """
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def client():
    return TestClient(app)
