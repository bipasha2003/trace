"""
TRACE - Phase 8: admin completion

DEVELOPMENT.md Phase 8 "Done when": an Admin can change the SMTP host without
touching .env (the LLM configuration stays fixed in .env), and a Manager can
download a project report for a date range from their dashboard. Plus the
Workforce tabs with bulk upload that reports rejected rows, and the Monitor's
recent Celery jobs.
"""

import csv
import io
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.services import mail_service
from app.services.system_settings import resolve_setting
from tests.api.v1.test_projects import API, World, _group, _task, world  # noqa: F401 — fixture

TODAY = date.today()


@pytest.fixture
async def admin(admin_headers, manager_headers, employee_headers, db_session: AsyncSession) -> dict:
    """Committed, so a request that fails (and rolls back) does not take the users with it."""
    await db_session.commit()
    return admin_headers


# ══════════════════════════════════════════════════════════════════
#  Configuration → Mail; the AI stays in .env
# ══════════════════════════════════════════════════════════════════

async def test_admin_changes_the_smtp_host_without_env(client: AsyncClient, admin, db_session: AsyncSession):
    url = f"{API}/admin/settings/mail"
    before = (await client.get(url, headers=admin)).json()
    assert before["host"] == get_settings().SMTP_HOST and before["password_set"] is False

    resp = await client.put(url, headers=admin, json={
        "host": "smtp.acme.com", "port": 587, "security": "starttls", "username": "trace",
        "password": "s3cret-pass", "from_address": "trace@acme.com"})
    assert resp.status_code == 200
    saved = resp.json()
    assert (saved["host"], saved["port"], saved["security"]) == ("smtp.acme.com", "587", "starttls")
    assert saved["password_set"] and saved["password_source"] == "database"
    assert "s3cret-pass" not in resp.text                                    # write-only

    config = await mail_service.mail_config(db_session)                     # what the next send uses
    assert (config.host, config.port, config.password) == ("smtp.acme.com", 587, "s3cret-pass")

    cleared = (await client.put(url, headers=admin, json={"password": ""})).json()
    assert cleared["password_set"] is False and cleared["host"] == "smtp.acme.com"


async def test_mail_settings_validation_and_guard(client: AsyncClient, admin, manager_headers):
    url = f"{API}/admin/settings/mail"
    assert (await client.put(url, headers=admin, json={"port": 0})).status_code == 422
    assert (await client.put(url, headers=admin, json={"security": "tls9"})).status_code == 422
    assert (await client.put(url, headers=admin, json={"from_address": "nope"})).status_code == 422
    assert (await client.get(url, headers=manager_headers)).status_code == 403


async def test_mail_connection_test(client: AsyncClient, admin, monkeypatch):
    seen = {}

    def fake_check(config):
        seen["host"] = config.host
        return [{"name": "Server", "ok": True, "detail": "answered"}]
    monkeypatch.setattr(mail_service, "check", fake_check)
    await client.put(f"{API}/admin/settings/mail", headers=admin, json={"host": "mail.acme.com"})
    resp = await client.post(f"{API}/admin/settings/mail/test", headers=admin)
    assert resp.json()["ok"] and seen["host"] == "mail.acme.com"


def test_mail_check_reports_an_unreachable_server():
    checks = mail_service.check(mail_service.MailConfig(host="127.0.0.1", port=1, from_address="a@b.co"))
    assert checks[0]["name"] == "Server" and not checks[0]["ok"]


def test_mail_body_is_escaped():
    _, html = mail_service.render("Hi", "<script>x</script>\nline two")
    assert "<script>" not in html and "&lt;script&gt;" in html and "<br>" in html


async def test_ai_is_not_a_database_setting(db_session: AsyncSession, monkeypatch):
    from app.services import ai_service
    from app.services.system_settings import store_setting
    monkeypatch.setattr(get_settings(), "OPENAI_API_KEY", "sk-from-env")
    await store_setting(db_session, "ai", "api_key", "sk-from-db")
    assert await resolve_setting(db_session, "ai", "model") == ""            # no .env fallback any more
    assert ai_service.client_from_settings()._client.api_key == "sk-from-env"


# ══════════════════════════════════════════════════════════════════
#  Workforce
# ══════════════════════════════════════════════════════════════════

WF = f"{API}/admin/workforce"


async def test_workforce_catalogue_has_every_tab(client: AsyncClient, admin, manager_headers):
    tabs = (await client.get(WF, headers=admin)).json()
    assert [t["key"] for t in tabs] == ["employees", "managers", "leaves", "holidays", "attendance",
                                         "shifts", "departments", "designations"]
    assert (await client.get(WF, headers=manager_headers)).status_code == 403
    assert (await client.get(f"{WF}/payroll", headers=admin)).status_code == 404


