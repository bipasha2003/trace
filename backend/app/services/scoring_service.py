"""
TRACE - AI Scoring Service
Implements the productivity scoring formula from the synopsis.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.productivity import ProductivityScore
from app.models.task import Task, TaskTimeLog


class ScoringService:
    """AI-based productivity scoring engine."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_weekly_score(self, employee_id: int, week_start: date) -> ProductivityScore:
        """
        Compute productivity score using the synopsis formula:
        - att_score = (days_present / working_days) * 100
        - task_score = (tasks_completed / tasks_assigned) * 100
        - deadline_score = (tasks_on_time / tasks_completed) * 100
        - active_time_score = (active_time / (shift_time * 0.7)) * 100, capped at 100
        - final_score = att*0.20 + task*0.30 + deadline*0.20 + active*0.30
        """
        week_end = week_start + timedelta(days=6)
        working_days = 5  # Mon-Fri

        # Attendance score
        att_count = await self.db.execute(
            select(func.count(Attendance.id)).where(
                and_(Attendance.employee_id == employee_id,
                     Attendance.attendance_date >= week_start,
                     Attendance.attendance_date <= week_end,
                     Attendance.deleted_at.is_(None))
            )
        )
        days_present = att_count.scalar() or 0
        att_score = min(Decimal(str((days_present / working_days) * 100)), Decimal("100"))

        # Task score
        tasks_assigned_count = await self._count_tasks(employee_id, week_start, week_end)
        tasks_completed_count = await self._count_tasks(employee_id, week_start, week_end, status="Completed")
        task_score = Decimal(str((tasks_completed_count / tasks_assigned_count * 100) if tasks_assigned_count > 0 else 100))

        # Deadline score
        tasks_on_time = await self._count_on_time_tasks(employee_id, week_start, week_end)
        deadline_score = Decimal(str((tasks_on_time / tasks_completed_count * 100) if tasks_completed_count > 0 else 100))

        # Active time score
        total_active = await self._get_active_minutes(employee_id, week_start, week_end)
        shift_minutes = working_days * 8 * 60  # 8-hour shifts
        threshold = shift_minutes * 0.7
        active_time_score = min(Decimal(str((total_active / threshold * 100) if threshold > 0 else 100)), Decimal("100"))

        # Final weighted score
        final_score = (
            att_score * Decimal("0.20") +
            task_score * Decimal("0.30") +
            deadline_score * Decimal("0.20") +
            active_time_score * Decimal("0.30")
        )

        # Rating
        rating = self._get_rating(final_score)

        # Anomaly detection
        anomaly_flags = await self._detect_anomalies(
            employee_id, week_start, week_end, final_score, total_active, shift_minutes
        )

        # Persist
        score = ProductivityScore(
            employee_id=employee_id, week_start=week_start,
            att_score=att_score, task_score=task_score,
            deadline_score=deadline_score, active_time_score=active_time_score,
            final_score=final_score.quantize(Decimal("0.01")),
            rating=rating, anomaly_flags=anomaly_flags,
            generated_at=datetime.now(timezone.utc),
        )
        self.db.add(score)
        await self.db.flush()
        return score

    @staticmethod
    def _get_rating(score: Decimal) -> str:
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 60:
            return "Average"
        return "Risk"

    async def _count_tasks(self, emp_id: int, start: date, end: date, status: str | None = None) -> int:
        conditions = [Task.assigned_to == emp_id, Task.created_at >= datetime.combine(start, datetime.min.time()),
                       Task.created_at <= datetime.combine(end, datetime.max.time()), Task.deleted_at.is_(None)]
        if status:
            conditions.append(Task.status == status)
        result = await self.db.execute(select(func.count(Task.id)).where(*conditions))
        return result.scalar() or 0

    async def _count_on_time_tasks(self, emp_id: int, start: date, end: date) -> int:
        result = await self.db.execute(
            select(func.count(Task.id)).where(
                Task.assigned_to == emp_id, Task.status == "Completed",
                Task.due_date.isnot(None), Task.updated_at <= Task.due_date,
                Task.deleted_at.is_(None),
            )
        )
        return result.scalar() or 0

    async def _get_active_minutes(self, emp_id: int, start: date, end: date) -> int:
        result = await self.db.execute(
            select(func.coalesce(func.sum(TaskTimeLog.active_minutes), 0)).where(
                TaskTimeLog.employee_id == emp_id,
                TaskTimeLog.start_time >= datetime.combine(start, datetime.min.time()),
                TaskTimeLog.start_time <= datetime.combine(end, datetime.max.time()),
            )
        )
        return result.scalar() or 0

    async def _detect_anomalies(self, emp_id: int, start: date, end: date,
                                 score: Decimal, active_min: int, shift_min: int) -> dict[str, Any]:
        flags: dict[str, Any] = {}
        if score < 60:
            flags["low_score"] = True
        delayed = await self._count_tasks(emp_id, start, end, status="Delayed")
        if delayed >= 3:
            flags["excessive_delays"] = delayed
        if shift_min > 0 and (active_min / shift_min) < 0.3:
            flags["low_active_time"] = round(active_min / shift_min * 100, 1)
        return flags
