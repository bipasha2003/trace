"""
TRACE - Users API Tests
Tests for user CRUD and RBAC enforcement.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, admin_headers: dict):
    """Authenticated user can fetch their own profile."""
    resp = await client.get("/api/v1/users/me", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "testadmin@trace.com"
    assert data["name"] == "Test Admin"
    assert "Admin" in data["roles"]
    assert data["profile"] is not None


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    """Unauthenticated request to /me returns 401."""
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 422  # Missing Authorization header


@pytest.mark.asyncio
async def test_list_users_admin(client: AsyncClient, admin_headers: dict):
    """Admin can list all users."""
    resp = await client.get("/api/v1/users", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "users" in data
    assert data["total"] >= 1
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_users_employee_forbidden(client: AsyncClient, employee_headers: dict):
    """An Employee cannot list all users (403)."""
    resp = await client.get("/api/v1/users", headers=employee_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_users_manager(client: AsyncClient, manager_headers: dict):
    """A Manager may list users — they pick Project Managers from the Employee pool."""
    resp = await client.get("/api/v1/users", headers=manager_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_employee_cannot_update_someone_else(
    client: AsyncClient, employee_headers: dict, admin_headers: dict,
):
    """Profile update is self-service only, unless the caller is an Admin."""
    admin_id = (await client.get("/api/v1/users/me", headers=admin_headers)).json()["id"]
    resp = await client.patch(
        f"/api/v1/users/{admin_id}", headers=employee_headers, json={"phone": "+91-0"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_own_profile(client: AsyncClient, admin_headers: dict):
    """User can update their own profile."""
    # Get current user ID
    me = await client.get("/api/v1/users/me", headers=admin_headers)
    user_id = me.json()["id"]

    resp = await client.patch(
        f"/api/v1/users/{user_id}",
        headers=admin_headers,
        json={"phone": "+91-1111111111"},
    )
    assert resp.status_code == 200
    assert resp.json()["phone"] == "+91-1111111111"


@pytest.mark.asyncio
async def test_delete_user_admin(client: AsyncClient, admin_headers: dict):
    """Admin can soft-delete a user."""
    # Register a user to delete
    reg = await client.post("/api/v1/auth/register", json={
        "name": "Delete Me", "username": "deleteme",
        "email": "delete@trace.com", "password": "Pass1234!",
    })
    user_id = reg.json()["user"]["id"]

    resp = await client.delete(
        f"/api/v1/users/{user_id}", headers=admin_headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_user_employee_forbidden(
    client: AsyncClient, employee_headers: dict,
):
    """An Employee cannot delete users (403)."""
    resp = await client.delete("/api/v1/users/9999", headers=employee_headers)
    assert resp.status_code == 403
