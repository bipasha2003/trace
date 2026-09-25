"""
TRACE - GitHub integration

A task *is* a GitHub issue (CORE.md §4). This client does the four things the
build needs: create an issue, set its assignees, open/close it, and commit a
markdown file. It is deliberately small and synchronous-per-request: the caller
wraps each call in the same DB transaction as the task change, so a GitHub
failure rolls the task back and the two never drift apart.

Credentials come from `system_settings` (github.token / github.api_url) with the
.env fallback — see app/services/system_settings.py.
"""

import base64
import re
from dataclasses import dataclass

import httpx
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import TraceException
from app.services.system_settings import resolve_setting

REPO_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}$")


class GitHubNotConfigured(TraceException):
    def __init__(self):
        super().__init__(
            status_code=503,
            detail=(
                "GitHub is not configured, so no issue can be created. "
                "Set github.token in Admin → Configuration, or GITHUB_TOKEN in .env."
            ),
        )


class GitHubError(TraceException):
    def __init__(self, action: str, response: httpx.Response | None = None, reason: str | None = None):
        if response is not None:
            try:
                message = response.json().get("message", response.text[:200])
            except ValueError:
                message = response.text[:200]
            reason = f"{response.status_code} {message}"
        super().__init__(status_code=502, detail=f"GitHub refused to {action}: {reason}")


@dataclass
class Issue:
    number: int
    url: str


class GitHubClient:
    def __init__(self, token: str, api_url: str = "https://api.github.com",
                 transport: httpx.AsyncBaseTransport | None = None,
                 committer: dict | None = None):
        self._token = token
        self._api_url = api_url.rstrip("/")
        self._transport = transport
        # {"name": ..., "email": ...} — author and committer of TRACE's own commits
        self._committer = committer

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._api_url,
            transport=self._transport,
            timeout=15.0,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

    async def _request(self, action: str, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            async with self._client() as client:
                response = await client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise GitHubError(action, reason=f"network error ({exc.__class__.__name__})") from exc
        if response.status_code >= 400:
            raise GitHubError(action, response)
        return response

    async def create_issue(self, repo: str, title: str, body: str,
                           assignees: list[str] | None = None) -> Issue:
        payload = {"title": title, "body": body}
        if assignees:
            payload["assignees"] = assignees
        data = (await self._request("create the issue", "POST", f"/repos/{repo}/issues", json=payload)).json()
        return Issue(number=data["number"], url=data["html_url"])

    async def set_assignees(self, repo: str, number: int, assignees: list[str]) -> None:
        await self._request("assign the issue", "PATCH", f"/repos/{repo}/issues/{number}",
                            json={"assignees": assignees})

    async def set_state(self, repo: str, number: int, open_: bool, not_planned: bool = False) -> None:
        payload = {"state": "open"} if open_ else {
            "state": "closed", "state_reason": "not_planned" if not_planned else "completed",
        }
        await self._request("update the issue state", "PATCH", f"/repos/{repo}/issues/{number}", json=payload)

    async def commit_file(self, repo: str, path: str, content: str, message: str,
                          branch: str = "main") -> str:
        """Create or update a file on `branch`; returns its html URL."""
        existing_sha = None
        try:
            async with self._client() as client:
                current = await client.get(f"/repos/{repo}/contents/{path}", params={"ref": branch})
        except httpx.HTTPError as exc:
            raise GitHubError("read the file", reason=f"network error ({exc.__class__.__name__})") from exc
        if current.status_code == 200:
            existing_sha = current.json().get("sha")
        elif current.status_code != 404:
            raise GitHubError("read the file", current)

        payload = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
        }
        if existing_sha:
            payload["sha"] = existing_sha
        if self._committer:
            payload["committer"] = self._committer
            payload["author"] = self._committer
        data = (await self._request("commit the file", "PUT", f"/repos/{repo}/contents/{path}", json=payload)).json()
        return data["content"]["html_url"]


async def get_github_client(db: AsyncSession = Depends(get_db)) -> GitHubClient | None:
    """FastAPI dependency: a configured client, or None when no token is set.

    Tests override this dependency with a client on an httpx.MockTransport.
    """
    token = await resolve_setting(db, "github", "token")
    if not token:
        return None
    name = await resolve_setting(db, "github", "committer_name")
    email = await resolve_setting(db, "github", "committer_email")
    return GitHubClient(
        token,
        await resolve_setting(db, "github", "api_url") or "https://api.github.com",
        committer={"name": name, "email": email} if name and email else None,
    )


def require_github(client: GitHubClient | None) -> GitHubClient:
    if client is None:
        raise GitHubNotConfigured()
    return client
