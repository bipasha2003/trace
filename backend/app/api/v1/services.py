"""
TRACE - Service Health & Monitoring API
Comprehensive health checks for all infrastructure services.
Includes: API, DB, Redis, Celery Worker, Celery Beat, Mailpit, MinIO, LLM.
Also: WebSocket chat, test mail, test upload, LLM chat endpoints.
"""

import asyncio
import json
import logging
import smtplib
import time
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("trace.services")

router = APIRouter(prefix="/services", tags=["Services"])


# ══════════════════════════════════════════════════════════════════
#  SCHEMAS
# ══════════════════════════════════════════════════════════════════

class MailRequest(BaseModel):
    to: str
    subject: str
    body: str


class LLMChatRequest(BaseModel):
    message: str
    model: Optional[str] = None


class FileUploadResponse(BaseModel):
    status: str
    task_id: Optional[str] = None
    filename: Optional[str] = None
    message: str


# ══════════════════════════════════════════════════════════════════
#  HEALTH CHECK ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@router.get("/health/all")
async def all_service_health():
    """Aggregate health check for all services."""
    results = {}

    # API Health
    results["api"] = {"status": "healthy", "uptime": True}

    # DB Health
    results["database"] = await _check_db_health()

    # Redis Health
    results["redis"] = await _check_redis_health()

    # Celery Worker Health
    results["celery_worker"] = _check_celery_worker_health()

    # Celery Beat Health
    results["celery_beat"] = _check_celery_beat_health()

    # Mailpit Health
    results["mailpit"] = _check_mailpit_health()

    # MinIO Health
    results["minio"] = _check_minio_health()

    # LLM Health
    results["llm"] = _check_llm_config()

    # WebSocket (always available if API is up)
    results["websocket"] = {"status": "healthy", "endpoint": "/api/v1/services/ws/chat"}

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": results,
    }


