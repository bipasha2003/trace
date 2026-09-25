"""
TRACE - Phase 3: projects, team, task groups and tasks — the manual path, no AI

DEVELOPMENT.md Phase 3 "Done when": a Manager creates a project and assigns a PM,
and that PM creates tasks that appear as GitHub issues. Plus the rules around it:
project-scoped authorisation (PROJECT.md §4, §16) and completion authority
(CORE.md §7).
"""

import io
from dataclasses import dataclass

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Notification
from tests.conftest import FakeGitHub, make_user

API = "/api/v1"


@dataclass
class World:
    manager: dict
    other_manager: dict
    admin: dict
    pm: dict
    pm_id: int
    dev: dict           # Employee with a GitHub username
    dev_id: int
    newbie: dict        # Employee without a GitHub username
    newbie_id: int
    outsider: dict      # Employee on no project
    project_id: int


@pytest.fixture
async def world(client: AsyncClient, db_session: AsyncSession) -> World:
    _, manager = await make_user(db_session, "Manager", "mgr_one")
    _, other_manager = await make_user(db_session, "Manager", "mgr_two")
    _, admin = await make_user(db_session, "Admin", "the_admin")
    pm_id, pm = await make_user(db_session, "Employee", "pm_priya", github_username="priya-gh")
    dev_id, dev = await make_user(db_session, "Employee", "dev_dan", github_username="dan-gh")
    newbie_id, newbie = await make_user(db_session, "Employee", "new_nia")
    _, outsider = await make_user(db_session, "Employee", "out_omar")

    resp = await client.post(f"{API}/projects", headers=manager, json={
        "name": "Storefront", "description": "Online shop", "github_repo": "acme/storefront",
    })
    assert resp.status_code == 201, resp.text
    project_id = resp.json()["id"]
    resp = await client.post(f"{API}/projects/{project_id}/assignments", headers=manager, json={"user_id": pm_id})
    assert resp.status_code == 201, resp.text
    return World(manager, other_manager, admin, pm, pm_id, dev, dev_id, newbie, newbie_id, outsider, project_id)


