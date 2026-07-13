"""
TRACE - Attendance API Router
Endpoints for check-in/out with geo-fence validation.
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import NotFoundException
from app.models.employee import Employee
from app.models.user import User
from app.schemas.attendance import AttendanceResponse, AttendanceListResponse, CheckInRequest
from app.services.attendance_service import AttendanceService

router = APIRouter(prefix="/attendance", tags=["Attendance"])


async def _get_employee(user: User, db: AsyncSession) -> Employee:
    """Resolve the Employee record for the current user via a proper async query."""
    result = await db.execute(
        select(Employee).where(
            Employee.user_id == user.id, Employee.deleted_at.is_(None)
        )
    )
    employee = result.scalar_one_or_none()
    if employee is None:
        raise NotFoundException("Employee record for this user")
    return employee


@router.post("/checkin", response_model=AttendanceResponse, summary="Check-in with GPS")
async def check_in(
    data: CheckInRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Employee check-in with geo-fence validation."""
    employee = await _get_employee(current_user, db)
    ip_address = request.client.host if request.client else None
    service = AttendanceService(db)
    return await service.check_in(
        employee_id=employee.id,
        data=data,
        ip_address=ip_address,
    )


@router.post("/checkout", response_model=AttendanceResponse, summary="Check-out")
async def check_out(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Employee check-out — computes total hours."""
    employee = await _get_employee(current_user, db)
    service = AttendanceService(db)
    return await service.check_out(employee_id=employee.id)


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
