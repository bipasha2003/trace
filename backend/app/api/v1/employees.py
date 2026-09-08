"""
TRACE - Employees API Router
Endpoints for employee, department, and work schedule management.
RBAC: Admin/Manager can create/update/delete. All authenticated users can read.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_admin, require_manager_or_admin
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.employee import (
    DepartmentCreate,
    DepartmentResponse,
    DesignationCreate,
    DesignationResponse,
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdate,
    WorkScheduleCreate,
    WorkScheduleResponse,
)
from app.services.employee_service import (
    DepartmentService,
    DesignationService,
    EmployeeService,
    WorkScheduleService,
)

router = APIRouter(tags=["Employees"])


# ══════════════════════════════════════════════════════════════════
#  DESIGNATIONS
# ══════════════════════════════════════════════════════════════════

@router.post(
    "/designations",
    response_model=DesignationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create designation",
    description="Admin/Manager only.",
)
async def create_designation(
    data: DesignationCreate,
    current_user: User = Depends(require_manager_or_admin),
    db: AsyncSession = Depends(get_db),
):
    service = DesignationService(db)
    return await service.create(data)


@router.get(
    "/designations",
    response_model=list[DesignationResponse],
    summary="List all designations",
)
async def list_designations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DesignationService(db)
    return await service.list_all()


@router.delete(
    "/designations/{desig_id}",
    summary="Delete designation",
    description="Admin only.",
)
async def delete_designation(
    desig_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = DesignationService(db)
    return await service.delete(desig_id)



# ══════════════════════════════════════════════════════════════════
#  DEPARTMENTS
# ══════════════════════════════════════════════════════════════════

@router.post(
    "/departments",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create department",
    description="Admin/Manager only.",
)
async def create_department(
    data: DepartmentCreate,
    current_user: User = Depends(require_manager_or_admin),
    db: AsyncSession = Depends(get_db),
):
    service = DepartmentService(db)
    return await service.create(data)


@router.get(
    "/departments",
    response_model=list[DepartmentResponse],
    summary="List all departments",
)
async def list_departments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DepartmentService(db)
    return await service.list_all()


@router.get(
    "/departments/{dept_id}",
    response_model=DepartmentResponse,
    summary="Get department by ID",
)
async def get_department(
    dept_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DepartmentService(db)
    return await service.get_by_id(dept_id)


@router.delete(
    "/departments/{dept_id}",
    summary="Delete department (soft)",
    description="Admin only.",
)
async def delete_department(
    dept_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = DepartmentService(db)
    return await service.delete(dept_id)


# ══════════════════════════════════════════════════════════════════
#  WORK SCHEDULES
# ══════════════════════════════════════════════════════════════════

@router.post(
    "/work-schedules",
    response_model=WorkScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create work schedule",
    description="Admin/Manager only.",
)
async def create_work_schedule(
    data: WorkScheduleCreate,
    current_user: User = Depends(require_manager_or_admin),
    db: AsyncSession = Depends(get_db),
):
    service = WorkScheduleService(db)
    return await service.create(data)


@router.get(
    "/work-schedules",
    response_model=list[WorkScheduleResponse],
    summary="List all work schedules",
)
async def list_work_schedules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkScheduleService(db)
    return await service.list_all()


@router.get(
    "/work-schedules/{schedule_id}",
    response_model=WorkScheduleResponse,
    summary="Get work schedule by ID",
)
async def get_work_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkScheduleService(db)
    return await service.get_by_id(schedule_id)


# ══════════════════════════════════════════════════════════════════
#  EMPLOYEES
# ══════════════════════════════════════════════════════════════════

@router.post(
    "/employees",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create employee record",
    description="Admin/Manager only. Links a user to the company structure.",
)
async def create_employee(
    data: EmployeeCreate,
    current_user: User = Depends(require_manager_or_admin),
    db: AsyncSession = Depends(get_db),
):
    service = EmployeeService(db)
    return await service.create(data)


@router.get(
    "/employees",
    response_model=EmployeeListResponse,
    summary="List employees",
    description="Filter by department and status. Admin/Manager only.",
)
async def list_employees(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    department_id: int | None = None,
    emp_status: str | None = Query(None, alias="status"),
    current_user: User = Depends(require_manager_or_admin),
    db: AsyncSession = Depends(get_db),
):
    service = EmployeeService(db)
    return await service.list_employees(
        page=page, per_page=per_page,
        department_id=department_id, status=emp_status,
    )


@router.get(
    "/employees/me",
    response_model=EmployeeResponse,
    summary="Get my employee record",
)
async def get_my_employee_record(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = EmployeeService(db)
    return await service.get_by_user_id(current_user.id)


@router.get(
    "/employees/{employee_id}",
    response_model=EmployeeResponse,
    summary="Get employee by ID",
)
async def get_employee(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = EmployeeService(db)
    return await service.get_by_id(employee_id)


@router.patch(
    "/employees/{employee_id}",
    response_model=EmployeeResponse,
    summary="Update employee",
    description="Admin/Manager only.",
)
async def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    current_user: User = Depends(require_manager_or_admin),
    db: AsyncSession = Depends(get_db),
):
    service = EmployeeService(db)
    return await service.update(employee_id, data)


@router.delete(
    "/employees/{employee_id}",
    summary="Deactivate employee (soft delete)",
    description="Admin only.",
)
async def deactivate_employee(
    employee_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = EmployeeService(db)
    return await service.deactivate(employee_id)
