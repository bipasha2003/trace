"""
TRACE - Enqueueing background jobs (AGENTS.md §5, CORE.md §2.1)

Routes and services enqueue by task name, *after* committing, so a worker never
reads a row that is not there yet. Tests replace `enqueue` with a recorder: no test
reaches Redis or a worker.

`job_session()` is for the worker side: every Celery task runs on a fresh event
loop, so it gets its own engine without a pool rather than the app's pooled one.
"""

import uuid
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings


def enqueue(name: str, *args, countdown: int | None = None) -> str:
    """Send `app.tasks.<name>` to the worker; returns the job id."""
    from app.celery_app import celery_app

    job_id = str(uuid.uuid4())
    celery_app.send_task(f"app.tasks.{name}", args=list(args), countdown=countdown, task_id=job_id)
    return job_id


@asynccontextmanager
async def job_session():
    engine = create_async_engine(get_settings().DATABASE_URL, poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session
    finally:
        await engine.dispose()
