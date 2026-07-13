"""
TRACE - Celery Background Tasks
Scheduled and on-demand tasks for the TRACE system.

Tasks:
1. mark_delayed_tasks — Nightly: marks overdue tasks as "Delayed"
2. compute_all_weekly_scores — Weekly: runs AI scoring for all employees
3. send_weekly_report — Weekly: emails the performance report to admin
"""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from app.celery_app import celery_app

logger = logging.getLogger("trace.tasks")


def _run_async(coro):
    """Helper to run async code inside synchronous Celery tasks."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ══════════════════════════════════════════════════════════════════
#  TASK 1: Mark Delayed Tasks (Nightly)
# ══════════════════════════════════════════════════════════════════

@celery_app.task(name="app.tasks.mark_delayed_tasks", bind=True, max_retries=3)
def mark_delayed_tasks(self):
    """
    Runs nightly at 11 PM.
    Finds all tasks past their due_date that are still Pending/WIP
    and marks them as "Delayed".
    """
    async def _mark():
        from sqlalchemy import select, update
        from app.database import async_session_factory
        from app.models.task import Task

        today = date.today()
        async with async_session_factory() as db:
            try:
                result = await db.execute(
                    update(Task)
                    .where(
                        Task.due_date < today,
                        Task.status.in_(["Pending", "WIP"]),
                        Task.deleted_at.is_(None),
                    )
                    .values(status="Delayed")
                    .returning(Task.id)
                )
                delayed_ids = [row[0] for row in result.all()]
                await db.commit()

                logger.info(
                    f"[mark_delayed_tasks] Marked {len(delayed_ids)} tasks as Delayed: {delayed_ids}"
                )
                return {
                    "status": "success",
                    "date": today.isoformat(),
                    "tasks_delayed": len(delayed_ids),
                    "task_ids": delayed_ids,
                }
            except Exception as e:
                await db.rollback()
                logger.error(f"[mark_delayed_tasks] Failed: {e}")
                raise self.retry(exc=e, countdown=60)

    return _run_async(_mark())


# ══════════════════════════════════════════════════════════════════
#  TASK 2: Compute Weekly Scores (Every Sunday)
# ══════════════════════════════════════════════════════════════════

@celery_app.task(name="app.tasks.compute_all_weekly_scores", bind=True, max_retries=3)
def compute_all_weekly_scores(self):
    """
    Runs every Sunday at 11:30 PM.
    Computes productivity scores for all active employees for the
    current week using the AI scoring engine.
    """
    async def _compute():
        from sqlalchemy import select
        from app.database import async_session_factory
        from app.models.employee import Employee
        from app.services.scoring_service import ScoringService

        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        async with async_session_factory() as db:
            try:
                result = await db.execute(
                    select(Employee.id).where(
                        Employee.status == "Active",
                        Employee.deleted_at.is_(None),
                    )
                )
                employee_ids = [row[0] for row in result.all()]

                service = ScoringService(db)
                computed = 0
                errors = []

                for emp_id in employee_ids:
                    try:
                        await service.compute_weekly_score(emp_id, week_start)
                        computed += 1
                    except Exception as e:
                        errors.append({"employee_id": emp_id, "error": str(e)})
                        logger.warning(
                            f"[compute_scores] Failed for employee {emp_id}: {e}"
                        )

                await db.commit()
                logger.info(
                    f"[compute_scores] Computed {computed}/{len(employee_ids)} scores "
                    f"for week {week_start}"
                )
                return {
                    "status": "success",
                    "week_start": week_start.isoformat(),
                    "total_employees": len(employee_ids),
                    "computed": computed,
                    "errors": errors,
                }
            except Exception as e:
                await db.rollback()
                logger.error(f"[compute_scores] Failed: {e}")
                raise self.retry(exc=e, countdown=120)

    return _run_async(_compute())


# ══════════════════════════════════════════════════════════════════
#  TASK 3: Send Weekly Report (Every Monday)
# ══════════════════════════════════════════════════════════════════

@celery_app.task(name="app.tasks.send_weekly_report", bind=True, max_retries=3)
def send_weekly_report(self):
    """
    Runs every Monday at 8 AM.
    Generates the weekly performance report and sends it to the admin email.
    Placeholder for SendGrid integration.
    """
    async def _send():
        from app.database import async_session_factory
        from app.services.report_service import ReportService
        from app.config import get_settings

        settings = get_settings()
        today = date.today()
        last_week_start = today - timedelta(days=today.weekday() + 7)

        async with async_session_factory() as db:
            try:
                service = ReportService(db)
                summary = await service.generate_weekly_summary(last_week_start)
                html = service.generate_report_html(summary)

                admin_email = settings.ADMIN_EMAIL

                # ── SendGrid Integration Point ──
                # In production, replace this block with actual SendGrid API call:
                #
                # import sendgrid
                # from sendgrid.helpers.mail import Mail, Content
                # sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
                # message = Mail(
                #     from_email="noreply@trace.com",
                #     to_emails=admin_email,
                #     subject=f"TRACE Weekly Report - Week of {last_week_start}",
                #     html_content=html,
                # )
                # sg.send(message)

                logger.info(
                    f"[weekly_report] Generated report for week {last_week_start}. "
                    f"Admin: {admin_email}. "
                    f"Employees: {summary.get('total_employees', 0)}. "
                    f"Avg Score: {summary.get('average_score', 'N/A')}"
                )

                return {
                    "status": "success",
                    "week_start": last_week_start.isoformat(),
                    "admin_email": admin_email,
                    "total_employees": summary.get("total_employees", 0),
                    "avg_score": summary.get("average_score"),
                    "at_risk_count": summary.get("at_risk_count", 0),
                    "email_sent": False,  # Set to True when SendGrid is configured
                }
            except Exception as e:
                logger.error(f"[weekly_report] Failed: {e}")
                raise self.retry(exc=e, countdown=300)

    return _run_async(_send())
