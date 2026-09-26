"""
TRACE - Live GitHub check (opt-in; Phase 3a)

Every other test runs against the fake GitHub in conftest.py. This one talks to the
real organization in the root .env, through TRACE's own API and GitHubClient, so the
fake's assumptions get checked against GitHub itself.

    TRACE_LIVE_GITHUB=1 .venv/bin/python -m pytest -q tests/test_github_live.py -s

Each run creates ONE public repository `trace-smoke-<timestamp>` in the organization
and leaves it **archived** (the token cannot delete). Delete it by hand if you like.
Optional: TRACE_LIVE_GITHUB_INVITEE=<github username> also sends that user a real
collaborator invitation, then withdraws it.
"""

import os
import time

import pytest
from dotenv import dotenv_values
from httpx import AsyncClient

from app.config import ROOT_DIR, get_settings
from app.exceptions import TraceException
from app.main import app
from app.services.github_service import GitHubClient, get_github_client
from tests.conftest import make_user

pytestmark = pytest.mark.skipif(
    os.environ.get("TRACE_LIVE_GITHUB") != "1",
    reason="live GitHub check — set TRACE_LIVE_GITHUB=1 to run it",
)

API = "/api/v1"
ENV = dotenv_values(ROOT_DIR / ".env")  # conftest blanks the real values in os.environ


@pytest.fixture
def live(monkeypatch) -> tuple[GitHubClient, str]:
    token, owner = ENV.get("GITHUB_TOKEN"), ENV.get("GITHUB_OWNER")
    if not token or not owner:
        pytest.fail("GITHUB_TOKEN and GITHUB_OWNER must be set in the root .env")
    client = GitHubClient(token, committer={"name": "TRACE live test", "email": "trace-live-test@example.com"})
    monkeypatch.setattr(get_settings(), "GITHUB_OWNER", owner)
    app.dependency_overrides[get_github_client] = lambda: client
    return client, owner


async def test_live_project_lifecycle(client: AsyncClient, db_session, live):
    github, owner = live
    login = await github.authenticated_login()
    assert (await github.organization(owner))["login"].lower() == owner.lower()

    # Connection test endpoint, as the Admin would press it
    _, admin = await make_user(db_session, "Admin", "live_admin")
    check = (await client.post(f"{API}/admin/settings/github/test", headers=admin)).json()
    assert check["ok"], check

    # Manager creates a project → TRACE creates the public repo
    _, manager = await make_user(db_session, "Manager", "live_manager")
    name = f"TRACE Smoke {int(time.time())}"
    resp = await client.post(f"{API}/projects", headers=manager, json={
        "name": name, "description": "Automated live check of TRACE's GitHub integration. Safe to delete.",
    })
    assert resp.status_code == 201, resp.text
    project = resp.json()
    repo = project["github_repo"]
    assert repo.lower() == f"{owner}/trace-smoke-{name.split()[-1]}".lower()
    print(f"\n  created https://github.com/{repo}")

    info = (await github._request("read the repository", "GET", f"/repos/{repo}")).json()
    assert info["private"] is False and info["has_issues"] is True
    assert project["github_default_branch"] == info["default_branch"]

    # Same name again → 409, never reused
    clash = await client.post(f"{API}/projects", headers=manager, json={"name": name})
    assert clash.status_code == 409, clash.text

    # Documents commit to the auto-initialised repo, twice (create, then update by sha)
    url = await github.commit_file(repo, "docs/live-check.md", "# Live check\n", "TRACE live check")
    assert url.endswith("docs/live-check.md")
    await github.commit_file(repo, "docs/live-check.md", "# Live check\n\nupdated\n", "TRACE live check update")

    # An issue assigned to the token's own account (an org owner, so assignable)
    issue = await github.create_issue(repo, "TRACE live check", "Created by tests/test_github_live.py", [login])
    got = (await github._request("read the issue", "GET", f"/repos/{repo}/issues/{issue.number}")).json()
    assert [a["login"] for a in got["assignees"]] == [login]
    await github.set_assignees(repo, issue.number, [])
    await github.set_state(repo, issue.number, open_=False, not_planned=True)
    got = (await github._request("read the issue", "GET", f"/repos/{repo}/issues/{issue.number}")).json()
    assert got["state"] == "closed" and got["state_reason"] == "not_planned" and got["assignees"] == []

    # Optional: a real invitation, then withdrawn
    invitee = os.environ.get("TRACE_LIVE_GITHUB_INVITEE")
    if invitee:
        assert await github.add_collaborator(repo, invitee) is True  # 201 → invitation sent
        await github.remove_collaborator(repo, invitee)
        pending = (await github._request("list invitations", "GET", f"/repos/{repo}/invitations")).json()
        assert all(i["invitee"]["login"].lower() != invitee.lower() for i in pending)

    # Deleting the project archives the repo
    resp = await client.delete(f"{API}/projects/{project['id']}", headers=manager)
    assert resp.status_code == 204, resp.text
    info = (await github._request("read the repository", "GET", f"/repos/{repo}")).json()
    assert info["archived"] is True
    print(f"  archived https://github.com/{repo}")


async def test_live_unknown_org_is_reported(live):
    github, _ = live
    with pytest.raises(TraceException) as exc:
        await github.organization("trace-no-such-org-" + str(int(time.time())))
    assert "404" in exc.value.detail
