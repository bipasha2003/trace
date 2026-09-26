"""
TRACE - Project and task service (Phase 3, no AI)

Holds the rules the routers share: project creation with its GitHub repository,
project summaries and stats, repository access for the people on a project, the
task ↔ GitHub issue lifecycle, task-group roll-ups, and Member creation on first
assignment.
Authorisation is decided before these are called (app.core.project_access).
"""

from datetime import date, datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.project_access import MEMBER, PROJECT_MANAGER, ProjectAccess, platform_roles
from app.exceptions import NotFoundException, TraceException
from app.models.project import Notification, Project, ProjectAssignment, ProjectSourceFile, TaskGroup
from app.models.task import Task
from app.models.user import User, UserRole
from app.services import jobs
from app.services.github_service import GitHubClient, GitHubError, repo_slug

OPEN_STATUSES = ("Pending", "In Progress", "In Review", "Blocked", "Overdue")


def person(user: User | None) -> dict | None:
    if user is None:
        return None
    return {"id": user.id, "name": user.name, "email": user.email,
            "github_username": user.github_username}


# ── Projects ─────────────────────────────────────────────────────

async def create_project(db: AsyncSession, user: User, data, github: GitHubClient, owner: str) -> Project:
    """TRACE creates the project's public repository itself (CORE.md §4.1): both exist, or neither."""
    slug = repo_slug(data.name)
    if not slug:
        raise TraceException(422, "The project name needs at least one letter or digit to name its repository")
    repo = await github.create_repo(owner, slug, data.description)  # before any row exists
    project = Project(created_by_user_id=user.id, status="Draft", name=data.name,
                      description=data.description, start_date=data.start_date, end_date=data.end_date,
                      github_repo=repo.full_name, github_default_branch=repo.default_branch)
    db.add(project)
    await db.commit()
    return project


async def delete_project(db: AsyncSession, project: Project, github: GitHubClient | None, owner: str) -> None:
    """Soft-delete the project and archive its repository — together or not at all.

    Only a repository under the configured organization is archived: one entered by hand
    before Phase 3a may belong to someone else, and is left alone.
    """
    repo = project.github_repo
    if repo and owner and repo.split("/")[0].lower() == owner.lower():
        from app.services.github_service import require_github
        await require_github(github).archive_repo(repo)  # before the row changes
    project.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def project_stats(db: AsyncSession, project_ids: list[int]) -> dict[int, dict]:
    if not project_ids:
        return {}
    today = date.today()
    live = (Task.deleted_at.is_(None), Task.status != "Cancelled")
    rows = (await db.execute(
        select(
            Task.project_id,
            func.count(Task.id),
            func.count(case((Task.status == "Completed", 1))),
            func.count(case((
                (Task.status == "Overdue")
                | ((Task.due_date < today) & Task.status.in_(OPEN_STATUSES)), 1,
            ))),
        ).where(Task.project_id.in_(project_ids), *live).group_by(Task.project_id)
    )).all()
    groups = dict((await db.execute(
        select(TaskGroup.project_id, func.count(TaskGroup.id))
        .where(TaskGroup.project_id.in_(project_ids), TaskGroup.deleted_at.is_(None))
        .group_by(TaskGroup.project_id)
    )).all())
    stats = {pid: {"task_groups": groups.get(pid, 0), "total_tasks": 0, "completed_tasks": 0,
                   "overdue_tasks": 0, "completion_percentage": 0.0} for pid in project_ids}
    for pid, total, completed, overdue in rows:
        stats[pid].update(total_tasks=total, completed_tasks=completed, overdue_tasks=overdue,
                          completion_percentage=round(completed / total * 100, 1) if total else 0.0)
    return stats


async def project_managers(db: AsyncSession, project_ids: list[int]) -> dict[int, list[dict]]:
    result = {pid: [] for pid in project_ids}
    if not project_ids:
        return result
    rows = (await db.execute(
        select(ProjectAssignment.project_id, User)
        .join(User, User.id == ProjectAssignment.user_id)
        .where(ProjectAssignment.project_id.in_(project_ids),
               ProjectAssignment.project_role == PROJECT_MANAGER,
               ProjectAssignment.deleted_at.is_(None))
        .order_by(User.name)
    )).all()
    for pid, user in rows:
        result[pid].append(person(user))
    return result


