"""
TRACE - Employee Schemas
Pydantic models for employee management.
"""

from datetime import date, datetime, time

from pydantic import BaseModel, Field


# ── Department ───────────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: str | None = None


class DepartmentResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Work Schedule ────────────────────────────────────────────────

class WorkScheduleCreate(BaseModel):
    schedule_name: str = Field(..., max_length=100)
    start_time: time
    end_time: time
    break_minutes: int = 0


class WorkScheduleResponse(BaseModel):
    id: int
    schedule_name: str
    start_time: time
    end_time: time
    break_minutes: int
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Employee Detail ──────────────────────────────────────────────

class EmployeeDetailCreate(BaseModel):
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    blood_group: str | None = None
    marital_status: str | None = None


class EmployeeDetailResponse(EmployeeDetailCreate):
    id: int
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Employee ─────────────────────────────────────────────────────

class EmployeeCreate(BaseModel):
    user_id: int
    employee_code: str = Field(..., max_length=50)
    manager_id: int | None = None
    department_id: int | None = None
    work_schedule_id: int | None = None
    joining_date: date | None = None
    employee_detail: EmployeeDetailCreate | None = None


class EmployeeUpdate(BaseModel):
    manager_id: int | None = None
    department_id: int | None = None
    work_schedule_id: int | None = None
    status: str | None = None


class EmployeeResponse(BaseModel):
    id: int
    user_id: int
    employee_code: str
    manager_id: int | None = None
    department_id: int | None = None
    work_schedule_id: int | None = None
    joining_date: date | None = None
    status: str
    employee_detail: EmployeeDetailResponse | None = None
    department: DepartmentResponse | None = None
    work_schedule: WorkScheduleResponse | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class EmployeeListResponse(BaseModel):
    employees: list[EmployeeResponse]
    total: int
    page: int
    per_page: int
