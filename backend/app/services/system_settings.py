"""
TRACE - Runtime settings resolution

Admin → Configuration writes `system_settings` rows; a value there wins over the
`.env` fallback (PROJECT.md §11.8). Every consumer of mail / AI / GitHub / CI-CD
credentials resolves them through `resolve_setting`, never straight from Settings.

Rows with `is_secret` are Fernet-encrypted at rest with SETTINGS_ENCRYPTION_KEY
and decrypted only here, in `resolve_setting`. No API returns a secret — callers
that describe settings ask `setting_source`, which never decrypts.
"""

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import TraceException
from app.models.project import SystemSetting

# (category, key) → Settings attribute used when no database row exists
ENV_FALLBACKS = {
    ("github", "owner"): "GITHUB_OWNER",
    ("github", "token"): "GITHUB_TOKEN",
    ("github", "api_url"): "GITHUB_API_URL",
    ("github", "committer_name"): "GITHUB_COMMITTER_NAME",
    ("github", "committer_email"): "GITHUB_COMMITTER_EMAIL",
    ("ai", "api_key"): "OPENAI_API_KEY",
    ("ai", "base_url"): "OPENAI_BASE_URL",
    ("ai", "model"): "OPENAI_MODEL",
}

# Settings that are always stored encrypted and never returned by any API
SECRET_SETTINGS = {("github", "token"), ("ai", "api_key")}


class EncryptionKeyMissing(TraceException):
    def __init__(self):
        super().__init__(
            status_code=503,
            detail="SETTINGS_ENCRYPTION_KEY is not set in .env, so secrets cannot be stored or read",
        )


def _fernet() -> Fernet:
    key = get_settings().SETTINGS_ENCRYPTION_KEY
    if not key:
        raise EncryptionKeyMissing()
    try:
        return Fernet(key.encode())
    except ValueError:
        raise TraceException(503, "SETTINGS_ENCRYPTION_KEY in .env is not a valid Fernet key") from None


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(token: str, label: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        raise TraceException(
            503,
            f"{label} cannot be decrypted — SETTINGS_ENCRYPTION_KEY has changed since it was saved. "
            "Enter it again in Admin → Configuration.",
        ) from None


async def _row(db: AsyncSession, category: str, key: str) -> SystemSetting | None:
    return (await db.execute(
        select(SystemSetting).where(
            SystemSetting.category == category,
            SystemSetting.key == key,
            SystemSetting.deleted_at.is_(None),
        )
    )).scalar_one_or_none()


def _env_value(category: str, key: str) -> str:
    attr = ENV_FALLBACKS.get((category, key))
    return getattr(get_settings(), attr, "") if attr else ""


async def resolve_setting(db: AsyncSession, category: str, key: str) -> str:
    """Database value if set and non-empty, else the .env fallback, else ''."""
    row = await _row(db, category, key)
    if row is not None and row.value:
        return decrypt_secret(row.value, f"{category}.{key}") if row.is_secret else row.value
    return _env_value(category, key)


async def setting_source(db: AsyncSession, category: str, key: str) -> str | None:
    """Where the effective value comes from — 'database', 'env', or None if unset. Never decrypts."""
    row = await _row(db, category, key)
    if row is not None and row.value:
        return "database"
    return "env" if _env_value(category, key) else None


async def store_setting(db: AsyncSession, category: str, key: str, value: str | None) -> None:
    """Write (or clear, with None / '') a database value; secrets are encrypted. Caller commits."""
    secret = (category, key) in SECRET_SETTINGS
    stored = encrypt_secret(value) if secret and value else (value or None)
    row = (await db.execute(
        select(SystemSetting).where(SystemSetting.category == category, SystemSetting.key == key)
    )).scalar_one_or_none()
    if row is None:
        db.add(SystemSetting(category=category, key=key, value=stored, is_secret=secret))
    else:
        row.value, row.is_secret, row.deleted_at = stored, secret, None
    await db.flush()
