"""
TRACE - Projects API (Phase 3 — the manual path, no AI)

Two-layer authorisation: platform role on the route, then the caller's project
role from app.core.project_access. PROJECT.md §6–7, §11; CORE.md §4, §7.
"""

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import RoleEnum, require_any_role, require_roles
from app.core.project_access import (
    MEMBER, PROJECT_MANAGER, ProjectAccess, resolve_project_access,
)
from app.database import get_db
from app.exceptions import NotFoundException, TraceException
from app.models.project import ProjectAssignment, ProjectSourceFile, TaskGroup
from app.models.task import Task
from app.models.user import User
from app.schemas.project import (
    ActivityItem, AssigneeSuggestionRequest, AssignmentResponse, AssignProjectManager, DocumentKind,
    DocumentResponse, DocumentSaved, DocumentUpdate, EvaluationStatus, JobQueued, PersonBrief, ProjectCreate,
    ProjectDetail, ProjectSummary, ProjectUpdate, RemovalResponse, SourceFileUploadResponse, TaskCreate,
    TaskGroupCreate, TaskGroupResponse, TaskGroupUpdate, TaskMutationResponse, TaskResponse,
)
from app.schemas.gantt import GanttResponse, GanttVersionBrief, ProjectTree
from app.services import ai_jobs, ai_service, gantt_service, jobs, project_report
from app.services import project_service as svc
from app.services.extraction import (
    MAX_SOURCE_FILE_BYTES, UnsupportedFile, extension_of, extract_text,
)
from app.services.github_service import GitHubClient, get_github_client, require_github, resolve_owner
from app.services.storage import ObjectStorage, get_storage

router = APIRouter(prefix="/projects", tags=["Projects"], dependencies=[Depends(require_any_role)])


async def project_access(
    project_id: int,
    user: User = Depends(require_any_role),
    db: AsyncSession = Depends(get_db),
) -> ProjectAccess:
    return await resolve_project_access(db, user, project_id)


# ══════════════════════════════════════════════════════════════════
#  PROJECTS
# ══════════════════════════════════════════════════════════════════

@router.get("", response_model=list[ProjectSummary], summary="Projects visible to the caller")
async def list_projects(user: User = Depends(require_any_role), db: AsyncSession = Depends(get_db)):
    projects, my_roles = await svc.visible_projects(db, user)
    return await svc.summarize(db, projects, my_roles)


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED,
             summary="Create a project and its GitHub repository (Manager)")
async def create_project(
    data: ProjectCreate,
    user: User = Depends(require_roles(RoleEnum.MANAGER)),
    github: GitHubClient | None = Depends(get_github_client),
    db: AsyncSession = Depends(get_db),
):
    """The repository is public and named after the project; a name clash is a 409, never reused."""
    github = require_github(github)
    project = await svc.create_project(db, user, data, github, await resolve_owner(db))
    return await svc.project_detail(db, await resolve_project_access(db, user, project.id))


@router.get("/activity", response_model=list[ActivityItem], summary="Recent task activity")
async def recent_activity(
    limit: int = 15,
    user: User = Depends(require_any_role),
    db: AsyncSession = Depends(get_db),
):
    projects, _ = await svc.visible_projects(db, user)
    if not projects:
        return []
    names = {p.id: p.name for p in projects}
    rows = (await db.execute(
        select(Task).where(Task.project_id.in_(list(names)), Task.deleted_at.is_(None))
        .order_by(func.coalesce(Task.updated_at, Task.created_at).desc()).limit(min(limit, 50))
    )).scalars().all()
    out = []
    for t in rows:
        t = await svc.load_task(db, t.id)
        out.append({"task_id": t.id, "task_title": t.title, "project_id": t.project_id,
                    "project_name": names[t.project_id], "status": t.status,
                    "assigned_to": svc.person(t.assigned_to_user),
                    "updated_at": t.updated_at or t.created_at})
    return out


