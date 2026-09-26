"""
TRACE - Phase 4: project tree and Gantt (PROJECT.md §21–22, CORE.md §5.1)

The tree is a live read; the Gantt is a stored, versioned, schema-validated snapshot.
Both are read-only and visible to exactly the people who can see the project.
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, TaskGroup
from app.models.task import Task
from app.schemas.gantt import GanttChartData
from app.services import gantt_service
from tests.api.v1.test_route_guards import ANONYMOUS_REJECTED
from tests.api.v1.test_projects import API, World, _group, _task, world  # noqa: F401 — fixture

VIEWS = ["tree", "gantt", "gantt/versions"]


async def _project(db: AsyncSession, w: World) -> Project:
    return await db.get(Project, w.project_id)


# ══════════════════════════════════════════════════════════════════
#  Who may look — project-scoped role matrix
# ══════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("view", VIEWS)
@pytest.mark.parametrize("who,expected", [
    ("manager", 200), ("admin", 200), ("pm", 200), ("dev", 200),
    ("other_manager", 403), ("outsider", 403), ("newbie", 403),
])
async def test_visible_to_whoever_sees_the_project(client: AsyncClient, world: World, view, who, expected):
    await _task(client, world, await _group(client, world), assignee=world.dev_id)  # dev becomes a Member
    resp = await client.get(f"{API}/projects/{world.project_id}/{view}", headers=getattr(world, who))
    assert resp.status_code == expected, resp.text


@pytest.mark.parametrize("view", VIEWS)
async def test_anonymous_and_missing_projects(client: AsyncClient, world: World, view):
    assert (await client.get(f"{API}/projects/{world.project_id}/{view}")).status_code in ANONYMOUS_REJECTED
    assert (await client.get(f"{API}/projects/999999/{view}", headers=world.admin)).status_code == 404


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
async def test_read_only(client: AsyncClient, world: World, method):
    for view in VIEWS:
        resp = await client.request(method.upper(), f"{API}/projects/{world.project_id}/{view}", headers=world.pm)
        assert resp.status_code == 405, f"{method} {view}"


# ══════════════════════════════════════════════════════════════════
#  Tree
# ══════════════════════════════════════════════════════════════════

async def test_tree_mirrors_groups_tasks_and_assignees(client: AsyncClient, world: World):
    checkout = await _group(client, world, "Checkout")
    search = await _group(client, world, "Search")
    done = (await _task(client, world, checkout, assignee=world.dev_id))["task"]
    late = (await _task(client, world, checkout, title="Late one",
                        due_date=str(date.today() - timedelta(days=2))))["task"]
    await client.patch(f"{API}/tasks/{done['id']}/status", headers=world.dev, json={"status": "Completed"})

    tree = (await client.get(f"{API}/projects/{world.project_id}/tree", headers=world.dev)).json()
    assert tree["project"]["name"] == "Storefront"
    assert tree["project"]["completion_percentage"] == 50.0
    assert [g["name"] for g in tree["groups"]] == ["Checkout", "Search"]
    first, second = tree["groups"]
    assert first["completion_percentage"] == 50.0 and second["tasks"] == [] and second["id"] == search
    by_id = {t["id"]: t for t in first["tasks"]}
    assert by_id[done["id"]]["status"] == "Completed"
    assert by_id[done["id"]]["assignee"]["github_username"] == "dan-gh"
    assert by_id[done["id"]]["github_issue_url"].startswith("https://github.com/acme/storefront/issues/")
    assert by_id[late["id"]]["overdue"] is True and by_id[late["id"]]["assignee"] is None


async def test_tree_leaves_out_deleted_tasks(client: AsyncClient, world: World):
    group = await _group(client, world)
    gone = (await _task(client, world, group))["task"]
    await client.delete(f"{API}/tasks/{gone['id']}", headers=world.pm)
    tree = (await client.get(f"{API}/projects/{world.project_id}/tree", headers=world.pm)).json()
    assert tree["groups"][0]["tasks"] == []


# ══════════════════════════════════════════════════════════════════
#  Gantt API
# ══════════════════════════════════════════════════════════════════

async def test_no_gantt_yet_is_null_not_an_error(client: AsyncClient, world: World):
    resp = await client.get(f"{API}/projects/{world.project_id}/gantt", headers=world.manager)
    assert resp.status_code == 200 and resp.json() is None
    assert (await client.get(f"{API}/projects/{world.project_id}/gantt/versions", headers=world.manager)).json() == []
    assert (await client.get(f"{API}/projects/{world.project_id}/gantt?version=1",
                             headers=world.manager)).status_code == 404


async def test_versions_are_appended_never_patched(client: AsyncClient, world: World, db_session: AsyncSession):
    group = await _group(client, world)
    task = (await _task(client, world, group, assignee=world.dev_id))["task"]
    project = await _project(db_session, world)
    await gantt_service.snapshot(db_session, project, "initial")
    await db_session.commit()

    await client.patch(f"{API}/tasks/{task['id']}/status", headers=world.dev, json={"status": "Completed"})
    await gantt_service.snapshot(db_session, project, "task_status_change")
    await db_session.commit()

    latest = (await client.get(f"{API}/projects/{world.project_id}/gantt", headers=world.dev)).json()
    assert latest["version"] == 2 == latest["latest_version"]
    assert latest["generated_reason"] == "task_status_change"
    assert latest["chart_data"]["bars"][0]["completion"] == 100.0

    first = (await client.get(f"{API}/projects/{world.project_id}/gantt?version=1", headers=world.dev)).json()
    assert first["version"] == 1 and first["latest_version"] == 2
    assert first["chart_data"]["bars"][0]["completion"] == 0.0  # what was true then
    assert first["chart_data"]["bars"][0]["tasks"][0]["status"] == "Pending"

    history = (await client.get(f"{API}/projects/{world.project_id}/gantt/versions", headers=world.dev)).json()
    assert [(v["version"], v["generated_reason"]) for v in history] == [(2, "task_status_change"), (1, "initial")]


# ══════════════════════════════════════════════════════════════════
#  Builder and schema — CORE.md §5.1
# ══════════════════════════════════════════════════════════════════

def _group_row(gid, name, seq, start=None, end=None, days=None, pct=0, status="Pending") -> TaskGroup:
    return TaskGroup(id=gid, project_id=1, name=name, sequence=seq, planned_start_date=start,
                     planned_end_date=end, estimated_duration_days=days, completion_percentage=pct, status=status)


def test_builder_lays_undated_groups_end_to_end():
    project = Project(id=1, name="P", start_date=date(2026, 1, 5), end_date=date(2026, 3, 31))
    dated = _group_row(1, "Design", 1, date(2026, 1, 5), date(2026, 1, 9))
    undated = _group_row(2, "Build", 2, days=10)
    default = _group_row(3, "Ship", 3)
    tasks = [Task(id=7, title="Wireframes", status="Completed", due_date=date(2026, 1, 8)),
             Task(id=8, title="Dropped", status="Cancelled")]
    data = gantt_service.build_chart_data(project, [(dated, tasks), (undated, []), (default, [])],
                                          dependencies=[(1, 2)]).dump()

    assert data["schema"] == 1
    bars = data["bars"]
    assert (bars[0]["start"], bars[0]["end"]) == ("2026-01-05", "2026-01-09")
    assert (bars[1]["start"], bars[1]["end"]) == ("2026-01-10", "2026-01-19")   # 10 days after Design
    assert (bars[2]["start"], bars[2]["end"]) == ("2026-01-20", "2026-01-26")   # the 7-day default
    assert [t["task_id"] for t in bars[0]["tasks"]] == [7]                      # cancelled left out
    assert data["dependencies"] == [{"from": 1, "to": 2}]
    assert data["milestones"] == [{"name": "Project end", "date": "2026-03-31"}]
    assert data["range"] == {"start": "2026-01-05", "end": "2026-03-31"}


def test_builder_without_a_start_date_starts_today():
    data = gantt_service.build_chart_data(Project(id=1, name="P"), [(_group_row(1, "A", 1), [])],
                                          today=date(2026, 5, 1)).dump()
    assert data["bars"][0]["start"] == "2026-05-01" and data["milestones"] == []


def _chart(**overrides) -> dict:
    chart = {
        "schema": 1, "range": {"start": "2026-01-01", "end": "2026-01-31"},
        "bars": [
            {"task_group_id": 1, "name": "A", "sequence": 1, "start": "2026-01-01", "end": "2026-01-10",
             "completion": 0, "status": "Pending", "tasks": []},
            {"task_group_id": 2, "name": "B", "sequence": 2, "start": "2026-01-11", "end": "2026-01-20",
             "completion": 50, "status": "In Progress", "tasks": []},
        ],
        "dependencies": [{"from": 1, "to": 2}], "milestones": [],
    }
    chart.update(overrides)
    return chart


@pytest.mark.parametrize("bad", [
    {"schema": 2},
    {"dependencies": [{"from": 1, "to": 1}]},
    {"dependencies": [{"from": 1, "to": 9}]},
    {"range": {"start": "2026-01-05", "end": "2026-01-31"}},
    {"milestones": [{"name": "Late", "date": "2026-02-15"}]},
    {"bars": [{"task_group_id": 1, "name": "A", "sequence": 1, "start": "2026-01-10", "end": "2026-01-01",
               "completion": 0, "status": "Pending"}], "dependencies": []},
    {"bars": [{"task_group_id": 1, "name": "A", "sequence": 1, "start": "2026-01-01", "end": "2026-01-02",
               "completion": 120, "status": "Pending"}], "dependencies": []},
    {"bars": [{"task_group_id": 1, "name": "A", "sequence": 1, "start": "2026-01-01", "end": "2026-01-02",
               "completion": 0, "status": "Overdue"}], "dependencies": []},
])
def test_schema_refuses_inconsistent_charts(bad):
    with pytest.raises(ValidationError):
        GanttChartData.model_validate(_chart(**bad))


def test_schema_round_trips_public_key_names():
    assert GanttChartData.model_validate(_chart()).dump() == _chart()


async def test_save_version_never_persists_an_invalid_chart(db_session: AsyncSession, world: World):
    with pytest.raises(ValidationError):
        await gantt_service.save_version(db_session, world.project_id, _chart(schema=2), "manual")
    assert await gantt_service.versions(db_session, world.project_id) == []


async def test_demo_seed_ships_a_hand_written_gantt(db_session: AsyncSession):
    """DEVELOPMENT.md Phase 4 'Done when': real data before Phase 5 writes charts."""
    from sqlalchemy import select
    from app import seeds
    from tests.conftest import make_user_headers
    await make_user_headers(db_session, "Manager", email="manager@trace.com")
    await seeds.seed_demo_project(db_session)

    project = (await db_session.execute(select(Project).where(Project.name == "TRACE Platform MVP"))).scalar_one()
    [chart] = await gantt_service.versions(db_session, project.id)
    data = GanttChartData.model_validate(chart.chart_data)
    assert chart.version == 1 and chart.generated_reason == "initial"
    assert [b.name for b in data.bars] == ["Backend Foundation", "Frontend Shell", "AI Pipeline"]
    assert str(data.bars[0].start) == "2026-09-01" and len(data.dependencies) == 2
    assert all(len(b.tasks) == 1 for b in data.bars)
