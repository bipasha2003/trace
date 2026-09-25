"""
TRACE - Attendance record tests

Attendance is an Admin-maintained record set (PROJECT.md §9.1): there is no
clock-in/out capture any more, so rows are inserted directly here the way a bulk
import would create them.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance


async def _record_attendance(
    client: AsyncClient, db: AsyncSession, admin_headers: dict, employee_headers: dict,
) -> datetime:
    """Create an employee record for the test Employee plus today's attendance row."""
    user_id = (await client.get("/api/v1/users/me", headers=employee_headers)).json()["id"]
    emp = await client.post(
        "/api/v1/employees", headers=admin_headers,
        json={"user_id": user_id, "employee_code": "EMP-ATT-001"},
    )
    assert emp.status_code == 201, emp.text

    time_in = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=8)
    db.add(Attendance(
        employee_id=emp.json()["id"],
        attendance_date=date.today(),
        time_in=time_in,
        time_out=time_in + timedelta(hours=8),
        total_hours=8,
        location_status="office",
    ))
    await db.flush()
    return time_in


@pytest.mark.asyncio
async def test_admin_reads_attendance_log(
    client: AsyncClient, db_session: AsyncSession, admin_headers: dict, employee_headers: dict,
):
    time_in = await _record_attendance(client, db_session, admin_headers, employee_headers)

    resp = await client.get("/api/v1/attendance/all", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    records = [r for r in resp.json()["records"] if r["employee_code"] == "EMP-ATT-001"]
    assert len(records) == 1
    assert records[0]["check_in"] == time_in.isoformat()
    assert records[0]["total_hours"] == 8.0
    assert records[0]["location_status"] == "office"


@pytest.mark.asyncio
async def test_daily_summary_counts_recorded_attendance(
    client: AsyncClient, db_session: AsyncSession, admin_headers: dict, employee_headers: dict,
):
    before = (await client.get("/api/v1/attendance/summary/daily", headers=admin_headers)).json()
    await _record_attendance(client, db_session, admin_headers, employee_headers)
    after = (await client.get("/api/v1/attendance/summary/daily", headers=admin_headers)).json()

    assert after["present"] == before["present"] + 1
    assert after["total_employees"] == before["total_employees"] + 1


@pytest.mark.asyncio
async def test_clock_in_and_out_are_gone(client: AsyncClient, employee_headers: dict):
    """Employee HR self-service was removed in Phase 0 and must stay removed."""
    for path in ("/api/v1/attendance/checkin", "/api/v1/attendance/checkout"):
        resp = await client.post(path, headers=employee_headers, json={})
        assert resp.status_code in {404, 405}, f"{path} answered {resp.status_code}"