@router.get("/report", summary="Download the project → task group → task report for a date range (CSV)",
            response_class=Response, responses={200: {"content": {"text/csv": {}}}})
async def download_report(
    start: date,
    end: date,
    project_id: int | None = None,
    user: User = Depends(require_roles(RoleEnum.MANAGER, RoleEnum.EMPLOYEE)),
    db: AsyncSession = Depends(get_db),
):
    """PLANNING.md Q7: from the Manager and Employee dashboards; every project the caller sees, or one."""
    if end < start:
        raise TraceException(422, "The end date is before the start date")
    if project_id is not None:
        projects = [(await resolve_project_access(db, user, project_id)).project]
    else:
        projects, _ = await svc.visible_projects(db, user)
    body = project_report.to_csv(await project_report.report_rows(db, projects, start, end))
    name = f"trace-report-{start.isoformat()}-to-{end.isoformat()}.csv"
    return Response(body, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(access: ProjectAccess = Depends(project_access), db: AsyncSession = Depends(get_db)):
    return await svc.project_detail(db, access)


@router.patch("/{project_id}", response_model=ProjectDetail, summary="Edit project details (owner)")
async def update_project(
    data: ProjectUpdate,
    access: ProjectAccess = Depends(project_access),
    db: AsyncSession = Depends(get_db),
):
    access.require_owner()
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(access.project, field, value)
    await db.commit()
    return await svc.project_detail(db, access)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a project and archive its repository (owner)")
async def delete_project(
    access: ProjectAccess = Depends(project_access),
    github: GitHubClient | None = Depends(get_github_client),
    db: AsyncSession = Depends(get_db),
):
    """Refused while tasks are open. The repository is archived, not deleted — its name stays taken."""
    access.require_owner()
    open_tasks = (await db.execute(
        select(func.count(Task.id)).where(Task.project_id == access.project.id, Task.deleted_at.is_(None),
                                          Task.status.notin_(["Completed", "Cancelled"]))
    )).scalar()
    if open_tasks:
        raise TraceException(409, f"{open_tasks} open task(s) — archive the project instead, or close them first")
    from app.services.system_settings import resolve_setting
    await svc.delete_project(db, access.project, github, await resolve_setting(db, "github", "owner"))


# ══════════════════════════════════════════════════════════════════
#  SOURCE FILES  (MinIO + text extraction)
# ══════════════════════════════════════════════════════════════════

@router.post("/{project_id}/source-files", response_model=SourceFileUploadResponse,
             status_code=status.HTTP_201_CREATED, summary="Upload requirement documents (owner)")
async def upload_source_files(
    files: list[UploadFile] = File(...),
    access: ProjectAccess = Depends(project_access),
    storage: ObjectStorage = Depends(get_storage),
    db: AsyncSession = Depends(get_db),
):
    """Each file is stored and extracted independently; rejects are reported, never silently dropped."""
    import asyncio

    access.require_owner()
    uploaded, rejected = [], []
    for upload in files:
        name = upload.filename or "unnamed"
        data = await upload.read()
        if not data:
            rejected.append({"file_name": name, "reason": "empty file"})
            continue
        if len(data) > MAX_SOURCE_FILE_BYTES:
            rejected.append({"file_name": name, "reason": f"larger than {MAX_SOURCE_FILE_BYTES // 2**20} MB"})
            continue
        try:
            text = await asyncio.to_thread(extract_text, name, data)
        except UnsupportedFile as exc:
            rejected.append({"file_name": name, "reason": str(exc).split(": ", 1)[-1]})
            continue
        key = f"projects/{access.project.id}/source/{uuid.uuid4().hex}{extension_of(name)}"
        await storage.put(key, data, upload.content_type or "application/octet-stream")
        row = ProjectSourceFile(
            project_id=access.project.id, file_name=name, storage_key=key,
            content_type=upload.content_type, size_bytes=len(data), extracted_text=text,
            uploaded_by_user_id=access.user.id,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)  # created_at is a server default
        uploaded.append(svc.source_file_dict(row))
    await db.commit()
    return {"uploaded": uploaded, "rejected": rejected}


@router.delete("/{project_id}/source-files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source_file(
    file_id: int,
    access: ProjectAccess = Depends(project_access),
    storage: ObjectStorage = Depends(get_storage),
    db: AsyncSession = Depends(get_db),
):
    access.require_owner()
    row = (await db.execute(
        select(ProjectSourceFile).where(ProjectSourceFile.id == file_id,
                                        ProjectSourceFile.project_id == access.project.id,
                                        ProjectSourceFile.deleted_at.is_(None))
    )).scalar_one_or_none()
    if row is None:
        raise NotFoundException("Source file")
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    await storage.delete(row.storage_key)


# ══════════════════════════════════════════════════════════════════
#  TEAM  (project_assignments)
# ══════════════════════════════════════════════════════════════════

@router.get("/{project_id}/assignments", response_model=list[AssignmentResponse])
async def list_assignments(access: ProjectAccess = Depends(project_access), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(ProjectAssignment, User).join(User, User.id == ProjectAssignment.user_id)
        .where(ProjectAssignment.project_id == access.project.id, ProjectAssignment.deleted_at.is_(None))
        .order_by(ProjectAssignment.project_role, User.name)
    )).all()
    open_counts = dict((await db.execute(
        select(Task.assigned_to_user_id, func.count(Task.id))
        .where(Task.project_id == access.project.id, Task.deleted_at.is_(None),
               Task.status.in_(svc.OPEN_STATUSES))
        .group_by(Task.assigned_to_user_id)
    )).all())
    return [{"user": svc.person(u), "project_role": a.project_role,
             "open_tasks": open_counts.get(u.id, 0), "assigned_at": a.created_at} for a, u in rows]


