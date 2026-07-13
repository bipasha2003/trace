"""
TRACE - Dashboard & Productivity API Tests
Tests for admin dashboard stats and productivity scoring.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dashboard_stats_admin(client: AsyncClient, auth_headers: dict):
    """Admin can access dashboard stats."""
    resp = await client.get("/api/v1/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "employees" in data
    assert "attendance" in data
    assert "tasks" in data
    assert "productivity" in data
    assert data["date"]
    assert data["week_start"]


@pytest.mark.asyncio
async def test_dashboard_stats_staff_forbidden(
    client: AsyncClient, staff_auth_headers: dict,
):
    """Staff cannot access admin dashboard."""
    resp = await client.get("/api/v1/dashboard/stats", headers=staff_auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_weekly_summary_admin(client: AsyncClient, auth_headers: dict):
    """Admin can access weekly summary."""
    resp = await client.get(
        "/api/v1/reports/weekly-summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "week_start" in data
    assert "rating_distribution" in data
    assert "total_employees" in data


@pytest.mark.asyncio
async def test_attendance_summary_admin(client: AsyncClient, auth_headers: dict):
    """Admin can access daily attendance summary."""
    resp = await client.get(
        "/api/v1/reports/attendance-summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "date" in data
    assert "present" in data
    assert "attendance_rate" in data
    assert "location_breakdown" in data


@pytest.mark.asyncio
async def test_weekly_html_report(client: AsyncClient, auth_headers: dict):
    """Admin can generate HTML report."""
    resp = await client.get(
        "/api/v1/reports/weekly-html",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "TRACE Weekly Performance Report" in resp.text
    assert "<!DOCTYPE html>" in resp.text


@pytest.mark.asyncio
async def test_reports_staff_forbidden(
    client: AsyncClient, staff_auth_headers: dict,
):
    """Staff cannot access reports."""
    resp = await client.get(
        "/api/v1/reports/weekly-summary",
        headers=staff_auth_headers,
    )
    assert resp.status_code == 403
