"""
TRACE - Celery Application Configuration
Configures the Celery worker with Redis as broker and result backend.
"""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "trace",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    imports=["app.tasks"],
)

# ── Periodic Task Schedule ───────────────────────────────────────
celery_app.conf.beat_schedule = {
    # Open past-due tasks → Overdue, then re-plan their Gantt charts — every night at 11 PM
    "mark-overdue-tasks-nightly": {
        "task": "app.tasks.mark_overdue_tasks",
        "schedule": crontab(hour=23, minute=0),
    },
    # AI progress roll-up for every Active project (CORE.md §6) — Mondays at 7 AM
    "project-progress-docs-weekly": {
        "task": "app.tasks.update_project_progress_docs",
        "schedule": crontab(day_of_week="monday", hour=7, minute=0),
    },
    # Compute weekly scores — runs every Sunday at 11:30 PM
    "compute-weekly-scores": {
        "task": "app.tasks.compute_all_weekly_scores",
        "schedule": crontab(day_of_week="sunday", hour=23, minute=30),
    },
    # Generate & email weekly report — runs every Monday at 8 AM
    "weekly-report-email": {
        "task": "app.tasks.send_weekly_report",
        "schedule": crontab(day_of_week="monday", hour=8, minute=0),
    },
}

# Auto-discover task modules
celery_app.autodiscover_tasks(["app"])
