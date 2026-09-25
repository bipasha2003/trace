"""
TRACE - Employee Service
Business logic for employee, department, designation, work schedule management, and user auto-creation.
"""

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.exceptions import AlreadyExistsException, NotFoundException
from app.models.employee import Department, Designation, Employee, EmployeeDetail, WorkSchedule
from app.models.user import User, Role, UserRole
from app.schemas.employee import (
    DepartmentCreate,
    DepartmentResponse,
    DesignationCreate,
    DesignationResponse,
    EmployeeCreate,
    EmployeeDetailCreate,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdate,
    WorkScheduleCreate,
    WorkScheduleResponse,
)


class DesignationService:
    """Designation CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: DesignationCreate) -> DesignationResponse:
        existing = await self.db.execute(
            select(Designation).where(
                Designation.name == data.name, Designation.deleted_at.is_(None)
            )
        )
        if existing.scalar_one_or_none():
            raise AlreadyExistsException("Designation")

        desig = Designation(name=data.name, description=data.description)
        self.db.add(desig)
        await self.db.flush()
        return DesignationResponse.model_validate(desig)

    async def list_all(self) -> list[DesignationResponse]:
        result = await self.db.execute(
            select(Designation)
            .where(Designation.deleted_at.is_(None))
            .order_by(Designation.name)
        )
        return [DesignationResponse.model_validate(d) for d in result.scalars().all()]

    async def get_by_id(self, desig_id: int) -> DesignationResponse:
        result = await self.db.execute(
            select(Designation).where(
                Designation.id == desig_id, Designation.deleted_at.is_(None)
            )
        )
        desig = result.scalar_one_or_none()
        if desig is None:
            raise NotFoundException("Designation")
        return DesignationResponse.model_validate(desig)

    async def delete(self, desig_id: int) -> dict:
        result = await self.db.execute(
            select(Designation).where(
                Designation.id == desig_id, Designation.deleted_at.is_(None)
            )
        )
        desig = result.scalar_one_or_none()
        if desig is None:
            raise NotFoundException("Designation")
        desig.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return {"message": "Designation deleted", "id": desig_id}


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

        # Resolve or auto-create User
        target_user_id = data.user_id
        if not target_user_id:
            if not data.email or not data.password:
                raise ValueError("Either user_id or email & password must be provided to create an employee.")
            
            # Check if user with this email already exists
            user_res = await self.db.execute(select(User).where(User.email == data.email))
            existing_user = user_res.scalar_one_or_none()
            if existing_user:
                target_user_id = existing_user.id
            else:
                uname = data.email.split("@")[0]
                user_name = data.name or uname
                new_user = User(
                    name=user_name,
                    username=uname,
                    email=data.email,
                    password=hash_password(data.password),
                    is_verified=True,
                    status="Active",
                )
                self.db.add(new_user)
                await self.db.flush()
                target_user_id = new_user.id

                # Assign requested role
                role_name = data.role or "Employee"
                role_res = await self.db.execute(select(Role).where(Role.role_name == role_name))
                role_obj = role_res.scalar_one_or_none()
                if not role_obj:
                    role_obj = Role(role_name=role_name)
                    self.db.add(role_obj)
                    await self.db.flush()
                
                user_role = UserRole(user_id=new_user.id, role_id=role_obj.id)
                self.db.add(user_role)
                await self.db.flush()

        # Create employee_detail if provided
        detail_id = None
        if data.employee_detail:
            detail = EmployeeDetail(**data.employee_detail.model_dump())
            self.db.add(detail)
            await self.db.flush()
            detail_id = detail.id

        employee = Employee(
            user_id=target_user_id,
            employee_code=data.employee_code,
            manager_id=data.manager_id,
            department_id=data.department_id,
            designation_id=data.designation_id,
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
                selectinload(Employee.designation),
                selectinload(Employee.work_schedule),
                selectinload(Employee.user).selectinload(User.user_roles).selectinload(UserRole.role),
            )
        )
        result = await self.db.execute(stmt)
        employee = result.scalar_one_or_none()
        if employee is None:
            raise NotFoundException("Employee")

        resp = EmployeeResponse.model_validate(employee)
        if employee.user:
            # Attach user role if available
            role_name = "Employee"
            if employee.user.user_roles:
                # Get role name from first user role
                r = employee.user.user_roles[0]
                if hasattr(r, 'role') and r.role:
                    role_name = r.role.role_name
            resp.user = {
                "id": employee.user.id,
                "name": employee.user.name,
                "username": employee.user.username,
                "email": employee.user.email,
                "role": role_name,
            }
        return resp

    async def get_by_user_id(self, user_id: int) -> EmployeeResponse:
        stmt = (
            select(Employee)
            .where(Employee.user_id == user_id, Employee.deleted_at.is_(None))
            .options(
                selectinload(Employee.employee_detail),
                selectinload(Employee.department),
                selectinload(Employee.designation),
                selectinload(Employee.work_schedule),
                selectinload(Employee.user).selectinload(User.user_roles).selectinload(UserRole.role),
            )
        )
        result = await self.db.execute(stmt)
        employee = result.scalar_one_or_none()
        if employee is None:
            raise NotFoundException("Employee")
        return await self.get_by_id(employee.id)

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
                selectinload(Employee.designation),
                selectinload(Employee.work_schedule),
                selectinload(Employee.user).selectinload(User.user_roles).selectinload(UserRole.role),
            )
            .order_by(Employee.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        result = await self.db.execute(stmt)
        employees = result.scalars().all()

        emp_responses = []
        for e in employees:
            resp = EmployeeResponse.model_validate(e)
            if e.user:
                role_name = "Employee"
                if e.user.user_roles:
                    r = e.user.user_roles[0]
                    if hasattr(r, 'role') and r.role:
                        role_name = r.role.role_name
                resp.user = {
                    "id": e.user.id,
                    "name": e.user.name,
                    "username": e.user.username,
                    "email": e.user.email,
                    "role": role_name,
                }
            emp_responses.append(resp)

        return EmployeeListResponse(
            employees=emp_responses,
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