def is_at_risk(project: Project, stats: dict) -> bool:
    if project.status in ("Completed", "Archived"):
        return False
    past_end = project.end_date is not None and project.end_date < date.today()
    return stats["overdue_tasks"] > 0 or (past_end and stats["completion_percentage"] < 100)


async def visible_projects(db: AsyncSession, user: User) -> tuple[list[Project], dict[int, str]]:
    """Projects the caller may see, plus their project role in each (Employees)."""
    roles = platform_roles(user)
    stmt = select(Project).where(Project.deleted_at.is_(None)).options(selectinload(Project.created_by))
    my_roles: dict[int, str] = {}
    if "Admin" in roles:
        pass
    elif "Manager" in roles:
        stmt = stmt.where(Project.created_by_user_id == user.id)
    else:
        assignments = (await db.execute(
            select(ProjectAssignment.project_id, ProjectAssignment.project_role).where(
                ProjectAssignment.user_id == user.id, ProjectAssignment.deleted_at.is_(None))
        )).all()
        my_roles = dict(assignments)
        stmt = stmt.where(Project.id.in_(list(my_roles) or [-1]))
    projects = (await db.execute(stmt.order_by(Project.created_at.desc()))).scalars().all()
    return list(projects), my_roles


async def summarize(db: AsyncSession, projects: list[Project], my_roles: dict[int, str]) -> list[dict]:
    ids = [p.id for p in projects]
    stats, pms = await project_stats(db, ids), await project_managers(db, ids)
    return [{
        "id": p.id, "name": p.name, "description": p.description, "status": p.status,
        "github_repo": p.github_repo, "start_date": p.start_date, "end_date": p.end_date,
        "created_at": p.created_at, "owner": person(p.created_by),
        "project_managers": pms[p.id], "my_role": my_roles.get(p.id),
        "stats": stats[p.id], "at_risk": is_at_risk(p, stats[p.id]),
    } for p in projects]


def source_file_dict(f: ProjectSourceFile) -> dict:
    return {"id": f.id, "file_name": f.file_name, "content_type": f.content_type,
            "size_bytes": f.size_bytes, "extracted_chars": len(f.extracted_text or ""),
            "uploaded_at": f.created_at}


async def project_detail(db: AsyncSession, access: ProjectAccess) -> dict:
    project = (await db.execute(
        select(Project).where(Project.id == access.project.id)
        .options(selectinload(Project.created_by), selectinload(Project.source_files))
    )).scalar_one()
    my_role = {project.id: access.project_role} if access.project_role else {}
    summary = (await summarize(db, [project], my_role))[0]
    return {
        **summary,
        "github_default_branch": project.github_default_branch,
        "last_evaluated_at": project.last_evaluated_at,
        "ai_errors": project.ai_errors or {},
        "documents": {k: getattr(project, k) for k in (
            "project_initial_doc", "project_doc", "project_progress_doc", "project_report_doc")},
        "source_files": [source_file_dict(f) for f in sorted(
            (f for f in project.source_files if f.deleted_at is None), key=lambda f: f.id)],
    }


# ── People ───────────────────────────────────────────────────────

async def active_employees(db: AsyncSession) -> list[User]:
    """Everyone who may be given a project role or a task, by name."""
    from app.models.user import Role
    return list((await db.execute(
        select(User).join(UserRole, UserRole.user_id == User.id).join(Role, Role.id == UserRole.role_id)
        .where(Role.role_name == "Employee", User.deleted_at.is_(None), User.status == "Active")
        .order_by(User.name)
    )).scalars().unique().all())


async def active_employee(db: AsyncSession, user_id: int) -> User:
    """A user who may take a project role: an active platform Employee."""
    user = (await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
    )).scalar_one_or_none()
    if user is None:
        raise NotFoundException("User")
    if "Employee" not in platform_roles(user) or user.status != "Active":
        raise TraceException(422, "Only an active Employee can hold a project role")
    return user


