"""
TRACE - FastAPI Application Factory
Entry point for the TRACE backend application.
"""

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.config import get_settings
from app.middleware import setup_middleware

settings = get_settings()

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("trace")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — seeds reference data on startup.

    The schema is owned by Alembic alone (`./start.sh migrate`). Never call
    `Base.metadata.create_all` here: it builds tables no revision knows about,
    and a fresh database then cannot reach head.
    """
    from app.database import async_session_factory
    from app.seeds import accounts_with_seed_passwords, run_seeds

    try:
        await run_seeds()
    except Exception as e:
        logger.warning(f"Seed script encountered an issue: {e}")

    if settings.is_production:
        async with async_session_factory() as db:
            weak = await accounts_with_seed_passwords(db)
        if weak:
            raise RuntimeError(
                "APP_ENV=production refused: these accounts still use their published seed "
                f"password: {', '.join(weak)}. Change each with `./start.sh set-password <email>`."
            )

    yield

    # ── Shutdown ─────────────────────────────────────────────────
    logger.info("TRACE shutting down.")


def create_app() -> FastAPI:
    """Application factory for TRACE."""

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "TRACE — Task and Resource Attendance and Comprehensive Evaluation System. "
            "AI-powered workforce management with geo-fenced attendance, "
            "task tracking, and productivity scoring."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────
    setup_middleware(app)

    # ── Routers ──────────────────────────────────────────────────
    app.include_router(v1_router)

    # ── Health Check ─────────────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    return app


# ── Create the app instance ─────────────────────────────────────
app = create_app()
