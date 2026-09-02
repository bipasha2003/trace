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


# ══════════════════════════════════════════════════════════════════
#  TASK 4: Send Mail via Mailpit SMTP (Celery)
# ══════════════════════════════════════════════════════════════════

@celery_app.task(name="app.tasks.send_mail_task", bind=True, max_retries=3)
def send_mail_task(self, to_email: str, subject: str, body: str):
    """
    Send an email via SMTP (Mailpit in development).
    Triggered by the service monitor mail test feature.
    """
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from app.config import get_settings

        settings = get_settings()

        msg = MIMEMultipart("alternative")
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email
        msg["Subject"] = subject

        # HTML body
        html = f"""
        <html>
        <body style="font-family: 'Inter', sans-serif; background: #0f0f11; color: #f0f0f5; padding: 32px;">
            <div style="max-width: 600px; margin: 0 auto; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 32px;">
                <h2 style="color: #c4b5fd; margin-top: 0;">📧 TRACE Mail</h2>
                <p style="color: #d1d5db; line-height: 1.6;">{body}</p>
                <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 24px 0;">
                <p style="color: #9ca3af; font-size: 12px;">Sent from TRACE Service Monitor</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
            smtp.sendmail(settings.SMTP_FROM, to_email, msg.as_string())

        logger.info(f"[send_mail_task] Email sent to {to_email}: {subject}")
        return {
            "status": "success",
            "to": to_email,
            "subject": subject,
            "smtp": f"{settings.SMTP_HOST}:{settings.SMTP_PORT}",
        }
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

        settings = get_settings()

        if not settings.OPENAI_API_KEY:
            return {
                "status": "error",
                "error": "OPENAI_API_KEY not configured. Set it in .env to use LLM features.",
            }

        client_kwargs = {"api_key": settings.OPENAI_API_KEY}
        if settings.OPENAI_BASE_URL:
            client_kwargs["base_url"] = settings.OPENAI_BASE_URL

        client = OpenAI(**client_kwargs)
        use_model = model or settings.OPENAI_MODEL

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
