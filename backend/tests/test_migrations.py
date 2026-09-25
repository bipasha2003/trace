"""
TRACE - Migration chain tests

The schema is owned by Alembic alone. Before Phase 2 completion, app startup ran
``Base.metadata.create_all``, so part of the schema existed in no revision and a
fresh database could not reach head. These tests keep that from coming back.
"""

import inspect
import re
import uuid

import asyncpg
from sqlalchemy.engine import make_url

import app.main
from tests.conftest import (
    TEST_DATABASE_URL, _asyncpg_dsn, _dev_url, create_database_if_missing, run_alembic,
)


def test_single_alembic_head():
    """Two collaborators adding revisions off the same parent must merge, not fork."""
    result = run_alembic(TEST_DATABASE_URL, "heads")
    assert result.returncode == 0, result.stderr
    heads = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(heads) == 1, f"Multiple alembic heads: {heads}"


async def test_empty_database_migrates_to_head_without_drift():
    """`alembic upgrade head` on an empty database, then no diff against the models."""
    name = f"trace_migcheck_{uuid.uuid4().hex[:8]}"
    url = make_url(TEST_DATABASE_URL).set(database=name).render_as_string(hide_password=False)
    await create_database_if_missing(url)
    try:
        upgrade = run_alembic(url, "upgrade", "head")
        assert upgrade.returncode == 0, f"upgrade head failed:\n{upgrade.stderr}"

        current = run_alembic(url, "current")
        assert "(head)" in current.stdout, current.stdout + current.stderr

        check = run_alembic(url, "check")
        assert check.returncode == 0, f"models and migrations disagree:\n{check.stdout}{check.stderr}"
    finally:
        # Only ever drops the uniquely named database this test created.
        conn = await asyncpg.connect(_asyncpg_dsn(url, database=_dev_url.database))
        try:
            await conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        finally:
            await conn.close()


def test_app_startup_does_not_build_schema():
    """create_all at startup builds tables no revision knows about — AGENTS.md §7."""
    # Matches a call or a run_sync(...) reference, not the comment that warns against it
    assert not re.search(r"metadata\.create_all\s*[()]", inspect.getsource(app.main))
