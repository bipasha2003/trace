"""
TRACE - Project-scoped authorisation (layer two)

Layer one is the platform role on the route (app.core.permissions). Layer two is
this: who is the caller *in this project*? Every project and task endpoint
resolves a `ProjectAccess` and asks it — never re-derives roles inline.

    Admin    → sees every project, changes nothing (Control Panel is the escape hatch)
    Manager  → sees and administers only projects they created (Q11)
    Employee → needs a project_assignments row: 'Project Manager' or 'Member'

Status authority (CORE.md §7) is decided by `may_set_status`: the assignee updates
their own task, completion included; the Project Manager may set any status.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InsufficientPermissionsException, NotFoundException, TraceException
from app.models.project import Project, ProjectAssignment
from app.models.task import Task
from app.models.user import User

PROJECT_MANAGER = "Project Manager"
MEMBER = "Member"

# Statuses the assignee may move their own task between. Cancelling is a scope
# decision, so it stays with the Project Manager.
ASSIGNEE_SETTABLE_STATUSES = {"Pending", "In Progress", "In Review", "Blocked", "Completed"}
# Statuses only the system sets (the nightly overdue sweep), never a human
SYSTEM_ONLY_STATUSES = {"Overdue"}
TASK_STATUSES = {"Pending", "In Progress", "In Review", "Completed", "Blocked", "Overdue", "Cancelled"}


def platform_roles(user: User) -> set[str]:
    return {ur.role.role_name for ur in (user.user_roles or []) if ur.role}


@dataclass
class ProjectAccess:
    project: Project
    user: User
    platform_role: str               # Admin | Manager | Employee
    project_role: str | None         # Project Manager | Member | None

    @property
    def is_owner(self) -> bool:
        return self.platform_role == "Manager" and self.project.created_by_user_id == self.user.id

    @property
    def is_project_manager(self) -> bool:
        return self.project_role == PROJECT_MANAGER

    def require_owner(self) -> None:
        """Project administration: details, source files, Project Manager roster."""
        if not self.is_owner:
            raise InsufficientPermissionsException()

    def require_project_manager(self) -> None:
        """Project structure: task groups, tasks, assignment."""
        if not self.is_project_manager:
            raise InsufficientPermissionsException()

    def is_assignee(self, task: Task) -> bool:
        return self.platform_role == "Employee" and task.assigned_to_user_id == self.user.id

    def may_set_status(self, task: Task, new_status: str) -> None:
        """CORE.md §7 — enforced here, in the API layer, whatever the UI shows."""
        if new_status in SYSTEM_ONLY_STATUSES:
            raise TraceException(403, f"'{new_status}' is set by the system, not by hand")
        if self.is_project_manager:
            return
        if self.is_assignee(task):
            if new_status in ASSIGNEE_SETTABLE_STATUSES:
                return
            raise TraceException(403, f"Only the Project Manager can set '{new_status}'")
        raise InsufficientPermissionsException()

    def allowed_statuses(self, task: Task) -> list[str]:
        """Every status this caller may move `task` to — for the UI, derived from may_set_status."""
        allowed = []
        for status in sorted(TASK_STATUSES):
            if status == task.status:
                continue
            try:
                self.may_set_status(task, status)
            except TraceException:
                continue
            allowed.append(status)
        return allowed


async def resolve_project_access(db: AsyncSession, user: User, project_id: int) -> ProjectAccess:
    project = (await db.execute(
        select(Project).where(Project.id == project_id, Project.deleted_at.is_(None))
    )).scalar_one_or_none()
    if project is None:
        raise NotFoundException("Project")

    roles = platform_roles(user)
    if "Admin" in roles:
        return ProjectAccess(project, user, "Admin", None)
    if "Manager" in roles:
        if project.created_by_user_id != user.id:
            raise InsufficientPermissionsException()
        return ProjectAccess(project, user, "Manager", None)

    assignment = (await db.execute(
        select(ProjectAssignment).where(
            ProjectAssignment.project_id == project_id,
            ProjectAssignment.user_id == user.id,
            ProjectAssignment.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if assignment is None:
        raise InsufficientPermissionsException()
    return ProjectAccess(project, user, "Employee", assignment.project_role)


async def resolve_task_access(db: AsyncSession, user: User, task_id: int) -> tuple[Task, ProjectAccess]:
    task = (await db.execute(
        select(Task).where(Task.id == task_id, Task.deleted_at.is_(None))
    )).scalar_one_or_none()
    if task is None or task.project_id is None:
        raise NotFoundException("Task")
    return task, await resolve_project_access(db, user, task.project_id)