@router.post("/{project_id}/assignments", response_model=AssignmentResponse,
             status_code=status.HTTP_201_CREATED, summary="Assign a Project Manager (owner)")
async def assign_project_manager(
    data: AssignProjectManager,
    access: ProjectAccess = Depends(project_access),
    github: GitHubClient | None = Depends(get_github_client),
    db: AsyncSession = Depends(get_db),
):
    """Also invites them to the project's repository with Write; a GitHub problem is a warning."""
    access.require_owner()
    employee = await svc.active_employee(db, data.user_id)
    row = (await db.execute(
        select(ProjectAssignment).where(ProjectAssignment.project_id == access.project.id,
                                        ProjectAssignment.user_id == employee.id)
    )).scalar_one_or_none()
    if row is None:
        row = ProjectAssignment(project_id=access.project.id, user_id=employee.id)
        db.add(row)
    elif row.project_role == PROJECT_MANAGER and row.deleted_at is None:
        raise TraceException(409, f"{employee.name} is already a Project Manager on this project")
    row.project_role, row.deleted_at, row.assigned_by_user_id = PROJECT_MANAGER, None, access.user.id
    warnings = await svc.grant_repo_access(github, access.project, employee)
    await db.commit()
    await db.refresh(row)
    return {"user": svc.person(employee), "project_role": PROJECT_MANAGER, "open_tasks": 0,
            "assigned_at": row.created_at, "warnings": warnings}


@router.delete("/{project_id}/assignments/{user_id}", response_model=RemovalResponse,
               summary="Remove a Project Manager (owner)")
