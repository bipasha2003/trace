"""
TRACE - HRMS API Endpoints
Manages employee leaves, holidays, work schedule shifts, and bulk dataset uploading.
"""

import csv
import io
import json
import logging
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.permissions import require_admin
from app.database import get_db
from app.models.employee import Employee, WorkSchedule, Department
from app.models.attendance import Attendance
from app.models.hrms import Leave, Holiday

logger = logging.getLogger("trace.hrms")
# Workforce records are Admin-owned — PROJECT.md §9.1
router = APIRouter(prefix="/hrms", tags=["HRMS"], dependencies=[Depends(require_admin)])


# ── Schemas ───────────────────────────────────────────────────────
class LeaveCreate(BaseModel):
    employee_id: int
    leave_type: str  # Casual, Sick, Earned, Unpaid
    start_date: date
    end_date: date
    reason: Optional[str] = None


class LeaveStatusUpdate(BaseModel):
    status: str  # Pending, Approved, Rejected
    approved_by: Optional[int] = None


class HolidayCreate(BaseModel):
    name: str
    holiday_date: date
    description: Optional[str] = None
    type: str = "Public"


class ShiftCreate(BaseModel):
    schedule_name: str
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    break_minutes: int = 0


# ── LEAVES ENDPOINTS ──────────────────────────────────────────────
@router.get("/leaves")
async def get_leaves(
    employee_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve leave requests with employee details."""
    query = select(Leave).options(selectinload(Leave.employee)).order_by(Leave.created_at.desc())
    if employee_id:
        query = query.where(Leave.employee_id == employee_id)
    result = await db.execute(query)
    leaves = result.scalars().all()
    
    return [
        {
            "id": l.id,
            "employee_id": l.employee_id,
            "employee_code": l.employee.employee_code if l.employee else "N/A",
            "leave_type": l.leave_type,
            "start_date": l.start_date.isoformat(),
            "end_date": l.end_date.isoformat(),
            "reason": l.reason,
            "status": l.status,
            "approved_by": l.approved_by,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in leaves
    ]


@router.post("/leaves")
async def create_leave(
    data: LeaveCreate,
    db: AsyncSession = Depends(get_db)
):
    """Apply for a leave."""
    leave = Leave(
        employee_id=data.employee_id,
        leave_type=data.leave_type,
        start_date=data.start_date,
        end_date=data.end_date,
        reason=data.reason,
        status="Pending",
    )
    db.add(leave)
    await db.commit()
    await db.refresh(leave)
    return {"status": "success", "message": "Leave application submitted", "leave_id": leave.id}


@router.patch("/leaves/{leave_id}/status")
async def update_leave_status(
    leave_id: int,
    data: LeaveStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Approve or reject a leave request."""
    result = await db.execute(select(Leave).where(Leave.id == leave_id))
    leave = result.scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave record not found")

    leave.status = data.status
    if data.approved_by:
        leave.approved_by = data.approved_by
    await db.commit()
    return {"status": "success", "message": f"Leave status updated to {data.status}"}


# ── HOLIDAYS ENDPOINTS ────────────────────────────────────────────
@router.get("/holidays")
async def get_holidays(db: AsyncSession = Depends(get_db)):
    """Get all scheduled company & public holidays."""
    result = await db.execute(select(Holiday).order_by(Holiday.holiday_date.asc()))
    holidays = result.scalars().all()
    return [
        {
            "id": h.id,
            "name": h.name,
            "holiday_date": h.holiday_date.isoformat(),
            "description": h.description,
            "type": h.type,
        }
        for h in holidays
    ]


@router.post("/holidays")
async def create_holiday(data: HolidayCreate, db: AsyncSession = Depends(get_db)):
    """Create a new holiday entry."""
    holiday = Holiday(
        name=data.name,
        holiday_date=data.holiday_date,
        description=data.description,
        type=data.type,
    )
    db.add(holiday)
    await db.commit()
    await db.refresh(holiday)
    return {"status": "success", "message": "Holiday added successfully", "holiday_id": holiday.id}


@router.put("/holidays/{holiday_id}")
async def update_holiday(holiday_id: int, data: HolidayCreate, db: AsyncSession = Depends(get_db)):
    """Update a holiday entry."""
    result = await db.execute(select(Holiday).where(Holiday.id == holiday_id))
    holiday = result.scalar_one_or_none()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    holiday.name = data.name
    holiday.holiday_date = data.holiday_date
    holiday.description = data.description
    holiday.type = data.type
    await db.commit()
    return {"status": "success", "message": "Holiday updated successfully"}


@router.delete("/holidays/{holiday_id}")
async def delete_holiday(holiday_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a holiday entry."""
    result = await db.execute(select(Holiday).where(Holiday.id == holiday_id))
    holiday = result.scalar_one_or_none()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    await db.delete(holiday)
    await db.commit()
    return {"status": "success", "message": "Holiday deleted"}


@router.delete("/leaves/{leave_id}")
async def delete_leave(leave_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a leave request."""
    result = await db.execute(select(Leave).where(Leave.id == leave_id))
    leave = result.scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave record not found")
    await db.delete(leave)
    await db.commit()
    return {"status": "success", "message": "Leave record deleted"}


# ── SHIFTS ENDPOINTS ──────────────────────────────────────────────
@router.get("/shifts")
async def get_shifts(db: AsyncSession = Depends(get_db)):
    """Get all work schedule shifts."""
    result = await db.execute(select(WorkSchedule).order_by(WorkSchedule.id.asc()))
    shifts = result.scalars().all()
    return [
        {
            "id": s.id,
            "schedule_name": s.schedule_name,
            "start_time": s.start_time.strftime("%H:%M") if s.start_time else "09:00",
            "end_time": s.end_time.strftime("%H:%M") if s.end_time else "18:00",
            "break_minutes": s.break_minutes,
        }
        for s in shifts
    ]


@router.post("/shifts")
async def create_shift(data: ShiftCreate, db: AsyncSession = Depends(get_db)):
    """Create a new work schedule shift."""
    from datetime import time
    sh_start = time.fromisoformat(data.start_time)
    sh_end = time.fromisoformat(data.end_time)
    shift = WorkSchedule(
        schedule_name=data.schedule_name,
        start_time=sh_start,
        end_time=sh_end,
        break_minutes=data.break_minutes,
    )
    db.add(shift)
    await db.commit()
    await db.refresh(shift)
    return {"status": "success", "message": "Shift created successfully", "shift_id": shift.id}


@router.put("/shifts/{shift_id}")
async def update_shift(shift_id: int, data: ShiftCreate, db: AsyncSession = Depends(get_db)):
    """Update a work schedule shift."""
    from datetime import time
    result = await db.execute(select(WorkSchedule).where(WorkSchedule.id == shift_id))
    shift = result.scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    shift.schedule_name = data.schedule_name
    shift.start_time = time.fromisoformat(data.start_time)
    shift.end_time = time.fromisoformat(data.end_time)
    shift.break_minutes = data.break_minutes
    await db.commit()
    return {"status": "success", "message": "Shift updated successfully"}


@router.delete("/shifts/{shift_id}")
async def delete_shift(shift_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a work schedule shift."""
    result = await db.execute(select(WorkSchedule).where(WorkSchedule.id == shift_id))
    shift = result.scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    await db.delete(shift)
    await db.commit()
    return {"status": "success", "message": "Shift deleted successfully"}


# ── BULK UPLOADING ENDPOINT ───────────────────────────────────────
@router.post("/bulk-upload")
async def bulk_upload_hrms_data(
    entity_type: str = Form(...),  # 'employees', 'attendance', 'leaves', 'holidays', 'shifts'
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk upload CSV or JSON data for HRMS entities.
    Supports uploading Employees, Attendance, Leaves, Holidays, and Shifts.
    """
    content = await file.read()
    filename = file.filename.lower()
    records = []

    try:
        if filename.endswith(".json"):
            records = json.loads(content.decode("utf-8"))
        elif filename.endswith(".csv"):
            text = content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(text))
            records = [row for row in reader]
        else:
            raise HTTPException(status_code=400, detail="Only CSV and JSON files are supported")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    inserted_count = 0
    try:
        if entity_type == "holidays":
            for r in records:
                date_val = datetime.strptime(r["holiday_date"], "%Y-%m-%d").date() if isinstance(r.get("holiday_date"), str) else r["holiday_date"]
                h = Holiday(
                    name=r["name"],
                    holiday_date=date_val,
                    description=r.get("description"),
                    type=r.get("type", "Public"),
                )
                db.add(h)
                inserted_count += 1

        elif entity_type == "leaves":
            for r in records:
                s_date = datetime.strptime(r["start_date"], "%Y-%m-%d").date() if isinstance(r.get("start_date"), str) else r["start_date"]
                e_date = datetime.strptime(r["end_date"], "%Y-%m-%d").date() if isinstance(r.get("end_date"), str) else r["end_date"]
                l = Leave(
                    employee_id=int(r["employee_id"]),
                    leave_type=r.get("leave_type", "Casual"),
                    start_date=s_date,
                    end_date=e_date,
                    reason=r.get("reason"),
                    status=r.get("status", "Pending"),
                )
                db.add(l)
                inserted_count += 1

        elif entity_type == "attendance":
            for r in records:
                att_date = datetime.strptime(r["attendance_date"], "%Y-%m-%d").date() if isinstance(r.get("attendance_date"), str) else r["attendance_date"]
                a = Attendance(
                    employee_id=int(r["employee_id"]),
                    attendance_date=att_date,
                    location=r.get("location", "Office"),
                    location_status=r.get("location_status", "office"),
                )
                db.add(a)
                inserted_count += 1

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported entity_type: {entity_type}")

        await db.commit()
        return {
            "status": "success",
            "message": f"Successfully bulk imported {inserted_count} {entity_type} records",
            "count": inserted_count,
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Bulk upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database import failed: {str(e)}")


# ── SHIFT ASSIGNMENT ──────────────────────────────────────────────
class ShiftAssignRequest(BaseModel):
    shift_id: int


@router.post("/employees/{employee_id}/assign-shift")
async def assign_shift_to_employee(
    employee_id: int,
    data: ShiftAssignRequest,
    db: AsyncSession = Depends(get_db),
):
    """Assign a work schedule shift to an employee."""
    from app.models.employee import Employee
    emp = (await db.execute(select(Employee).where(Employee.id == employee_id, Employee.deleted_at.is_(None)))).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    shift = (await db.execute(select(WorkSchedule).where(WorkSchedule.id == data.shift_id))).scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    emp.work_schedule_id = data.shift_id
    await db.commit()
    return {"status": "success", "message": f"Shift '{shift.schedule_name}' assigned to employee {employee_id}"}


# ── LEAVE BALANCE ─────────────────────────────────────────────────
LEAVE_ENTITLEMENTS = {
    "Casual": 10,
    "Sick": 7,
    "Earned": 15,
    "Unpaid": 0,
}


@router.get("/employees/{employee_id}/leave-balance")
async def get_leave_balance(employee_id: int, year: int = None, db: AsyncSession = Depends(get_db)):
    """Get annual leave balance for an employee (used vs. remaining)."""
    from sqlalchemy import func, extract
    import datetime

    yr = year or datetime.date.today().year
    result = await db.execute(
        select(Leave.leave_type, func.count(Leave.id).label("count"))
        .where(
            Leave.employee_id == employee_id,
            Leave.status == "Approved",
            extract("year", Leave.start_date) == yr,
        )
        .group_by(Leave.leave_type)
    )
    used_map = {row.leave_type: row.count for row in result.all()}

    balance = {}
    for lt, entitlement in LEAVE_ENTITLEMENTS.items():
        used = used_map.get(lt, 0)
        balance[lt] = {"entitlement": entitlement, "used": used, "remaining": max(0, entitlement - used)}

    return {"employee_id": employee_id, "year": yr, "balance": balance}


@router.get("/leave-balance/summary")
async def all_employees_leave_balance(year: int = None, db: AsyncSession = Depends(get_db)):
    """Aggregate leave balance summary for all employees."""
    from sqlalchemy import func, extract
    from app.models.employee import Employee
    import datetime

    yr = year or datetime.date.today().year
    result = await db.execute(
        select(Leave.employee_id, Leave.leave_type, func.count(Leave.id).label("count"))
        .where(Leave.status == "Approved", extract("year", Leave.start_date) == yr)
        .group_by(Leave.employee_id, Leave.leave_type)
    )
    rows = result.all()

    # Build per-employee map
    emp_map: dict[int, dict] = {}
    for row in rows:
        if row.employee_id not in emp_map:
            emp_map[row.employee_id] = {}
        emp_map[row.employee_id][row.leave_type] = row.count

    # Get all employees
    emps = (await db.execute(select(Employee).where(Employee.deleted_at.is_(None)))).scalars().all()
    summary = []
    for emp in emps:
        used = emp_map.get(emp.id, {})
        b = {}
        for lt, ent in LEAVE_ENTITLEMENTS.items():
            u = used.get(lt, 0)
            b[lt] = {"entitlement": ent, "used": u, "remaining": max(0, ent - u)}
        summary.append({"employee_id": emp.id, "employee_code": emp.employee_code, "balance": b})

    return {"year": yr, "entitlements": LEAVE_ENTITLEMENTS, "employees": summary}
