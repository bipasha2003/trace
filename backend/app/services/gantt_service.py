"""
TRACE - Project tree and Gantt (Phase 4)

The tree is a live read over project → task groups → tasks (PROJECT.md §21).
The Gantt is a stored, versioned snapshot in `gantt_charts` (CORE.md §5): every
version is validated against `GanttChartData` and written as a new row, never patched.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import GanttChart, Project, TaskGroup
from app.models.task import Task
from app.schemas.gantt import GanttChartData
from app.services.project_service import OPEN_STATUSES, person

DEFAULT_GROUP_DAYS = 7


def is_overdue(task: Task, today: date | None = None) -> bool:
    today = today or date.today()
    return task.status == "Overdue" or (
        task.due_date is not None and task.due_date < today and task.status in OPEN_STATUSES)


async def groups_with_tasks(db: AsyncSession, project_id: int) -> list[tuple[TaskGroup, list[Task]]]:
    """The project's live task groups in sequence order, each with its live tasks."""
    groups = (await db.execute(
        select(TaskGroup).where(TaskGroup.project_id == project_id, TaskGroup.deleted_at.is_(None))
        .order_by(TaskGroup.sequence, TaskGroup.id)
    )).scalars().all()
    tasks = (await db.execute(
        select(Task).where(Task.project_id == project_id, Task.deleted_at.is_(None))
        .options(selectinload(Task.assigned_to_user)).order_by(Task.id)
    )).scalars().all()
    by_group: dict[int, list[Task]] = {}
    for task in tasks:
        by_group.setdefault(task.task_group_id, []).append(task)
    return [(g, by_group.get(g.id, [])) for g in groups]


# ── Tree ─────────────────────────────────────────────────────────

async def project_tree(db: AsyncSession, project: Project) -> dict:
    groups = await groups_with_tasks(db, project.id)
    today = date.today()
    live = [t for _, tasks in groups for t in tasks if t.status != "Cancelled"]
    done = sum(1 for t in live if t.status == "Completed")
    return {
        "project": {"id": project.id, "name": project.name, "status": project.status,
                    "completion_percentage": round(done / len(live) * 100, 1) if live else 0.0},
        "groups": [{
            "id": g.id, "name": g.name, "sequence": g.sequence, "status": g.status,
            "completion_percentage": float(g.completion_percentage or 0),
            "tasks": [{
                "id": t.id, "title": t.title, "status": t.status, "priority": t.priority,
                "due_date": t.due_date, "overdue": is_overdue(t, today),
                "assignee": person(t.assigned_to_user), "github_issue_url": t.github_issue_url,
            } for t in tasks],
        } for g, tasks in groups],
    }


# ── Gantt ────────────────────────────────────────────────────────

def build_chart_data(project: Project, groups: list[tuple[TaskGroup, list[Task]]],
                     dependencies: list[tuple[int, int]] | None = None,
                     today: date | None = None) -> GanttChartData:
    """(task group, tasks) pairs → chart_data, no AI (CORE.md §5.1)."""
    cursor = project.start_date or today or date.today()
    bars = []
    for g, tasks in groups:
        start = g.planned_start_date or cursor
        end = g.planned_end_date or start + timedelta(days=(g.estimated_duration_days or DEFAULT_GROUP_DAYS) - 1)
        end = max(end, start)
        cursor = end + timedelta(days=1)
        bars.append({
            "task_group_id": g.id, "name": g.name, "sequence": g.sequence,
            "start": start, "end": end, "completion": float(g.completion_percentage or 0),
            "status": g.status,
            "tasks": [{"task_id": t.id, "title": t.title, "status": t.status, "due": t.due_date,
                       "assignee": t.assigned_to_user.name if t.assigned_to_user else None}
                      for t in tasks if t.status != "Cancelled"],
        })
    milestones = [{"name": "Project end", "date": project.end_date}] if project.end_date else []
    dates = [d for b in bars for d in (b["start"], b["end"])] + [m["date"] for m in milestones]
    dates += [t["due"] for b in bars for t in b["tasks"] if t["due"]]
    start = min(dates, default=cursor)
    return GanttChartData.model_validate({
        "schema": 1,
        "range": {"start": start, "end": max(dates, default=start)},
        "bars": bars,
        "dependencies": [{"from": a, "to": b} for a, b in (dependencies or [])],
        "milestones": milestones,
    })


async def save_version(db: AsyncSession, project_id: int, data: GanttChartData | dict, reason: str) -> GanttChart:
    """Validate, then write the next version. Caller commits."""
    chart_data = (data if isinstance(data, GanttChartData) else GanttChartData.model_validate(data)).dump()
    latest = (await db.execute(
        select(func.max(GanttChart.version)).where(GanttChart.project_id == project_id,
                                                   GanttChart.deleted_at.is_(None))
    )).scalar() or 0
    row = GanttChart(project_id=project_id, version=latest + 1, chart_data=chart_data,
                     generated_reason=reason, generated_at=datetime.now(timezone.utc))
    db.add(row)
    await db.flush()
    return row


async def snapshot(db: AsyncSession, project: Project, reason: str,
                   dependencies: list[tuple[int, int]] | None = None) -> GanttChart:
    """Build chart_data from the project's current groups and save it as a new version."""
    groups = await groups_with_tasks(db, project.id)
    return await save_version(db, project.id, build_chart_data(project, groups, dependencies), reason)


async def versions(db: AsyncSession, project_id: int) -> list[GanttChart]:
    return list((await db.execute(
        select(GanttChart).where(GanttChart.project_id == project_id, GanttChart.deleted_at.is_(None))
        .order_by(GanttChart.version.desc())
    )).scalars().all())
