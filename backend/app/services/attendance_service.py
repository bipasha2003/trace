"""
TRACE - Attendance Service
Business logic for check-in/out with geo-fence validation.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.geolocation import check_geo_fence
from app.exceptions import AlreadyCheckedInException, NotFoundException
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.schemas.attendance import AttendanceResponse, CheckInRequest


class AttendanceService:
    """Handles attendance business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_in(
        self,
        employee_id: int,
        data: CheckInRequest,
        ip_address: str | None = None,
        office_lat: float = 0.0,
        office_lon: float = 0.0,
    ) -> AttendanceResponse:
        """
        Record employee check-in with geo-fence validation.
        
        Process:
        1. Verify employee exists
        2. Check for duplicate check-in today
        3. Validate location via Haversine formula
        4. Persist attendance record
        """
        # Verify employee
        emp = await self.db.execute(
            select(Employee).where(Employee.id == employee_id, Employee.deleted_at.is_(None))
        )
        if emp.scalar_one_or_none() is None:
            raise NotFoundException("Employee")

        # Check duplicate
        today = date.today()
        existing = await self.db.execute(
            select(Attendance).where(
                and_(
                    Attendance.employee_id == employee_id,
                    Attendance.attendance_date == today,
                    Attendance.deleted_at.is_(None),
                )
            )
        )
        if existing.scalar_one_or_none():
            raise AlreadyCheckedInException()

        # Geo-fence check
        location_status = check_geo_fence(
            data.latitude, data.longitude, office_lat, office_lon
        )

        # Create record
        attendance = Attendance(
            employee_id=employee_id,
            attendance_date=today,
            time_in=datetime.now(timezone.utc),
            latitude=Decimal(str(data.latitude)),
            longitude=Decimal(str(data.longitude)),
            location_status=location_status,
            ip_address=ip_address,
        )
        self.db.add(attendance)
        await self.db.flush()

        return AttendanceResponse.model_validate(attendance)

    async def check_out(self, employee_id: int) -> AttendanceResponse:
        """Record employee check-out and compute total hours."""
        today = date.today()
        result = await self.db.execute(
            select(Attendance).where(
                and_(
                    Attendance.employee_id == employee_id,
                    Attendance.attendance_date == today,
                    Attendance.time_out.is_(None),
                    Attendance.deleted_at.is_(None),
                )
            )
        )
        attendance = result.scalar_one_or_none()

        if attendance is None:
            raise NotFoundException("Active check-in for today")

        now = datetime.now(timezone.utc)
        attendance.time_out = now

        # Calculate total hours
        if attendance.time_in:
            delta = now - attendance.time_in
            attendance.total_hours = Decimal(str(round(delta.total_seconds() / 3600, 2)))

        await self.db.flush()
        return AttendanceResponse.model_validate(attendance)
