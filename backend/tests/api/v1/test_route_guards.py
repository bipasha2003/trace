"""
TRACE - Platform-role route guards (DEVELOPMENT.md Phase 2 step 6)

Two layers:
- a static audit that every route declares an auth dependency, so a new
  unguarded endpoint fails the suite rather than shipping;
- a role matrix that calls real endpoints as Admin, Manager, Employee and an
  anonymous caller, and checks who gets in.
"""

import pytest
from fastapi.routing import APIRoute
from httpx import AsyncClient

from app.main import app

# The only routes reachable without a token — AGENTS.md §4.
PUBLIC_ROUTES = {
    ("GET", "/health"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/refresh"),
    ("POST", "/api/v1/auth/register"),
}

# Dependency callables that authenticate the caller. `role_checker` is the closure
# built by app.core.permissions.require_roles; `require_admin` is admin.py's own.
AUTH_DEPENDENCIES = {"get_current_user", "role_checker", "require_admin"}

# Anonymous callers: a missing Authorization header is a 422, a bad one a 401.
ANONYMOUS_REJECTED = {401, 422}


def _dependency_names(dependant) -> set[str]:
    names = set()
    for sub in dependant.dependencies:
        names.add(getattr(sub.call, "__name__", ""))
        names |= _dependency_names(sub)
    return names


def test_every_route_declares_an_auth_guard():
    unguarded = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods:
            if (method, route.path) in PUBLIC_ROUTES:
                continue
            if not _dependency_names(route.dependant) & AUTH_DEPENDENCIES:
                unguarded.append(f"{method} {route.path}")
    assert not unguarded, f"Routes with no auth guard: {sorted(unguarded)}"


def test_public_routes_still_exist():
    """Guard the allow-list itself: a renamed public route must not linger here."""
    registered = {
        (m, r.path) for r in app.routes if isinstance(r, APIRoute) for m in r.methods
    }
    assert PUBLIC_ROUTES <= registered


# ── Role matrix ──────────────────────────────────────────────────

ADMIN = {"Admin"}
ADMIN_MANAGER = {"Admin", "Manager"}
ANY_ROLE = {"Admin", "Manager", "Employee"}

# Endpoints safe to call for real: no external service, no seeded data needed.
ROLE_MATRIX = [
    ("GET", "/api/v1/hrms/holidays", ADMIN),
    ("GET", "/api/v1/hrms/shifts", ADMIN),
    ("GET", "/api/v1/hrms/leaves", ADMIN),
    ("GET", "/api/v1/hrms/leave-balance/summary", ADMIN),
    ("GET", "/api/v1/attendance/all", ADMIN),
    ("GET", "/api/v1/attendance/summary/daily", ADMIN),
    ("GET", "/api/v1/employees", ADMIN),
    ("GET", "/api/v1/work-schedules", ADMIN),
    ("GET", "/api/v1/productivity/scores", ADMIN),
    ("GET", "/api/v1/reports/weekly-summary", ADMIN),
    ("GET", "/api/v1/reports/attendance-summary", ADMIN),
    ("GET", "/api/v1/dashboard/stats", ADMIN),
    ("GET", "/api/v1/admin/tables", ADMIN),
    ("GET", "/api/v1/users", ADMIN_MANAGER),
    ("GET", "/api/v1/users/me", ANY_ROLE),
    ("GET", "/api/v1/departments", ANY_ROLE),
    ("GET", "/api/v1/designations", ANY_ROLE),
]

# Admin-only endpoints whose handlers reach live services (SMTP, MinIO, LLM,
# Celery). Only the refusals are asserted — the guard runs before the handler.
ADMIN_ONLY_DENIAL_CHECKS = [
    ("GET", "/api/v1/services/health/all", None),
    ("GET", "/api/v1/services/health/database", None),
    ("GET", "/api/v1/services/health/llm", None),
    ("GET", "/api/v1/services/ws/chat/status", None),
    ("POST", "/api/v1/services/mail/send", {"to": "a@b.co", "subject": "s", "body": "b"}),
    ("POST", "/api/v1/services/llm/chat", {"message": "hi"}),
    ("POST", "/api/v1/hrms/holidays", {"name": "X", "holiday_date": "2026-12-25"}),
    ("DELETE", "/api/v1/hrms/leaves/999999", None),
    ("POST", "/api/v1/employees", {"user_id": 1, "employee_code": "EMP-X"}),
    ("POST", "/api/v1/departments", {"name": "Blocked Dept"}),
    ("POST", "/api/v1/productivity/compute-all", None),
]


def _matrix_id(case):
    return f"{case[0]} {case[1]}"


@pytest.mark.parametrize("method,path,allowed", ROLE_MATRIX, ids=map(_matrix_id, ROLE_MATRIX))
@pytest.mark.parametrize("role", ["Admin", "Manager", "Employee", None])
async def test_role_matrix(client: AsyncClient, role_headers, role, method, path, allowed):
    resp = await client.request(method, path, headers=role_headers[role])
    if role is None:
        assert resp.status_code in ANONYMOUS_REJECTED, resp.text
    elif role in allowed:
        assert resp.status_code == 200, f"{role} should reach {path}: {resp.text}"
    else:
        assert resp.status_code == 403, f"{role} should be refused {path}: {resp.text}"


@pytest.mark.parametrize(
    "method,path,body", ADMIN_ONLY_DENIAL_CHECKS, ids=map(_matrix_id, ADMIN_ONLY_DENIAL_CHECKS),
)
@pytest.mark.parametrize("role", ["Manager", "Employee", None])
async def test_admin_only_endpoints_refuse_others(
    client: AsyncClient, role_headers, role, method, path, body,
):
    resp = await client.request(method, path, headers=role_headers[role], json=body)
    expected = ANONYMOUS_REJECTED if role is None else {403}
    assert resp.status_code in expected, resp.text


@pytest.mark.parametrize("role", ["Admin", "Manager", "Employee"])
async def test_every_role_may_poll_a_job_result(client: AsyncClient, role_headers, role):
    """Every AI action is enqueue-and-poll (AGENTS.md §5), so polling is open to all roles."""
    resp = await client.get(
        "/api/v1/services/task/00000000-0000-0000-0000-000000000000/result",
        headers=role_headers[role],
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "PENDING"


async def test_anonymous_may_not_poll_a_job_result(client: AsyncClient):
    resp = await client.get("/api/v1/services/task/any/result")
    assert resp.status_code in ANONYMOUS_REJECTED
