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


# ══════════════════════════════════════════════════════════════════
#  TASK 7: Task Health Computation & Auto-Escalation Engine (Beat)
# ══════════════════════════════════════════════════════════════════

@celery_app.task(name="app.tasks.compute_task_health_and_escalate", bind=True, max_retries=2)
def compute_task_health_and_escalate(self):
    """
    Computes risk score (Green/Yellow/Red) per task node and rolls up worst health to parent tasks.
    Triggers auto-escalation emails via Mailpit if health is Red.
    """
    async def _compute():
        from sqlalchemy import select
        from app.database import async_session_factory
        from app.models.task import Task, ProjectGroup, ProjectGroupMessage
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
                task_map = {t.id: t for t in tasks}

                updated_count = 0
                escalations_sent = 0

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

                    # 2. Check group chat for blocker keywords
                    pg_res = await db.execute(select(ProjectGroup.id).where(ProjectGroup.task_id == t.id))
                    pg_id = pg_res.scalar()
                    if pg_id:
                        msg_res = await db.execute(
                            select(ProjectGroupMessage.message)
                            .where(ProjectGroupMessage.group_id == pg_id)
                            .order_by(ProjectGroupMessage.id.desc())
                            .limit(5)
                        )
                        msgs = msg_res.scalars().all()
                        blocker_keywords = ["blocker", "stuck", "bug", "delay", "failed", "critical"]
                        if any(any(kw in m.lower() for kw in blocker_keywords) for m in msgs):
                            health = "Red"
                            reasons.append("Blocker/issue reported in project chat")

                    t.health_score = health
                    t.health_reason = "; ".join(reasons) if reasons else "On track"
                    t.last_health_check = now
                    updated_count += 1

                # 3. Tree Rollup: Parent inherits worst health of children
                for t in sorted(tasks, key=lambda x: x.parent_task_id or 0, reverse=True):
                    if t.parent_task_id and t.parent_task_id in task_map:
                        parent = task_map[t.parent_task_id]
                        if t.health_score == "Red":
                            parent.health_score = "Red"
                            parent.health_reason = f"Subtask #{t.id} ({t.title}) is Red"
                        elif t.health_score == "Yellow" and parent.health_score != "Red":
                            parent.health_score = "Yellow"
                            parent.health_reason = f"Subtask #{t.id} ({t.title}) is Yellow"

                # 4. Auto-Escalation Engine: Trigger Mailpit email for Red tasks
                for t in tasks:
                    if t.health_score == "Red":
                        # Find recipient (Team Lead or Project Manager or Assignee)
                        target_id = t.team_lead_id or t.project_manager_id or t.assigned_to
                        if target_id:
                            emp_res = await db.execute(select(Employee).where(Employee.id == target_id))
                            emp = emp_res.scalar()
                            if emp and emp.email:
                                send_mail_task.delay(
                                    to_email=emp.email,
                                    subject=f"[AUTO-ESCALATION] Task Risk Alert: {t.title} is RED",
                                    body=f"Task #{t.id} '{t.title}' has been flagged as RED RISK.\nReason: {t.health_reason}\nDue Date: {t.due_date}\nPlease review and take corrective action."
                                )
                                escalations_sent += 1

                await db.commit()
                return {
                    "status": "success",
                    "tasks_checked": len(tasks),
                    "tasks_updated": updated_count,
                    "escalations_sent": escalations_sent,
                }
            except Exception as e:
                await db.rollback()
                logger.error(f"[compute_task_health_and_escalate] Failed: {e}")
                raise self.retry(exc=e, countdown=60)

    return _run_async(_compute())


# ══════════════════════════════════════════════════════════════════
#  TASK 8: Cross-Tree Overallocation Detection (Beat)
# ══════════════════════════════════════════════════════════════════

@celery_app.task(name="app.tasks.detect_overallocation", bind=True, max_retries=2)
def detect_overallocation(self):
    """
    Scans active assignments across all infinite task subtrees.
    Flags employees assigned to > 3 active tasks or > 40 estimated hours.
    """
    async def _detect():
        from sqlalchemy import select, func
        from app.database import async_session_factory
        from app.models.task import Task
        from app.models.employee import Employee

        async with async_session_factory() as db:
            try:
                res = await db.execute(
                    select(
                        Task.assigned_to,
                        func.count(Task.id).label("active_task_count"),
                        func.sum(Task.estimated_hours).label("total_hours")
                    )
                    .where(
                        Task.assigned_to.isnot(None),
                        Task.status.in_(["Pending", "WIP", "Review"]),
                        Task.deleted_at.is_(None)
                    )
                    .group_by(Task.assigned_to)
                )
                conflicts = []
                for row in res.all():
                    emp_id, task_count, total_hrs = row
                    if task_count > 3 or (total_hrs and float(total_hrs) > 40):
                        emp_res = await db.execute(select(Employee.name).where(Employee.id == emp_id))
                        emp_name = emp_res.scalar() or f"Employee #{emp_id}"
                        conflicts.append({
                            "employee_id": emp_id,
                            "employee_name": emp_name,
                            "active_task_count": task_count,
                            "total_estimated_hours": float(total_hrs or 0),
                            "conflict_reason": "High workload across multiple task trees"
                        })
                return {"status": "success", "workload_conflicts": conflicts}
            except Exception as e:
                logger.error(f"[detect_overallocation] Failed: {e}")
                raise self.retry(exc=e, countdown=60)

    return _run_async(_detect())

