"""
TRACE - Phase 5: the AI pipeline (CORE.md §2–8)

Routes enqueue and return (`jobs_sent` records instead of reaching Redis); job
bodies in app/services/ai_jobs.py are called directly with `fake_ai` and
`fake_github`. Nothing here reaches a real model, queue or GitHub.
"""

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.employee import Employee
from app.models.project import Project, TaskGroup
from app.models.task import Task
from app.schemas.ai import PeopleSuggestionsOut, TaskGroupPlanOut
from app.services import ai_jobs, gantt_service, project_service
from app.services.ai_service import AIOutputInvalid, complete
from app.services.scoring_service import ScoringService, candidate_stats
from tests.conftest import FakeAI, FakeGitHub, JobRecorder
from tests.api.v1.test_projects import API, World, _group, _task, world  # noqa: F401 — fixture

REPO = "acme/storefront"
TODAY = date.today()

DOCUMENT = {"title": "Storefront", "markdown": "# Storefront\n\nSell things online: a catalogue, a cart "
                                               "and a checkout that takes cards."}
PLAN = {"task_groups": [
    {"name": "Catalogue", "description": "Products and categories", "sequence": 1,
     "estimated_duration_days": 10, "depends_on": []},
    {"name": "Checkout", "description": "Cart and payment", "sequence": 2,
     "estimated_duration_days": 5, "depends_on": ["Catalogue"]},
    {"name": "Search", "description": "Find products", "sequence": 3,
     "estimated_duration_days": 4, "depends_on": []},
]}


async def _upload(client: AsyncClient, w: World, text: str = "The shop sells shoes. Customers pay by card.") -> None:
    resp = await client.post(f"{API}/projects/{w.project_id}/source-files", headers=w.manager,
                             files=[("files", ("brief.md", text.encode(), "text/markdown"))])
    assert resp.status_code == 201, resp.text


async def _evaluate(client, w: World, db: AsyncSession, ai: FakeAI, gh: FakeGitHub) -> dict:
    """Upload a brief, press Evaluate Project, and run the job the route queued."""
    await _upload(client, w)
    ai.reply("ProjectDocumentOut", DOCUMENT)
    ai.reply("TaskGroupPlanOut", PLAN)
    resp = await client.post(f"{API}/projects/{w.project_id}/evaluate", headers=w.manager)
    assert resp.status_code == 202, resp.text
    return await ai_jobs.run_evaluate_project(db, w.project_id, job_id="job-eval", ai=ai, github=gh.client())


async def _groups(db: AsyncSession, project_id: int) -> list[TaskGroup]:
    return list((await db.execute(select(TaskGroup).where(
        TaskGroup.project_id == project_id, TaskGroup.deleted_at.is_(None)).order_by(TaskGroup.sequence))).scalars())


# ══════════════════════════════════════════════════════════════════
#  §2.1 — the service layer: validate, retry, never persist bad output
# ══════════════════════════════════════════════════════════════════

async def test_complete_retries_with_the_errors_then_succeeds():
    ai = FakeAI()
    ai.reply("TaskGroupPlanOut", "not json at all", PLAN)
    plan = await complete(ai, TaskGroupPlanOut, "plan", "brief")
    assert [g.name for g in plan.task_groups] == ["Catalogue", "Checkout", "Search"]
    assert ai.called("TaskGroupPlanOut") == 2
    retry_prompt = ai.calls[1][1][-1]["content"]
    assert retry_prompt.startswith("That JSON is invalid")


async def test_complete_gives_up_after_two_retries():
    ai = FakeAI()
    ai.reply("TaskGroupPlanOut", {"task_groups": []})
    with pytest.raises(AIOutputInvalid):
        await complete(ai, TaskGroupPlanOut, "plan", "brief")
    assert ai.called("TaskGroupPlanOut") == 3


