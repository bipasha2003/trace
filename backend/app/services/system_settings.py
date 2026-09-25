"""
TRACE - Runtime settings resolution

Admin → Configuration writes `system_settings` rows; a value there wins over the
`.env` fallback (PROJECT.md §11.8). Every consumer of mail / AI / GitHub / CI-CD
credentials resolves them through `resolve_setting`, never straight from Settings.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.project import SystemSetting

# (category, key) → Settings attribute used when no database row exists
ENV_FALLBACKS = {
    ("github", "token"): "GITHUB_TOKEN",
    ("github", "api_url"): "GITHUB_API_URL",
    ("github", "committer_name"): "GITHUB_COMMITTER_NAME",
    ("github", "committer_email"): "GITHUB_COMMITTER_EMAIL",
    ("ai", "api_key"): "OPENAI_API_KEY",
    ("ai", "base_url"): "OPENAI_BASE_URL",
    ("ai", "model"): "OPENAI_MODEL",
}


async def resolve_setting(db: AsyncSession, category: str, key: str) -> str:
    """Database value if set and non-empty, else the .env fallback, else ''."""
    row = (await db.execute(
        select(SystemSetting.value).where(
            SystemSetting.category == category,
            SystemSetting.key == key,
            SystemSetting.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if row:
        return row
    attr = ENV_FALLBACKS.get((category, key))
    return getattr(get_settings(), attr, "") if attr else ""
