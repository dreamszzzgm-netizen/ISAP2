"""Integration smoke test against a real PostgreSQL.

Runs ONLY in CI integration scope — the test is skipped unless DATABASE_URL
points at the dedicated CI test database (host/database name contains
"isap_test"). This protects dev/prod databases from accidental test runs.

What this test proves end-to-end:
1. The CI service dependency (PostgreSQL 16) is reachable.
2. `alembic upgrade head` has been applied — the alembic_version table reports
   the expected migration head.
3. The application can insert and read back a row through the real repository
   (OrganizationRepository) over async SQLAlchemy/asyncpg.
4. The row is cleaned up after the test (delete + verify gone).

This test intentionally does NOT touch ChromaDB and does NOT hit the network.
ChromaDB is not required for the current integration CI scope.
"""
from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.settings import settings
from src.infrastructure.repositories.organization_repo import OrganizationRepository


# ---------------------------------------------------------------------------
# Expected migration head — keep in sync with backend/alembic/versions/.
# Update this constant when a new migration lands; a mismatch is a visible
# signal that the integration stage needs to be updated, not a hidden failure.
# ---------------------------------------------------------------------------
EXPECTED_ALEMBIC_HEAD = "021"

# Marker that identifies the CI integration test database. Checked against the
# configured DATABASE_URL so this test never runs against dev/prod.
_CI_DB_MARKER = "isap_test"


def _database_url() -> str:
    return os.environ.get("DATABASE_URL") or settings.database_url


def _ci_db_enabled() -> bool:
    return _CI_DB_MARKER in _database_url()


def test_ci_integration_database_is_configured():
    """Guard: confirm we are pointed at the CI test database (or skip)."""
    if not _ci_db_enabled():
        pytest.skip(
            f"DATABASE_URL does not target the CI test database "
            f"(marker {_CI_DB_MARKER!r} not found in {_database_url()!r}). "
            f"Integration smoke test runs only in CI integration scope."
        )


async def test_alembic_head_applied():
    """Migration head must match EXPECTED_ALEMBIC_HEAD on the CI database."""
    if not _ci_db_enabled():
        pytest.skip("not CI integration database")

    engine = create_async_engine(_database_url(), echo=False)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.scalar_one_or_none()
    finally:
        await engine.dispose()

    assert row is not None, "alembic_version table is empty — migrations not applied"
    assert row == EXPECTED_ALEMBIC_HEAD, (
        f"alembic head mismatch: expected {EXPECTED_ALEMBIC_HEAD!r}, got {row!r}. "
        f"Update EXPECTED_ALEMBIC_HEAD in this test or fix the migration chain."
    )


async def test_organization_create_read_delete():
    """Insert → read → delete a single Organization through the real repository."""
    if not _ci_db_enabled():
        pytest.skip("not CI integration database")

    engine = create_async_engine(_database_url(), echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    org_id = uuid4()
    payload = {
        "id": org_id,
        "name": "CI Integration Smoke Org",
        "inn": "9999999999",
    }

    try:
        async with factory() as session:
            repo = OrganizationRepository(session)
            created = await repo.create(payload)
            assert created.id == org_id
            assert created.name == payload["name"]
            assert created.inn == payload["inn"]

        # Read-back in a fresh session to prove the row actually persisted.
        async with factory() as session:
            repo = OrganizationRepository(session)
            fetched = await repo.get(org_id)
            assert fetched is not None, "created Organization not found on read-back"
            assert fetched.id == org_id
            assert fetched.name == payload["name"]
            assert fetched.inn == payload["inn"]

        # Cleanup: delete and verify gone, even on assertion failure.
        async with factory() as session:
            repo = OrganizationRepository(session)
            deleted = await repo.delete(org_id)
            assert deleted is True, f"failed to clean up Organization {org_id}"

        async with factory() as session:
            repo = OrganizationRepository(session)
            gone = await repo.get(org_id)
            assert gone is None, "Organization still present after delete — cleanup failed"
    finally:
        # If anything above failed before delete, make a best-effort cleanup so
        # the CI database is not polluted with smoke rows.
        try:
            async with factory() as session:
                repo = OrganizationRepository(session)
                await repo.delete(org_id)
        except Exception:
            pass
        await engine.dispose()