@pytest.mark.parametrize("groups", [
    [{"name": "A", "sequence": 1, "estimated_duration_days": 3, "depends_on": ["B"]},
     {"name": "B", "sequence": 2, "estimated_duration_days": 3}],                        # waits for a later group
    [{"name": "A", "sequence": 1, "estimated_duration_days": 3},
     {"name": "a", "sequence": 2, "estimated_duration_days": 3}],                        # duplicate name
    [{"name": "A", "sequence": 1, "estimated_duration_days": 0}],                        # no duration
])
def test_task_group_plan_rules(groups):
    with pytest.raises(ValidationError):
        TaskGroupPlanOut.model_validate({"task_groups": groups})


def test_people_suggestions_must_name_candidates():
    data = {"suggestions": [{"user_id": 99, "score": 0.9, "reasoning": "strong"}]}
    with pytest.raises(ValidationError):
        PeopleSuggestionsOut.model_validate(data, context={"candidates": {1, 2}})
    assert PeopleSuggestionsOut.model_validate(data, context={"candidates": {99}}).suggestions[0].user_id == 99


# ══════════════════════════════════════════════════════════════════
#  §3 — Evaluate Project: the route
# ══════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("who,expected", [
    ("manager", 202), ("admin", 403), ("pm", 403), ("other_manager", 403), ("outsider", 403),
])
async def test_only_the_owner_evaluates(client: AsyncClient, world: World, fake_ai, who, expected):
    await _upload(client, world)
    resp = await client.post(f"{API}/projects/{world.project_id}/evaluate", headers=getattr(world, who))
    assert resp.status_code == expected, resp.text


async def test_evaluate_marks_the_project_and_queues_the_job(client: AsyncClient, world: World, fake_ai,
                                                             jobs_sent: JobRecorder):
    await _upload(client, world)
    resp = await client.post(f"{API}/projects/{world.project_id}/evaluate", headers=world.manager)
    assert resp.json() == {"job_id": "job-1"}
    assert jobs_sent.named("evaluate_project") == [(world.project_id,)]
    status = (await client.get(f"{API}/projects/{world.project_id}/evaluate/status", headers=world.pm)).json()
    assert status["state"] == "running" and status["project_status"] == "Evaluating"
    again = await client.post(f"{API}/projects/{world.project_id}/evaluate", headers=world.manager)
    assert again.status_code == 409


async def test_evaluate_refusals(client: AsyncClient, world: World, db_session: AsyncSession, monkeypatch):
    url = f"{API}/projects/{world.project_id}/evaluate"
    assert (await client.post(url, headers=world.manager)).status_code == 503        # no AI configured
    monkeypatch.setattr(get_settings(), "OPENAI_API_KEY", "sk-test")
    resp = await client.post(url, headers=world.manager)
    assert resp.status_code == 409 and "requirement document" in resp.json()["detail"]
    await _upload(client, world)
    await _task(client, world, await _group(client, world))
    resp = await client.post(url, headers=world.manager)
    assert resp.status_code == 409 and "already has tasks" in resp.json()["detail"]


# ══════════════════════════════════════════════════════════════════
#  §3 — Evaluate Project: the job
# ══════════════════════════════════════════════════════════════════

