"""
TRACE - The dashboard report download (PLANNING.md Q7, DEVELOPMENT.md Phase 8 step 5)

One CSV for a date range: project → task group → task, one row per task. A task
is in the report if it was **created, due or completed** inside the range; each row
shows its status *today*, its dates and its assignee, with its group's completion.
The caller's visibility decides which projects are read (`visible_projects`).
"""

import csv
import io
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.task import Task

COLUMNS = [
    "Project", "Project status", "Task group", "Group completion %", "Task", "Status", "Priority",
    "Assignee", "Created", "Due", "Completed", "Completed by", "GitHub issue",
]


def _in_range(task: Task, start: date, end: date) -> bool:
    days = [
        task.created_at.date() if task.created_at else None,
        task.due_date,
        task.completed_at.date() if task.completed_at else None,
    ]
    return any(d is not None and start <= d <= end for d in days)


async def report_rows(db: AsyncSession, projects: list[Project], start: date, end: date) -> list[list]:
    if not projects:
        return []
    by_id = {p.id: p for p in projects}
    tasks = (await db.execute(
        select(Task).where(Task.project_id.in_(list(by_id)), Task.deleted_at.is_(None))
        .options(selectinload(Task.task_group), selectinload(Task.assigned_to_user))
    )).scalars().all()
    tasks = [t for t in tasks if _in_range(t, start, end)]

    def order(t: Task):
        group = t.task_group
        return (by_id[t.project_id].name.lower(), group.sequence if group else 1_000_000,
                group.name.lower() if group else "", t.id)

    rows = []
    for t in sorted(tasks, key=order):
        project, group = by_id[t.project_id], t.task_group
        rows.append([
            project.name, project.status,
            group.name if group else "",
            f"{float(group.completion_percentage or 0):.0f}" if group else "",
            t.title, t.status, t.priority,
            t.assigned_to_user.name if t.assigned_to_user else "",
            t.created_at.date().isoformat() if t.created_at else "",
            t.due_date.isoformat() if t.due_date else "",
            t.completed_at.date().isoformat() if t.completed_at else "",
            t.completed_by or "",
            t.github_issue_url or "",
        ])
    return rows


def to_csv(rows: list[list]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(COLUMNS)
    writer.writerows(rows)
    return out.getvalue()
