"""
TRACE - Performance scoring on task signals (CORE.md §3 ranking inputs, §8)

The weekly score stores two task signals per Employee: throughput (completed ÷
assigned tasks due that week) and on-time rate (completed by the due date ÷
completed). Attendance and active time are still recorded elsewhere but are no
longer inputs — `att_score` and `active_time_score` stay empty.

`candidate_stats` computes the same signals live, over all time, for the people
the AI ranks as Project Managers or assignees.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundException
from app.models.employee import Employee
from app.models.productivity import ProductivityScore
from app.models.project import Project, ProjectAssignment
from app.models.task import Task

OPEN_STATUSES = ("Pending", "In Progress", "In Review", "Blocked", "Overdue")


def _on_time(task: Task) -> bool:
    return task.due_date is None or (task.completed_at is not None and task.completed_at.date() <= task.due_date)


def _pct(part: int, whole: int) -> Decimal:
    return Decimal(str(round(part / whole * 100, 2))) if whole else Decimal("100")


class ScoringService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_weekly_score(self, employee_id: int, week_start: date) -> ProductivityScore:
        """Score the Employee's tasks due in the week starting `week_start`."""
        employee = await self.db.get(Employee, employee_id)
        if employee is None or employee.deleted_at is not None:
            raise NotFoundException("Employee")
        week_end = week_start + timedelta(days=6)
        tasks = (await self.db.execute(select(Task).where(
            Task.assigned_to_user_id == employee.user_id, Task.deleted_at.is_(None),
            Task.status != "Cancelled", Task.due_date >= week_start, Task.due_date <= week_end,
        ))).scalars().all()
        completed = [t for t in tasks if t.status == "Completed"]
        task_score = _pct(len(completed), len(tasks))
        deadline_score = _pct(sum(1 for t in completed if _on_time(t)), len(completed))
        final = ((task_score + deadline_score) / 2).quantize(Decimal("0.01"))

        overdue = (await self.db.execute(select(func.count(Task.id)).where(
            Task.assigned_to_user_id == employee.user_id, Task.deleted_at.is_(None),
            Task.status.in_(OPEN_STATUSES), Task.due_date < date.today(),
        ))).scalar() or 0
        flags = {}
        if final < 60:
            flags["low_score"] = True
        if overdue >= 3:
            flags["overdue_tasks"] = overdue

        score = ProductivityScore(
            employee_id=employee_id, week_start=week_start, task_score=task_score,
            deadline_score=deadline_score, final_score=final, rating=self._get_rating(final),
            anomaly_flags=flags, generated_at=datetime.now(timezone.utc),
        )
        self.db.add(score)
        await self.db.flush()
        return score

    @staticmethod
    def _get_rating(score: Decimal) -> str:
        if score >= 90:
            return "Excellent"
        if score >= 75:
            return "Good"
        if score >= 60:
            return "Average"
        return "Risk"


async def candidate_stats(db: AsyncSession, user_ids: list[int]) -> dict[int, dict]:
    """Live ranking inputs per user (CORE.md §3): task record, PM record, latest weekly score."""
    stats = {uid: {"tasks_completed": 0, "on_time_rate": None, "open_tasks": 0,
                   "projects_managed": 0, "projects_delivered": 0, "managed_projects_completion": None,
                   "latest_weekly_score": None, "recent_completed_titles": []} for uid in user_ids}
    if not user_ids:
        return stats

    tasks = (await db.execute(select(Task).where(
        Task.assigned_to_user_id.in_(user_ids), Task.deleted_at.is_(None), Task.status != "Cancelled",
    ).order_by(Task.completed_at.desc().nullslast()))).scalars().all()
    on_time: dict[int, int] = {}
    for t in tasks:
        s = stats[t.assigned_to_user_id]
        if t.status == "Completed":
            s["tasks_completed"] += 1
            on_time[t.assigned_to_user_id] = on_time.get(t.assigned_to_user_id, 0) + _on_time(t)
            if len(s["recent_completed_titles"]) < 10:
                s["recent_completed_titles"].append(t.title)
        elif t.status in OPEN_STATUSES:
            s["open_tasks"] += 1
    for uid, n in on_time.items():
        stats[uid]["on_time_rate"] = round(n / stats[uid]["tasks_completed"], 2)

    managed = (await db.execute(
        select(ProjectAssignment.user_id, Project.id, Project.status)
        .join(Project, Project.id == ProjectAssignment.project_id)
        .where(ProjectAssignment.user_id.in_(user_ids), ProjectAssignment.project_role == "Project Manager",
               ProjectAssignment.deleted_at.is_(None), Project.deleted_at.is_(None))
    )).all()
    project_ids = {pid for _, pid, _ in managed}
    completion: dict[int, float] = {}
    if project_ids:
        rows = (await db.execute(
            select(Task.project_id, func.count(Task.id),
                   func.count(Task.id).filter(Task.status == "Completed"))
            .where(Task.project_id.in_(project_ids), Task.deleted_at.is_(None), Task.status != "Cancelled")
            .group_by(Task.project_id)
        )).all()
        completion = {pid: done / total for pid, total, done in rows if total}
    per_user: dict[int, list[float]] = {}
    for uid, pid, status in managed:
        stats[uid]["projects_managed"] += 1
        stats[uid]["projects_delivered"] += status == "Completed"
        if pid in completion:
            per_user.setdefault(uid, []).append(completion[pid])
    for uid, values in per_user.items():
        stats[uid]["managed_projects_completion"] = round(sum(values) / len(values), 2)

    latest = (await db.execute(
        select(Employee.user_id, ProductivityScore.final_score)
        .join(ProductivityScore, ProductivityScore.employee_id == Employee.id)
        .where(Employee.user_id.in_(user_ids), ProductivityScore.deleted_at.is_(None))
        .order_by(ProductivityScore.week_start.desc())
    )).all()
    for uid, score in latest:
        if stats[uid]["latest_weekly_score"] is None and score is not None:
            stats[uid]["latest_weekly_score"] = float(score)
    return stats