async def test_evaluation_writes_documents_groups_and_gantt_v1(client: AsyncClient, world: World,
                                                              db_session: AsyncSession, fake_ai: FakeAI,
                                                              fake_github: FakeGitHub):
    """DEVELOPMENT.md Phase 5 'Done when'."""
    result = await _evaluate(client, world, db_session, fake_ai, fake_github)
    assert result == {"status": "success", "task_groups": 3}

    initial = fake_github.text(REPO, "docs/project_initial_doc.md")
    assert initial == fake_github.text(REPO, "docs/project_doc.md") and initial.startswith("# Storefront")
    assert "(evaluate_project job-eval)" in fake_github.files[(REPO, "docs/project_doc.md")]["message"]
    prompt = fake_ai.calls[0][1][-1]["content"]
    assert "The shop sells shoes" in prompt                          # the extracted source text went in

    project = await db_session.get(Project, world.project_id)
    assert project.status == "Active" and project.last_evaluated_at and not project.ai_errors
    assert project.project_initial_doc.endswith("docs/project_initial_doc.md")
    catalogue, checkout, search = await _groups(db_session, world.project_id)
    assert {g.created_by for g in (catalogue, checkout, search)} == {"AI"}
    assert checkout.depends_on == [catalogue.id] and search.depends_on is None
    assert (catalogue.planned_start_date, catalogue.planned_end_date) == (TODAY, TODAY + timedelta(days=9))
    assert checkout.planned_start_date == TODAY + timedelta(days=10)   # waits for the catalogue
    assert search.planned_start_date == TODAY                          # waits for nothing
    assert project.start_date == TODAY and project.end_date == TODAY + timedelta(days=14)

    [v1] = await gantt_service.versions(db_session, world.project_id)
    assert (v1.version, v1.generated_reason, v1.generated_by_job) == (1, "initial", "job-eval")
    assert v1.chart_data["dependencies"] == [{"from": catalogue.id, "to": checkout.id}]

    detail = (await client.get(f"{API}/projects/{world.project_id}", headers=world.manager)).json()
    assert detail["documents"]["project_doc"] and detail["ai_errors"] == {}
    tree = (await client.get(f"{API}/projects/{world.project_id}/tree", headers=world.pm)).json()
    assert [g["name"] for g in tree["groups"]] == ["Catalogue", "Checkout", "Search"]


async def test_failed_evaluation_is_visible_and_keeps_nothing(client: AsyncClient, world: World,
                                                             db_session: AsyncSession, fake_ai: FakeAI,
                                                             fake_github: FakeGitHub):
    kept = await _group(client, world, "Hand-made")
    await _upload(client, world)
    fake_ai.reply("ProjectDocumentOut", DOCUMENT)
    fake_ai.reply("TaskGroupPlanOut", "{}")                                   # never valid
    await client.post(f"{API}/projects/{world.project_id}/evaluate", headers=world.manager)
    result = await ai_jobs.run_evaluate_project(db_session, world.project_id, job_id="j", ai=fake_ai,
                                                github=fake_github.client())
    assert result["status"] == "failed"

    project = await db_session.get(Project, world.project_id)
    assert project.status == "Draft" and project.project_doc is None
    assert "planning the task groups" in project.ai_errors["evaluate_project"]["message"]
    assert [g.id for g in await _groups(db_session, world.project_id)] == [kept]
    assert await gantt_service.versions(db_session, world.project_id) == []
    status = (await client.get(f"{API}/projects/{world.project_id}/evaluate/status", headers=world.manager)).json()
    assert status["state"] == "failed" and "planning the task groups" in status["error"]


async def test_evaluation_without_github_fails_visibly(client: AsyncClient, world: World,
                                                      db_session: AsyncSession, fake_ai: FakeAI):
    await _upload(client, world)
    result = await ai_jobs.run_evaluate_project(db_session, world.project_id, job_id="j", ai=fake_ai, github=None)
    assert result["status"] == "failed" and "GitHub is not configured" in result["error"]


# ══════════════════════════════════════════════════════════════════
#  §3 steps 7–8, §4 — suggestions: ranked, never assigned
# ══════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("path,who,expected", [
    ("suggest-managers", "manager", 202), ("suggest-managers", "pm", 403), ("suggest-managers", "admin", 403),
    ("tasks/suggest-assignees", "pm", 202), ("tasks/suggest-assignees", "manager", 403),
    ("tasks/suggest-assignees", "dev", 403),
])
async def test_who_may_ask_for_suggestions(client: AsyncClient, world: World, fake_ai, path, who, expected):
    await _task(client, world, await _group(client, world), assignee=world.dev_id)  # dev is a Member
    resp = await client.post(f"{API}/projects/{world.project_id}/{path}", headers=getattr(world, who),
                             json={"title": "Coupon codes"})
    assert resp.status_code == expected, resp.text


