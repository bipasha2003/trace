"""
TRACE - Test Configuration

Tests run against a dedicated database (default ``trace_test``), never the dev
database. It is created if missing and brought to head with ``alembic upgrade
head`` — the same path a fresh checkout takes — so every run also proves the
migration chain. Each test runs inside a transaction that is rolled back.

Override the target with ``TEST_DATABASE_URL``.
"""

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy.engine import make_url

# Point the app at the test database *before* anything imports app.config.
from app.config import get_settings  # noqa: E402

_dev_url = make_url(get_settings().DATABASE_URL)
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    _dev_url.set(database="trace_test").render_as_string(hide_password=False),
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
get_settings.cache_clear()

import asyncpg  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas.auth import RegisterRequest  # noqa: E402
from app.seeds import seed_roles  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _asyncpg_dsn(url: str, database: str | None = None) -> str:
    u = make_url(url).set(drivername="postgresql")
    if database:
        u = u.set(database=database)
    return u.render_as_string(hide_password=False)


async def create_database_if_missing(url: str) -> None:
    """CREATE DATABASE for ``url`` if it does not exist (connects via the dev DB)."""
    name = make_url(url).database
    conn = await asyncpg.connect(_asyncpg_dsn(url, database=_dev_url.database))
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{name}"')
    finally:
        await conn.close()


def run_alembic(url: str, *args: str) -> subprocess.CompletedProcess:
    """Run an alembic command against ``url`` in a subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": url},
        capture_output=True,
        text=True,
    )


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def _test_database():
    """Create the test DB, migrate it to head, and seed the three platform roles."""
    await create_database_if_missing(TEST_DATABASE_URL)
    result = run_alembic(TEST_DATABASE_URL, "upgrade", "head")
    assert result.returncode == 0, f"alembic upgrade head failed:\n{result.stderr}"

    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with AsyncSession(engine) as session:
        await seed_roles(session)
        await session.commit()
    await engine.dispose()
    yield


@pytest_asyncio.fixture
async def db_session():
    """A session whose commits land in savepoints; everything is rolled back after the test."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Async HTTP client with the DB dependency pointed at the test session."""

    async def _override_get_db():
        # Mirrors app.database.get_db: an error rolls the request's work back
        try:
            yield db_session
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Users per platform role ──────────────────────────────────────
# Created through the service layer: the API (correctly) refuses to let an
# anonymous caller register an Admin or Manager.

TEST_USERS = {
    "Admin": {
        "name": "Test Admin", "username": "testadmin", "email": "testadmin@trace.com",
        "password": "TestPass123!", "phone": "+91-1234567890", "gender": "Female",
    },
    "Manager": {
        "name": "Test Manager", "username": "testmanager", "email": "testmanager@trace.com",
        "password": "TestPass123!",
    },
    "Employee": {
        "name": "Test Employee", "username": "testemployee", "email": "testemployee@trace.com",
        "password": "TestPass123!",
    },
}


async def make_user_headers(db: AsyncSession, role: str, **overrides) -> dict:
    data = RegisterRequest(**{**TEST_USERS[role], **overrides, "role": role})
    result = await AuthService(db).register(data)
    return {"Authorization": f"Bearer {result.tokens.access_token}"}


@pytest_asyncio.fixture
async def admin_headers(db_session: AsyncSession) -> dict:
    return await make_user_headers(db_session, "Admin")


@pytest_asyncio.fixture
async def manager_headers(db_session: AsyncSession) -> dict:
    return await make_user_headers(db_session, "Manager")


@pytest_asyncio.fixture
async def employee_headers(db_session: AsyncSession) -> dict:
    return await make_user_headers(db_session, "Employee")


@pytest.fixture
def role_headers(admin_headers, manager_headers, employee_headers) -> dict:
    """All three at once, keyed by platform role, plus ``None`` for anonymous."""
    return {"Admin": admin_headers, "Manager": manager_headers,
            "Employee": employee_headers, None: {}}


