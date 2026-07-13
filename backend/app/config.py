"""
TRACE - Application Configuration
Loads settings from environment variables using pydantic-settings.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "TRACE"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://trace_user:trace_password@localhost:5432/trace_db"
    DATABASE_ECHO: bool = False

    # ── JWT Authentication ───────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ─────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Redis ────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Email (SendGrid) ─────────────────────────────────────────
    SENDGRID_API_KEY: str = ""
    ADMIN_EMAIL: str = "admin@trace.com"

    # ── Geo-Fence ────────────────────────────────────────────────
    DEFAULT_GEO_FENCE_RADIUS_METERS: int = 200

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance (loaded once per process)."""
    return Settings()
