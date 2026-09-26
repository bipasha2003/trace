"""
TRACE - Notifications (CORE.md §9, PROJECT.md §11.7)

Two steps, around the caller's commit — like every other side effect:

    outbox = await notify(db, [user ids], "task_completed", title, body, task=task)
    await db.commit()
    deliver(outbox)          # live event to open browsers + the email, if any

`notify` writes the `notifications` rows; `deliver` publishes the live event
(app.services.realtime) and enqueues `send_mail_task` for the rows that also go
by email. The acting user is never notified of their own action (`exclude`).
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.project_access import PROJECT_MANAGER, platform_roles
from app.models.project import Notification, ProjectAssignment
from app.models.task import Task
from app.models.user import User, UserRole
from app.services import jobs, realtime


@dataclass
class Outbox:
    user_ids: set[int] = field(default_factory=set)
    emails: list[tuple[str, str, str]] = field(default_factory=list)  # (to, subject, body)

    def __add__(self, other: "Outbox") -> "Outbox":
        return Outbox(self.user_ids | other.user_ids, self.emails + other.emails)


def task_link(user: User, task_id: int) -> str:
    """The task page in the recipient's own panel."""
    panel = "manager" if "Manager" in platform_roles(user) else "employee"
    return f"/{panel}/tasks/{task_id}"


def project_link(user: User, project_id: int) -> str:
    panel = "manager" if "Manager" in platform_roles(user) else "employee"
    return f"/{panel}/projects/{project_id}"


async def project_managers(db: AsyncSession, project_id: int) -> list[int]:
    return list((await db.execute(
        select(ProjectAssignment.user_id).where(
            ProjectAssignment.project_id == project_id,
            ProjectAssignment.project_role == PROJECT_MANAGER,
            ProjectAssignment.deleted_at.is_(None),
        )
    )).scalars())


async def notify(db: AsyncSession, user_ids, type_: str, title: str, body: str, *,
                 task: Task | None = None, project_id: int | None = None,
                 email: bool = True, exclude: int | None = None) -> Outbox:
    """Add one notification per recipient; returns what `deliver` sends after the commit."""
    ids = {u for u in user_ids if u and u != exclude}
    outbox = Outbox()
    if not ids:
        return outbox
    users = (await db.execute(
        select(User).where(User.id.in_(ids), User.deleted_at.is_(None))
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
    )).scalars().all()
    project_id = project_id or (task.project_id if task else None)
    for user in users:
        if task is not None:
            link = task_link(user, task.id)
        elif project_id is not None:
            link = project_link(user, project_id)
        else:
            link = None
        db.add(Notification(
            user_id=user.id, type=type_, title=title[:255], body=body, link=link,
            related_task_id=task.id if task else None, related_project_id=project_id,
        ))
        outbox.user_ids.add(user.id)
        if email and user.email:
            url = f"{get_settings().app_url}{link}" if link else get_settings().app_url
            outbox.emails.append((user.email, title[:255], f"{body}\n\nOpen in TRACE: {url}"))
    return outbox


def deliver(outbox: Outbox) -> None:
    """After the commit: the live event, then the emails."""
    realtime.publish(outbox.user_ids, {"type": "notification"})
    for to, subject, body in outbox.emails:
        jobs.enqueue("send_mail_task", to, subject, body)


def discussion_event(user_ids, task_id: int) -> None:
    """A new message — open task pages of these users reload the thread."""
    realtime.publish(user_ids, {"type": "discussion", "task_id": task_id})
