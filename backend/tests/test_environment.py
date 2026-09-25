"""
TRACE - APP_ENV separation (local / production)

`Settings.is_production` is the only place Python asks which environment it is
in; these tests pin what production changes and what it refuses.
"""

from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.cli as cli
from app.config import INSECURE_JWT_SECRETS, ROOT_DIR, Settings, get_settings
from app.core.security import verify_password
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.seeds import SEED_USERS, accounts_with_seed_passwords
from app.services.auth_service import AuthService

GOOD_SECRET = "x" * 48


def make_settings(**overrides) -> Settings:
    """Settings from explicit values only — never the developer's .env files.

    DATABASE_URL defaults to "" (derive) because conftest exports the test DB's URL.
    """
    overrides.setdefault("DATABASE_URL", "")
    return Settings(_env_file=None, **overrides)


@pytest.fixture
def fresh_settings():
    """Clear the settings cache around a test that changes environment variables."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ── One env file ─────────────────────────────────────────────────

def test_root_env_is_the_only_env_file():
    assert Settings.model_config["env_file"] == ROOT_DIR / ".env"
    assert not (ROOT_DIR / "backend" / ".env.example").exists()


def test_connection_settings_derive_from_compose_keys():
    s = make_settings(
        POSTGRES_USER="u", POSTGRES_PASSWORD="p", POSTGRES_DB="d", DB_PORT=6543,
        REDIS_PORT=6380, MINIO_ROOT_USER="mu", MINIO_ROOT_PASSWORD="mp",
        MINIO_API_PORT=9100, MAILPIT_SMTP_PORT=2025,
    )
    assert s.DATABASE_URL == "postgresql+asyncpg://u:p@localhost:6543/d"
    assert s.REDIS_URL == "redis://localhost:6380/0"
    assert s.MINIO_ENDPOINT == "localhost:9100"
    assert (s.MINIO_ACCESS_KEY, s.MINIO_SECRET_KEY) == ("mu", "mp")
    assert s.SMTP_PORT == 2025


def test_explicit_connection_settings_win():
    """The tests and the Compose app containers set these directly."""
    s = make_settings(
        DB_PORT=6543, DATABASE_URL="postgresql+asyncpg://x:y@db:5432/z",
        REDIS_URL="redis://redis:6379/0", MINIO_ACCESS_KEY="explicit", SMTP_PORT=25,
    )
    assert s.DATABASE_URL == "postgresql+asyncpg://x:y@db:5432/z"
    assert s.REDIS_URL == "redis://redis:6379/0"
    assert s.MINIO_ACCESS_KEY == "explicit"
    assert s.SMTP_PORT == 25


def test_defaults_match_docker_compose_defaults():
    """With no .env at all, the backend must reach the stack Compose starts by default."""
    compose = (ROOT_DIR / "docker-compose.yml").read_text()
    s = make_settings()
    assert '"${DB_PORT:-5433}:5432"' in compose and s.DB_PORT == 5433
    assert s.DATABASE_URL == "postgresql+asyncpg://trace_user:trace_password@localhost:5433/trace_db"
    assert s.MINIO_ACCESS_KEY == "trace_minio" and s.SMTP_PORT == 1025


# ── Settings ─────────────────────────────────────────────────────

def test_local_is_the_default():
    s = make_settings()
    assert s.APP_ENV == "local"
    assert not s.is_production
    assert s.cors_origins == s.CORS_ORIGINS
    assert s.production_problems() == []


def test_local_tolerates_development_settings():
    s = make_settings(DEBUG=True, JWT_SECRET_KEY="change-me-in-production")
    assert s.production_problems() == []


def test_unknown_app_env_is_rejected():
    with pytest.raises(ValueError):
        make_settings(APP_ENV="staging")


@pytest.mark.parametrize("url", ["trace.example.com", "https://trace.example.com/", "http://trace.example.com"])
def test_production_domain_is_normalised(url):
    s = make_settings(APP_ENV="production", PRODUCTION_URL=url, JWT_SECRET_KEY=GOOD_SECRET)
    assert s.production_domain == "trace.example.com"
    assert s.cors_origins == ["https://trace.example.com", "https://www.trace.example.com"]
    assert s.production_problems() == []


@pytest.mark.parametrize("secret", sorted(INSECURE_JWT_SECRETS) + ["short"])
def test_production_rejects_weak_jwt_secret(secret):
    s = make_settings(APP_ENV="production", PRODUCTION_URL="t.example.com", JWT_SECRET_KEY=secret)
    assert any("JWT_SECRET_KEY" in p for p in s.production_problems())


def test_production_rejects_debug_and_missing_url():
    s = make_settings(APP_ENV="production", DEBUG=True, JWT_SECRET_KEY=GOOD_SECRET)
    problems = " ".join(s.production_problems())
    assert "DEBUG" in problems
    assert "PRODUCTION_URL" in problems


def test_get_settings_refuses_production_without_leaking_secrets(monkeypatch, fresh_settings):
    """A refusal must name the problem, never echo configuration values."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PRODUCTION_URL", "t.example.com")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("JWT_SECRET_KEY", "change-me-in-production")
    monkeypatch.setenv("MINIO_SECRET_KEY", "leak-canary-9f2c")
    monkeypatch.setenv("OPENAI_API_KEY", "leak-canary-7a1d")

    with pytest.raises(RuntimeError) as exc:
        get_settings()
    message = str(exc.value)
    assert "APP_ENV=production refused" in message
    assert "DEBUG" in message and "JWT_SECRET_KEY" in message
    assert "leak-canary" not in message


# ── Seeds and default credentials ────────────────────────────────

async def test_production_does_not_seed_demo_accounts(monkeypatch, fresh_settings, db_session):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PRODUCTION_URL", "t.example.com")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", GOOD_SECRET)

    import app.seeds as seeds

    @asynccontextmanager
    async def _test_session():
        yield db_session

    monkeypatch.setattr(seeds, "async_session_factory", _test_session)
    await seeds.run_seeds()

    assert await accounts_with_seed_passwords(db_session) == []
    for u in SEED_USERS:
        found = (await db_session.execute(
            User.__table__.select().where(User.email == u["email"])
        )).first()
        assert found is None, f"{u['email']} was seeded in production"


async def _seed_account(db: AsyncSession, index: int = 0) -> dict:
    u = SEED_USERS[index]
    await AuthService(db).register(RegisterRequest(
        name=u["name"], username=u["username"], email=u["email"],
        password=u["password"], role=u["role"],
    ))
    return u


async def test_seed_password_guard_flags_published_passwords(db_session):
    u = await _seed_account(db_session)
    assert await accounts_with_seed_passwords(db_session) == [u["email"]]


async def test_set_password_clears_the_guard(monkeypatch, db_session):
    u = await _seed_account(db_session)

    @asynccontextmanager
    async def _test_session():
        yield db_session

    monkeypatch.setattr(cli, "async_session_factory", _test_session)
    await cli.set_password(u["email"], "a-much-better-passphrase")

    assert await accounts_with_seed_passwords(db_session) == []
    user = (await db_session.execute(
        User.__table__.select().where(User.email == u["email"])
    )).first()
    assert verify_password("a-much-better-passphrase", user.password)


async def test_set_password_rejects_short_passwords(db_session):
    u = await _seed_account(db_session)
    with pytest.raises(SystemExit):
        await cli.set_password(u["email"], "short")
