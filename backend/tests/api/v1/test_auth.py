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
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["user"]["email"] == "new@trace.com"
    assert data["user"]["name"] == "New User"
    assert data["user"]["roles"] == ["Employee"]
    assert data["tokens"]["access_token"]
    assert data["tokens"]["refresh_token"]
    assert data["tokens"]["token_type"] == "Bearer"


# ── Who may create which role (PLANNING.md §2, 2026-09-25) ──────

NEW_USER = {"name": "Role Probe", "username": "roleprobe",
            "email": "roleprobe@trace.com", "password": "SecurePass1!"}


@pytest.mark.asyncio
async def test_register_defaults_to_employee(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json=NEW_USER)
    assert resp.status_code == 201
    assert resp.json()["user"]["roles"] == ["Employee"]


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["Staff", "Platform Admin", "Team Lead", "admin"])
async def test_register_rejects_unknown_roles(client: AsyncClient, role: str):
    """Only the three hardcoded platform roles exist; retired ones are not recreated."""
    resp = await client.post("/api/v1/auth/register", json={**NEW_USER, "role": role})
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["Admin", "Manager"])
async def test_anonymous_cannot_register_privileged_role(client: AsyncClient, role: str):
    resp = await client.post("/api/v1/auth/register", json={**NEW_USER, "role": role})
    assert resp.status_code == 403
    login = await client.post("/api/v1/auth/login", json={
        "email": NEW_USER["email"], "password": NEW_USER["password"],
    })
    assert login.status_code == 401, "the refused account must not have been created"


@pytest.mark.asyncio
@pytest.mark.parametrize("caller", ["Manager", "Employee"])
@pytest.mark.parametrize("role", ["Admin", "Manager"])
async def test_non_admin_cannot_register_privileged_role(
    client: AsyncClient, role_headers, caller: str, role: str,
):
    resp = await client.post(
        "/api/v1/auth/register", headers=role_headers[caller], json={**NEW_USER, "role": role},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["Admin", "Manager", "Employee"])
async def test_admin_can_register_any_role(client: AsyncClient, admin_headers: dict, role: str):
    resp = await client.post(
        "/api/v1/auth/register", headers=admin_headers, json={**NEW_USER, "role": role},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["user"]["roles"] == [role]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Duplicate email registration returns 409."""
    payload = {
        "name": "Dup User",
        "username": "dup1",
        "email": "dup@trace.com",
        "password": "Pass1234!",
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
        "email": "login@trace.com", "password": "Pass1234!",
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
        "email": "wrong@trace.com", "password": "Correct1!",
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
        "email": "refresh@trace.com", "password": "Pass1234!",
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
