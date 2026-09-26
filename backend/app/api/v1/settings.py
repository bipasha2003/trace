"""
TRACE - Admin → Configuration API (DEVELOPMENT.md Phase 3a; the other sections are Phase 8)

GitHub: the company organization, its token and the commit identity (CORE.md §4.1).
The token is write-only — responses say only whether one is set, and where from.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import RoleEnum, require_roles
from app.database import get_db
from app.services.github_service import (
    OWNER_PATTERN, GitHubClient, GitHubError, get_github_client,
)
from app.services.system_settings import resolve_setting, setting_source, store_setting

router = APIRouter(prefix="/admin/settings", tags=["Configuration"],
                   dependencies=[Depends(require_roles(RoleEnum.ADMIN))])

GITHUB_FIELDS = ("owner", "committer_name", "committer_email")


class GitHubSettings(BaseModel):
    owner: str
    committer_name: str
    committer_email: str
    token_set: bool
    token_source: str | None  # 'database' | 'env' | None


class GitHubSettingsUpdate(BaseModel):
    """Omitted fields are left alone. `token`: a new value replaces it, '' clears the database copy."""
    owner: str | None = Field(None, max_length=39)
    committer_name: str | None = Field(None, max_length=100)
    committer_email: str | None = Field(None, max_length=255)
    token: str | None = Field(None, max_length=500)

    @field_validator("owner")
    @classmethod
    def _owner(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().removeprefix("https://github.com/").strip("/")
        if value and not OWNER_PATTERN.match(value):
            raise ValueError("must be a GitHub organization login, e.g. acme-corp")
        return value

    @field_validator("committer_email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return value
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("must be an email address")
        return value.strip()


class ConnectionCheck(BaseModel):
    name: str
    ok: bool
    detail: str


class GitHubTestResult(BaseModel):
    ok: bool
    checks: list[ConnectionCheck]


async def _github_settings(db: AsyncSession) -> dict:
    values = {f: await resolve_setting(db, "github", f) for f in GITHUB_FIELDS}
    source = await setting_source(db, "github", "token")
    return {**values, "token_set": source is not None, "token_source": source}


@router.get("/github", response_model=GitHubSettings, summary="GitHub settings (token never returned)")
async def get_github_settings(db: AsyncSession = Depends(get_db)):
    return await _github_settings(db)


@router.put("/github", response_model=GitHubSettings, summary="Save GitHub settings (token is write-only)")
async def put_github_settings(data: GitHubSettingsUpdate, db: AsyncSession = Depends(get_db)):
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "token" and value is None:
            continue
        await store_setting(db, "github", field, value.strip() if isinstance(value, str) else value)
    await db.commit()
    return await _github_settings(db)


@router.post("/github/test", response_model=GitHubTestResult, summary="Test the saved GitHub settings")
async def test_github_settings(
    github: GitHubClient | None = Depends(get_github_client),
    db: AsyncSession = Depends(get_db),
):
    """Token authenticates · organization visible. Repo-creation rights are proven only by creating one."""
    owner = await resolve_setting(db, "github", "owner")
    checks = []
    if github is None:
        checks.append(ConnectionCheck(name="Token", ok=False, detail="No token is set"))
    else:
        try:
            login = await github.authenticated_login()
            checks.append(ConnectionCheck(name="Token", ok=True, detail=f"Authenticates as {login}"))
        except GitHubError as exc:
            checks.append(ConnectionCheck(name="Token", ok=False, detail=exc.detail))
    if not owner:
        checks.append(ConnectionCheck(name="Organization", ok=False, detail="No organization is set"))
    elif github is not None and checks[0].ok:
        try:
            org = await github.organization(owner)
            checks.append(ConnectionCheck(
                name="Organization", ok=True,
                detail=f"{org.get('name') or org.get('login', owner)} is visible to the token"))
        except GitHubError as exc:
            detail = (f"'{owner}' is not an organization this token can see — personal accounts are "
                      "not supported" if exc.github_status == 404 else exc.detail)
            checks.append(ConnectionCheck(name="Organization", ok=False, detail=detail))
    else:
        checks.append(ConnectionCheck(name="Organization", ok=False, detail="Not checked — the token failed"))
    return {"ok": all(c.ok for c in checks), "checks": checks}