async def grant_repo_access(github: GitHubClient | None, project: Project, user: User) -> list[str]:
    """Invite someone joining the project to its repository with Write (CORE.md §4.1).

    Never fails the change that triggered it: a problem comes back as a warning.
    """
    if not project.github_repo:
        return []
    if not user.github_username:
        return [f"{user.name} has no GitHub username, so they were not given access to {project.github_repo}"]
    if github is None:
        return [f"GitHub is not configured, so {user.name} was not given access to {project.github_repo}"]
    try:
        await github.add_collaborator(project.github_repo, user.github_username)
    except GitHubError as exc:
        return [f"{user.name} was not given access to {project.github_repo}: {exc.detail}"]
    return []


async def revoke_repo_access(github: GitHubClient | None, project: Project, user: User) -> list[str]:
    """Someone left the project: remove their Write access, or withdraw the pending invitation."""
    if not project.github_repo or not user.github_username:
        return []
    if github is None:
        return [f"GitHub is not configured, so {user.name}'s access to {project.github_repo} was not removed"]
    try:
        await github.remove_collaborator(project.github_repo, user.github_username)
    except GitHubError as exc:
        return [f"{user.name}'s access to {project.github_repo} was not removed: {exc.detail}"]
    return []


async def ensure_member(db: AsyncSession, project: Project, user: User, assigned_by: int,
                        github: GitHubClient | None) -> list[str]:
    """First task assignment grants project membership (PLANNING.md Q8). A PM stays a PM.

    Every assignment (re-)invites the assignee to the repository — idempotent on GitHub's
    side, and it heals an earlier invitation that failed. Returns warnings.
    """
    project_id, user_id = project.id, user.id
    existing = (await db.execute(
        select(ProjectAssignment).where(ProjectAssignment.project_id == project_id,
                                        ProjectAssignment.user_id == user_id)
    )).scalar_one_or_none()
    if existing is None:
        db.add(ProjectAssignment(project_id=project_id, user_id=user_id,
                                 project_role=MEMBER, assigned_by_user_id=assigned_by))
    elif existing.deleted_at is not None:
        existing.deleted_at = None
        existing.project_role = MEMBER
        existing.assigned_by_user_id = assigned_by
    await db.flush()
    return await grant_repo_access(github, project, user)


def notify_assignment(db: AsyncSession, task: Task, project: Project, assignee_id: int) -> None:
    db.add(Notification(
        user_id=assignee_id, type="task_assigned",
        title=f"New task: {task.title}",
        body=f"You were assigned '{task.title}' in {project.name}.",
        link=f"/employee/tasks/{task.id}",
        related_task_id=task.id, related_project_id=project.id,
    ))


# ── Tasks ────────────────────────────────────────────────────────

def issue_body(task: Task, project: Project) -> str:
    parts = [task.description.strip()] if task.description else []
    parts.append(
        "---\n"
        f"Managed by TRACE · project **{project.name}**.\n\n"
        "Update the task's status in TRACE — marking it Completed there closes this issue."
    )
    return "\n\n".join(parts)


async def load_task(db: AsyncSession, task_id: int) -> Task:
    return (await db.execute(
        select(Task).where(Task.id == task_id).options(
            selectinload(Task.project), selectinload(Task.task_group),
            selectinload(Task.assigned_to_user), selectinload(Task.assigned_by_user),
        ).execution_options(populate_existing=True)
    )).scalar_one()


def task_dict(task: Task, access: ProjectAccess | None = None) -> dict:
    return {
        "id": task.id, "project_id": task.project_id,
        "project_name": task.project.name if task.project else "",
        "task_group_id": task.task_group_id,
        "task_group_name": task.task_group.name if task.task_group else None,
        "title": task.title, "description": task.description, "priority": task.priority,
        "status": task.status, "due_date": task.due_date,
        "estimated_hours": float(task.estimated_hours) if task.estimated_hours is not None else None,
        "github_issue_id": task.github_issue_id, "github_issue_url": task.github_issue_url,
        "task_progress_doc": task.task_progress_doc,
        "progress_doc_error": task.progress_doc_error,
        "assigned_to": person(task.assigned_to_user), "assigned_by": person(task.assigned_by_user),
        "completed_by": task.completed_by, "completed_at": task.completed_at,
        "health_score": task.health_score, "health_reason": task.health_reason,
        "created_at": task.created_at, "updated_at": task.updated_at,
        "can_edit": bool(access and access.is_project_manager),
        "allowed_statuses": access.allowed_statuses(task) if access else [],
    }


