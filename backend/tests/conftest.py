"""Shared test setup: PostgreSQL-backed stores run on in-memory SQLite.

The DATABASE_URL env var must be set before any app module is imported
(app.db builds its engine at import time), so it happens at conftest import.
An autouse fixture resets the schema before every test so tests stay
independent of each other and of any live PostgreSQL server.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest


@pytest.fixture(autouse=True)
def fresh_db():
    from app.db import Base, engine, init_db
    from app.services import regintel_store

    Base.metadata.drop_all(bind=engine)
    init_db()
    regintel_store.ensure_sources_seeded()
    yield