async def test_suggest_tasks_route(client: AsyncClient, world: World, fake_ai, jobs_sent: JobRecorder):
    group = await _group(client, world)
    url = f"{API}/projects/{world.project_id}/task-groups/{group}/suggest-tasks"
    assert (await client.post(url, headers=world.manager)).status_code == 403
    assert (await client.post(url, headers=world.pm)).status_code == 202
    assert jobs_sent.named("suggest_tasks") == [(group,)]
    missing = f"{API}/projects/{world.project_id}/task-groups/999999/suggest-tasks"
    assert (await client.post(missing, headers=world.pm)).status_code == 422  # as the other group routes


async def test_manager_suggestions_rank_candidates_and_skip_current_pms(
        client: AsyncClient, world: World, db_session: AsyncSession, fake_ai: FakeAI):
    await _task(client, world, await _group(client, world), assignee=world.dev_id)
    fake_ai.reply("PeopleSuggestionsOut",
                  {"suggestions": [{"user_id": world.pm_id, "score": 0.9, "reasoning": "x"}]},   # already PM
                  {"suggestions": [{"user_id": world.newbie_id, "score": 0.4, "reasoning": "new"},
                                   {"user_id": world.dev_id, "score": 0.8, "reasoning": "delivers",
                                    "evidence": ["1 open task"]}]})
    result = await ai_jobs.run_suggest_managers(db_session, world.project_id, ai=fake_ai)
    assert fake_ai.called("PeopleSuggestionsOut") == 2                # the current PM was refused, then retried
    assert [s["user"]["id"] for s in result["suggestions"]] == [world.dev_id, world.newbie_id]
    assert result["suggestions"][0]["stats"]["open_tasks"] == 1
    candidates = fake_ai.calls[0][1][-1]["content"]
    assert "Dev Dan" in candidates and "Pm Priya" not in candidates
    team = (await client.get(f"{API}/projects/{world.project_id}/assignments", headers=world.manager)).json()
    assert {m["user"]["id"] for m in team if m["project_role"] == "Project Manager"} == {world.pm_id}


async def test_assignee_suggestions_see_the_task_and_past_work(client: AsyncClient, world: World,
                                                              db_session: AsyncSession, fake_ai: FakeAI):
    task = (await _task(client, world, await _group(client, world), assignee=world.dev_id))["task"]
    await client.patch(f"{API}/tasks/{task['id']}/status", headers=world.dev, json={"status": "Completed"})
    fake_ai.reply("PeopleSuggestionsOut", {"suggestions": [{"user_id": world.dev_id, "score": 0.7, "reasoning": "r"}]})
    result = await ai_jobs.run_suggest_assignees(db_session, world.project_id, "Coupon codes", "10% off",
                                                 ai=fake_ai)
    assert result["suggestions"][0]["stats"]["tasks_completed"] == 1
    prompt = fake_ai.calls[0][1][-1]["content"]
    assert "Coupon codes" in prompt and "Build the cart" in prompt      # the task, and dev's past work


async def test_task_suggestions(client: AsyncClient, world: World, db_session: AsyncSession, fake_ai: FakeAI):
    group = await _group(client, world)
    fake_ai.reply("TaskSuggestionsOut", {"tasks": [{"title": "Coupon field", "priority": "High",
                                                    "estimated_hours": 6}]})
    result = await ai_jobs.run_suggest_tasks(db_session, group, ai=fake_ai)
    assert result["task_group_id"] == group and result["tasks"][0]["title"] == "Coupon field"
    assert await db_session.scalar(select(Task.id).where(Task.task_group_id == group)) is None  # nothing created


# ══════════════════════════════════════════════════════════════════
#  §4 — the task progress document
# ══════════════════════════════════════════════════════════════════

TASK_PLAN = {"steps": [{"order": 2, "title": "Wire the API", "detail": "POST /cart"},
                       {"order": 1, "title": "Design the cart"}],
             "acceptance_criteria": ["Items can be added and removed"]}