async def test_employee_crud_with_references(client: AsyncClient, admin):
    await client.post(f"{WF}/departments", headers=admin, json={"name": "Platform"})
    await client.post(f"{WF}/shifts", headers=admin,
                      json={"schedule_name": "Early", "start_time": "07:00", "end_time": "15:00"})
    resp = await client.post(f"{WF}/employees", headers=admin, json={
        "name": "Wendy Worker", "username": "wendy", "email": "wendy@trace.com", "password": "Passw0rd!",
        "employee_code": "E-100", "department": "platform", "shift": "Early", "joining_date": "2026-01-05"})
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["id"]

    rows = (await client.get(f"{WF}/employees", headers=admin)).json()
    wendy = next(r for r in rows if r["id"] == user_id)
    assert (wendy["employee_code"], wendy["department"], wendy["shift"]) == ("E-100", "Platform", "Early")
    assert "password" not in wendy

    login = await client.post(f"{API}/auth/login", json={"email": "wendy@trace.com", "password": "Passw0rd!"})
    assert login.status_code == 200                                          # a real account

    resp = await client.put(f"{WF}/employees/{user_id}", headers=admin,
                            json={"department": "", "status": "Blocked"})
    assert resp.status_code == 200
    wendy = next(r for r in (await client.get(f"{WF}/employees", headers=admin)).json() if r["id"] == user_id)
    assert wendy["department"] is None and wendy["status"] == "Blocked"

    bad = await client.post(f"{WF}/employees", headers=admin, json={
        "name": "Xavier", "username": "xx1", "email": "x@trace.com", "password": "Passw0rd!",
        "employee_code": "E-101", "department": "Nowhere"})
    assert bad.status_code == 422 and "Nowhere" in bad.json()["detail"]

    assert (await client.delete(f"{WF}/employees/{user_id}", headers=admin)).status_code == 204
    assert all(r["id"] != user_id for r in (await client.get(f"{WF}/employees", headers=admin)).json())


async def test_required_fields_and_duplicates(client: AsyncClient, admin):
    missing = await client.post(f"{WF}/holidays", headers=admin, json={"name": "No date"})
    assert missing.status_code == 422 and "Date" in missing.json()["detail"]
    assert (await client.post(f"{WF}/designations", headers=admin, json={"name": "Chef"})).status_code == 201
    dup = await client.post(f"{WF}/designations", headers=admin, json={"name": "Chef"})
    assert dup.status_code == 409


async def test_a_department_in_use_is_not_deleted(client: AsyncClient, admin):
    dept = (await client.post(f"{WF}/departments", headers=admin, json={"name": "Ops"})).json()["id"]
    await client.post(f"{WF}/employees", headers=admin, json={
        "name": "Olly Ops", "username": "olly", "email": "olly@trace.com", "password": "Passw0rd!",
        "employee_code": "E-200", "department": "Ops"})
    assert (await client.delete(f"{WF}/departments/{dept}", headers=admin)).status_code == 409


async def test_bulk_upload_reports_rejected_rows(client: AsyncClient, admin):
    await client.post(f"{WF}/employees", headers=admin, json={
        "name": "Lee Leave", "username": "lee", "email": "lee@trace.com", "password": "Passw0rd!",
        "employee_code": "E-300"})
    template = (await client.get(f"{WF}/leaves/template", headers=admin)).text
    assert template.strip() == "employee_code,leave_type,start_date,end_date,reason,status"

    body = (template +
            "E-300,Sick,2026-03-02,2026-03-03,Flu,Approved\n"      # line 2 — good
            "E-999,Sick,2026-03-02,2026-03-03,,\n"                 # line 3 — unknown employee
            "E-300,Casual,2026-13-01,2026-03-03,,\n"               # line 4 — bad date
            ",,,,,\n"                                              # blank — skipped
            "E-300,Casual,2026-04-10,2026-04-08,,\n"               # line 6 — ends before it starts
            "E-300,Earned,2026-05-01,2026-05-02,Trip,\n")          # line 7 — good
    resp = await client.post(f"{WF}/leaves/bulk", headers=admin,
                             files={"file": ("leaves.csv", body.encode(), "text/csv")})
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["created"] == 2
    assert [r["line"] for r in result["rejected"]] == [3, 4, 6]
    assert "E-999" in result["rejected"][0]["error"]

    leaves = (await client.get(f"{WF}/leaves", headers=admin)).json()
    assert {(r["employee_name"], r["status"]) for r in leaves} == {("Lee Leave", "Approved"), ("Lee Leave", "Pending")}


async def test_attendance_records_hours(client: AsyncClient, admin):
    await client.post(f"{WF}/employees", headers=admin, json={
        "name": "Ana Attend", "username": "ana", "email": "ana@trace.com", "password": "Passw0rd!",
        "employee_code": "E-400"})
    resp = await client.post(f"{WF}/attendance", headers=admin, json={
        "employee_code": "E-400", "attendance_date": "2026-03-02", "time_in": "09:00", "time_out": "17:30",
        "location_status": "office"})
    assert resp.status_code == 201, resp.text
    [row] = (await client.get(f"{WF}/attendance", headers=admin)).json()
    assert (row["time_in"], row["time_out"], row["employee_name"]) == ("09:00", "17:30", "Ana Attend")
    backwards = await client.put(f"{WF}/attendance/{row['id']}", headers=admin, json={"time_out": "08:00"})
    assert backwards.status_code == 422


