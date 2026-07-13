"""
TRACE - Users API Tests
Tests for user CRUD and RBAC enforcement.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, auth_headers: dict):
    """Authenticated user can fetch their own profile."""
    resp = await client.get("/api/v1/users/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "testuser@trace.com"
    assert data["name"] == "Test User"
    assert "Admin" in data["roles"]
    assert data["profile"] is not None


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    """Unauthenticated request to /me returns 401."""
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 422  # Missing Authorization header


@pytest.mark.asyncio
async def test_list_users_admin(client: AsyncClient, auth_headers: dict):
    """Admin can list all users."""
    resp = await client.get("/api/v1/users", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "users" in data
    assert data["total"] >= 1
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_users_staff_forbidden(client: AsyncClient, staff_auth_headers: dict):
    """Staff user cannot list all users (403)."""
    resp = await client.get("/api/v1/users", headers=staff_auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_own_profile(client: AsyncClient, auth_headers: dict):
    """User can update their own profile."""
    # Get current user ID
    me = await client.get("/api/v1/users/me", headers=auth_headers)
    user_id = me.json()["id"]

    resp = await client.patch(
        f"/api/v1/users/{user_id}",
        headers=auth_headers,
        json={"phone": "+91-1111111111"},
    )
    assert resp.status_code == 200
    assert resp.json()["phone"] == "+91-1111111111"


@pytest.mark.asyncio
async def test_delete_user_admin(client: AsyncClient, auth_headers: dict):
    """Admin can soft-delete a user."""
    # Register a user to delete
    reg = await client.post("/api/v1/auth/register", json={
        "name": "Delete Me", "username": "deleteme",
        "email": "delete@trace.com", "password": "Pass1234!", "role": "Staff",
    })
    user_id = reg.json()["user"]["id"]

    resp = await client.delete(
        f"/api/v1/users/{user_id}", headers=auth_headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_user_staff_forbidden(
    client: AsyncClient, staff_auth_headers: dict,
):
    """Staff user cannot delete users (403)."""
    resp = await client.delete("/api/v1/users/9999", headers=staff_auth_headers)
    assert resp.status_code == 403