async def test_task_creation_queues_its_progress_doc(client: AsyncClient, world: World, db_session: AsyncSession,
                                                     fake_ai: FakeAI, fake_github: FakeGitHub,
                                                     jobs_sent: JobRecorder):
    task = (await _task(client, world, await _group(client, world), assignee=world.dev_id))["task"]
    assert jobs_sent.named("generate_task_progress_doc") == [(task["id"],)]
    fake_ai.reply("TaskProgressPlanOut", TASK_PLAN)
    result = await ai_jobs.run_task_progress_doc(db_session, task["id"], job_id="job-doc", ai=fake_ai,
                                                 github=fake_github.client())
    assert result["status"] == "success"
    text = fake_github.text(REPO, f"docs/tasks/task-{task['id']}.md")
    assert text.index("Design the cart") < text.index("Wire the API")    # ordered by `order`
    assert "- [ ] **Wire the API** — POST /cart" in text and "- [ ] Items can be added" in text

    body = (await client.get(f"{API}/tasks/{task['id']}", headers=world.dev)).json()
    assert body["task_progress_doc"].endswith(f"task-{task['id']}.md") and body["progress_doc_error"] is None
    doc = (await client.get(f"{API}/tasks/{task['id']}/progress-doc", headers=world.dev)).json()
    assert doc["content"] == text
    assert (await client.get(f"{API}/tasks/{task['id']}/progress-doc", headers=world.outsider)).status_code == 403


async def test_failed_progress_doc_shows_on_the_task(client: AsyncClient, world: World, db_session: AsyncSession,
                                                     fake_ai: FakeAI, fake_github: FakeGitHub):
    task = (await _task(client, world, await _group(client, world)))["task"]
    fake_ai.reply("TaskProgressPlanOut", {"steps": []})
    await ai_jobs.run_task_progress_doc(db_session, task["id"], job_id="j", ai=fake_ai, github=fake_github.client())
    body = (await client.get(f"{API}/tasks/{task['id']}", headers=world.pm)).json()
    assert body["task_progress_doc"] is None and "invalid TaskProgressPlanOut" in body["progress_doc_error"]
    doc = (await client.get(f"{API}/tasks/{task['id']}/progress-doc", headers=world.pm)).json()
    assert doc == {"kind": "task", "url": None, "content": None}


# ══════════════════════════════════════════════════════════════════
#  §5 — Gantt re-evaluation: triggers, debounce, the re-plan
# ══════════════════════════════════════════════════════════════════

async def test_completion_triggers_a_debounced_replan(client: AsyncClient, world: World, jobs_sent: JobRecorder):
    task = (await _task(client, world, await _group(client, world), assignee=world.dev_id))["task"]
    await client.patch(f"{API}/tasks/{task['id']}/status", headers=world.dev, json={"status": "In Progress"})
    assert jobs_sent.named("reevaluate_gantt") == []
    await client.patch(f"{API}/tasks/{task['id']}/status", headers=world.dev, json={"status": "Completed"})
    await client.patch(f"{API}/tasks/{task['id']}/status", headers=world.dev, json={"status": "In Progress"})
    sent = [(args[:2], countdown) for name, args, countdown in jobs_sent.sent if name == "reevaluate_gantt"]
    assert sent == [((world.project_id, "task_status_change"), 30)] * 2   # completed, then reopened


@pytest.mark.parametrize("who,expected", [("pm", 202), ("manager", 403), ("dev", 403), ("admin", 403)])
async def test_manual_reevaluate_is_the_pms(client: AsyncClient, world: World, jobs_sent: JobRecorder, who, expected):
    await _task(client, world, await _group(client, world), assignee=world.dev_id)
    resp = await client.post(f"{API}/projects/{world.project_id}/gantt/reevaluate", headers=getattr(world, who))
    assert resp.status_code == expected
    if expected == 202:
        [(name, args, countdown)] = [s for s in jobs_sent.sent if s[0] == "reevaluate_gantt"]
        assert args[:2] == (world.project_id, "manual") and countdown == 0


