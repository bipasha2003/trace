"""
TRACE - Attendance Schemas
Pydantic models for check-in/out and attendance records.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# ── Check-In ─────────────────────────────────────────────────────

class CheckInRequest(BaseModel):
    """Employee check-in payload with GPS coords."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class CheckOutRequest(BaseModel):
    """Employee check-out payload."""
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)


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