async def _group(client, w: World, name="Checkout") -> int:
    resp = await client.post(f"{API}/projects/{w.project_id}/task-groups", headers=w.pm, json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _task(client, w: World, group_id: int, assignee: int | None = None, **extra) -> dict:
    resp = await client.post(f"{API}/projects/{w.project_id}/tasks", headers=w.pm, json={
        "title": "Build the cart", "task_group_id": group_id, "assigned_to_user_id": assignee, **extra,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


# ══════════════════════════════════════════════════════════════════
#  The Phase 3 "Done when", end to end
# ══════════════════════════════════════════════════════════════════

async def test_manager_to_pm_to_github_issue(client: AsyncClient, world: World, fake_github: FakeGitHub):
    group_id = await _group(client, world)
    body = await _task(client, world, group_id, assignee=world.dev_id, description="Cart with coupons")

    task = body["task"]
    assert body["warnings"] == []
    assert task["github_issue_id"] == "1"
    assert task["github_issue_url"] == "https://github.com/acme/storefront/issues/1"
    issue = fake_github.issues[("acme/storefront", 1)]
    assert issue["title"] == "Build the cart"
    assert issue["assignees"] == ["dan-gh"]
    assert "Cart with coupons" in issue["body"] and "commit messages" in issue["body"]


# ══════════════════════════════════════════════════════════════════
#  Projects
# ══════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("who", ["admin", "pm"])
async def test_only_managers_create_projects(client: AsyncClient, world: World, who: str):
    resp = await client.post(f"{API}/projects", headers=getattr(world, who),
                             json={"name": "Nope", "github_repo": "acme/nope"})
    assert resp.status_code == 403


@pytest.mark.parametrize("repo,expected", [
    ("https://github.com/acme/app.git", "acme/app"), ("acme/app", "acme/app"),
])
async def test_repo_is_normalised(client: AsyncClient, world: World, repo, expected):
    resp = await client.post(f"{API}/projects", headers=world.manager, json={"name": "Repo", "github_repo": repo})
    assert resp.status_code == 201
    assert resp.json()["github_repo"] == expected
    assert resp.json()["status"] == "Draft"


@pytest.mark.parametrize("repo", ["not a repo", "acme", "acme/app/extra", ""])
async def test_bad_repo_is_rejected(client: AsyncClient, world: World, repo):
    resp = await client.post(f"{API}/projects", headers=world.manager, json={"name": "Repo", "github_repo": repo})
    assert resp.status_code == 422


async def test_managers_see_only_their_own_projects(client: AsyncClient, world: World):
    mine = await client.get(f"{API}/projects", headers=world.manager)
    assert [p["id"] for p in mine.json()] == [world.project_id]
    theirs = await client.get(f"{API}/projects", headers=world.other_manager)
    assert world.project_id not in [p["id"] for p in theirs.json()]
    assert (await client.get(f"{API}/projects/{world.project_id}", headers=world.other_manager)).status_code == 403


async def test_admin_sees_everything_and_changes_nothing(client: AsyncClient, world: World):
    listed = await client.get(f"{API}/projects", headers=world.admin)
    assert world.project_id in [p["id"] for p in listed.json()]
    assert (await client.get(f"{API}/projects/{world.project_id}", headers=world.admin)).status_code == 200
    resp = await client.patch(f"{API}/projects/{world.project_id}", headers=world.admin, json={"name": "Hijacked"})
    assert resp.status_code == 403


async def test_owner_edits_project(client: AsyncClient, world: World):
    resp = await client.patch(f"{API}/projects/{world.project_id}", headers=world.manager,
                              json={"status": "Active", "github_default_branch": "develop"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "Active" and resp.json()["github_default_branch"] == "develop"
    # 'Evaluating' belongs to the AI pipeline
    bad = await client.patch(f"{API}/projects/{world.project_id}", headers=world.manager, json={"status": "Evaluating"})
    assert bad.status_code == 422


async def test_employees_see_only_projects_they_are_on(client: AsyncClient, world: World):
    listed = await client.get(f"{API}/projects", headers=world.pm)
    assert [(p["id"], p["my_role"]) for p in listed.json()] == [(world.project_id, "Project Manager")]
    assert (await client.get(f"{API}/projects", headers=world.outsider)).json() == []
    assert (await client.get(f"{API}/projects/{world.project_id}", headers=world.outsider)).status_code == 403


async def test_project_with_open_tasks_cannot_be_deleted(client: AsyncClient, world: World, fake_github):
    await _task(client, world, await _group(client, world))
    resp = await client.delete(f"{API}/projects/{world.project_id}", headers=world.manager)
    assert resp.status_code == 409


# ══════════════════════════════════════════════════════════════════
#  Source files
# ══════════════════════════════════════════════════════════════════

def _tiny_pdf(text: str) -> bytes:
    stream = f"BT /F1 24 Tf 72 700 Td ({text}) Tj ET".encode()
    objs = [b"<</Type/Catalog/Pages 2 0 R>>", b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
            b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
            b"<</Length %d>>stream\n" % len(stream) + stream + b"\nendstream",
            b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"]
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj" % i + o + b"endobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    return out + b"trailer<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref)


def _docx(text: str) -> bytes:
    import docx

    document = docx.Document()
    document.add_paragraph(text)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


async def test_source_files_upload_extract_and_report_rejects(client: AsyncClient, world: World, fake_storage):
    files = [
        ("files", ("brief.md", b"# Brief\nUsers can pay by UPI", "text/markdown")),
        ("files", ("notes.txt", b"Ship by March", "text/plain")),
        ("files", ("spec.docx", _docx("Refunds within 7 days"),
                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ("files", ("scan.pdf", _tiny_pdf("Checkout must support UPI"), "application/pdf")),
        ("files", ("tool.exe", b"MZ...", "application/octet-stream")),
        ("files", ("empty.txt", b"", "text/plain")),
        ("files", ("broken.pdf", b"not a pdf", "application/pdf")),
    ]
    resp = await client.post(f"{API}/projects/{world.project_id}/source-files", headers=world.manager, files=files)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert sorted(f["file_name"] for f in body["uploaded"]) == ["brief.md", "notes.txt", "scan.pdf", "spec.docx"]
    assert all(f["extracted_chars"] > 0 for f in body["uploaded"])
    assert sorted(r["file_name"] for r in body["rejected"]) == ["broken.pdf", "empty.txt", "tool.exe"]
    assert len(fake_storage.objects) == 4

    detail = (await client.get(f"{API}/projects/{world.project_id}", headers=world.manager)).json()
    assert len(detail["source_files"]) == 4

    file_id = body["uploaded"][0]["id"]
    assert (await client.delete(f"{API}/projects/{world.project_id}/source-files/{file_id}",
                                headers=world.manager)).status_code == 204
    assert len(fake_storage.objects) == 3


async def test_extracted_text_is_stored_for_the_ai(client: AsyncClient, world: World, db_session: AsyncSession):
    from app.models.project import ProjectSourceFile

    await client.post(f"{API}/projects/{world.project_id}/source-files", headers=world.manager,
                      files=[("files", ("scan.pdf", _tiny_pdf("Checkout must support UPI"), "application/pdf"))])
    row = (await db_session.execute(select(ProjectSourceFile).where(
        ProjectSourceFile.project_id == world.project_id))).scalar_one()
    assert row.extracted_text == "Checkout must support UPI"


@pytest.mark.parametrize("who", ["pm", "admin", "other_manager"])
async def test_only_the_owner_uploads(client: AsyncClient, world: World, who: str):
    resp = await client.post(f"{API}/projects/{world.project_id}/source-files", headers=getattr(world, who),
                             files=[("files", ("a.md", b"x", "text/markdown"))])
    assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════
#  Team — Project Managers
# ══════════════════════════════════════════════════════════════════

async def test_pm_roster(client: AsyncClient, world: World):
    team = (await client.get(f"{API}/projects/{world.project_id}/assignments", headers=world.manager)).json()
    assert [(m["user"]["id"], m["project_role"]) for m in team] == [(world.pm_id, "Project Manager")]

    dup = await client.post(f"{API}/projects/{world.project_id}/assignments", headers=world.manager,
                            json={"user_id": world.pm_id})
    assert dup.status_code == 409


async def test_only_employees_can_be_project_managers(client: AsyncClient, world: World, db_session):
    manager_id, _ = await make_user(db_session, "Manager", "mgr_three")
    resp = await client.post(f"{API}/projects/{world.project_id}/assignments", headers=world.manager,
                             json={"user_id": manager_id})
    assert resp.status_code == 422


async def test_pm_cannot_appoint_pms(client: AsyncClient, world: World):
    resp = await client.post(f"{API}/projects/{world.project_id}/assignments", headers=world.pm,
                             json={"user_id": world.dev_id})
    assert resp.status_code == 403


async def test_removed_pm_loses_access(client: AsyncClient, world: World):
    assert (await client.delete(f"{API}/projects/{world.project_id}/assignments/{world.pm_id}",
                                headers=world.manager)).status_code == 204
    assert (await client.get(f"{API}/projects/{world.project_id}", headers=world.pm)).status_code == 403


async def test_removed_pm_holding_tasks_stays_as_member(client: AsyncClient, world: World, fake_github):
    await _task(client, world, await _group(client, world), assignee=world.pm_id)
    await client.delete(f"{API}/projects/{world.project_id}/assignments/{world.pm_id}", headers=world.manager)
    listed = (await client.get(f"{API}/projects", headers=world.pm)).json()
    assert [p["my_role"] for p in listed] == ["Member"]


async def test_candidates_are_for_owner_and_pm(client: AsyncClient, world: World, fake_github):
    for who in ("manager", "pm"):
        resp = await client.get(f"{API}/projects/{world.project_id}/candidates", headers=getattr(world, who))
        assert resp.status_code == 200
        assert world.dev_id in [p["id"] for p in resp.json()]
    await _task(client, world, await _group(client, world), assignee=world.dev_id)
    assert (await client.get(f"{API}/projects/{world.project_id}/candidates",
                             headers=world.dev)).status_code == 403


# ══════════════════════════════════════════════════════════════════
#  Task groups
# ══════════════════════════════════════════════════════════════════

async def test_task_groups_are_the_pms(client: AsyncClient, world: World):
    first, second = await _group(client, world, "Auth"), await _group(client, world, "Payments")
    groups = (await client.get(f"{API}/projects/{world.project_id}/task-groups", headers=world.manager)).json()
    assert [(g["id"], g["sequence"], g["created_by"]) for g in groups] == [(first, 1, "Human"), (second, 2, "Human")]

    for who in ("manager", "admin"):
        resp = await client.post(f"{API}/projects/{world.project_id}/task-groups",
                                 headers=getattr(world, who), json={"name": "Nope"})
        assert resp.status_code == 403


async def test_group_with_tasks_cannot_be_deleted(client: AsyncClient, world: World, fake_github):
    group_id = await _group(client, world)
    await _task(client, world, group_id)
    resp = await client.delete(f"{API}/projects/{world.project_id}/task-groups/{group_id}", headers=world.pm)
    assert resp.status_code == 409


# ══════════════════════════════════════════════════════════════════
#  Tasks ↔ GitHub issues
# ══════════════════════════════════════════════════════════════════

async def test_assignment_makes_a_member_and_notifies(client: AsyncClient, world: World, fake_github,
                                                      db_session: AsyncSession):
    task = (await _task(client, world, await _group(client, world), assignee=world.dev_id))["task"]
    team = (await client.get(f"{API}/projects/{world.project_id}/assignments", headers=world.manager)).json()
    assert (world.dev_id, "Member") in [(m["user"]["id"], m["project_role"]) for m in team]
    listed = (await client.get(f"{API}/projects", headers=world.dev)).json()
    assert [p["my_role"] for p in listed] == ["Member"]

    note = (await db_session.execute(select(Notification).where(
        Notification.user_id == world.dev_id, Notification.type == "task_assigned"))).scalar_one()
    assert note.related_task_id == task["id"] and note.link == f"/employee/tasks/{task['id']}"


async def test_assignee_without_github_username_gets_a_warning(client: AsyncClient, world: World, fake_github):
    body = await _task(client, world, await _group(client, world), assignee=world.newbie_id)
    assert body["warnings"] and "no GitHub username" in body["warnings"][0]
    assert fake_github.issues[("acme/storefront", 1)]["assignees"] == []


async def test_no_github_means_no_task(client: AsyncClient, world: World):
    """Task creation is issue creation — without GitHub neither happens (CORE.md §4)."""
    group_id = await _group(client, world)
    resp = await client.post(f"{API}/projects/{world.project_id}/tasks", headers=world.pm,
                             json={"title": "Orphan", "task_group_id": group_id})
    assert resp.status_code == 503
    assert "GitHub is not configured" in resp.json()["detail"]
    tasks = (await client.get(f"{API}/projects/{world.project_id}/tasks", headers=world.pm)).json()
    assert tasks == []


async def test_github_failure_rolls_the_task_back(client: AsyncClient, world: World, fake_github):
    group_id = await _group(client, world)
    fake_github.fail_with = 500
    resp = await client.post(f"{API}/projects/{world.project_id}/tasks", headers=world.pm,
                             json={"title": "Doomed", "task_group_id": group_id})
    assert resp.status_code == 502
    assert "simulated GitHub failure" in resp.json()["detail"]
    fake_github.fail_with = None
    assert (await client.get(f"{API}/projects/{world.project_id}/tasks", headers=world.pm)).json() == []


async def test_group_must_belong_to_the_project(client: AsyncClient, world: World, fake_github):
    other = (await client.post(f"{API}/projects", headers=world.manager,
                               json={"name": "Other", "github_repo": "acme/other"})).json()
    await client.post(f"{API}/projects/{other['id']}/assignments", headers=world.manager, json={"user_id": world.pm_id})
    foreign_group = (await client.post(f"{API}/projects/{other['id']}/task-groups", headers=world.pm,
                                       json={"name": "Foreign"})).json()["id"]
    resp = await client.post(f"{API}/projects/{world.project_id}/tasks", headers=world.pm,
                             json={"title": "Wrong group", "task_group_id": foreign_group})
    assert resp.status_code == 422


@pytest.mark.parametrize("who", ["dev", "manager", "admin"])
async def test_only_the_pm_creates_tasks(client: AsyncClient, world: World, fake_github, who):
    group_id = await _group(client, world)
    await _task(client, world, group_id, assignee=world.dev_id)  # makes dev a Member
    resp = await client.post(f"{API}/projects/{world.project_id}/tasks", headers=getattr(world, who),
                             json={"title": "Sneaky", "task_group_id": group_id})
    assert resp.status_code == 403


async def test_reassignment_updates_the_issue(client: AsyncClient, world: World, fake_github):
    task = (await _task(client, world, await _group(client, world), assignee=world.dev_id))["task"]
    resp = await client.patch(f"{API}/tasks/{task['id']}/assign", headers=world.pm,
                              json={"assigned_to_user_id": world.pm_id})
    assert resp.status_code == 200
    assert resp.json()["task"]["assigned_to"]["id"] == world.pm_id
    assert fake_github.issues[("acme/storefront", 1)]["assignees"] == ["priya-gh"]


async def test_delete_closes_the_issue_as_not_planned(client: AsyncClient, world: World, fake_github):
    task = (await _task(client, world, await _group(client, world)))["task"]
    assert (await client.delete(f"{API}/tasks/{task['id']}", headers=world.pm)).status_code == 204
    issue = fake_github.issues[("acme/storefront", 1)]
    assert issue["state"] == "closed" and issue["state_reason"] == "not_planned"
    assert (await client.get(f"{API}/tasks/{task['id']}", headers=world.pm)).status_code == 404


# ══════════════════════════════════════════════════════════════════
#  Completion authority — CORE.md §7
# ══════════════════════════════════════════════════════════════════

@pytest.fixture
async def assigned_task(client: AsyncClient, world: World, fake_github) -> dict:
    return (await _task(client, world, await _group(client, world), assignee=world.dev_id))["task"]


async def test_member_moves_own_task_but_never_completes_it(client: AsyncClient, world: World, assigned_task):
    url = f"{API}/tasks/{assigned_task['id']}/status"
    assert (await client.patch(url, headers=world.dev, json={"status": "In Progress"})).status_code == 200
    resp = await client.patch(url, headers=world.dev, json={"status": "Completed"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Completion is confirmed by CI/CD or the Project Manager"


@pytest.mark.parametrize("status", ["In Review", "Cancelled", "Overdue"])
async def test_member_cannot_set_other_statuses(client: AsyncClient, world: World, assigned_task, status):
    resp = await client.patch(f"{API}/tasks/{assigned_task['id']}/status", headers=world.dev, json={"status": status})
    assert resp.status_code == 403


async def test_member_cannot_touch_someone_elses_task(client: AsyncClient, world: World, assigned_task):
    other = (await _task(client, world, assigned_task["task_group_id"], assignee=world.newbie_id))["task"]
    resp = await client.patch(f"{API}/tasks/{other['id']}/status", headers=world.dev, json={"status": "In Progress"})
    assert resp.status_code == 403


@pytest.mark.parametrize("who", ["manager", "admin"])
async def test_observers_cannot_complete(client: AsyncClient, world: World, assigned_task, who):
    resp = await client.patch(f"{API}/tasks/{assigned_task['id']}/status", headers=getattr(world, who),
                              json={"status": "Completed"})
    assert resp.status_code == 403


async def test_generic_edit_cannot_sneak_a_status_change(client: AsyncClient, world: World, assigned_task):
    """The legacy PATCH /tasks/{id} took a status; completion now has exactly one door."""
    resp = await client.patch(f"{API}/tasks/{assigned_task['id']}", headers=world.pm,
                              json={"status": "Completed", "title": "Renamed"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "Pending" and resp.json()["title"] == "Renamed"
    assert (await client.patch(f"{API}/tasks/{assigned_task['id']}", headers=world.dev,
                               json={"title": "Mine now"})).status_code == 403


async def test_pm_completes_closes_issue_and_rolls_up(client: AsyncClient, world: World, assigned_task,
                                                      fake_github: FakeGitHub):
    resp = await client.patch(f"{API}/tasks/{assigned_task['id']}/status", headers=world.pm,
                              json={"status": "Completed"})
    assert resp.status_code == 200
    task = resp.json()
    assert task["completed_by"] == "Project Manager" and task["completed_at"]
    assert fake_github.issues[("acme/storefront", 1)]["state"] == "closed"

    group = (await client.get(f"{API}/projects/{world.project_id}/task-groups", headers=world.pm)).json()[0]
    assert group["completion_percentage"] == 100.0 and group["status"] == "Completed"
    stats = (await client.get(f"{API}/projects/{world.project_id}", headers=world.manager)).json()["stats"]
    assert stats["completion_percentage"] == 100.0

    reopened = await client.patch(f"{API}/tasks/{assigned_task['id']}/status", headers=world.pm,
                                  json={"status": "In Progress"})
    assert reopened.json()["completed_by"] is None and reopened.json()["completed_at"] is None
    assert fake_github.issues[("acme/storefront", 1)]["state"] == "open"


async def test_allowed_statuses_mirror_the_rule(client: AsyncClient, world: World, assigned_task):
    as_member = (await client.get(f"{API}/tasks/{assigned_task['id']}", headers=world.dev)).json()
    assert "Completed" not in as_member["allowed_statuses"]
    assert set(as_member["allowed_statuses"]) == {"In Progress", "Blocked"}
    assert as_member["can_edit"] is False
    as_pm = (await client.get(f"{API}/tasks/{assigned_task['id']}", headers=world.pm)).json()
    assert "Completed" in as_pm["allowed_statuses"] and "Overdue" not in as_pm["allowed_statuses"]
    as_manager = (await client.get(f"{API}/tasks/{assigned_task['id']}", headers=world.manager)).json()
    assert as_manager["allowed_statuses"] == []


# ══════════════════════════════════════════════════════════════════
#  Dashboards
# ══════════════════════════════════════════════════════════════════

async def test_my_tasks_across_projects(client: AsyncClient, world: World, assigned_task):
    mine = (await client.get(f"{API}/tasks/mine", headers=world.dev)).json()
    assert [(t["id"], t["project_name"]) for t in mine] == [(assigned_task["id"], "Storefront")]
    assert (await client.get(f"{API}/tasks/mine", headers=world.manager)).status_code == 403


async def test_overdue_task_marks_project_at_risk(client: AsyncClient, world: World, fake_github):
    await _task(client, world, await _group(client, world), due_date="2020-01-01")
    summary = (await client.get(f"{API}/projects", headers=world.manager)).json()[0]
    assert summary["stats"]["overdue_tasks"] == 1 and summary["at_risk"] is True
    assert summary["project_managers"][0]["id"] == world.pm_id


async def test_activity_feed(client: AsyncClient, world: World, assigned_task):
    feed = (await client.get(f"{API}/projects/activity", headers=world.manager)).json()
    assert feed[0]["task_id"] == assigned_task["id"] and feed[0]["project_name"] == "Storefront"
    assert (await client.get(f"{API}/projects/activity", headers=world.other_manager)).json() == []


# ══════════════════════════════════════════════════════════════════
#  GitHub username (PLANNING.md Q9)
# ══════════════════════════════════════════════════════════════════

async def test_users_set_their_own_github_username(client: AsyncClient, world: World):
    me = (await client.get(f"{API}/users/me", headers=world.newbie)).json()
    resp = await client.patch(f"{API}/users/{me['id']}", headers=world.newbie, json={"github_username": "nia-codes"})
    assert resp.status_code == 200 and resp.json()["github_username"] == "nia-codes"
    bad = await client.patch(f"{API}/users/{me['id']}", headers=world.newbie, json={"github_username": "not valid!"})
    assert bad.status_code == 422
    cleared = await client.patch(f"{API}/users/{me['id']}", headers=world.newbie, json={"github_username": ""})
    assert cleared.json()["github_username"] is None