async def remove_project_manager(
    user_id: int,
    access: ProjectAccess = Depends(project_access),
    github: GitHubClient | None = Depends(get_github_client),
    db: AsyncSession = Depends(get_db),
):
    """A removed PM who still holds tasks here stays on as a Member; otherwise they leave the
    project, and their repository access (or pending invitation) is revoked."""
    access.require_owner()
    row = (await db.execute(
        select(ProjectAssignment).where(ProjectAssignment.project_id == access.project.id,
                                        ProjectAssignment.user_id == user_id,
                                        ProjectAssignment.project_role == PROJECT_MANAGER,
                                        ProjectAssignment.deleted_at.is_(None))
    )).scalar_one_or_none()
    if row is None:
        raise NotFoundException("Project Manager assignment")
    holds_tasks = (await db.execute(
        select(func.count(Task.id)).where(Task.project_id == access.project.id,
                                          Task.assigned_to_user_id == user_id, Task.deleted_at.is_(None))
    )).scalar()
    warnings = []
    if holds_tasks:
        row.project_role = MEMBER
    else:
        row.deleted_at = datetime.now(timezone.utc)
        warnings = await svc.revoke_repo_access(github, access.project, await db.get(User, user_id))
    await db.commit()
    return {"project_role": MEMBER if holds_tasks else None, "warnings": warnings}


@router.get("/{project_id}/candidates", response_model=list[PersonBrief],
            summary="Employees who can be given a role or a task here")
async def list_candidates(access: ProjectAccess = Depends(project_access), db: AsyncSession = Depends(get_db)):
    """For the owner's PM picker and the Project Manager's assignee picker; AI ranking is the suggest-* jobs."""
    if not (access.is_owner or access.is_project_manager):
        from app.exceptions import InsufficientPermissionsException
        raise InsufficientPermissionsException()
    return [svc.person(u) for u in await svc.active_employees(db)]


# ══════════════════════════════════════════════════════════════════
#  TASK GROUPS
# ══════════════════════════════════════════════════════════════════

async def _group_dicts(db: AsyncSession, groups: list[TaskGroup]) -> list[dict]:
    ids = [g.id for g in groups]
    counts = {gid: (0, 0) for gid in ids}
    if ids:
        from sqlalchemy import case
        for gid, total, done in (await db.execute(
            select(Task.task_group_id, func.count(Task.id), func.count(case((Task.status == "Completed", 1))))
            .where(Task.task_group_id.in_(ids), Task.deleted_at.is_(None), Task.status != "Cancelled")
            .group_by(Task.task_group_id)
        )).all():
            counts[gid] = (total, done)
    return [{
        "id": g.id, "project_id": g.project_id, "name": g.name, "description": g.description,
        "sequence": g.sequence, "estimated_duration_days": g.estimated_duration_days,
        "planned_start_date": g.planned_start_date, "planned_end_date": g.planned_end_date,
        "completion_percentage": float(g.completion_percentage or 0), "status": g.status,
        "created_by": g.created_by, "total_tasks": counts[g.id][0], "completed_tasks": counts[g.id][1],
    } for g in groups]


@router.get("/{project_id}/task-groups", response_model=list[TaskGroupResponse])
async def list_task_groups(access: ProjectAccess = Depends(project_access), db: AsyncSession = Depends(get_db)):
    groups = (await db.execute(
        select(TaskGroup).where(TaskGroup.project_id == access.project.id, TaskGroup.deleted_at.is_(None))
        .order_by(TaskGroup.sequence, TaskGroup.id)
    )).scalars().all()
    return await _group_dicts(db, list(groups))


