"""
TRACE - Auth API Tests
Tests for registration, login, token refresh, and validation.
"""

import pytest
from httpx import AsyncClient


# ══════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns app info."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["app"] == "TRACE"
    assert "version" in data


# ══════════════════════════════════════════════════════════════════
#  REGISTRATION
# ══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Valid registration returns user and tokens."""
    payload = {
        "name": "New User",
        "username": "newuser",
        "email": "new@trace.com",
        "password": "SecurePass1!",
        "role": "Staff",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["user"]["email"] == "new@trace.com"
    assert data["user"]["name"] == "New User"
    assert "Staff" in data["user"]["roles"]
    assert data["tokens"]["access_token"]
    assert data["tokens"]["refresh_token"]
    assert data["tokens"]["token_type"] == "Bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Duplicate email registration returns 409."""
    payload = {
        "name": "Dup User",
        "username": "dup1",
        "email": "dup@trace.com",
        "password": "Pass1234!",
        "role": "Staff",
    }
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_missing_fields(client: AsyncClient):
    """Missing required fields returns 422."""
    resp = await client.post("/api/v1/auth/register", json={"name": "X"})
    assert resp.status_code == 422
    data = resp.json()
    assert data["error"] is True
    assert "errors" in data


# ══════════════════════════════════════════════════════════════════
#  LOGIN
# ══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Valid login returns tokens and user."""
    # Register first
    await client.post("/api/v1/auth/register", json={
        "name": "Login Test", "username": "logintest",
        "email": "login@trace.com", "password": "Pass1234!", "role": "Staff",
    })

    resp = await client.post("/api/v1/auth/login", json={
        "email": "login@trace.com", "password": "Pass1234!",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["email"] == "login@trace.com"
    assert data["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Wrong password returns 401."""
    await client.post("/api/v1/auth/register", json={
        "name": "Wrong PW", "username": "wrongpw",
        "email": "wrong@trace.com", "password": "Correct1!", "role": "Staff",
    })

    resp = await client.post("/api/v1/auth/login", json={
        "email": "wrong@trace.com", "password": "WrongPassword!",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Login with nonexistent email returns 401."""
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nobody@trace.com", "password": "Pass1234!",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_missing_body(client: AsyncClient):
    """Login without body returns 422."""
    resp = await client.post("/api/v1/auth/login")
    assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════
#  TOKEN REFRESH
# ══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    """Refresh token returns a new access token."""
    reg = await client.post("/api/v1/auth/register", json={
        "name": "Refresh Test", "username": "refreshtest",
        "email": "refresh@trace.com", "password": "Pass1234!", "role": "Staff",
    })
    refresh_token = reg.json()["tokens"]["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["token_type"] == "Bearer"


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    """Invalid refresh token returns 401."""
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": "invalid.token.here",
    })
    assert resp.status_code == 401
