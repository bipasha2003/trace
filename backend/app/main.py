"""
TRACE - FastAPI Application Factory
Entry point for the TRACE backend application.
"""

import logging

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
