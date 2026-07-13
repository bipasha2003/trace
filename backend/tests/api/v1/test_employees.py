"""
TRACE - Employee API Tests
Tests for department, work schedule, and employee CRUD with RBAC.
"""

import pytest
from httpx import AsyncClient


# ══════════════════════════════════════════════════════════════════
#  DEPARTMENTS
# ══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_department_admin(client: AsyncClient, auth_headers: dict):
    """Admin can create a department."""
    resp = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": "Test Dept", "description": "Test department"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Dept"
    assert data["id"]


@pytest.mark.asyncio
async def test_create_department_staff_forbidden(
    client: AsyncClient, staff_auth_headers: dict,
):
    """Staff cannot create departments."""
    resp = await client.post(
        "/api/v1/departments",
        headers=staff_auth_headers,
        json={"name": "Blocked Dept"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_departments(client: AsyncClient, auth_headers: dict):
    """Any authenticated user can list departments."""
    # Seed a department first
    await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": "Listable Dept"},
    )
    resp = await client.get("/api/v1/departments", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_duplicate_department(client: AsyncClient, auth_headers: dict):
    """Duplicate department name returns 409."""
    await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": "Unique Dept"},
    )
    resp = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": "Unique Dept"},
    )
    assert resp.status_code == 409


# ══════════════════════════════════════════════════════════════════
#  EMPLOYEES
# ══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_employee_admin(client: AsyncClient, auth_headers: dict):
    """Admin can create an employee record."""
    me = await client.get("/api/v1/users/me", headers=auth_headers)
    user_id = me.json()["id"]

    # Create department first
    dept = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": "Eng Dept"},
    )
    dept_id = dept.json()["id"]

    resp = await client.post(
        "/api/v1/employees",
        headers=auth_headers,
        json={
            "user_id": user_id,
            "employee_code": "EMP-TEST-001",
            "department_id": dept_id,
            "joining_date": "2026-01-15",
            "employee_detail": {
                "city": "Kolkata",
                "state": "West Bengal",
                "country": "India",
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["employee_code"] == "EMP-TEST-001"
    assert data["department"]["name"] == "Eng Dept"
    assert data["employee_detail"]["city"] == "Kolkata"
    assert data["status"] == "Active"


@pytest.mark.asyncio
async def test_create_employee_staff_forbidden(
    client: AsyncClient, staff_auth_headers: dict,
):
    """Staff cannot create employee records."""
    resp = await client.post(
        "/api/v1/employees",
        headers=staff_auth_headers,
        json={"user_id": 1, "employee_code": "EMP-X"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_employee_me(client: AsyncClient, auth_headers: dict):
    """Any authenticated user can fetch their own employee record."""
    me = await client.get("/api/v1/users/me", headers=auth_headers)
    user_id = me.json()["id"]

    # Create department and employee first
    dept = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": "My Dept"},
    )
    await client.post(
        "/api/v1/employees",
        headers=auth_headers,
        json={
            "user_id": user_id,
            "employee_code": "EMP-ME-001",
            "department_id": dept.json()["id"],
        },
    )

    resp = await client.get("/api/v1/employees/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["employee_code"] == "EMP-ME-001"