@router.post("/{project_id}/task-groups", response_model=TaskGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_task_group(
    data: TaskGroupCreate,
    access: ProjectAccess = Depends(project_access),
    db: AsyncSession = Depends(get_db),
):
    access.require_project_manager()
    values = data.model_dump()
    if values["sequence"] is None:
        values["sequence"] = ((await db.execute(
            select(func.max(TaskGroup.sequence)).where(TaskGroup.project_id == access.project.id,
                                                       TaskGroup.deleted_at.is_(None))
        )).scalar() or 0) + 1
    group = TaskGroup(project_id=access.project.id, created_by="Human", status="Pending",
                      completion_percentage=0, **values)
    db.add(group)
    await db.commit()
    return (await _group_dicts(db, [group]))[0]


@router.patch("/{project_id}/task-groups/{group_id}", response_model=TaskGroupResponse)
async def update_task_group(
    group_id: int,
    data: TaskGroupUpdate,
    access: ProjectAccess = Depends(project_access),
    db: AsyncSession = Depends(get_db),
):
    access.require_project_manager()
    group = await svc.group_in_project(db, access.project.id, group_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(group, field, value)
    await db.commit()
    return (await _group_dicts(db, [group]))[0]


@router.delete("/{project_id}/task-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_group(
    group_id: int,
    access: ProjectAccess = Depends(project_access),
    db: AsyncSession = Depends(get_db),
):
    access.require_project_manager()
    group = await svc.group_in_project(db, access.project.id, group_id)
    has_tasks = (await db.execute(
        select(func.count(Task.id)).where(Task.task_group_id == group.id, Task.deleted_at.is_(None))
    )).scalar()
    if has_tasks:
        raise TraceException(409, "Move or delete this group's tasks first")
    group.deleted_at = datetime.now(timezone.utc)
    await db.commit()


# ══════════════════════════════════════════════════════════════════
#  TASKS (project-scoped list + create)
# ══════════════════════════════════════════════════════════════════

@router.get("/{project_id}/tasks", response_model=list[TaskResponse])
async def list_project_tasks(
    task_group_id: int | None = None,
    mine: bool = False,
    access: ProjectAccess = Depends(project_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Task.id).where(Task.project_id == access.project.id, Task.deleted_at.is_(None))
    if task_group_id is not None:
        stmt = stmt.where(Task.task_group_id == task_group_id)
    if mine:
        stmt = stmt.where(Task.assigned_to_user_id == access.user.id)
    ids = (await db.execute(stmt.order_by(Task.due_date.asc().nulls_last(), Task.id))).scalars().all()
    return [svc.task_dict(await svc.load_task(db, i), access) for i in ids]


@router.post("/{project_id}/tasks", response_model=TaskMutationResponse, status_code=status.HTTP_201_CREATED,
             summary="Create a task — and its GitHub issue (Project Manager)")
async def create_project_task(
    data: TaskCreate,
    access: ProjectAccess = Depends(project_access),
    github: GitHubClient | None = Depends(get_github_client),
    db: AsyncSession = Depends(get_db),
):
    access.require_project_manager()
    task, warnings = await svc.create_task(db, access, data, require_github(github))
    return {"task": svc.task_dict(task, access), "warnings": warnings}


# ══════════════════════════════════════════════════════════════════
#  VISUALISATION (Phase 4) — read-only for everyone who sees the project
# ══════════════════════════════════════════════════════════════════

@router.get("/{project_id}/tree", response_model=ProjectTree,
            summary="Project → task groups → tasks → assignees, for the graph view")
async def get_project_tree(access: ProjectAccess = Depends(project_access), db: AsyncSession = Depends(get_db)):
    return await gantt_service.project_tree(db, access.project)


@router.get("/{project_id}/gantt", response_model=GanttResponse | None,
            summary="The latest Gantt version (or ?version=N); null before the first one")
async def get_gantt(
    version: int | None = None,
    access: ProjectAccess = Depends(project_access),
    db: AsyncSession = Depends(get_db),
):
    rows = await gantt_service.versions(db, access.project.id)
    if not rows:
        if version is not None:
            raise NotFoundException("Gantt version")
        return None
    row = rows[0] if version is None else next((r for r in rows if r.version == version), None)
    if row is None:
        raise NotFoundException("Gantt version")
    return {"version": row.version, "generated_reason": row.generated_reason, "generated_at": row.generated_at,
            "chart_data": row.chart_data, "latest_version": rows[0].version}


@router.get("/{project_id}/gantt/versions", response_model=list[GanttVersionBrief],
            summary="Gantt version history, newest first")
async def list_gantt_versions(access: ProjectAccess = Depends(project_access), db: AsyncSession = Depends(get_db)):
    return [{"version": r.version, "generated_reason": r.generated_reason, "generated_at": r.generated_at}
            for r in await gantt_service.versions(db, access.project.id)]


# ══════════════════════════════════════════════════════════════════
#  AI PIPELINE (Phase 5) — every route enqueues and returns a job id
#  (CORE.md §2 rule 1); nothing here awaits the model.
# ══════════════════════════════════════════════════════════════════

async def _require_ai(db: AsyncSession) -> None:
    if not ai_service.ai_configured():
        raise ai_service.AINotConfigured()


def _enqueue_or_503(name: str, *args) -> str:
    try:
        return jobs.enqueue(name, *args)
    except Exception as exc:  # broker down — say so instead of leaving a job that never runs
        raise TraceException(503, f"The job queue is unavailable ({exc.__class__.__name__}); try again shortly") from exc


@router.post("/{project_id}/evaluate", response_model=JobQueued, status_code=status.HTTP_202_ACCEPTED,
             summary="Evaluate Project — source files → documents, task groups, Gantt v1 (owner)")
async def evaluate_project(
    access: ProjectAccess = Depends(project_access),
    github: GitHubClient | None = Depends(get_github_client),
    db: AsyncSession = Depends(get_db),
):
    """CORE.md §3. Refused while running, without source text, or once the project has tasks."""
    access.require_owner()
    await _require_ai(db)
    require_github(github)
    project = access.project
    if project.status == "Evaluating":
        raise TraceException(409, "This project is already being evaluated")
    has_text = (await db.execute(select(func.count(ProjectSourceFile.id)).where(
        ProjectSourceFile.project_id == project.id, ProjectSourceFile.deleted_at.is_(None),
        func.length(func.coalesce(ProjectSourceFile.extracted_text, "")) > 0,
    ))).scalar()
    if not has_text:
        raise TraceException(409, "Upload at least one requirement document with readable text first")
    if (await db.execute(select(func.count(Task.id)).where(
            Task.project_id == project.id, Task.deleted_at.is_(None)))).scalar():
        raise TraceException(409, "This project already has tasks, so evaluating it again would replace task "
                                  "groups that hold work. Edit the project document instead — it re-plans the Gantt")

    previous = project.status
    project.status = "Evaluating"
    ai_jobs.set_ai_error(project, "evaluate_project", None)
    await db.commit()
    try:
        return {"job_id": jobs.enqueue("evaluate_project", project.id)}
    except Exception as exc:
        project.status = previous
        ai_jobs.set_ai_error(project, "evaluate_project", f"Could not queue the evaluation ({exc.__class__.__name__})")
        await db.commit()
        raise TraceException(503, "The job queue is unavailable; try again shortly") from exc


@router.get("/{project_id}/evaluate/status", response_model=EvaluationStatus,
            summary="Evaluation state: idle, running or failed (with the reason)")
async def evaluation_status(access: ProjectAccess = Depends(project_access)):
    project = access.project
    error = (project.ai_errors or {}).get("evaluate_project")
    state = "running" if project.status == "Evaluating" else "failed" if error else "idle"
    return {"state": state, "error": error["message"] if error else None,
            "project_status": project.status, "last_evaluated_at": project.last_evaluated_at}


@router.post("/{project_id}/suggest-managers", response_model=JobQueued, status_code=status.HTTP_202_ACCEPTED,
             summary="AI-ranked Project Manager candidates (owner) — poll /services/task/{job_id}/result")
async def suggest_managers(access: ProjectAccess = Depends(project_access), db: AsyncSession = Depends(get_db)):
    """Suggestions only — the owner still appoints (CORE.md §2 rule 3)."""
    access.require_owner()
    await _require_ai(db)
    return {"job_id": _enqueue_or_503("suggest_managers", access.project.id)}


@router.post("/{project_id}/tasks/suggest-assignees", response_model=JobQueued,
             status_code=status.HTTP_202_ACCEPTED,
             summary="AI-ranked assignees for a draft task (Project Manager)")
async def suggest_assignees(
    data: AssigneeSuggestionRequest,
    access: ProjectAccess = Depends(project_access),
    db: AsyncSession = Depends(get_db),
):
    access.require_project_manager()
    await _require_ai(db)
    return {"job_id": _enqueue_or_503("suggest_assignees", access.project.id, data.title, data.description)}


@router.post("/{project_id}/task-groups/{group_id}/suggest-tasks", response_model=JobQueued,
             status_code=status.HTTP_202_ACCEPTED, summary="AI-suggested tasks for a task group (Project Manager)")
async def suggest_tasks(
    group_id: int,
    access: ProjectAccess = Depends(project_access),
    db: AsyncSession = Depends(get_db),
):
    access.require_project_manager()
    await svc.group_in_project(db, access.project.id, group_id)
    await _require_ai(db)
    return {"job_id": _enqueue_or_503("suggest_tasks", group_id)}


@router.post("/{project_id}/gantt/reevaluate", response_model=JobQueued, status_code=status.HTTP_202_ACCEPTED,
             summary="Re-plan the Gantt now (Project Manager)")
async def reevaluate_gantt(access: ProjectAccess = Depends(project_access)):
    access.require_project_manager()
    try:
        return {"job_id": gantt_service.request_reevaluation(access.project.id, "manual", manual=True)}
    except Exception as exc:
        raise TraceException(503, "The job queue is unavailable; try again shortly") from exc


@router.post("/{project_id}/progress-report", response_model=JobQueued, status_code=status.HTTP_202_ACCEPTED,
             summary="Rewrite the progress document and report now (owner or Project Manager)")
async def refresh_progress_report(
    access: ProjectAccess = Depends(project_access),
    github: GitHubClient | None = Depends(get_github_client),
    db: AsyncSession = Depends(get_db),
):
    if not (access.is_owner or access.is_project_manager):
        from app.exceptions import InsufficientPermissionsException
        raise InsufficientPermissionsException()
    await _require_ai(db)
    require_github(github)
    return {"job_id": _enqueue_or_503("update_project_progress_doc", access.project.id)}


# ── Project documents (CORE.md §10) ──────────────────────────────

@router.get("/{project_id}/documents/{kind}", response_model=DocumentResponse,
            summary="A project document's markdown, read from the repository")
async def get_document(
    kind: DocumentKind,
    access: ProjectAccess = Depends(project_access),
    github: GitHubClient | None = Depends(get_github_client),
):
    project = access.project
    url = getattr(project, ai_jobs.DOC_COLUMNS[kind])
    if not url:
        return {"kind": kind, "url": None, "content": None}
    content = await ai_jobs.read_document(require_github(github), project, ai_jobs.DOC_PATHS[kind])
    return {"kind": kind, "url": url, "content": content}


@router.put("/{project_id}/documents/doc", response_model=DocumentSaved,
            summary="Save the project document (Project Manager) — re-plans the Gantt when it changed")
async def save_project_doc(
    data: DocumentUpdate,
    access: ProjectAccess = Depends(project_access),
    github: GitHubClient | None = Depends(get_github_client),
    db: AsyncSession = Depends(get_db),
):
    access.require_project_manager()
    project, github = access.project, require_github(github)
    if not project.project_doc:
        raise TraceException(409, "There is no project document yet — the project has to be evaluated first")
    current = await ai_jobs.read_document(github, project, ai_jobs.DOC_PATHS["doc"])
    content = data.content if data.content.endswith("\n") else data.content + "\n"
    if current is not None and current.strip() == content.strip():
        return {"kind": "doc", "url": project.project_doc, "content": current, "changed": False}
    project.project_doc = await github.commit_file(
        project.github_repo, ai_jobs.DOC_PATHS["doc"], content,
        f"TRACE: docs/project_doc.md (edited by {access.user.name})", project.github_default_branch)
    await db.commit()
    gantt_service.request_reevaluation(project.id, "project_doc_updated")  # CORE.md §5
    return {"kind": "doc", "url": project.project_doc, "content": content, "changed": True}