async def test_a_burst_of_triggers_makes_one_version(client: AsyncClient, world: World, db_session: AsyncSession):
    await _group(client, world)
    first = datetime.now(timezone.utc).isoformat()
    second = datetime.now(timezone.utc).isoformat()
    ran = await ai_jobs.run_reevaluate_gantt(db_session, world.project_id, "task_status_change", first,
                                             job_id="j1", ai=None, github=None)
    skipped = await ai_jobs.run_reevaluate_gantt(db_session, world.project_id, "task_status_change", second,
                                                 job_id="j2", ai=None, github=None)
    assert ran == {"status": "success", "version": 1}
    assert skipped["status"] == "skipped" and "version 1" in skipped["reason"]
    later = datetime.now(timezone.utc).isoformat()
    again = await ai_jobs.run_reevaluate_gantt(db_session, world.project_id, "manual", later,
                                               job_id="j3", ai=None, github=None)
    assert again["version"] == 2
    [v2, _] = await gantt_service.versions(db_session, world.project_id)
    assert (v2.generated_reason, v2.generated_by_job) == ("manual", "j3")


def _row(gid, seq, start=None, days=None, status="Pending", deps=None, actual_end=None, end=None) -> TaskGroup:
    return TaskGroup(id=gid, sequence=seq, planned_start_date=start, planned_end_date=end,
                     estimated_duration_days=days, status=status, depends_on=deps, actual_end_date=actual_end)


def test_schedule_follows_dependencies_and_slips():
    start, today = date(2026, 1, 1), date(2026, 1, 20)
    design = _row(1, 1, days=5, status="Completed", actual_end=date(2026, 1, 8))   # finished late
    build = _row(2, 2, days=5, deps=[1])                                           # waits for design
    docs = _row(3, 3, start=date(2026, 1, 2), days=3)                             # overdue, unfinished
    ship = _row(4, 4, days=2, deps=[2, 3])
    gantt_service.schedule([ship, docs, build, design], start, today)
    assert (design.planned_start_date, design.planned_end_date) == (start, date(2026, 1, 8))
    assert (build.planned_start_date, build.planned_end_date) == (date(2026, 1, 9), date(2026, 1, 20))
    assert docs.planned_end_date == today                                          # stretched to today
    assert ship.planned_start_date == date(2026, 1, 21)                            # pushed by both


def test_schedule_keeps_a_hand_planned_span():
    group = _row(1, 1, start=date(2026, 3, 1), end=date(2026, 3, 10))
    gantt_service.schedule([group], date(2026, 1, 1), date(2026, 1, 1))
    assert (group.planned_start_date, group.planned_end_date) == (date(2026, 3, 1), date(2026, 3, 10))


async def test_document_change_lets_the_ai_revise_the_plan(client: AsyncClient, world: World,
                                                           db_session: AsyncSession, fake_ai: FakeAI,
                                                           fake_github: FakeGitHub):
    await _evaluate(client, world, db_session, fake_ai, fake_github)
    catalogue, checkout, _ = await _groups(db_session, world.project_id)
    fake_ai.reply("GanttRevisionOut", {
        "revisions": [{"task_group_id": checkout.id, "estimated_duration_days": 8}],
        "new_groups": [{"name": "Wishlist", "estimated_duration_days": 3, "depends_on": [catalogue.id]}],
    })
    result = await ai_jobs.run_reevaluate_gantt(db_session, world.project_id, "project_doc_updated",
                                                datetime.now(timezone.utc).isoformat(), job_id="j",
                                                ai=fake_ai, github=fake_github.client())
    assert result == {"status": "success", "version": 2}
    assert "Sell things online" in fake_ai.calls[-1][1][-1]["content"]      # it read the document back
    groups = await _groups(db_session, world.project_id)
    wishlist = groups[-1]
    assert (wishlist.name, wishlist.created_by, wishlist.depends_on) == ("Wishlist", "AI", [catalogue.id])
    assert wishlist.planned_start_date == catalogue.planned_end_date + timedelta(days=1)
    assert checkout.estimated_duration_days == 8
    [v2, _] = await gantt_service.versions(db_session, world.project_id)
    assert len(v2.chart_data["bars"]) == 4 and v2.generated_reason == "project_doc_updated"