# ── External services: never real in tests ───────────────────────
import json as _json  # noqa: E402

import httpx  # noqa: E402

from app.services.github_service import GitHubClient, get_github_client  # noqa: E402
from app.services.storage import get_storage  # noqa: E402


class FakeGitHub:
    """GitHub's REST API on an httpx.MockTransport: the real GitHubClient runs, only the network is fake."""

    def __init__(self):
        self.issues: dict[tuple[str, int], dict] = {}
        self.files: dict[tuple[str, str], dict] = {}
        self.requests: list[tuple[str, str, dict | None]] = []
        self.fail_with: int | None = None  # set to e.g. 500 to make every call fail

    def _handle(self, request: httpx.Request) -> httpx.Response:
        body = _json.loads(request.content) if request.content else None
        self.requests.append((request.method, request.url.path, body))
        if self.fail_with:
            return httpx.Response(self.fail_with, json={"message": "simulated GitHub failure"})
        parts = request.url.path.strip("/").split("/")  # repos/{owner}/{repo}/...
        repo = f"{parts[1]}/{parts[2]}"
        if parts[3] == "issues" and request.method == "POST":
            number = len([k for k in self.issues if k[0] == repo]) + 1
            self.issues[(repo, number)] = {**body, "state": "open", "assignees": body.get("assignees", [])}
            return httpx.Response(201, json={"number": number,
                                             "html_url": f"https://github.com/{repo}/issues/{number}"})
        if parts[3] == "issues" and request.method == "PATCH":
            issue = self.issues[(repo, int(parts[4]))]
            issue.update(body)
            return httpx.Response(200, json={"number": int(parts[4])})
        if parts[3] == "contents":
            path = "/".join(parts[4:])
            if request.method == "GET":
                f = self.files.get((repo, path))
                return httpx.Response(200, json={"sha": f["sha"]}) if f else httpx.Response(404, json={})
            self.files[(repo, path)] = {**body, "sha": f"sha{len(self.files) + 1}"}
            return httpx.Response(201, json={"content": {
                "html_url": f"https://github.com/{repo}/blob/{body['branch']}/{path}"}})
        return httpx.Response(404, json={"message": "not faked"})

    def client(self) -> GitHubClient:
        return GitHubClient("test-token", transport=httpx.MockTransport(self._handle),
                            committer={"name": "TRACE Test", "email": "trace@example.com"})


class FakeStorage:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    async def put(self, key, data, content_type):
        self.objects[key] = data

    async def get(self, key):
        return self.objects[key]

    async def delete(self, key):
        self.objects.pop(key, None)


@pytest.fixture(autouse=True)
def _isolate_external_services():
    """No test reaches real GitHub or MinIO, whatever .env says. `fake_github` opts in to a fake."""
    storage = FakeStorage()
    app.dependency_overrides[get_github_client] = lambda: None
    app.dependency_overrides[get_storage] = lambda: storage
    yield storage
    app.dependency_overrides.pop(get_github_client, None)
    app.dependency_overrides.pop(get_storage, None)


@pytest.fixture
def fake_storage(_isolate_external_services) -> FakeStorage:
    return _isolate_external_services


@pytest.fixture
def fake_github() -> FakeGitHub:
    fake = FakeGitHub()
    app.dependency_overrides[get_github_client] = fake.client
    return fake


async def make_user(db: AsyncSession, role: str, username: str, github_username: str | None = None) -> tuple[int, dict]:
    """A user of `role` → (user_id, auth headers)."""
    from app.models.user import User

    result = await AuthService(db).register(RegisterRequest(
        name=username.replace("_", " ").title(), username=username,
        email=f"{username}@trace.com", password="TestPass123!", role=role,
    ))
    if github_username:
        (await db.get(User, result.user.id)).github_username = github_username
        await db.flush()
    return result.user.id, {"Authorization": f"Bearer {result.tokens.access_token}"}
