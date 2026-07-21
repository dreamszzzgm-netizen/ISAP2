"""Integration tests that require a real PostgreSQL instance.

These tests are marked with the ``postgres`` marker and are excluded from the
default test run (``pytest -m "not postgres"``). The guard test
``test_database_is_configured`` fails the suite unless ``DATABASE_URL`` is a
PostgreSQL URL whose database name is exactly ``isap_test`` — checked by
parsing the URL with SQLAlchemy (not substring matching), so a hostname or
path fragment cannot accidentally satisfy the guard.

What this module proves end-to-end against a real PostgreSQL:

1. The database is reachable and is the dedicated CI test database.
2. ``alembic upgrade head`` has been applied — the value in
   ``alembic_version`` matches the current Alembic head (resolved dynamically
   from the migration scripts, not hard-coded).
3. The application can insert, read back, and delete a row through the real
   ``OrganizationRepository`` over async SQLAlchemy/asyncpg.

ChromaDB is not required for these tests and is not imported. No network
calls are made.
"""
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.settings import settings
from src.infrastructure.repositories.organization_repo import OrganizationRepository


# ---------------------------------------------------------------------------
# Constants and helpers
# ---------------------------------------------------------------------------

# Name of the dedicated CI integration test database. Enforced exactly via
# SQLAlchemy URL parsing (not substring matching) so these tests never run
# against dev/prod databases even if a hostname happens to contain the token.
_REQUIRED_DB_NAME = "isap_test"

# Backend root (where alembic/ and alembic.ini live). The integration test
# module is at tests/integration/, so the backend root is two levels up.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _database_url() -> str:
    """Return the effective DATABASE_URL (env override > settings default)."""
    return os.environ.get("DATABASE_URL") or settings.database_url


def _ci_db_enabled() -> bool:
    """True iff DATABASE_URL is a PostgreSQL URL pointing at ``isap_test``.

    Parsed with SQLAlchemy's ``make_url`` rather than substring matching, so
    a host/path fragment like ``isap_test.example.com`` or ``prod_isap_test``
    cannot satisfy the check. Returns False on any parse error.
    """
    try:
        url = make_url(_database_url())
    except ArgumentError:
        return False
    return (
        url.get_backend_name() == "postgresql"
        and url.database == _REQUIRED_DB_NAME
    )


def _resolve_alembic_heads() -> set[str]:
    """Return the current Alembic head revision(s) from the migration scripts.

    Uses the Alembic API directly (no subprocess) so this works on any OS.
    Multiple heads are returned unchanged — the assertion in the test then
    enforces that the database's ``alembic_version`` matches the head set
    exactly (which catches branching migration trees).
    """
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
    script_dir = ScriptDirectory.from_config(cfg)
    # ScriptDirectory.get_heads() returns revision-id strings directly
    # (Alembic >= 1.9). Wrap in a set for order-independent comparison.
    return set(script_dir.get_heads())


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------

@pytest.mark.postgres
def test_database_is_configured():
    """Fail the integration suite unless DATABASE_URL is the CI test DB.

    This is a synchronous guard test (no async, no DB connection). It fails
    loudly rather than skipping, so a misconfigured integration run is
    impossible to miss. The error message is intentionally narrow: only the
    expected database name is mentioned, never the password or full URL.

    Parses the URL with SQLAlchemy (not substring matching) and enforces:
      * backend is PostgreSQL
      * database name is exactly ``isap_test``
    """
    url = make_url(_database_url())
    assert url.get_backend_name() == "postgresql", (
        "PostgreSQL integration tests require a PostgreSQL backend; "
        f"got backend={url.get_backend_name()!r}, driver={url.drivername!r}."
    )
    assert url.database == _REQUIRED_DB_NAME, (
        f"PostgreSQL integration tests require database name {_REQUIRED_DB_NAME!r}; "
        f"got database={url.database!r}."
    )


# ---------------------------------------------------------------------------
# Fixtures (function-scoped async)
# ---------------------------------------------------------------------------

@pytest.fixture
async def db_session():
    """Yield a fresh AsyncSession against the CI Postgres, then dispose.

    Function scope is used intentionally: on pytest-asyncio>=1.0 the
    default event-loop scope is per-function, and a function-scoped engine
    avoids cross-test event-loop lifetime issues seen with asyncpg on
    Windows. Each test gets its own engine + session, disposed in finally.
    """
    if not _ci_db_enabled():
        pytest.skip(f"not CI integration database (url={_database_url()!r})")

    engine = create_async_engine(_database_url(), echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.postgres
async def test_alembic_head_matches_database(db_session: AsyncSession):
    """The DB's alembic_version must equal the current Alembic head set.

    Head revisions are resolved dynamically from alembic/versions/, so this
    test keeps working as new migrations land — it fails only if the
    database is behind, ahead of, or branches away from the script tree.
    """
    expected_heads = _resolve_alembic_heads()
    assert expected_heads, "no Alembic heads resolved — migration scripts missing?"

    result = await db_session.execute(text("SELECT version_num FROM alembic_version"))
    db_versions = {row[0] for row in result.fetchall()}

    assert db_versions == expected_heads, (
        f"alembic_version mismatch: database has {db_versions!r}, "
        f"scripts report heads {expected_heads!r}. "
        f"Run `alembic upgrade head` against the test database."
    )


@pytest.mark.postgres
async def test_organization_crud(db_session: AsyncSession):
    """Insert → read → delete a single Organization through the repository."""
    repo = OrganizationRepository(db_session)
    org_id = uuid4()
    payload = {
        "id": org_id,
        "name": "CI Integration Smoke Org",
        "inn": "9999999999",
    }

    try:
        created = await repo.create(payload)
        assert created.id == org_id
        assert created.name == payload["name"]
        assert created.inn == payload["inn"]

        fetched = await repo.get(org_id)
        assert fetched is not None, "created Organization not found on read-back"
        assert fetched.id == org_id
        assert fetched.name == payload["name"]
        assert fetched.inn == payload["inn"]
    finally:
        # Cleanup in finally so the test database is not polluted even on
        # assertion failure.
        try:
            await repo.delete(org_id)
        except Exception:
            pass

    gone = await repo.get(org_id)
    assert gone is None, "Organization still present after delete — cleanup failed"
