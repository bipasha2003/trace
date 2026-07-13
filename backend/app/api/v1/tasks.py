"""
TRACE - Tasks API Router
Endpoints for task CRUD, timer, and comments.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import NotFoundException
from app.models.employee import Employee
from app.models.user import User
from app.schemas.task import (
    TaskCommentCreate, TaskCommentResponse, TaskCreate,
    TaskListResponse, TaskResponse, TaskTimeLogResponse, TaskUpdate,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


async def _get_employee(user: User, db: AsyncSession) -> Employee:
    """Resolve employee via async query to avoid lazy-loading issues."""
    result = await db.execute(
        select(Employee).where(
            Employee.user_id == user.id, Employee.deleted_at.is_(None)
        )
    )
    employee = result.scalar_one_or_none()
    if employee is None:
        raise NotFoundException("Employee record for this user")
    return employee


@router.post("", response_model=TaskResponse, status_code=201, summary="Create task")
async def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    employee = await _get_employee(current_user, db)
    service = TaskService(db)
    return await service.create_task(data, assigned_by=employee.id)


@router.get("", response_model=TaskListResponse, summary="List tasks")
async def list_tasks(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = None,
    assigned_to: int | None = None,
    priority: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    return await service.list_tasks(
        page=page, per_page=per_page, status=status,
        assigned_to=assigned_to, priority=priority,
    )


@router.get("/{task_id}", response_model=TaskResponse, summary="Get task")
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    return await service.get_task_by_id(task_id)


@router.patch("/{task_id}", response_model=TaskResponse, summary="Update task")
async def update_task(
    task_id: int,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    return await service.update_task(task_id, data)


@router.post("/{task_id}/timer/start", response_model=TaskTimeLogResponse, summary="Start timer")
async def start_timer(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    employee = await _get_employee(current_user, db)
    service = TaskService(db)
    return await service.start_timer(task_id, employee_id=employee.id)


@router.post("/timer/{time_log_id}/stop", response_model=TaskTimeLogResponse, summary="Stop timer")
async def stop_timer(
    time_log_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    return await service.stop_timer(time_log_id)


@router.post("/{task_id}/comments", response_model=TaskCommentResponse, status_code=201, summary="Add comment")
async def add_comment(
    task_id: int,
    data: TaskCommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    employee = await _get_employee(current_user, db)
    service = TaskService(db)
    return await service.add_comment(task_id, employee_id=employee.id, data=data)
