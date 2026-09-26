"""
TRACE - Phase 7: notifications and per-task discussion

DEVELOPMENT.md Phase 7 "Done when": an assignment, a due date and a completion each
reach the right people without anyone refreshing a page — a `notifications` row,
an email (`send_mail_task` queued) and a live event (`events_sent`) per recipient,
never to the person who acted (CORE.md §9). Discussions follow PROJECT.md §11.6.
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Notification
from app.services import ai_jobs, project_service
from tests.conftest import FakeAI, FakeGitHub, JobRecorder
from tests.api.v1.test_ai_pipeline import _evaluate
from tests.api.v1.test_projects import API, World, _group, _task, world  # noqa: F401 — fixture

TODAY = date.today()


async def _notes(db: AsyncSession, user_id: int, type_: str | None = None) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if type_:
        stmt = stmt.where(Notification.type == type_)
    return list((await db.execute(stmt.order_by(Notification.id))).scalars())


def _mailed(jobs_sent: JobRecorder) -> list[str]:
    return [args[0] for args in jobs_sent.named("send_mail_task")]


async def _me(client: AsyncClient, headers: dict) -> int:
    return (await client.get(f"{API}/users/me", headers=headers)).json()["id"]


# ══════════════════════════════════════════════════════════════════
#  CORE.md §9 — who hears about what
# ══════════════════════════════════════════════════════════════════

async def test_assignment_reaches_the_assignee_live_and_by_mail(client: AsyncClient, world: World,
                                                               db_session: AsyncSession, jobs_sent, events_sent):
    task = (await _task(client, world, await _group(client, world), assignee=world.dev_id))["task"]

    [note] = await _notes(db_session, world.dev_id, "task_assigned")
    assert note.link == f"/employee/tasks/{task['id']}" and not note.is_read
    assert _mailed(jobs_sent) == ["dev_dan@trace.com"]
    assert events_sent.to(world.dev_id) == [{"type": "notification"}]
    assert await _notes(db_session, world.pm_id) == []          # the PM did it


async def test_pm_assigning_themselves_is_silent(client: AsyncClient, world: World, db_session: AsyncSession,
                                                 jobs_sent):
    await _task(client, world, await _group(client, world), assignee=world.pm_id)
    assert await _notes(db_session, world.pm_id) == [] and _mailed(jobs_sent) == []


async def test_completion_by_the_assignee_reaches_the_project_managers(client: AsyncClient, world: World,
                                                                      db_session: AsyncSession, jobs_sent):
    task = (await _task(client, world, await _group(client, world), assignee=world.dev_id))["task"]
    jobs_sent.sent.clear()
    resp = await client.patch(f"{API}/tasks/{task['id']}/status", headers=world.dev, json={"status": "Completed"})
    assert resp.status_code == 200

    [note] = await _notes(db_session, world.pm_id, "task_completed")
    assert "Dev Dan" in note.body and note.related_task_id == task["id"]
    assert await _notes(db_session, world.dev_id, "task_completed") == []
    assert _mailed(jobs_sent) == ["pm_priya@trace.com"]


async def test_completion_by_the_pm_reaches_the_assignee(client: AsyncClient, world: World,
                                                        db_session: AsyncSession):
    task = (await _task(client, world, await _group(client, world), assignee=world.dev_id))["task"]
    await client.patch(f"{API}/tasks/{task['id']}/status", headers=world.pm, json={"status": "Completed"})
    assert len(await _notes(db_session, world.dev_id, "task_completed")) == 1
    assert await _notes(db_session, world.pm_id, "task_completed") == []


async def test_other_statuses_notify_nobody(client: AsyncClient, world: World, db_session: AsyncSession):
    task = (await _task(client, world, await _group(client, world), assignee=world.dev_id))["task"]
    await client.patch(f"{API}/tasks/{task['id']}/status", headers=world.dev, json={"status": "In Progress"})
    assert await _notes(db_session, world.pm_id) == []


async def test_overdue_sweep_notifies_assignee_and_pms(client: AsyncClient, world: World,
                                                       db_session: AsyncSession, jobs_sent, events_sent):
    group = await _group(client, world)
    late = (await _task(client, world, group, assignee=world.dev_id,
                        due_date=str(TODAY - timedelta(days=1))))["task"]
    await _task(client, world, group, assignee=world.dev_id, due_date=str(TODAY + timedelta(days=5)))
    jobs_sent.sent.clear()
    events_sent.sent.clear()

    await project_service.mark_overdue_tasks(db_session, TODAY)
    for uid in (world.dev_id, world.pm_id):
        [note] = await _notes(db_session, uid, "task_due")
        assert note.title == "Overdue: Build the cart" and note.related_task_id == late["id"]
    assert sorted(_mailed(jobs_sent)) == ["dev_dan@trace.com", "pm_priya@trace.com"]
    assert events_sent.sent == [([world.pm_id, world.dev_id] if world.pm_id < world.dev_id
                                 else [world.dev_id, world.pm_id], {"type": "notification"})]


async def test_due_reminders_are_for_tomorrow_only(client: AsyncClient, world: World, db_session: AsyncSession):
    group = await _group(client, world)
    soon = (await _task(client, world, group, assignee=world.dev_id,
                        due_date=str(TODAY + timedelta(days=1))))["task"]
    await _task(client, world, group, assignee=world.dev_id, due_date=str(TODAY + timedelta(days=3)))
    done = (await _task(client, world, group, assignee=world.dev_id,
                        due_date=str(TODAY + timedelta(days=1))))["task"]
    await client.patch(f"{API}/tasks/{done['id']}/status", headers=world.dev, json={"status": "Completed"})

    result = await project_service.task_due_reminders(db_session, TODAY)
    assert result["tasks"] == [soon["id"]]
    [note] = await _notes(db_session, world.dev_id, "task_due")
    assert note.title == "Due tomorrow: Build the cart"
    assert len(await _notes(db_session, world.pm_id, "task_due")) == 1


async def test_evaluation_result_reaches_the_owner(client: AsyncClient, world: World, db_session: AsyncSession,
                                                   fake_ai: FakeAI, fake_github: FakeGitHub):
    manager_id = await _me(client, world.manager)
    assert (await _evaluate(client, world, db_session, fake_ai, fake_github))["status"] == "success"
    [note] = await _notes(db_session, manager_id, "project_evaluated")
    assert note.title == "Evaluated: Storefront" and note.link == f"/manager/projects/{world.project_id}"


async def test_failed_evaluation_reaches_the_owner(client: AsyncClient, world: World, db_session: AsyncSession,
                                                   fake_ai: FakeAI):
    manager_id = await _me(client, world.manager)
    await ai_jobs.run_evaluate_project(db_session, world.project_id, job_id="j", ai=fake_ai, github=None)
    [note] = await _notes(db_session, manager_id, "project_evaluated")
    assert note.title.startswith("Evaluation failed") and "GitHub" in note.body


# ══════════════════════════════════════════════════════════════════
#  /notifications — each caller sees only their own
# ══════════════════════════════════════════════════════════════════

async def test_notification_inbox(client: AsyncClient, world: World):
    group = await _group(client, world)
    await _task(client, world, group, assignee=world.dev_id)
    await _task(client, world, group, assignee=world.dev_id)

    inbox = (await client.get(f"{API}/notifications", headers=world.dev)).json()
    assert inbox["unread"] == 2 and len(inbox["items"]) == 2
    assert inbox["items"][0]["id"] > inbox["items"][1]["id"]                  # newest first
    assert (await client.get(f"{API}/notifications", headers=world.pm)).json() == {"items": [], "unread": 0}

    first = inbox["items"][0]["id"]
    assert (await client.patch(f"{API}/notifications/{first}/read", headers=world.pm)).status_code == 404
    resp = await client.patch(f"{API}/notifications/{first}/read", headers=world.dev)
    assert resp.status_code == 200 and resp.json()["is_read"]
    assert (await client.get(f"{API}/notifications/unread-count", headers=world.dev)).json() == {"unread": 1}
    unread = (await client.get(f"{API}/notifications?unread_only=true", headers=world.dev)).json()["items"]
    assert [n["id"] for n in unread] == [inbox["items"][1]["id"]]

    assert (await client.post(f"{API}/notifications/read-all", headers=world.dev)).json() == {"updated": 1}
    assert (await client.get(f"{API}/notifications/unread-count", headers=world.dev)).json() == {"unread": 0}


async def test_notifications_need_a_login(client: AsyncClient):
    assert (await client.get(f"{API}/notifications")).status_code in (401, 422)


def test_live_socket_refuses_a_bad_token():
    from starlette.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect
    from app.main import app

    # Not `with TestClient(app)`: that runs the app's startup, which seeds demo data and commits
    with pytest.raises(WebSocketDisconnect):
        with TestClient(app).websocket_connect("/api/v1/ws?token=nonsense") as ws:
            ws.receive_text()


# ══════════════════════════════════════════════════════════════════
#  Discussions — PROJECT.md §11.6
# ══════════════════════════════════════════════════════════════════

@pytest.fixture
async def task(client: AsyncClient, world: World) -> dict:
    return (await _task(client, world, await _group(client, world), assignee=world.dev_id))["task"]


@pytest.mark.parametrize("who,expected", [
    ("dev", 200), ("pm", 200), ("manager", 200),        # assignee, assigner + PM, owner
    ("admin", 403), ("newbie", 403), ("other_manager", 403), ("outsider", 403),
])
async def test_who_sees_a_discussion(client: AsyncClient, world: World, task, who, expected):
    if who == "newbie":  # a Member of the project, but not on this task
        await _task(client, world, task["task_group_id"], assignee=world.newbie_id)
    resp = await client.get(f"{API}/tasks/{task['id']}/discussions", headers=getattr(world, who))
    assert resp.status_code == expected
    post = await client.post(f"{API}/tasks/{task['id']}/discussions", headers=getattr(world, who),
                             json={"message": "hello"})
    assert post.status_code == (201 if expected == 200 else expected)
    detail = await client.get(f"{API}/tasks/{task['id']}", headers=getattr(world, who))
    if detail.status_code == 200:
        assert detail.json()["can_discuss"] is (expected == 200)


async def test_discussion_thread_and_its_notifications(client: AsyncClient, world: World, task,
                                                       db_session: AsyncSession, jobs_sent, events_sent):
    manager_id = await _me(client, world.manager)
    url = f"{API}/tasks/{task['id']}/discussions"
    jobs_sent.sent.clear()

    root = (await client.post(url, headers=world.dev, json={"message": "Which card provider?"})).json()
    assert root["author"]["id"] == world.dev_id and root["parent_id"] is None
    [note] = await _notes(db_session, world.pm_id, "discussion_reply")        # the assigner
    assert note.body == "Which card provider?" and note.link == f"/employee/tasks/{task['id']}"
    assert _mailed(jobs_sent) == []                                           # in-app only
    assert {"type": "discussion", "task_id": task["id"]} in events_sent.to(manager_id)

    reply = (await client.post(url, headers=world.manager, json={"message": "Stripe", "parent_id": root["id"]})).json()
    nested = (await client.post(url, headers=world.pm, json={"message": "Agreed", "parent_id": reply["id"]})).json()
    assert reply["parent_id"] == root["id"] and nested["parent_id"] == root["id"]   # one level deep

    thread = (await client.get(url, headers=world.dev)).json()
    assert [m["message"] for m in thread] == ["Which card provider?", "Stripe", "Agreed"]
    assert len(await _notes(db_session, world.dev_id, "discussion_reply")) == 2
    [to_manager] = await _notes(db_session, manager_id, "discussion_reply")      # joined by writing
    assert to_manager.link == f"/manager/tasks/{task['id']}"


async def test_reply_must_be_on_the_same_task(client: AsyncClient, world: World, task):
    other = (await _task(client, world, task["task_group_id"], assignee=world.dev_id))["task"]
    root = (await client.post(f"{API}/tasks/{other['id']}/discussions", headers=world.dev,
                              json={"message": "elsewhere"})).json()
    resp = await client.post(f"{API}/tasks/{task['id']}/discussions", headers=world.dev,
                             json={"message": "hi", "parent_id": root["id"]})
    assert resp.status_code == 422
    blank = await client.post(f"{API}/tasks/{task['id']}/discussions", headers=world.dev, json={"message": ""})
    assert blank.status_code == 422