async def test_ai_failure_still_replans_and_says_so(client: AsyncClient, world: World, db_session: AsyncSession,
                                                    fake_ai: FakeAI, fake_github: FakeGitHub):
    await _evaluate(client, world, db_session, fake_ai, fake_github)
    fake_ai.reply("GanttRevisionOut", {"revisions": [{"task_group_id": 999999, "estimated_duration_days": 3}]})
    result = await ai_jobs.run_reevaluate_gantt(db_session, world.project_id, "project_doc_updated",
                                                datetime.now(timezone.utc).isoformat(), job_id="j",
                                                ai=fake_ai, github=fake_github.client())
    assert result["version"] == 2
    project = await db_session.get(Project, world.project_id)
    assert "re-planned from the current task groups" in project.ai_errors["reevaluate_gantt"]["message"]


# ══════════════════════════════════════════════════════════════════
#  §10 — project documents
# ══════════════════════════════════════════════════════════════════

async def test_documents_before_and_after_evaluation(client: AsyncClient, world: World, db_session: AsyncSession,
                                                     fake_ai: FakeAI, fake_github: FakeGitHub):
    url = f"{API}/projects/{world.project_id}/documents"
    assert (await client.get(f"{url}/doc", headers=world.pm)).json() == {"kind": "doc", "url": None, "content": None}
    assert (await client.get(f"{url}/nonsense", headers=world.pm)).status_code == 422
    assert (await client.put(f"{url}/doc", headers=world.pm, json={"content": "# x"})).status_code == 409
    await _evaluate(client, world, db_session, fake_ai, fake_github)
    for who in ("manager", "admin", "pm"):
        body = (await client.get(f"{url}/initial", headers=getattr(world, who))).json()
        assert body["content"].startswith("# Storefront")
    assert (await client.get(f"{url}/doc", headers=world.outsider)).status_code == 403


async def test_saving_the_project_doc(client: AsyncClient, world: World, db_session: AsyncSession, fake_ai: FakeAI,
                                      fake_github: FakeGitHub, jobs_sent: JobRecorder):
    await _evaluate(client, world, db_session, fake_ai, fake_github)
    url = f"{API}/projects/{world.project_id}/documents/doc"
    original = (await client.get(url, headers=world.pm)).json()["content"]
    assert (await client.put(url, headers=world.manager, json={"content": "# New"})).status_code == 403

    same = (await client.put(url, headers=world.pm, json={"content": original.strip()})).json()
    assert same["changed"] is False and jobs_sent.named("reevaluate_gantt") == []

    edited = original + "\n## Wishlist\n\nCustomers save products for later.\n"
    saved = (await client.put(url, headers=world.pm, json={"content": edited})).json()
    assert saved["changed"] is True
    assert fake_github.text(REPO, "docs/project_doc.md") == edited
    assert fake_github.text(REPO, "docs/project_initial_doc.md") == original      # the brief never changes
    assert "edited by Pm Priya" in fake_github.files[(REPO, "docs/project_doc.md")]["message"]
    assert [a[:2] for a in jobs_sent.named("reevaluate_gantt")] == [(world.project_id, "project_doc_updated")]


# ══════════════════════════════════════════════════════════════════
#  §6 — the progress roll-up
# ══════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("who,expected", [("manager", 202), ("pm", 202), ("dev", 403), ("admin", 403)])
async def test_who_may_refresh_the_report(client: AsyncClient, world: World, fake_ai, who, expected):
    await _task(client, world, await _group(client, world), assignee=world.dev_id)
    resp = await client.post(f"{API}/projects/{world.project_id}/progress-report", headers=getattr(world, who))
    assert resp.status_code == expected