@router.get("/health/api")
async def api_health():
    return {"status": "healthy", "service": "api", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@router.get("/health/database")
async def database_health():
    return await _check_db_health()


@router.get("/health/redis")
async def redis_health():
    return await _check_redis_health()


@router.get("/health/celery-worker")
async def celery_worker_health():
    return _check_celery_worker_health()


@router.get("/health/celery-beat")
async def celery_beat_health():
    return _check_celery_beat_health()


@router.get("/health/mailpit")
async def mailpit_health():
    return _check_mailpit_health()


@router.get("/health/minio")
async def minio_health():
    return _check_minio_health()


@router.get("/health/llm")
async def llm_health():
    return _check_llm_config()


# ══════════════════════════════════════════════════════════════════
#  HEALTH CHECK HELPERS
# ══════════════════════════════════════════════════════════════════

async def _check_db_health():
    try:
        from app.database import async_session_factory
        async with async_session_factory() as db:
            from sqlalchemy import text
            result = await db.execute(text("SELECT 1"))
            row = result.scalar()
            if row == 1:
                # Get DB version
                ver = await db.execute(text("SELECT version()"))
                version = ver.scalar()
                return {
                    "status": "healthy",
                    "service": "database",
                    "version": version.split(",")[0] if version else "unknown",
                    "connection": settings.DATABASE_URL.split("@")[-1].split("/")[0] if "@" in settings.DATABASE_URL else "unknown",
                }
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        return {"status": "unhealthy", "service": "database", "error": str(e)}


async def _check_redis_health():
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pong = await r.ping()
        info = await r.info("server")
        await r.aclose()
        return {
            "status": "healthy" if pong else "unhealthy",
            "service": "redis",
            "version": info.get("redis_version", "unknown"),
            "url": settings.REDIS_URL.split("@")[-1] if "@" in settings.REDIS_URL else settings.REDIS_URL,
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {"status": "unhealthy", "service": "redis", "error": str(e)}


def _check_celery_worker_health():
    try:
        from app.celery_app import celery_app
        inspector = celery_app.control.inspect(timeout=3.0)
        active = inspector.active()
        stats = inspector.stats()
        if active is not None:
            worker_names = list(active.keys())
            active_tasks = sum(len(v) for v in active.values())
            return {
                "status": "healthy",
                "service": "celery_worker",
                "workers": worker_names,
                "active_tasks": active_tasks,
                "pool": stats[worker_names[0]].get("pool", {}).get("implementation", "unknown") if stats and worker_names else "unknown",
            }
        return {"status": "unhealthy", "service": "celery_worker", "error": "No workers responding"}
    except Exception as e:
        logger.error(f"Celery worker health check failed: {e}")
        return {"status": "unhealthy", "service": "celery_worker", "error": str(e)}


def _check_celery_beat_health():
    try:
        from app.celery_app import celery_app
        schedule = celery_app.conf.beat_schedule
        task_names = list(schedule.keys()) if schedule else []
        # Check if beat is running via inspector
        inspector = celery_app.control.inspect(timeout=3.0)
        active = inspector.active()
        # Beat doesn't register as a worker, so we check if schedule is configured
        # and if redis is reachable (beat uses same broker)
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        r.close()
        return {
            "status": "healthy",
            "service": "celery_beat",
            "scheduled_tasks": task_names,
            "task_count": len(task_names),
        }
    except Exception as e:
        logger.error(f"Celery beat health check failed: {e}")
        return {"status": "unhealthy", "service": "celery_beat", "error": str(e)}


def _check_mailpit_health():
    try:
        sock = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=5)
        sock.ehlo()
        sock.quit()
        return {
            "status": "healthy",
            "service": "mailpit",
            "smtp": f"{settings.SMTP_HOST}:{settings.SMTP_PORT}",
            "ui_url": f"http://localhost:8025",
        }
    except Exception as e:
        logger.error(f"Mailpit health check failed: {e}")
        return {"status": "unhealthy", "service": "mailpit", "error": str(e)}


def _check_minio_health():
    try:
        from minio import Minio
        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        # Check if bucket exists, create if not
        if not client.bucket_exists(settings.MINIO_BUCKET):
            client.make_bucket(settings.MINIO_BUCKET)
        buckets = [b.name for b in client.list_buckets()]
        return {
            "status": "healthy",
            "service": "minio",
            "endpoint": settings.MINIO_ENDPOINT,
            "bucket": settings.MINIO_BUCKET,
            "buckets": buckets,
            "console_url": f"http://localhost:9001",
        }
    except Exception as e:
        logger.error(f"MinIO health check failed: {e}")
        return {"status": "unhealthy", "service": "minio", "error": str(e)}


def _check_llm_config():
    configured = bool(settings.OPENAI_API_KEY)
    return {
        "status": "configured" if configured else "not_configured",
        "service": "llm",
        "model": settings.OPENAI_MODEL,
        "base_url": settings.OPENAI_BASE_URL or "https://api.openai.com/v1",
        "note": "LLM health cannot be actively checked — use the test chatbox instead.",
    }


# ══════════════════════════════════════════════════════════════════
#  WEBSOCKET CHAT
# ══════════════════════════════════════════════════════════════════

class ConnectionManager:
    """Manages WebSocket connections for the chat feature."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        await self.broadcast_system(f"User {client_id[:8]} joined the chat")

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)

    async def send_personal(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, sender_id: str):
        payload = json.dumps({
            "type": "message",
            "sender": sender_id[:8],
            "content": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_text(payload)
            except Exception:
                pass

    async def broadcast_system(self, message: str):
        payload = json.dumps({
            "type": "system",
            "content": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        for connection in self.active_connections.values():
            try:
                await connection.send_text(payload)
            except Exception:
                pass

    def get_online_count(self):
        return len(self.active_connections)


manager = ConnectionManager()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    client_id = str(uuid.uuid4())
    await manager.connect(websocket, client_id)
    try:
        # Send welcome message
        welcome = json.dumps({
            "type": "welcome",
            "client_id": client_id[:8],
            "online": manager.get_online_count(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await websocket.send_text(welcome)

        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data, client_id)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await manager.broadcast_system(f"User {client_id[:8]} left the chat")


@router.get("/ws/chat/status")
async def ws_chat_status():
    """Get current WebSocket chat status."""
    return {
        "online_users": manager.get_online_count(),
        "status": "active",
    }


# ══════════════════════════════════════════════════════════════════
#  CELERY-POWERED ACTIONS: Mail, File Upload, LLM
# ══════════════════════════════════════════════════════════════════

@router.post("/mail/send")
async def send_test_mail(request: MailRequest):
    """Send a test email via Celery task (through Mailpit SMTP)."""
    from app.tasks import send_mail_task
    task = send_mail_task.delay(request.to, request.subject, request.body)
    return {
        "status": "queued",
        "task_id": task.id,
        "message": f"Mail to {request.to} queued via Celery",
    }


@router.post("/minio/upload")
async def upload_test_file(file: UploadFile = File(...)):
    """Upload a file to MinIO via Celery task."""
    content = await file.read()
    import base64
    encoded = base64.b64encode(content).decode("utf-8")

    from app.tasks import upload_file_task
    task = upload_file_task.delay(file.filename, encoded, file.content_type)
    return {
        "status": "queued",
        "task_id": task.id,
        "filename": file.filename,
        "message": f"File '{file.filename}' upload queued via Celery",
    }


@router.post("/llm/chat")
async def llm_chat(request: LLMChatRequest):
    """Send a message to the LLM via Celery task."""
    from app.tasks import llm_chat_task
    task = llm_chat_task.delay(request.message, request.model)
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "LLM request queued via Celery",
    }


@router.get("/task/{task_id}/result")
async def get_task_result(task_id: str):
    """Get the result of a Celery task by ID."""
    from app.celery_app import celery_app
    result = celery_app.AsyncResult(task_id)
    response = {
        "task_id": task_id,
        "status": result.status,
    }
    if result.ready():
        if result.successful():
            response["result"] = result.result
        else:
            response["error"] = str(result.result)
    return response