async def group_in_project(db: AsyncSession, project_id: int, group_id: int) -> TaskGroup:
    group = (await db.execute(
        select(TaskGroup).where(TaskGroup.id == group_id, TaskGroup.project_id == project_id,
                                TaskGroup.deleted_at.is_(None))
    )).scalar_one_or_none()
    if group is None:
        raise TraceException(422, "task_group_id does not belong to this project")
    return group


async def recompute_group(db: AsyncSession, group_id: int | None) -> None:
    """Roll task statuses up into the group's Gantt fields (completion %, status)."""
    if group_id is None:
        return
    await db.flush()
    group = await db.get(TaskGroup, group_id)
    statuses = (await db.execute(
        select(Task.status).where(Task.task_group_id == group_id, Task.deleted_at.is_(None),
                                  Task.status != "Cancelled")
    )).scalars().all()
    done = sum(1 for s in statuses if s == "Completed")
    group.completion_percentage = round(done / len(statuses) * 100, 2) if statuses else 0
    if statuses and done == len(statuses):
        group.status = "Completed"
    elif any(s in ("In Progress", "In Review", "Completed") for s in statuses):
        group.status = "In Progress"
    elif statuses and all(s == "Blocked" for s in statuses):
        group.status = "Blocked"
    else:
        group.status = "Pending"
    # What actually happened, for the Gantt re-plan (CORE.md §5)
    today = date.today()
    if group.status != "Pending" and group.actual_start_date is None:
        group.actual_start_date = today
    if group.status == "Completed":
        group.actual_end_date = group.actual_end_date or today
    else:
        group.actual_end_date = None


def _pending_invitation(assignee: User, project: Project) -> str:
    return (f"GitHub would not assign the issue to {assignee.github_username} — their invitation to "
            f"{project.github_repo} is probably not accepted yet — so it was left unassigned. "
            f"Assign the task again once they have accepted")


async def _open_issue(github: GitHubClient, project: Project, task: Task,
                      assignee: User | None) -> tuple[object, list[str]]:
    """Create the issue; if GitHub rejects the assignee, create it unassigned and warn."""
    assignees = [assignee.github_username] if assignee and assignee.github_username else []
    try:
        return await github.create_issue(project.github_repo, task.title, issue_body(task, project), assignees), []
    except GitHubError as exc:
        if not (assignees and exc.github_status == 422):
            raise
    issue = await github.create_issue(project.github_repo, task.title, issue_body(task, project), [])
    return issue, [_pending_invitation(assignee, project)]


def _issue_number(task: Task) -> int | None:
    return int(task.github_issue_id) if task.github_issue_id and task.github_issue_id.isdigit() else None


async def create_task(db: AsyncSession, access: ProjectAccess, data, github: GitHubClient) -> tuple[Task, list[str]]:
    """Task creation *is* issue creation (CORE.md §4): both happen, or neither."""
    project, warnings = access.project, []
    if not project.github_repo:
        raise TraceException(409, "This project has no GitHub repository; set one before creating tasks")
    group = await group_in_project(db, project.id, data.task_group_id)
    assignee = await active_employee(db, data.assigned_to_user_id) if data.assigned_to_user_id else None

    task = Task(
        project_id=project.id, task_group_id=group.id, title=data.title,
        description=data.description, priority=data.priority, due_date=data.due_date,
        estimated_hours=data.estimated_hours, status="Pending",
        assigned_to_user_id=assignee.id if assignee else None,
        assigned_by_user_id=access.user.id if assignee else None,
    )
    db.add(task)
    await db.flush()

    try:
        if assignee:  # invite first, so the issue can be assigned to them
            warnings += await ensure_member(db, project, assignee, access.user.id, github)
            if not assignee.github_username:
                warnings = [f"{assignee.name} has no GitHub username, so the issue was left unassigned"]
        issue, issue_warnings = await _open_issue(github, project, task, assignee)
    except Exception:
        await db.rollback()  # no issue → no task; never rely on the caller to undo the flush
        raise
    warnings += issue_warnings
    task.github_issue_id, task.github_issue_url = str(issue.number), issue.url

    if assignee:
        notify_assignment(db, task, project, assignee.id)
    await recompute_group(db, group.id)
    await db.commit()
    jobs.enqueue("generate_task_progress_doc", task.id)  # CORE.md §4 step 4 — after the commit
    return await load_task(db, task.id), warnings


