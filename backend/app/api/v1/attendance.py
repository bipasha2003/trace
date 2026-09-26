"""
TRACE - Attendance API Router
Read-only and admin endpoints for attendance records.
Clock-in/out capture has been removed (employee HR self-service is out of scope).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_admin
from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import NotFoundException
from app.models.employee import Employee
from app.models.user import User
from app.schemas.attendance import AttendanceResponse, AttendanceListResponse

# Attendance records are Admin-owned — PROJECT.md §9.1
router = APIRouter(prefix="/attendance", tags=["Attendance"], dependencies=[Depends(require_admin)])


async def _get_employee(user: User, db: AsyncSession) -> Employee:
    """Resolve the Employee record for the current user, or auto-create if missing."""
    result = await db.execute(
        select(Employee).where(
            Employee.user_id == user.id, Employee.deleted_at.is_(None)
        )
    )
    employee = result.scalar_one_or_none()
    if employee is None:
        employee = Employee(
            user_id=user.id,
            employee_code=f"EMP-{user.id:03d}",
            status="Active",
        )
        db.add(employee)
        await db.commit()
        await db.refresh(employee)
    return employee


@router.get("/history", response_model=AttendanceListResponse, summary="My attendance history")
async def attendance_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's attendance history with pagination."""
    from sqlalchemy import func
    from app.models.attendance import Attendance

    employee = await _get_employee(current_user, db)
    offset = (page - 1) * per_page

    count = (await db.execute(
        select(func.count(Attendance.id)).where(
            Attendance.employee_id == employee.id,
            Attendance.deleted_at.is_(None),
        )
    )).scalar() or 0

    result = await db.execute(
        select(Attendance)
        .where(Attendance.employee_id == employee.id, Attendance.deleted_at.is_(None))
        .order_by(Attendance.attendance_date.desc())
        .offset(offset)
        .limit(per_page)
    )
    records = result.scalars().all()

    return AttendanceListResponse(
        records=[AttendanceResponse.model_validate(r) for r in records],
        total=count,
        page=page,
        per_page=per_page,
    )


@router.get("/all", summary="Manager view — all employees attendance")
async def all_employees_attendance(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    date_filter: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin/Manager view — see all employees' attendance records.
    Optionally filter by a specific date (YYYY-MM-DD).
    """
    from sqlalchemy import func, Date as SQLDate, cast
    from app.models.attendance import Attendance

    filters = [Attendance.deleted_at.is_(None)]
    if date_filter:
        from datetime import date as dt_date
        try:
            d = dt_date.fromisoformat(date_filter)
            filters.append(Attendance.attendance_date == d)
        except ValueError:
            pass

    offset = (page - 1) * per_page
    count = (await db.execute(select(func.count(Attendance.id)).where(*filters))).scalar() or 0

    result = await db.execute(
        select(Attendance, Employee)
        .join(Employee, Employee.id == Attendance.employee_id)
        .where(*filters)
        .order_by(Attendance.attendance_date.desc(), Attendance.time_in.desc())
        .offset(offset).limit(per_page)
    )
    rows = result.all()

    records = []
    for att, emp in rows:
        records.append({
            "id": att.id,
            "employee_id": att.employee_id,
            "employee_code": emp.employee_code,
            "attendance_date": att.attendance_date.isoformat() if att.attendance_date else None,
            "check_in": att.time_in.isoformat() if att.time_in else None,
            "check_out": att.time_out.isoformat() if att.time_out else None,
            "total_hours": float(att.total_hours) if att.total_hours else None,
            "location": att.location,
            "location_status": att.location_status,
        })

    return {"records": records, "total": count, "page": page, "per_page": per_page}


@router.get("/summary/daily", summary="Today's attendance summary")
async def daily_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Summary of today's attendance: present count, total employees, rate."""
    from sqlalchemy import func, cast, Date as SQLDate
    from datetime import date, datetime, timezone
    from app.models.attendance import Attendance

    today = date.today()
    total_emp = (await db.execute(
        select(func.count(Employee.id)).where(Employee.deleted_at.is_(None), Employee.status == "Active")
    )).scalar() or 0

    present = (await db.execute(
        select(func.count(Attendance.id)).where(
            Attendance.attendance_date == today,
            Attendance.deleted_at.is_(None),
        )
    )).scalar() or 0

    rate = round(present / total_emp * 100, 1) if total_emp > 0 else 0
    return {
        "date": today.isoformat(),
        "total_employees": total_emp,
        "present": present,
        "absent": max(0, total_emp - present),
        "attendance_rate": rate,
    }