async def test_manager_tab_creates_manager_accounts(client: AsyncClient, admin):
    resp = await client.post(f"{WF}/managers", headers=admin, json={
        "name": "Mia Manager", "username": "mia", "email": "mia@trace.com", "password": "Passw0rd!"})
    assert resp.status_code == 201
    login = (await client.post(f"{API}/auth/login", json={"email": "mia@trace.com", "password": "Passw0rd!"})).json()
    assert login["user"]["roles"] == ["Manager"]


# ══════════════════════════════════════════════════════════════════
#  Monitor — recent Celery jobs
# ══════════════════════════════════════════════════════════════════

def test_job_outcomes_read_failures_from_the_result():
    from app.api.v1.services import _job_outcome
    ok = _job_outcome({"task_id": "1", "name": "app.tasks.evaluate_project", "status": "SUCCESS",
                       "result": {"status": "success"}, "date_done": "2026-09-26T10:00:00"})
    failed = _job_outcome({"task_id": "2", "name": "app.tasks.evaluate_project", "status": "SUCCESS",
                           "result": {"status": "failed", "error": "Failed while planning"}})
    crashed = _job_outcome({"task_id": "3", "name": "app.tasks.send_mail_task", "status": "FAILURE",
                            "result": {"exc_type": "OSError", "exc_message": ["refused"]}})
    assert (ok["name"], ok["outcome"]) == ("evaluate_project", "SUCCESS")
    assert (failed["outcome"], failed["detail"]) == ("FAILED", "Failed while planning")
    assert (crashed["outcome"], crashed["detail"]) == ("FAILURE", "refused")


def test_weekly_report_email_is_retired():
    from app.celery_app import celery_app
    import app.tasks  # noqa: F401
    assert "app.tasks.send_weekly_report" not in celery_app.tasks
    scheduled = {e["task"] for e in celery_app.conf.beat_schedule.values()}
    assert "app.tasks.send_weekly_report" not in scheduled
    assert "app.tasks.task_due_reminders" in scheduled


# ══════════════════════════════════════════════════════════════════
#  Dashboard report download (PLANNING.md Q7)
# ══════════════════════════════════════════════════════════════════

def _csv(resp) -> list[dict]:
    return list(csv.DictReader(io.StringIO(resp.text)))


async def test_manager_downloads_a_report_for_a_range(client: AsyncClient, world: World):
    group = await _group(client, world)
    await _task(client, world, group, assignee=world.dev_id, due_date=str(TODAY + timedelta(days=3)))
    await _task(client, world, group, title="Write the docs", due_date=str(TODAY + timedelta(days=60)))

    resp = await client.get(f"{API}/projects/report", headers=world.manager,
                            params={"start": str(TODAY - timedelta(days=7)), "end": str(TODAY)})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    rows = _csv(resp)
    assert [r["Task"] for r in rows] == ["Build the cart", "Write the docs"]         # both created today
    assert rows[0]["Project"] == "Storefront" and rows[0]["Task group"] == "Checkout"
    assert rows[0]["Assignee"] == "Dev Dan" and rows[0]["Group completion %"] == "0"

    later = _csv(await client.get(f"{API}/projects/report", headers=world.manager, params={
        "start": str(TODAY + timedelta(days=30)), "end": str(TODAY + timedelta(days=90))}))
    assert [r["Task"] for r in later] == ["Write the docs"]                          # due in range

    empty = await client.get(f"{API}/projects/report", headers=world.manager, params={
        "start": str(TODAY - timedelta(days=90)), "end": str(TODAY - timedelta(days=30))})
    assert _csv(empty) == [] and empty.text.startswith("Project,")


async def test_report_follows_project_visibility(client: AsyncClient, world: World):
    await _task(client, world, await _group(client, world), assignee=world.dev_id)
    params = {"start": str(TODAY), "end": str(TODAY)}
    assert len(_csv(await client.get(f"{API}/projects/report", headers=world.dev, params=params))) == 1
    assert _csv(await client.get(f"{API}/projects/report", headers=world.other_manager, params=params)) == []
    assert _csv(await client.get(f"{API}/projects/report", headers=world.outsider, params=params)) == []
    one = await client.get(f"{API}/projects/report", headers=world.other_manager,
                           params={**params, "project_id": world.project_id})
    assert one.status_code == 403
    assert (await client.get(f"{API}/projects/report", headers=world.admin, params=params)).status_code == 403
    backwards = await client.get(f"{API}/projects/report", headers=world.manager,
                                 params={"start": str(TODAY), "end": str(TODAY - timedelta(days=1))})
    assert backwards.status_code == 422


@pytest.mark.parametrize("path", ["/api/v1/admin/workforce", "/api/v1/admin/settings/mail"])
async def test_admin_only(client: AsyncClient, employee_headers, path):
    assert (await client.get(path, headers=employee_headers)).status_code == 403
