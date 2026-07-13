"""
TRACE - Task & Attendance API Tests
Tests for attendance check-in/out, task CRUD, timers, and comments.
"""

import pytest
from httpx import AsyncClient


# ══════════════════════════════════════════════════════════════════
#  HELPER: Create employee for the test user
# ══════════════════════════════════════════════════════════════════

async def _create_employee(client: AsyncClient, auth_headers: dict) -> int:
    """Helper to create department + employee for the test user. Returns employee_id."""
    me = await client.get("/api/v1/users/me", headers=auth_headers)
    user_id = me.json()["id"]

    dept = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": "TaskDept"},
    )
    dept_id = dept.json()["id"]

    emp = await client.post(
        "/api/v1/employees",
        headers=auth_headers,
        json={
            "user_id": user_id,
            "employee_code": "EMP-TASK-001",
            "department_id": dept_id,
        },
    )
    return emp.json()["id"]


# ══════════════════════════════════════════════════════════════════
#  ATTENDANCE
# ══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_attendance_checkin(client: AsyncClient, auth_headers: dict):
    """Employee can check-in with GPS coordinates."""
    await _create_employee(client, auth_headers)

    resp = await client.post(
        "/api/v1/attendance/checkin",
        headers=auth_headers,
        json={"latitude": 22.5726, "longitude": 88.3639},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["employee_id"]
    assert data["attendance_date"]
    assert data["time_in"]
    assert data["location_status"] in ["office", "remote", "suspicious"]


@pytest.mark.asyncio
async def test_attendance_checkout(client: AsyncClient, auth_headers: dict):
    """Employee can check-out after checking in."""
    await _create_employee(client, auth_headers)

    await client.post(
        "/api/v1/attendance/checkin",
        headers=auth_headers,
        json={"latitude": 22.5726, "longitude": 88.3639},
    )

    resp = await client.post(
        "/api/v1/attendance/checkout",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["time_out"] is not None
    assert data["total_hours"] is not None


@pytest.mark.asyncio
async def test_attendance_history(client: AsyncClient, auth_headers: dict):
    """Employee can view attendance history."""
    await _create_employee(client, auth_headers)

    await client.post(
        "/api/v1/attendance/checkin",
        headers=auth_headers,
        json={"latitude": 22.57, "longitude": 88.36},
    )

    resp = await client.get(
        "/api/v1/attendance/history",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["records"]) >= 1


# ══════════════════════════════════════════════════════════════════
#  TASKS
# ══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_task(client: AsyncClient, auth_headers: dict):
    """Admin can create a task."""
    await _create_employee(client, auth_headers)

    resp = await client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={
            "title": "Test Task",
            "description": "A test task description",
            "assigned_to": 1,
            "priority": "High",
            "estimated_hours": 4.0,
            "due_date": "2026-12-31",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Task"
    assert data["status"] == "Pending"
    assert data["priority"] == "High"


@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient, auth_headers: dict):
    """Can list tasks with pagination."""
    await _create_employee(client, auth_headers)
    await client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"title": "List Test Task", "assigned_to": 1, "priority": "Low"},
    )

    resp = await client.get("/api/v1/tasks", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "tasks" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_task_timer_flow(client: AsyncClient, auth_headers: dict):
    """Start and stop timer on a task."""
    await _create_employee(client, auth_headers)

    # Create task
    task_resp = await client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"title": "Timer Task", "assigned_to": 1, "priority": "Medium"},
    )
    task_id = task_resp.json()["id"]

    # Start timer
    start_resp = await client.post(
        f"/api/v1/tasks/{task_id}/timer/start",
        headers=auth_headers,
    )
    assert start_resp.status_code == 200
    time_log_id = start_resp.json()["id"]
    assert start_resp.json()["start_time"]
    assert start_resp.json()["end_time"] is None

    # Stop timer
    stop_resp = await client.post(
        f"/api/v1/tasks/timer/{time_log_id}/stop",
        headers=auth_headers,
    )
    assert stop_resp.status_code == 200
    assert stop_resp.json()["end_time"] is not None


@pytest.mark.asyncio
async def test_task_comment(client: AsyncClient, auth_headers: dict):
    """Can add a comment to a task."""
    await _create_employee(client, auth_headers)

    task = await client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"title": "Comment Task", "assigned_to": 1, "priority": "Low"},
    )
    task_id = task.json()["id"]

    resp = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        headers=auth_headers,
        json={"comment": "Great progress on this task!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["comment"] == "Great progress on this task!"
    assert data["task_id"] == task_id


@pytest.mark.asyncio
async def test_task_update(client: AsyncClient, auth_headers: dict):
    """Can update task status and priority."""
    await _create_employee(client, auth_headers)

    task = await client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"title": "Update Task", "assigned_to": 1, "priority": "Low"},
    )
    task_id = task.json()["id"]

    resp = await client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=auth_headers,
        json={"status": "Completed", "priority": "High"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Completed"
    assert resp.json()["priority"] == "High"