async def update_task(db: AsyncSession, access: ProjectAccess, task: Task, data) -> Task:
    changes = data.model_dump(exclude_unset=True)
    old_group = task.task_group_id
    if "task_group_id" in changes:
        await group_in_project(db, access.project.id, changes["task_group_id"])
    for field, value in changes.items():
        setattr(task, field, value)
    await recompute_group(db, old_group)
    if task.task_group_id != old_group:
        await recompute_group(db, task.task_group_id)
    await db.commit()
    return await load_task(db, task.id)


async def assign_task(db: AsyncSession, access: ProjectAccess, task: Task, user_id: int | None,
                      github: GitHubClient) -> tuple[Task, list[str]]:
    warnings, assignees, project = [], [], access.project
    assignee = await active_employee(db, user_id) if user_id else None
    if assignee:
        warnings += await ensure_member(db, project, assignee, access.user.id, github)
        if assignee.github_username:
            assignees = [assignee.github_username]
        else:
            warnings = [f"{assignee.name} has no GitHub username, so the issue was left unassigned"]
    number = _issue_number(task)
    if number is not None:
        try:
            await github.set_assignees(project.github_repo, number, assignees)
        except GitHubError as exc:
            if not (assignees and exc.github_status == 422):
                raise
            await github.set_assignees(project.github_repo, number, [])
            warnings.append(_pending_invitation(assignee, project))

    task.assigned_to_user_id = assignee.id if assignee else None
    task.assigned_by_user_id = access.user.id if assignee else None
    if assignee:
        notify_assignment(db, task, project, assignee.id)
    await db.commit()
    return await load_task(db, task.id), warnings


async def set_status(db: AsyncSession, access: ProjectAccess, task: Task, new_status: str,
                     github: GitHubClient | None) -> Task:
    access.may_set_status(task, new_status)  # CORE.md §7 — raises 403
    completion_changed = (task.status == "Completed") != (new_status == "Completed")
    was_closed = task.status in ("Completed", "Cancelled")
    closes = new_status in ("Completed", "Cancelled")
    number = _issue_number(task)
    if number is not None and was_closed != closes:
        from app.services.github_service import require_github
        await require_github(github).set_state(
            access.project.github_repo, number, open_=not closes, not_planned=new_status == "Cancelled")

    task.status = new_status
    if new_status == "Completed":
        task.completed_by = "Assignee" if access.is_assignee(task) else "Project Manager"
        task.completed_at = datetime.now(timezone.utc)
    else:
        task.completed_by = None
        task.completed_at = None
    await recompute_group(db, task.task_group_id)
    await db.commit()
    if completion_changed:
        from app.services.gantt_service import request_reevaluation
        request_reevaluation(access.project.id, "task_status_change")  # CORE.md §5
    return await load_task(db, task.id)


async def delete_task(db: AsyncSession, access: ProjectAccess, task: Task, github: GitHubClient | None) -> None:
    number = _issue_number(task)
    if number is not None and task.status not in ("Completed", "Cancelled"):
        from app.services.github_service import require_github
        await require_github(github).set_state(access.project.github_repo, number, open_=False, not_planned=True)
    task.deleted_at = datetime.now(timezone.utc)
    await recompute_group(db, task.task_group_id)
    await db.commit()


async def mark_overdue_tasks(db: AsyncSession, today: date) -> dict:
    """The nightly sweep (CORE.md §8): open past-due tasks → Overdue, one Gantt re-plan per project."""
    from sqlalchemy import update
    from app.services.gantt_service import request_reevaluation

    rows = (await db.execute(
        update(Task)
        .where(Task.due_date < today, Task.status.in_(("Pending", "In Progress", "In Review", "Blocked")),
               Task.deleted_at.is_(None), Task.project_id.is_not(None))
        .values(status="Overdue")
        .returning(Task.id, Task.project_id)
    )).all()
    await db.commit()
    projects = sorted({pid for _, pid in rows})
    for project_id in projects:
        request_reevaluation(project_id, "task_status_change")
    return {"status": "success", "date": today.isoformat(), "tasks": [tid for tid, _ in rows], "projects": projects}
