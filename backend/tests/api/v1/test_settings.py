"""
TRACE - Phase 3a: Admin → Configuration → GitHub (CORE.md §4.1)

The token is encrypted at rest, decrypted only by resolve_setting, and never
returned by any API. The connection test checks the token and the organization.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.project import SystemSetting
from app.services.system_settings import resolve_setting
from tests.conftest import FakeGitHub

URL = "/api/v1/admin/settings/github"
TOKEN = "github_pat_11AAAAAAA0_secretsecretsecret"


async def _row(db: AsyncSession, key: str) -> SystemSetting | None:
    return (await db.execute(select(SystemSetting).where(
        SystemSetting.category == "github", SystemSetting.key == key))).scalar_one_or_none()


async def test_defaults_come_from_env(client: AsyncClient, admin_headers):
    body = (await client.get(URL, headers=admin_headers)).json()
    assert body["owner"] == "acme"  # GITHUB_OWNER, pinned by conftest
    assert body["token_set"] is False and body["token_source"] is None
    assert "token" not in body


async def test_token_is_encrypted_at_rest_and_never_returned(client: AsyncClient, admin_headers,
                                                             db_session: AsyncSession):
    resp = await client.put(URL, headers=admin_headers, json={
        "owner": "https://github.com/acme-corp/", "token": TOKEN,
        "committer_name": "TRACE Bot", "committer_email": "bot@acme.test",
    })
    assert resp.status_code == 200, resp.text
    assert TOKEN not in resp.text
    assert resp.json() == {"owner": "acme-corp", "committer_name": "TRACE Bot",
                           "committer_email": "bot@acme.test", "token_set": True, "token_source": "database"}

    row = await _row(db_session, "token")
    assert row.is_secret and row.value and TOKEN not in row.value
    assert await resolve_setting(db_session, "github", "token") == TOKEN
    assert TOKEN not in (await client.get(URL, headers=admin_headers)).text


async def test_omitting_the_token_keeps_it_and_empty_clears_it(client: AsyncClient, admin_headers,
                                                               db_session: AsyncSession):
    await client.put(URL, headers=admin_headers, json={"token": TOKEN})
    kept = await client.put(URL, headers=admin_headers, json={"committer_name": "Someone"})
    assert kept.json()["token_set"] is True
    assert await resolve_setting(db_session, "github", "token") == TOKEN

    cleared = await client.put(URL, headers=admin_headers, json={"token": ""})
    assert cleared.json()["token_set"] is False


@pytest.mark.parametrize("payload", [
    {"owner": "not an org"}, {"owner": "-leading-dash"}, {"committer_email": "nope"},
])
async def test_bad_values_are_refused(client: AsyncClient, admin_headers, payload):
    assert (await client.put(URL, headers=admin_headers, json=payload)).status_code == 422


async def test_changed_encryption_key_is_a_clear_error(client: AsyncClient, admin_headers,
                                                       db_session: AsyncSession, monkeypatch):
    from app.exceptions import TraceException
    await client.put(URL, headers=admin_headers, json={"token": TOKEN})
    from cryptography.fernet import Fernet
    monkeypatch.setattr(get_settings(), "SETTINGS_ENCRYPTION_KEY", Fernet.generate_key().decode())
    with pytest.raises(TraceException, match="cannot be decrypted"):
        await resolve_setting(db_session, "github", "token")


@pytest.mark.parametrize("key", ["", "not-a-fernet-key"])
async def test_no_usable_encryption_key_refuses_to_store_a_secret(client: AsyncClient, admin_headers,
                                                                  monkeypatch, key):
    monkeypatch.setattr(get_settings(), "SETTINGS_ENCRYPTION_KEY", key)
    resp = await client.put(URL, headers=admin_headers, json={"token": TOKEN})
    assert resp.status_code == 503 and "SETTINGS_ENCRYPTION_KEY" in resp.json()["detail"]


async def test_generic_admin_crud_does_not_expose_settings(client: AsyncClient, admin_headers):
    tables = (await client.get("/api/v1/admin/tables", headers=admin_headers)).json()
    assert "system_settings" not in str(tables)
    assert (await client.get("/api/v1/admin/tables/system_settings", headers=admin_headers)).status_code in (400, 404)


# ── Test connection ─────────────────────────────────────────────

async def test_connection_ok(client: AsyncClient, admin_headers, fake_github: FakeGitHub):
    body = (await client.post(f"{URL}/test", headers=admin_headers)).json()
    assert body["ok"] is True
    assert [c["name"] for c in body["checks"]] == ["Token", "Organization"]
    assert "trace-bot" in body["checks"][0]["detail"]


async def test_connection_personal_account_or_unknown_org(client: AsyncClient, admin_headers, fake_github):
    await client.put(URL, headers=admin_headers, json={"owner": "someone"})
    body = (await client.post(f"{URL}/test", headers=admin_headers)).json()
    assert body["ok"] is False and "personal accounts are not supported" in body["checks"][1]["detail"]


async def test_connection_bad_token(client: AsyncClient, admin_headers, fake_github):
    fake_github.fail_with = 401
    body = (await client.post(f"{URL}/test", headers=admin_headers)).json()
    assert body["ok"] is False
    assert not body["checks"][0]["ok"] and "401" in body["checks"][0]["detail"]
    assert body["checks"][1]["detail"] == "Not checked — the token failed"


async def test_connection_without_token(client: AsyncClient, admin_headers):
    body = (await client.post(f"{URL}/test", headers=admin_headers)).json()
    assert body["ok"] is False and body["checks"][0]["detail"] == "No token is set"


# ── Production preflight ────────────────────────────────────────

def _production(**overrides):
    from app.config import Settings
    return Settings(APP_ENV="production", PRODUCTION_URL="trace.example.com", DEBUG=False,
                    JWT_SECRET_KEY="x" * 40, **overrides)


def test_production_requires_an_encryption_key():
    assert any("SETTINGS_ENCRYPTION_KEY is empty" in p
               for p in _production(SETTINGS_ENCRYPTION_KEY="").production_problems())
    assert any("not a valid Fernet key" in p
               for p in _production(SETTINGS_ENCRYPTION_KEY="short").production_problems())
    assert _production(SETTINGS_ENCRYPTION_KEY=get_settings().SETTINGS_ENCRYPTION_KEY).production_problems() == []
