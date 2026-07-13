"""
TRACE - Test Configuration
Shared fixtures for pytest with async DB support.
"""

import asyncio
from datetime import date

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.database import Base, get_db
from app.main import app

settings = get_settings()


# ── Use the real test database ───────────────────────────────────
engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session():
    """Provide a transactional DB session that rolls back after each test."""
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await trans.rollback()
            await session.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Async HTTP client with DB dependency override."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Helper Data ──────────────────────────────────────────────────

TEST_USER = {
    "name": "Test User",
    "username": "testuser",
    "email": "testuser@trace.com",
    "password": "TestPass123!",
    "phone": "+91-1234567890",
    "gender": "Female",
    "role": "Admin",
}

TEST_STAFF_USER = {
    "name": "Staff User",
    "username": "staffuser",
    "email": "staff@trace.com",
    "password": "StaffPass123!",
    "phone": "+91-9876543210",
    "gender": "Male",
    "role": "Staff",
}


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Register a test user and return auth headers."""
    resp = await client.post("/api/v1/auth/register", json=TEST_USER)
    token = resp.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def staff_auth_headers(client: AsyncClient) -> dict:
    """Register a staff user and return auth headers."""
    resp = await client.post("/api/v1/auth/register", json=TEST_STAFF_USER)
    token = resp.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
