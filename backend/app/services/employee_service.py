"""
TRACE - Employee Service
Business logic for employee, department, and work schedule management.
"""

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import AlreadyExistsException, NotFoundException
from app.models.employee import Department, Employee, EmployeeDetail, WorkSchedule
from app.schemas.employee import (
    DepartmentCreate,
    DepartmentResponse,
    EmployeeCreate,
    EmployeeDetailCreate,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdate,
    WorkScheduleCreate,
    WorkScheduleResponse,
)


class DepartmentService:
    """Department CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: DepartmentCreate) -> DepartmentResponse:
        existing = await self.db.execute(
            select(Department).where(
                Department.name == data.name, Department.deleted_at.is_(None)
            )
        )
        if existing.scalar_one_or_none():
            raise AlreadyExistsException("Department")

        dept = Department(name=data.name, description=data.description)
        self.db.add(dept)
        await self.db.flush()
        return DepartmentResponse.model_validate(dept)

    async def list_all(self) -> list[DepartmentResponse]:
        result = await self.db.execute(
            select(Department)
            .where(Department.deleted_at.is_(None))
            .order_by(Department.name)
        )
        return [DepartmentResponse.model_validate(d) for d in result.scalars().all()]

    async def get_by_id(self, dept_id: int) -> DepartmentResponse:
        result = await self.db.execute(
            select(Department).where(
                Department.id == dept_id, Department.deleted_at.is_(None)
            )
        )
        dept = result.scalar_one_or_none()
        if dept is None:
            raise NotFoundException("Department")
        return DepartmentResponse.model_validate(dept)

    async def delete(self, dept_id: int) -> dict:
        result = await self.db.execute(
            select(Department).where(
                Department.id == dept_id, Department.deleted_at.is_(None)
            )
        )
        dept = result.scalar_one_or_none()
        if dept is None:
            raise NotFoundException("Department")
        dept.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return {"message": "Department deleted", "id": dept_id}


class WorkScheduleService:
    """Work schedule CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: WorkScheduleCreate) -> WorkScheduleResponse:
        schedule = WorkSchedule(
            schedule_name=data.schedule_name,
            start_time=data.start_time,
            end_time=data.end_time,
            break_minutes=data.break_minutes,
        )
        self.db.add(schedule)
        await self.db.flush()
        return WorkScheduleResponse.model_validate(schedule)

    async def list_all(self) -> list[WorkScheduleResponse]:
        result = await self.db.execute(
            select(WorkSchedule)
            .where(WorkSchedule.deleted_at.is_(None))
            .order_by(WorkSchedule.schedule_name)
        )
        return [WorkScheduleResponse.model_validate(s) for s in result.scalars().all()]

    async def get_by_id(self, schedule_id: int) -> WorkScheduleResponse:
        result = await self.db.execute(
            select(WorkSchedule).where(
                WorkSchedule.id == schedule_id, WorkSchedule.deleted_at.is_(None)
            )
        )
        schedule = result.scalar_one_or_none()
        if schedule is None:
            raise NotFoundException("Work Schedule")
        return WorkScheduleResponse.model_validate(schedule)


class EmployeeService:
    """Employee management business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: EmployeeCreate) -> EmployeeResponse:
        # Check duplicate employee_code
        existing = await self.db.execute(
            select(Employee).where(
                Employee.employee_code == data.employee_code,
                Employee.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise AlreadyExistsException("Employee with this code")

        # Create employee_detail if provided
        detail_id = None
        if data.employee_detail:
            detail = EmployeeDetail(**data.employee_detail.model_dump())
            self.db.add(detail)
            await self.db.flush()
            detail_id = detail.id

        employee = Employee(
            user_id=data.user_id,
            employee_code=data.employee_code,
            manager_id=data.manager_id,
            department_id=data.department_id,
            work_schedule_id=data.work_schedule_id,
            employee_details_id=detail_id,
            joining_date=data.joining_date or date.today(),
            status="Active",
        )
        self.db.add(employee)
        await self.db.flush()
        return await self.get_by_id(employee.id)

    async def get_by_id(self, employee_id: int) -> EmployeeResponse:
        stmt = (
            select(Employee)
            .where(Employee.id == employee_id, Employee.deleted_at.is_(None))
            .options(
                selectinload(Employee.employee_detail),
                selectinload(Employee.department),
                selectinload(Employee.work_schedule),
            )
        )
        result = await self.db.execute(stmt)
        employee = result.scalar_one_or_none()
        if employee is None:
            raise NotFoundException("Employee")
        return EmployeeResponse.model_validate(employee)

    async def get_by_user_id(self, user_id: int) -> EmployeeResponse:
        stmt = (
            select(Employee)
            .where(Employee.user_id == user_id, Employee.deleted_at.is_(None))
            .options(
                selectinload(Employee.employee_detail),
                selectinload(Employee.department),
                selectinload(Employee.work_schedule),
            )
        )
        result = await self.db.execute(stmt)
        employee = result.scalar_one_or_none()
        if employee is None:
            raise NotFoundException("Employee")
        return EmployeeResponse.model_validate(employee)

    async def list_employees(
        self,
        page: int = 1,
        per_page: int = 20,
        department_id: int | None = None,
        status: str | None = None,
    ) -> EmployeeListResponse:
        offset = (page - 1) * per_page
        conditions = [Employee.deleted_at.is_(None)]
        if department_id:
            conditions.append(Employee.department_id == department_id)
        if status:
            conditions.append(Employee.status == status)

        count_stmt = select(func.count(Employee.id)).where(*conditions)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Employee)
            .where(*conditions)
            .options(
                selectinload(Employee.employee_detail),
                selectinload(Employee.department),
                selectinload(Employee.work_schedule),
            )
            .order_by(Employee.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        result = await self.db.execute(stmt)
        employees = result.scalars().all()

        return EmployeeListResponse(
            employees=[EmployeeResponse.model_validate(e) for e in employees],
            total=total,
            page=page,
            per_page=per_page,
        )

    async def update(self, employee_id: int, data: EmployeeUpdate) -> EmployeeResponse:
        stmt = select(Employee).where(
            Employee.id == employee_id, Employee.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        employee = result.scalar_one_or_none()
        if employee is None:
            raise NotFoundException("Employee")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(employee, field, value)

        await self.db.flush()
        return await self.get_by_id(employee_id)

    async def deactivate(self, employee_id: int) -> dict:
        stmt = select(Employee).where(
            Employee.id == employee_id, Employee.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        employee = result.scalar_one_or_none()
        if employee is None:
            raise NotFoundException("Employee")

        employee.status = "Inactive"
        employee.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return {"message": "Employee deactivated", "id": employee_id}
