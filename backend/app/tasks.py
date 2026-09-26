"""
TRACE - Celery Background Tasks
Scheduled and on-demand tasks for the TRACE system.

Scheduled (celery_app.beat_schedule):
- mark_overdue_tasks — nightly: open past-due tasks → Overdue, notify, Gantt re-plan
- task_due_reminders — daily: due-tomorrow notifications
- compute_all_weekly_scores — weekly: task-signal scores for every Employee
- update_project_progress_docs — weekly: the AI progress roll-up per Active project

On demand: the AI pipeline (evaluate_project, generate_task_progress_doc,
reevaluate_gantt, suggest_*), mail, MinIO upload, LLM test, task health.
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
#  TASK 1: Mark Overdue Tasks (Nightly) — CORE.md §8
# ══════════════════════════════════════════════════════════════════

@celery_app.task(name="app.tasks.mark_overdue_tasks", bind=True, max_retries=3)
def mark_overdue_tasks(self):
    """Flip open past-due tasks to Overdue, then re-plan each affected project's Gantt."""
    async def _mark():
        from app.services.jobs import job_session
        from app.services.project_service import mark_overdue_tasks as mark

        async with job_session() as db:
            return await mark(db, date.today())

    try:
        return _run_async(_mark())
    except Exception as e:
        logger.error(f"[mark_overdue_tasks] Failed: {e}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(name="app.tasks.task_due_reminders", bind=True, max_retries=3)
def task_due_reminders(self):
    """Notify the assignee and Project Managers of open tasks due tomorrow (CORE.md §8–9)."""
    async def _remind():
        from app.services.jobs import job_session
        from app.services.project_service import task_due_reminders as remind

        async with job_session() as db:
            return await remind(db, date.today())

    try:
        return _run_async(_remind())
    except Exception as e:
        logger.error(f"[task_due_reminders] Failed: {e}")
        raise self.retry(exc=e, countdown=60)


# ══════════════════════════════════════════════════════════════════
#  AI PIPELINE — CORE.md §3–6. The bodies are in app/services/ai_jobs.py;
#  these only open a session and build the AI and GitHub clients.
# ══════════════════════════════════════════════════════════════════

def _ai_job(task, runner: str, *args):
    async def _run():
        from app.services import ai_jobs, ai_service
        from app.services.github_service import get_github_client
        from app.services.jobs import job_session

        async with job_session() as db:
            ai = ai_service.client_from_settings() if ai_service.ai_configured() else None
            github = await get_github_client(db)
            return await getattr(ai_jobs, runner)(db, *args, job_id=task.request.id, ai=ai, github=github)

    return _run_async(_run())


@celery_app.task(name="app.tasks.evaluate_project", bind=True)
def evaluate_project(self, project_id: int):
    return _ai_job(self, "run_evaluate_project", project_id)


@celery_app.task(name="app.tasks.generate_task_progress_doc", bind=True)
def generate_task_progress_doc(self, task_id: int):
    return _ai_job(self, "run_task_progress_doc", task_id)


@celery_app.task(name="app.tasks.reevaluate_gantt", bind=True)
def reevaluate_gantt(self, project_id: int, reason: str, requested_at: str):
    return _ai_job(self, "run_reevaluate_gantt", project_id, reason, requested_at)


@celery_app.task(name="app.tasks.update_project_progress_doc", bind=True)
def update_project_progress_doc(self, project_id: int):
    return _ai_job(self, "run_progress_report", project_id)


@celery_app.task(name="app.tasks.update_project_progress_docs", bind=True)
def update_project_progress_docs(self):
    """Weekly (Beat): one roll-up job per Active project."""
    async def _ids():
        from sqlalchemy import select
        from app.models.project import Project
        from app.services.jobs import job_session

        async with job_session() as db:
            return list((await db.execute(select(Project.id).where(
                Project.status == "Active", Project.deleted_at.is_(None)))).scalars())

    from app.services.jobs import enqueue
    ids = _run_async(_ids())
    for project_id in ids:
        enqueue("update_project_progress_doc", project_id)
    return {"status": "success", "projects": ids}


# Suggestions: the result *is* the answer (polled via /services/task/{id}/result); nothing is written

@celery_app.task(name="app.tasks.suggest_managers", bind=True)
def suggest_managers(self, project_id: int):
    return _ai_job(self, "run_suggest_managers", project_id)


@celery_app.task(name="app.tasks.suggest_assignees", bind=True)
def suggest_assignees(self, project_id: int, title: str, description: str | None = None):
    return _ai_job(self, "run_suggest_assignees", project_id, title, description)


@celery_app.task(name="app.tasks.suggest_tasks", bind=True)
def suggest_tasks(self, group_id: int):
    return _ai_job(self, "run_suggest_tasks", group_id)


# ══════════════════════════════════════════════════════════════════
#  TASK 2: Compute Weekly Scores (Every Sunday)
# ══════════════════════════════════════════════════════════════════

@celery_app.task(name="app.tasks.compute_all_weekly_scores", bind=True, max_retries=3)
def compute_all_weekly_scores(self):
    """
    Runs every Sunday at 11:30 PM.
    Scores every active Employee's week on task signals (CORE.md §8).
    """
    async def _compute():
        from sqlalchemy import select
        from app.models.employee import Employee
        from app.services.jobs import job_session
        from app.services.scoring_service import ScoringService

        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        async with job_session() as db:
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
#  TASK 4: Send Mail via Mailpit SMTP (Celery)
# ══════════════════════════════════════════════════════════════════

@celery_app.task(name="app.tasks.send_mail_task", bind=True, max_retries=3)
def send_mail_task(self, to_email: str, subject: str, body: str):
    """
    Send one email: notification emails (notification_service.deliver) and the
    Service Monitor's test mail. The SMTP server is resolved on every send from
    Admin → Configuration, then .env (mail_service).
    """
    async def _config():
        from app.services.jobs import job_session
        from app.services.mail_service import mail_config
        async with job_session() as db:
            return await mail_config(db)

    try:
        from app.services.mail_service import send

        config = _run_async(_config())
        send(config, to_email, subject, body)
        logger.info(f"[send_mail_task] Email sent to {to_email}: {subject}")
        return {"status": "success", "to": to_email, "subject": subject, "smtp": f"{config.host}:{config.port}"}
    except Exception as e:
        logger.error(f"[send_mail_task] Failed: {e}")
        raise self.retry(exc=e, countdown=30)


# ══════════════════════════════════════════════════════════════════
#  TASK 5: Upload File to MinIO (Celery)
# ══════════════════════════════════════════════════════════════════

@celery_app.task(name="app.tasks.upload_file_task", bind=True, max_retries=3)
def upload_file_task(self, filename: str, encoded_content: str, content_type: str):
    """
    Upload a file to MinIO S3-compatible storage.
    File content is base64 encoded for Celery serialization.
    """
    try:
        import base64
        import io
        from minio import Minio
        from app.config import get_settings

        settings = get_settings()
        content = base64.b64decode(encoded_content)

        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

        # Ensure bucket exists
        if not client.bucket_exists(settings.MINIO_BUCKET):
            client.make_bucket(settings.MINIO_BUCKET)

        # Upload file
        import uuid
        object_name = f"uploads/{uuid.uuid4().hex[:8]}_{filename}"
        data = io.BytesIO(content)

        client.put_object(
            settings.MINIO_BUCKET,
            object_name,
            data,
            length=len(content),
            content_type=content_type or "application/octet-stream",
        )

        logger.info(f"[upload_file_task] Uploaded {object_name} to {settings.MINIO_BUCKET}")
        return {
            "status": "success",
            "bucket": settings.MINIO_BUCKET,
            "object_name": object_name,
            "size_bytes": len(content),
            "content_type": content_type,
        }
    except Exception as e:
        logger.error(f"[upload_file_task] Failed: {e}")
        raise self.retry(exc=e, countdown=30)


# ══════════════════════════════════════════════════════════════════
#  TASK 6: LLM Chat via OpenAI SDK (Celery)
# ══════════════════════════════════════════════════════════════════

@celery_app.task(name="app.tasks.llm_chat_task", bind=True, max_retries=2)
def llm_chat_task(self, message: str, model: str = None):
    """
    Send a message to an LLM via OpenAI SDK.
    Supports dynamic model selection and custom base URLs.
    """
    try:
        from openai import OpenAI

        from app.config import get_settings

        settings = get_settings()  # fixed in .env — never Admin-configurable
        api_key, base_url, default_model = settings.OPENAI_API_KEY, settings.OPENAI_BASE_URL, settings.OPENAI_MODEL
        if not api_key:
            return {"status": "error", "error": "AI is not configured. Set OPENAI_API_KEY in .env."}

        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = OpenAI(**client_kwargs)
        use_model = model or default_model

        response = client.chat.completions.create(
            model=use_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant for the TRACE task management system. Be concise and professional."},
                {"role": "user", "content": message},
            ],
            max_tokens=1024,
            temperature=0.7,
        )

        reply = response.choices[0].message.content
        logger.info(f"[llm_chat_task] LLM response received (model: {use_model})")
        return {
            "status": "success",
            "model": use_model,
            "reply": reply,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
        }
    except Exception as e:
        logger.error(f"[llm_chat_task] Failed: {e}")
        raise self.retry(exc=e, countdown=15)


