"""
TRACE - Tasks API (task-by-id operations)

Project-scoped list and create live under /projects/{id}/tasks. Everything here
resolves the task's project and the caller's role in it first.

PATCH /tasks/{id}/status is where status authority is enforced (CORE.md §7): the
assignee updates their own task, completion included; the Project Manager may set
any status; everyone else gets 403.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import RoleEnum, require_any_role, require_roles
from app.core.project_access import resolve_project_access, resolve_task_access
from app.database import get_db
from app.models.task import Task
from app.models.user import User
from app.exceptions import InsufficientPermissionsException
from app.schemas.project import (
    DiscussionCreate, DiscussionResponse, DocumentResponse, TaskAssign, TaskMutationResponse, TaskResponse, TaskStatusUpdate, TaskUpdate,
)
from app.services import project_service as svc
from app.services.github_service import GitHubClient, get_github_client, require_github

router = APIRouter(prefix="/tasks", tags=["Tasks"], dependencies=[Depends(require_any_role)])


@router.get("/mine", response_model=list[TaskResponse], summary="Tasks assigned to me, across projects")
async def my_tasks(
    include_closed: bool = False,
    user: User = Depends(require_roles(RoleEnum.EMPLOYEE)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Task).where(Task.assigned_to_user_id == user.id, Task.deleted_at.is_(None),
                              Task.project_id.is_not(None))
    if not include_closed:
        stmt = stmt.where(Task.status.notin_(["Completed", "Cancelled"]))
    tasks = (await db.execute(stmt.order_by(Task.due_date.asc().nulls_last(), Task.id))).scalars().all()
    out, access_by_project = [], {}
    for t in tasks:
        if t.project_id not in access_by_project:
            access_by_project[t.project_id] = await resolve_project_access(db, user, t.project_id)
        out.append(svc.task_dict(await svc.load_task(db, t.id), access_by_project[t.project_id]))
    return out


@router.get("/health-summary", summary="Task Health Score totals (Admin)")
async def task_health_summary(
    _: User = Depends(require_roles(RoleEnum.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    tasks = (await db.execute(
        select(Task).where(Task.deleted_at.is_(None), Task.status.notin_(["Completed", "Cancelled"]))
    )).scalars().all()
    counts = {"Green": 0, "Yellow": 0, "Red": 0}
    at_risk = []
    for t in tasks:
        score = t.health_score or "Green"
        counts[score] = counts.get(score, 0) + 1
        if score in ("Yellow", "Red"):
            at_risk.append({"id": t.id, "title": t.title, "project_id": t.project_id,
                            "health_score": score, "health_reason": t.health_reason,
                            "due_date": t.due_date, "status": t.status})
    return {"summary": counts, "total_tasks": len(tasks), "at_risk_tasks": at_risk}


@router.post("/compute-health", summary="Recompute Task Health Scores (Admin)")
async def compute_health(_: User = Depends(require_roles(RoleEnum.ADMIN))):
    """On demand; no auto-escalation (CORE.md §8). Phase 7 folds this into the nightly sweep."""
    from app.tasks import compute_task_health_and_escalate
    return {"job_id": compute_task_health_and_escalate.delay().id}


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, user: User = Depends(require_any_role), db: AsyncSession = Depends(get_db)):
    task, access = await resolve_task_access(db, user, task_id)
    return svc.task_dict(await svc.load_task(db, task.id), access)


@router.patch("/{task_id}", response_model=TaskResponse, summary="Edit task details (Project Manager)")
async def update_task(
    task_id: int,
    data: TaskUpdate,
    user: User = Depends(require_any_role),
    db: AsyncSession = Depends(get_db),
):
    """Details only — status has its own endpoint so completion authority has one door."""
    task, access = await resolve_task_access(db, user, task_id)
    access.require_project_manager()
    return svc.task_dict(await svc.update_task(db, access, task, data), access)


@router.patch("/{task_id}/assign", response_model=TaskMutationResponse,
              summary="Assign or unassign a Member (Project Manager)")
async def assign_task(
    task_id: int,
    data: TaskAssign,
    user: User = Depends(require_any_role),
    github: GitHubClient | None = Depends(get_github_client),
    db: AsyncSession = Depends(get_db),
):
    task, access = await resolve_task_access(db, user, task_id)
    access.require_project_manager()
    task, warnings = await svc.assign_task(db, access, task, data.assigned_to_user_id, require_github(github))
    return {"task": svc.task_dict(task, access), "warnings": warnings}


@router.patch("/{task_id}/status", response_model=TaskResponse, summary="Change status — assignee or Project Manager")
async def update_task_status(
    task_id: int,
    data: TaskStatusUpdate,
    user: User = Depends(require_any_role),
    github: GitHubClient | None = Depends(get_github_client),
    db: AsyncSession = Depends(get_db),
):
    task, access = await resolve_task_access(db, user, task_id)
    return svc.task_dict(await svc.set_status(db, access, task, data.status, github), access)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a task and close its issue as not planned (Project Manager)")
async def delete_task(
    task_id: int,
    user: User = Depends(require_any_role),
    github: GitHubClient | None = Depends(get_github_client),
    db: AsyncSession = Depends(get_db),
):
    task, access = await resolve_task_access(db, user, task_id)
    access.require_project_manager()
    await svc.delete_task(db, access, task, github)


@router.get("/{task_id}/progress-doc", response_model=DocumentResponse,
            summary="The task's AI-written plan and checklist, read from the repository")
async def get_task_progress_doc(
    task_id: int,
    user: User = Depends(require_any_role),
    github: GitHubClient | None = Depends(get_github_client),
    db: AsyncSession = Depends(get_db),
):
    from app.services import ai_jobs
    task, access = await resolve_task_access(db, user, task_id)
    if not task.task_progress_doc:
        return {"kind": "task", "url": None, "content": None}
    content = await ai_jobs.read_document(require_github(github), access.project, ai_jobs.task_doc_path(task.id))
    return {"kind": "task", "url": task.task_progress_doc, "content": content}


# ── Discussions (PROJECT.md §11.6) ───────────────────────────────

async def _discussion_access(db: AsyncSession, user: User, task_id: int):
    task, access = await resolve_task_access(db, user, task_id)
    if not access.may_discuss(task):
        raise InsufficientPermissionsException()
    return task, access


@router.get("/{task_id}/discussions", response_model=list[DiscussionResponse],
            summary="The task's discussion — assignee, assigner, Project Managers, owning Manager")
async def list_discussions(task_id: int, user: User = Depends(require_any_role), db: AsyncSession = Depends(get_db)):
    task, _ = await _discussion_access(db, user, task_id)
    return await svc.list_discussions(db, task)


@router.post("/{task_id}/discussions", response_model=DiscussionResponse, status_code=status.HTTP_201_CREATED,
             summary="Post a message or a reply; the other participants are notified")
async def post_discussion(task_id: int, data: DiscussionCreate, user: User = Depends(require_any_role),
                          db: AsyncSession = Depends(get_db)):
    task, access = await _discussion_access(db, user, task_id)
    return await svc.post_discussion(db, access, task, data.message, data.parent_id)
