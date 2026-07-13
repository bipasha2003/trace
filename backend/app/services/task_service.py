"""
TRACE - Task Service
Business logic for task CRUD and time tracking.
"""

from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundException
from app.models.task import Task, TaskComment, TaskDetail, TaskTimeLog
from app.schemas.task import (
    TaskCommentCreate, TaskCommentResponse, TaskCreate,
    TaskListResponse, TaskResponse, TaskTimeLogResponse, TaskUpdate,
)


class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(self, data: TaskCreate, assigned_by: int) -> TaskResponse:
        task = Task(
            title=data.title, description=data.description, type_id=data.type_id,
            assigned_to=data.assigned_to, assigned_by=assigned_by,
            parent_task_id=data.parent_task_id, priority=data.priority,
            impact_type=data.impact_type, estimated_hours=data.estimated_hours,
            due_date=data.due_date, status="Pending",
        )
        self.db.add(task)
        await self.db.flush()
        if data.task_detail:
            detail = TaskDetail(
                task_id=task.id, requirements=data.task_detail.requirements,
                acceptance_criteria=data.task_detail.acceptance_criteria,
                remarks=data.task_detail.remarks,
            )
            self.db.add(detail)
            await self.db.flush()
        return await self.get_task_by_id(task.id)

    async def get_task_by_id(self, task_id: int) -> TaskResponse:
        stmt = (
            select(Task).where(Task.id == task_id, Task.deleted_at.is_(None))
            .options(selectinload(Task.task_type), selectinload(Task.task_detail), selectinload(Task.comments))
        )
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        if task is None:
            raise NotFoundException("Task")
        return TaskResponse.model_validate(task)

    async def list_tasks(self, page: int = 1, per_page: int = 20, status: str | None = None,
                         assigned_to: int | None = None, priority: str | None = None) -> TaskListResponse:
        offset = (page - 1) * per_page
        conditions = [Task.deleted_at.is_(None)]
        if status:
            conditions.append(Task.status == status)
        if assigned_to:
            conditions.append(Task.assigned_to == assigned_to)
        if priority:
            conditions.append(Task.priority == priority)
        count_stmt = select(func.count(Task.id)).where(*conditions)
        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = (
            select(Task).where(*conditions)
            .options(selectinload(Task.task_type), selectinload(Task.task_detail), selectinload(Task.comments))
            .order_by(Task.created_at.desc()).offset(offset).limit(per_page)
        )
        result = await self.db.execute(stmt)
        tasks = result.scalars().all()
        return TaskListResponse(
            tasks=[TaskResponse.model_validate(t) for t in tasks],
            total=total, page=page, per_page=per_page,
        )

    async def update_task(self, task_id: int, data: TaskUpdate) -> TaskResponse:
        stmt = select(Task).where(Task.id == task_id, Task.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        if task is None:
            raise NotFoundException("Task")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(task, field, value)
        await self.db.flush()
        return await self.get_task_by_id(task_id)

    async def start_timer(self, task_id: int, employee_id: int) -> TaskTimeLogResponse:
        task = (await self.db.execute(select(Task).where(Task.id == task_id, Task.deleted_at.is_(None)))).scalar_one_or_none()
        if task is None:
            raise NotFoundException("Task")
        task.status = "WIP"
        time_log = TaskTimeLog(task_id=task_id, employee_id=employee_id, start_time=datetime.now(timezone.utc), active_minutes=0, idle_minutes=0)
        self.db.add(time_log)
        await self.db.flush()
        return TaskTimeLogResponse.model_validate(time_log)

    async def stop_timer(self, time_log_id: int) -> TaskTimeLogResponse:
        result = await self.db.execute(select(TaskTimeLog).where(TaskTimeLog.id == time_log_id, TaskTimeLog.end_time.is_(None)))
        time_log = result.scalar_one_or_none()
        if time_log is None:
            raise NotFoundException("Active time log")
        now = datetime.now(timezone.utc)
        time_log.end_time = now
        if time_log.start_time:
            time_log.active_minutes = int((now - time_log.start_time).total_seconds() / 60)
        await self.db.flush()
        return TaskTimeLogResponse.model_validate(time_log)

    async def add_comment(self, task_id: int, employee_id: int, data: TaskCommentCreate) -> TaskCommentResponse:
        comment = TaskComment(task_id=task_id, employee_id=employee_id, comment=data.comment)
        self.db.add(comment)
        await self.db.flush()
        return TaskCommentResponse.model_validate(comment)