# ══════════════════════════════════════════════════════════════════
#  TASK 7: Task Health Computation & Auto-Escalation Engine (Beat)
# ══════════════════════════════════════════════════════════════════

@celery_app.task(name="app.tasks.compute_task_health_and_escalate", bind=True, max_retries=2)
def compute_task_health_and_escalate(self):
    """
    Computes risk score (Green/Yellow/Red) per task from its due date.
    Health is on-demand only; auto-escalation is deferred (see PLANNING.md 00a73.2).
    """
    async def _compute():
        from sqlalchemy import select
        from app.database import async_session_factory
        from app.models.task import Task
        from app.models.employee import Employee

        today = date.today()
        now = datetime.now(timezone.utc)

        async with async_session_factory() as db:
            try:
                # Fetch all active non-completed tasks
                res = await db.execute(
                    select(Task).where(
                        Task.status.notin_(["Completed", "Cancelled"]),
                        Task.deleted_at.is_(None)
                    )
                )
                tasks = res.scalars().all()

                updated_count = 0
                for t in tasks:
                    health = "Green"
                    reasons = []

                    # 1. Due date check
                    if t.due_date:
                        if t.due_date < today:
                            health = "Red"
                            reasons.append(f"Overdue since {t.due_date}")
                        elif t.due_date == today:
                            if health != "Red":
                                health = "Yellow"
                            reasons.append("Due today")

                    t.health_score = health
                    t.health_reason = "; ".join(reasons) if reasons else "On track"
                    t.last_health_check = now
                    updated_count += 1

                await db.commit()
                return {
                    "status": "success",
                    "tasks_checked": len(tasks),
                    "tasks_updated": updated_count,
                }
            except Exception as e:
                await db.rollback()
                logger.error(f"[compute_task_health_and_escalate] Failed: {e}")
                raise self.retry(exc=e, countdown=60)

    return _run_async(_compute())