async def test_progress_report_reads_task_docs_and_writes_both(client: AsyncClient, world: World,
                                                                db_session: AsyncSession, fake_ai: FakeAI,
                                                                fake_github: FakeGitHub):
    task = (await _task(client, world, await _group(client, world), assignee=world.dev_id))["task"]
    fake_ai.reply("TaskProgressPlanOut", TASK_PLAN)
    await ai_jobs.run_task_progress_doc(db_session, task["id"], job_id="j", ai=fake_ai, github=fake_github.client())
    fake_ai.reply("ProgressReportOut", {"progress_markdown": "# Progress\n\nCart: pending.",
                                        "report_markdown": "# Report\n\nOn track, nothing blocked."})
    result = await ai_jobs.run_progress_report(db_session, world.project_id, job_id="j", ai=fake_ai,
                                               github=fake_github.client())
    assert result == {"status": "success"}
    prompt = fake_ai.calls[-1][1][-1]["content"]
    assert "Design the cart" in prompt and "Dev Dan" in prompt
    report = (await client.get(f"{API}/projects/{world.project_id}/documents/report", headers=world.manager)).json()
    assert report["content"].startswith("# Report")
    assert fake_github.text(REPO, "docs/project_progress_doc.md").startswith("# Progress")


# ══════════════════════════════════════════════════════════════════
#  §8 — scheduled jobs
# ══════════════════════════════════════════════════════════════════

async def test_overdue_sweep(client: AsyncClient, world: World, db_session: AsyncSession, jobs_sent: JobRecorder):
    group = await _group(client, world)
    late = (await _task(client, world, group, due_date=str(TODAY - timedelta(days=1))))["task"]
    done = (await _task(client, world, group, assignee=world.dev_id, due_date=str(TODAY - timedelta(days=1))))["task"]
    await client.patch(f"{API}/tasks/{done['id']}/status", headers=world.dev, json={"status": "Completed"})
    future = (await _task(client, world, group, due_date=str(TODAY + timedelta(days=3))))["task"]
    jobs_sent.sent.clear()

    result = await project_service.mark_overdue_tasks(db_session, TODAY)
    assert result["tasks"] == [late["id"]] and result["projects"] == [world.project_id]
    statuses = {t.id: t.status for t in (await db_session.execute(select(Task))).scalars()}
    assert (statuses[late["id"]], statuses[done["id"]], statuses[future["id"]]) == ("Overdue", "Completed", "Pending")
    assert [a[:2] for a in jobs_sent.named("reevaluate_gantt")] == [(world.project_id, "task_status_change")]


def test_every_job_is_registered_and_scheduled():
    from app.celery_app import celery_app
    import app.tasks  # noqa: F401 — registers them
    names = {"evaluate_project", "generate_task_progress_doc", "reevaluate_gantt", "update_project_progress_doc",
             "update_project_progress_docs", "suggest_managers", "suggest_assignees", "suggest_tasks",
             "mark_overdue_tasks", "compute_all_weekly_scores"}
    assert {f"app.tasks.{n}" for n in names} <= set(celery_app.tasks)
    scheduled = {entry["task"] for entry in celery_app.conf.beat_schedule.values()}
    assert scheduled <= set(celery_app.tasks)
    assert "app.tasks.mark_delayed_tasks" not in celery_app.tasks


async def test_weekly_score_uses_task_signals_only(client: AsyncClient, world: World, db_session: AsyncSession):
    employee = Employee(user_id=world.dev_id, employee_code="E-DAN")
    db_session.add(employee)
    await db_session.flush()
    monday = TODAY - timedelta(days=TODAY.weekday())
    group = await _group(client, world)
    on_time = (await _task(client, world, group, assignee=world.dev_id, due_date=str(monday + timedelta(days=6))))
    await _task(client, world, group, assignee=world.dev_id, due_date=str(monday + timedelta(days=6)))
    await client.patch(f"{API}/tasks/{on_time['task']['id']}/status", headers=world.dev, json={"status": "Completed"})

    score = await ScoringService(db_session).compute_weekly_score(employee.id, monday)
    assert (score.task_score, score.deadline_score, score.final_score) == (Decimal("50"), Decimal("100"), Decimal("75"))
    assert score.att_score is None and score.active_time_score is None and score.rating == "Good"
    stats = await candidate_stats(db_session, [world.dev_id])
    assert stats[world.dev_id]["latest_weekly_score"] == 75.0 and stats[world.dev_id]["open_tasks"] == 1
    assert json.dumps(stats, default=str)  # goes into a prompt as JSON
