"""
TRACE - Attendance Schemas
Pydantic models for attendance records (Admin-maintained; no clock-in/out).
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


# ── Attendance Response ──────────────────────────────────────────

class AttendanceResponse(BaseModel):
    id: int
    employee_id: int
    attendance_date: date
    time_in: datetime | None = None
    time_out: datetime | None = None
    total_hours: Decimal | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    location: str | None = None
    location_status: str | None = None
    ip_address: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class AttendanceListResponse(BaseModel):
    records: list[AttendanceResponse]
    total: int
    page: int
    per_page: int
