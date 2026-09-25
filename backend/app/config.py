"""
TRACE - Application Configuration
Loads settings from environment variables using pydantic-settings.

There is one env file: the repo-root ``.env``, shared with Docker Compose,
start.sh and the Vite config. Real environment variables override it.

Connection settings (DATABASE_URL, REDIS_URL, MINIO_*, SMTP_PORT) are derived
from the same infrastructure keys Docker Compose uses (POSTGRES_*, DB_PORT,
MINIO_ROOT_*, ...), so each value is written once. Setting one explicitly —
as the tests and the Compose app containers do — still wins.

``Settings.is_production`` is the one place Python code asks which environment it
is in. Do not compare APP_ENV anywhere else.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent

# Placeholder JWT secrets that must never reach production
INSECURE_JWT_SECRETS = {
    "change-me-in-production",
    "your-super-secret-key-change-in-production",
}


class Settings(BaseSettings):
    """Application settings loaded from the root .env file."""

    # ── Infrastructure (shared with docker-compose.yml) ──────────
    POSTGRES_USER: str = "trace_user"
    POSTGRES_PASSWORD: str = "trace_password"
    POSTGRES_DB: str = "trace_db"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5433
    REDIS_PORT: int = 6379
    MINIO_ROOT_USER: str = "trace_minio"
    MINIO_ROOT_PASSWORD: str = "trace_minio_secret"
    MINIO_API_PORT: int = 9000
    MAILPIT_SMTP_PORT: int = 1025

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "TRACE"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Environment ──────────────────────────────────────────────
    # local: developer machine. production: served publicly through the
    # Cloudflare tunnel at PRODUCTION_URL. Read via `is_production` only.
    APP_ENV: Literal["local", "production"] = "local"
    PRODUCTION_URL: str = ""  # bare domain, e.g. "trace.example.com"

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = ""  # derived from POSTGRES_* / DB_HOST / DB_PORT when empty
    DATABASE_ECHO: bool = False

    # ── JWT Authentication ───────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ─────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Redis ────────────────────────────────────────────────────
    REDIS_URL: str = ""  # derived from REDIS_PORT when empty

    # ── Email (SendGrid) ─────────────────────────────────────────
    SENDGRID_API_KEY: str = ""
    ADMIN_EMAIL: str = "admin@trace.com"


    # ── MinIO (S3-Compatible Storage) ────────────────────────────
    MINIO_ENDPOINT: str = ""  # derived from MINIO_API_PORT when empty
    MINIO_ACCESS_KEY: str = ""  # defaults to MINIO_ROOT_USER
    MINIO_SECRET_KEY: str = ""  # defaults to MINIO_ROOT_PASSWORD
    MINIO_BUCKET: str = "trace-uploads"
    MINIO_SECURE: bool = False

    # ── Mailpit (SMTP) ──────────────────────────────────────────
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int | None = None  # defaults to MAILPIT_SMTP_PORT
    SMTP_FROM: str = "noreply@trace.com"

    # ── GitHub (fallback — Admin → Configuration overrides) ──────
    GITHUB_TOKEN: str = ""
    GITHUB_API_URL: str = "https://api.github.com"
    # Identity on the commits TRACE makes into project repos (generated docs).
    # Empty → GitHub attributes them to the token's own account.
    GITHUB_COMMITTER_NAME: str = ""
    GITHUB_COMMITTER_EMAIL: str = ""

    # ── OpenAI SDK (LLM) ────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    @model_validator(mode="after")
    def _derive_connection_settings(self) -> "Settings":
        """Fill connection settings from the shared infrastructure keys."""
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.POSTGRES_DB}"
            )
        if not self.REDIS_URL:
            self.REDIS_URL = f"redis://localhost:{self.REDIS_PORT}/0"
        if not self.MINIO_ENDPOINT:
            self.MINIO_ENDPOINT = f"localhost:{self.MINIO_API_PORT}"
        self.MINIO_ACCESS_KEY = self.MINIO_ACCESS_KEY or self.MINIO_ROOT_USER
        self.MINIO_SECRET_KEY = self.MINIO_SECRET_KEY or self.MINIO_ROOT_PASSWORD
        if self.SMTP_PORT is None:
            self.SMTP_PORT = self.MAILPIT_SMTP_PORT
        return self

    # ── Environment helpers ─────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def production_domain(self) -> str:
        """PRODUCTION_URL without scheme or trailing slash."""
        return self.PRODUCTION_URL.strip().removeprefix("https://").removeprefix("http://").rstrip("/")

    @property
    def cors_origins(self) -> list[str]:
        if self.is_production:
            domain = self.production_domain
            return [f"https://{domain}", f"https://www.{domain}"]
        return self.CORS_ORIGINS

    def production_problems(self) -> list[str]:
        """Settings that must not reach a public deployment. Empty when local."""
        if not self.is_production:
            return []
        problems = []
        if not self.production_domain:
            problems.append("PRODUCTION_URL is empty (.env)")
        if self.DEBUG:
            problems.append("DEBUG must be false — it leaks exception details to clients (.env)")
        if self.JWT_SECRET_KEY in INSECURE_JWT_SECRETS or len(self.JWT_SECRET_KEY) < 32:
            problems.append(
                "JWT_SECRET_KEY is a placeholder or shorter than 32 characters (.env) — "
                'generate one with: python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return problems

    model_config = {
        "env_file": ROOT_DIR / ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance (loaded once per process).

    Refuses a production configuration with development settings. Raised here,
    not in a pydantic validator, because a ValidationError echoes every input
    value — secrets included — into the terminal and logs.
    """
    settings = Settings()
    if problems := settings.production_problems():
        raise RuntimeError("APP_ENV=production refused:\n  - " + "\n  - ".join(problems))
    return settings
