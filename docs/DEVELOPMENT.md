# DEVELOPMENT.md — Build Phases

> Step-by-step requirements for agents building TRACE, in dependency order.
>
> **Before starting any phase:** read [`PROJECT.md`](PROJECT.md) for what you are
> building, [`CORE.md`](CORE.md) if the phase touches AI, the Gantt or task status, and
> [`PLANNING.md`](PLANNING.md) for the open questions in that area. Conventions are
> in [`../AGENTS.md`](../AGENTS.md).

## Handoff — where the build stands *(updated 2026-09-26)*

**Start here if you are picking this up fresh.** Then read [`../AGENTS.md`](../AGENTS.md),
[`PROJECT.md`](PROJECT.md), and — for anything GitHub, AI or completion — [`CORE.md`](CORE.md).

| Phase | State |
|-------|-------|
| 0 · Clear the ground | ✅ |
| 1 · Schema | ✅ |
| 2 · Panels, landing, route guards | ✅ |
| 3 · Projects, without AI | ✅ built and tested — see its status note for what is unverified |
| 3a · GitHub owner model | ✅ built, tested, and verified against real GitHub (opt-in live test) |
| 4 · Visualisation | ✅ built and tested; not browser-checked (user decision) |
| **5 · The AI pipeline** | 🔲 **next** — read *Starting Phase 5* below |
| 7 – 9 | 🔲 not started. Phase 8 may run in parallel |
| ~~6 · CI/CD-driven completion~~ | ❌ **removed** 2026-09-26 — the assignee marks their own task complete ([`CORE.md`](CORE.md) §7) |

**Verify before you trust this table** — facts that change outside the docs:
- `git log --oneline -5` and `git status` — what is committed; untracked files are
  how Phase 2 once went missing from `main`.
- `cd backend && .venv/bin/python -m pytest -q` — 326 passing and 2 skipped at handoff (the skips are the opt-in live GitHub test). The suite
  uses its own `trace_test` database (built by Alembic) and fakes GitHub and MinIO,
  so it is safe to run anywhere — but it needs the Compose `db` **and** `redis`
  services up (`docker compose up -d db redis`); without Redis three job-poll tests
  fail.
- `cd frontend && npm run build` — must pass.

**Environment traps**
- **Develop and test locally only.** The user tests production themselves — do not
  check, restart or deploy it. Production can run from this same working tree and
  database (README → Production), so before `./start.sh` or anything binding ports
  5173 / 8000, check `./start.sh status`; `APP_ENV=local` at handoff.
- The root `.env` is the only env file (AGENTS.md §4). It holds the real
  `GITHUB_OWNER=trace-organization` and a real `GITHUB_TOKEN` — never print them.
  Tests pin their own values (`conftest.py`) and can never reach real GitHub.
- The local database's demo project (id 1) points at
  `trace-organization/trace-platform`, a repo the user created by hand.
- `SETTINGS_ENCRYPTION_KEY` was generated into the root `.env` by Phase 3a.
  Production now refuses to start without it, and **changing it makes every saved
  secret unreadable** (re-enter them). Don't regenerate it casually.
- `cryptography` was added to `requirements.txt` — reinstall the venv
  (`pip install -r requirements.txt`) on any other checkout before starting.
- `@xyflow/react` was added to `frontend/package.json` in Phase 4 — run `npm install`
  in `frontend/` on any other checkout.
- The local database is at Alembic head `c4e1d2a7f9b3` (drops `cicd_events`). A
  database that runs production must be migrated too — `./start.sh start` does it.
- Only the Admin can create Admin / Manager accounts. Production does not seed demo
  users, and refuses to start while any seeded account still has its published
  password — change them with `./start.sh set-password <email>` (README → Production).

**Known gaps** (each is also in its phase or `PROJECT.md` §24)
- **Real GitHub is verified** against `trace-organization` (owner account
  `trace-personal`) by the opt-in `tests/test_github_live.py`: connection test,
  project → public repo, name clash 409, document commits, issue assign / unassign /
  close, project delete → repo archived. Run it with
  `TRACE_LIVE_GITHUB=1 .venv/bin/python -m pytest -q tests/test_github_live.py -s`;
  **each run leaves one archived public `trace-smoke-<timestamp>` repo** — ask the user
  before running it. Still not exercised for real: a collaborator invitation to
  another account (set `TRACE_LIVE_GITHUB_INVITEE=<username>` to include it).
- If the database commit fails right after GitHub created a repo, the repo is left
  behind (the token cannot delete). Rare; clean up by hand.
- There is no delete-project button — `DELETE /projects/{id}` is API-only.

*Owned by later phases, not gaps in 0–3a:*
- `services/scoring_service.py` still reads the dropped `Task.assigned_to` —
  `/productivity/compute*` fails until Phase 5 step 3 re-bases scoring.
- `components/ServiceMonitor.jsx` links to Mailpit / MinIO / pgAdmin at `localhost` — Phase 8.
- Progress Report and Project Doc tabs are placeholders — Phase 5.
- **Nothing generates Gantt versions yet.** Only the demo project has one (hand-written
  v1); every other project shows "No Gantt chart yet" until Phase 5.
- The nightly `mark_delayed_tasks` (`app/tasks.py`, Celery Beat) is pre-re-spec: it
  sets past-due `Pending` / `WIP` tasks to **`Delayed`**, a status that no longer
  exists. Harmless only while Beat is not running. Phase 7 step 5 replaces it with
  `mark_overdue_tasks` (`CORE.md` §8) — do that early if Beat is started.
- Old pages `AttendancePage`, `EmployeesPage`, `ProductivityPage`, `AdminPanelPage`,
  `FilesPage`, `SettingsPage` are unrouted; Phase 8 rebuilds or deletes them.

*Not planned* (user decision, `PLANNING.md` §4): removing Members from a project,
a resend-invitation action. Don't build them unasked.

**Starting Phase 5** — what the phase text below does not tell you
- **Read `CORE.md` in full first** — it changed on 2026-09-26: completion is manual
  (§7, no CI/CD, no AI), and §5.1 now fixes the `chart_data` shape.
- **The Gantt plumbing exists; only the AI is missing.** `gantt_service.snapshot(db,
  project, reason, dependencies)` builds a valid version from the task groups and
  saves it; `save_version()` validates anything else against `GanttChartData`.
  Stage 1 step 6 = write dates/durations into the task groups, then `snapshot(...,
  "initial", dependencies=...)`. `reevaluate_gantt` needs its triggers wired:
  `project_service.set_status` (→ Completed), the overdue sweep, a `project_doc`
  save, and a manual button — debounced (CORE §5).
- **`task_groups` has no dependency column.** The AI's `depends_on` (CORE §3 step 5)
  names groups; decide whether to add a column (one Alembic revision) so
  re-evaluations keep the dependencies, and log it in `PLANNING.md` §2.
- **There is no AI service layer yet** — only `llm_chat_task` in `app/tasks.py`,
  which reads `OPENAI_*` straight from `Settings`. Step 1 must resolve credentials
  through `resolve_setting(db, "ai", …)` (the `ai.api_key` secret is already in
  `SECRET_SETTINGS`) and validate every response against a schema (AGENTS.md §4).
  Tests must fake the model the way `fake_github` fakes GitHub — no real LLM calls.
- `services/scoring_service.py` still reads the dropped `Task.assigned_to` — step 3
  re-bases it on task signals only (no CI/CD any more).
- Every AI action is enqueue-and-poll (AGENTS.md §5); the job-result endpoint exists.

---

**Rules for every phase**
- **Every feature you implement, modify or remove requires its documentation
  updated in the same change.** The full map of what to update is at the top of
  [`../AGENTS.md`](../AGENTS.md). At minimum: flip the feature's status in
  [`PROJECT.md`](PROJECT.md) §24, and log any non-obvious decision in
  [`PLANNING.md`](PLANNING.md) §2 and §5. **A step is not done until the docs
  describe what the code now does.**
- A phase is done when its "Done when" line is demonstrably true — not when the
  code is written.
- Do not extend or polish anything marked ❌ in the registry.
- Never drop a table without confirmation. The workforce record set is **retained**.
- If a phase's instructions turn out to be wrong, fix this document as part of the
  work rather than diverging from it silently.

**Dependency graph**
```
Phase 0 ─► Phase 1 ─► Phase 2 ─► Phase 3 ─► Phase 3a ─► Phase 4 ─► Phase 5 ─► Phase 7
                          │
                          └────────────────────────────────────────► Phase 8 ─► Phase 9
```
Phase 8 needs only 0–2 and may run in parallel with 3–7 (its GitHub section is Phase 3a).
Phase 6 (CI/CD-driven completion) was removed; the numbers of later phases are kept
so existing references stay valid.

---

## Phase 0 — Clear the ground ✅

*Status: Completed. All routes, services, template scaffolding, and frontend dead features removed. Retained workforce and health endpoints verified operational.*
optional tidying** — leftover routes, dead components and stale seeds actively
mislead agents about what the system does. Do this first, completely, before
writing anything new.

> **Golden rule for this phase: delete routes, services and frontend now; delete
> model classes in Phase 1.**
> If you delete a model class while its table still exists, the next
> `alembic revision --autogenerate` will propose dropping that table at a moment
> when nothing has been backfilled yet. Phase 1 removes each model class in the
> same revision that drops its table. Phase 0 leaves `backend/app/models/**` and
> `models/__init__.py` alone.

### 0.1 Repository hygiene

| Item | Action |
|------|--------|
| `.trace_pids` | Runtime artifact, currently **tracked**. `git rm --cached .trace_pids` and add it to `.gitignore` |
| `bipasha-Synopsis2026.pdf` (1.5 MB, repo root) | Unrelated to the codebase. **Ask before deleting** — if it is a reference document it belongs in `docs/`, otherwise out of the repo |
| `.gitignore` | Confirm `.env`, `.venv/`, `node_modules/`, `__pycache__/`, `*.pid` are covered |

### 0.2 Collapse to three platform roles

| File | Change |
|------|--------|
| `backend/app/seeds.py` | `ROLES = ["Platform Admin", "Admin", "Manager", "Staff"]` → `["Admin", "Manager", "Employee"]` |
| `backend/app/seeds.py` | Delete `seed_platform_admin()` entirely and its call in `run_seeds()` |
| `backend/app/core/permissions.py` | `RoleEnum.STAFF = "Staff"` → `EMPLOYEE = "Employee"`; update `require_any_role` |
| `backend/app/api/v1/admin.py` | The local `require_admin()` checks for `"Platform Admin"` — reduce to `"Admin"` |
| `backend/app/config.py` | Delete `PLATFORM_ADMIN_EMAIL`, `PLATFORM_ADMIN_USERNAME`, `PLATFORM_ADMIN_PASSWORD`, `PLATFORM_ADMIN_NAME` |
| `backend/.env`, `backend/.env.example` | Remove the same four keys |
| `frontend/src/layouts/Sidebar.jsx` | The `isAdmin` check tests `'Platform Admin' \|\| 'Admin'` — reduce to `'Admin'` |

Existing rows are migrated in Phase 1 step 3. Phase 0 only changes the code that
would keep recreating them.

### 0.3 Dynamic roles, dynamic menus, permission matrix

| File | Change |
|------|--------|
| `backend/app/api/v1/master.py` | Delete `/roles` ×3, `/menus` ×3, `/menu-permissions` ×2, `/my-permissions`. That is the entire file — **delete `master.py`** and its `include_router` line in `api/v1/router.py`. Designations already live under `/employees`, so nothing is orphaned |
| `backend/app/api/v1/admin.py` | Remove the `role_menu_permissions` entry from `MODEL_REGISTRY` |
| `frontend/src/pages/MasterPage.jsx` | Delete (540 lines) |
| `frontend/src/api/master.js` | Delete; drop its re-export from `api/index.js`. Move the three designation calls to `api/employees.js` |
| `frontend/src/App.jsx` | Remove the `/master` route |
| `frontend/src/layouts/Sidebar.jsx` | Remove the `master` nav item **and the whole `getMyPermissions()` / `allowedKeys` mechanism** — menus are static from Phase 2 |

### 0.4 HR interfaces — remove the UI, keep the data

This is the step most likely to be over-applied. Read [`PROJECT.md`](PROJECT.md)
§9.1 first.

**Remove**

| File | Change |
|------|--------|
| `backend/app/api/v1/attendance.py` | Delete `POST /checkin` and `POST /checkout` only |
| `backend/app/core/geolocation.py` | Delete the file — geo-fence enforcement is gone |
| `backend/app/config.py` | Delete `DEFAULT_GEO_FENCE_RADIUS_METERS` |
| `frontend/src/api/attendance.js` | Remove `checkIn` and `checkOut` |
| `frontend/src/pages/AttendancePage.jsx` | Remove the clock-in/out controls, the browser Geolocation call, and the Manager multi-tab view. **Keep the file** — Phase 8 rebuilds it as Admin → Workforce |

**Keep — do not touch**

- `GET /attendance/history`, `GET /attendance/all`, `GET /attendance/summary/daily`
- Every endpoint in `hrms.py`: leaves, holidays, **shifts**, `bulk-upload`,
  `assign-shift`, leave-balance
- The `attendance` and `work_schedules` tables and their models
- The `geo_latitude` / `geo_longitude` columns — they stay as recorded values
- `scoring_service.py` — leave scoring alone here; Phase 5 step 3 re-bases it

### 0.5 Project group chat

| File | Change |
|------|--------|
| `backend/app/api/v1/tasks.py` | Delete `GET /groups/list`, `POST /groups/{id}/messages`, and the `@router.websocket("/groups/{group_id}/ws")` handler |
| `backend/app/api/v1/admin.py` | Remove `project_groups` and `project_group_messages` from `MODEL_REGISTRY` |
| `frontend/src/api/tasks.js` | Remove `getGroups`, `postGroupMessage` |
| `frontend/src/pages/TasksPage.jsx` | Remove the chat channel UI and its tagging-rule dropdown |

The WebSocket *infrastructure* stays — Phase 7 re-points it at notifications and
task discussion.

### 0.6 Park the deferred AI features

Their designs are preserved in [`PLANNING.md`](PLANNING.md) §3. Delete the code,
not the thinking.

| File | Change |
|------|--------|
| `backend/app/api/v1/tasks.py` | Delete `POST /dispute`, `GET /disputes`, `PATCH /disputes/{id}`, `GET /overallocations` |
| `backend/app/tasks.py` | Delete the `detect_overallocation` Celery task |
| `backend/app/celery_app.py` | Remove the `detect-overallocation-nightly` Beat entry |
| `frontend/src/api/tasks.js` | Remove `createDispute`, `getDisputes`, `reviewDispute`, `getOverallocations` |
| `frontend/src/pages/TasksPage.jsx` | Remove the Dispute Queue tab and the risk/overallocation cards |

**Task Health Score is retained — handle it carefully.** It is ✅ in
[`PROJECT.md`](PROJECT.md) §24, but the job it lives in also performs
auto-escalation, which is deferred. Split them:

- **Keep** the `health_score`, `health_reason`, `last_health_check` columns,
  `GET /tasks/health-summary`, and `POST /tasks/{id}/compute-health`
- **Remove** the Mailpit escalation email from `compute_task_health_and_escalate`,
  and drop its hourly Beat entry ([`CORE.md`](CORE.md) §8)
- Health is then computed on demand; Phase 7 folds recomputation into the nightly
  overdue sweep

### 0.7 Infinite-tree endpoints

| File | Change |
|------|--------|
| `backend/app/api/v1/tasks.py` | Delete `GET /tree/hierarchy` and `POST /{id}/evaluate-tree` |
| `backend/app/services/task_service.py` | Remove tree-walking helpers these depended on |
| `frontend/src/api/tasks.js` | Remove `getTree`, `evaluateTree` |
| `frontend/src/pages/TasksPage.jsx` | Remove the tree view |

**Do not drop the columns yet.** `parent_task_id`, `team_lead_id`,
`project_manager_id`, `task_level_role` and `tree_path` carry the data Phase 1
step 4 backfills from. They go in Phase 1 step 5.

### 0.8 Dead frontend scaffolding

Left over from the shadcn dashboard template; never imported by the app. **Verify
with `grep -rl` before deleting each one** — do not trust this list blindly.

| File | Note |
|------|------|
| `components/app-sidebar.jsx` | Unused duplicate of `layouts/Sidebar.jsx` |
| `components/nav-main.jsx`, `nav-documents.jsx`, `nav-secondary.jsx`, `nav-user.jsx` | Imported **only** by `app-sidebar.jsx`; they die with it |
| `components/chart-area-interactive.jsx` | Template demo |
| `components/data-table.jsx` | Template demo |
| `components/section-cards.jsx` | Template demo |
| `components/site-header.jsx` | Unused duplicate of `layouts/Header.jsx` |
| `components/login-form.jsx` | Unused duplicate of `pages/LoginPage.jsx` |
| `data/mock.js` | Unused mock data |
| `hooks/useApi.js` | Unused |

Leave `components/ui/**` alone — it is shadcn-generated, and unused primitives
there are harmless.

### 0.9 Seeds

| Function in `seeds.py` | Action |
|------------------------|--------|
| `seed_roles` | Update to the three roles (0.2) |
| `seed_platform_admin` | Delete (0.2) |
| `seed_sample_tree_and_hrms` | Seeds the infinite tree — delete the tree portion. Phase 1 step 6 replaces it with a demo project |
| `seed_departments`, `seed_task_types`, `seed_work_schedules`, `seed_time_zones`, `seed_admin_user` | **Keep** |

### 0.10 Do not remove

An explicit guard list, because several of these look like collateral:

- The workforce record set — `employees`, `employee_details`, `departments`,
  `designations`, `leaves`, `holidays`, `attendance`, `work_schedules` — tables,
  models **and** their read/CRUD endpoints
- `/hrms/bulk-upload` — it is required by Phase 8 for every Workforce tab
- Task Health Score columns and its two endpoints (0.6)
- `api/v1/services.py` — health checks, MinIO, Mailpit, LLM, and the
  `/services/task/{id}/result` polling endpoint every AI action depends on
- `components/ServiceMonitor.jsx` — becomes Admin → Monitor
- `api/v1/admin.py` and `AdminPanelPage.jsx` — become Control Panel
- `components/ProtectedRoute.jsx` — Phase 2 builds on it
- `components/ui/**`
- The WebSocket infrastructure — re-pointed, not removed
- Celery, MinIO, Mailpit and Redis wiring

### 0.11 Verification

Phase 0 is done when **all** of these hold:

1. `grep -rn "ProjectGroup\|EvaluationDispute\|SystemMenu\|RoleMenuPermission\|Platform Admin\|getMyPermissions\|evaluateTree\|detect_overallocation" backend/app frontend/src` returns only model definitions in `backend/app/models/` (which Phase 1 removes).
2. `./start.sh start` brings the stack up with no import errors in the backend log or the browser console.
3. Login works, and the app renders without the removed pages.
4. `http://localhost:8000/docs` lists no removed endpoint, and still lists every
   workforce endpoint from 0.4.
5. `./start.sh migrate` still runs clean — no model classes were deleted, so there
   should be **no** pending autogenerate diff.
6. Nothing in `frontend/src` imports a deleted file.

**Done when:** the app starts, login works, every removed feature is gone from the
API and the UI, and the workforce endpoints in 0.4 still respond.

## Phase 1 — Schema ✅

*Status: Completed 2026-09-24. All new tables created, tasks altered, backfill done, deprecated tables dropped, roles migrated, demo project seeded. `alembic revision --autogenerate` produces a clean diff.*

---

## Phase 2 — Panel separation & landing page ✅

*Status: Completed 2026-09-25. Three panel layouts (AdminLayout sidebar, ManagerLayout/EmployeeLayout topbar-only) built. GuestOnlyRoute and RoleRoute guards implemented. /403 ForbiddenPage built — shows role info, never silently redirects. LoginPage redirects to role-based base route. LandingPage built with hero, problem statement, 3-step how-it-works, feature grid, CTA and footer. Admin sidebar rewritten with static 5-item menu. MonitorPage promoted from header overlay to full /admin/monitor page. Stub panel pages in place for Phase 3 wiring. Frontend build passes with exit code 0.*

*Step 6 completed 2026-09-25 (the frontend files above only reached `main` in commit `c1f915a`). Every route now carries a platform-role guard: `/hrms`, `/attendance`, `/productivity`, the workforce writes and lists in `/employees`, and the `/services` health, test-mail, MinIO and LLM endpoints are Admin-only; `/services/task/{id}/result`, `/employees/me`, the department and designation lists and the legacy `/tasks` router require any signed-in role. The only unauthenticated routes are `/health`, `/auth/login`, `/auth/refresh` and `/auth/register` — and self-registration now always creates an `Employee`; only an Admin may create Admin or Manager accounts.*

*Verified 2026-09-25 by `backend/tests` (162 passing): a static audit that every route is guarded, a role matrix over real endpoints for Admin / Manager / Employee / anonymous, the registration rules, and a migration test that takes an **empty** database to head with no autogenerate drift. That last one needed a catch-up revision (`0a1c2e3f4d5b`) — see [`PLANNING.md`](PLANNING.md) §2.*

1. Split `DashboardLayout` into `AdminLayout` (sidebar), `ManagerLayout` and
   `EmployeeLayout` (topbar only).
2. Build `RoleRoute`, `GuestOnlyRoute`, the `/403` page, and the `/` → base-route
   redirect ([`PROJECT.md`](PROJECT.md) §16).
3. Build `LandingPage.jsx` (§17). This is the product's front door — give it real
   design effort.
4. Rewrite `Sidebar.jsx` with the static Admin menu; delete the permission fetch.
5. Move existing pages under their panel: Control Panel, Workforce, Monitor.
6. Backend: guard every route by platform role.

**Done when:** each role lands on its own panel, cross-panel access 403s, and a
logged-out visitor sees the landing page.

---

## Phase 3 — Projects, without AI ✅

*Status: built and tested 2026-09-26 (232 backend tests; frontend builds). Not yet
checked in a browser — production occupies the local ports — and not yet live until
production restarts. Step 3's repository and credential handling was reworked
by **Phase 3a** below.*

- *Backend:* `api/v1/projects.py` (projects, source files, team, candidates, task
  groups, project tasks) and a rewritten `api/v1/tasks.py` (task by id, assign,
  status, delete, `/tasks/mine`). Authorisation in `core/project_access.py`;
  rules in `services/project_service.py`; GitHub in `services/github_service.py`;
  MinIO in `services/storage.py`; extraction in `services/extraction.py`.
- *The legacy `/tasks` router is gone.* It let any signed-in user set `Completed`
  through `PATCH /tasks/{id}` or `/status`, and most handlers referenced dropped
  columns. `task_service.py`, `schemas/task.py`, `TasksPage.jsx` and
  `DashboardPage.jsx` were deleted with it.
- *Frontend:* `ProjectSelector`, Manager dashboard / create stepper / project
  detail, Employee dashboard / project (PM and Member tabs) / task detail, GitHub
  username on the Employee profile.
- *Tests:* `tests/api/v1/test_projects.py` against a fake GitHub on
  `httpx.MockTransport` — the real client runs, only the network is fake.
  An autouse fixture keeps every test away from real GitHub and MinIO.

Build the full manual path first, so the AI layer has something real to plug into.

1. `/projects` CRUD, Manager-owned, one owning Manager per project (Q11).
2. Multi-file source upload to MinIO plus text extraction (pdf / docx / md / txt).
3. A GitHub integration service: create issue, assign issue, commit a markdown
   file, return its URL. Credentials resolved from `system_settings`.
4. Project Manager assignment and removal via `project_assignments`.
5. Manager panel: project selector, combined dashboard, create-project stepper,
   project detail ([`PROJECT.md`](PROJECT.md) §19).
6. Task groups and tasks CRUD — manually created at this stage — with **automatic
   GitHub issue creation** on task create.
7. Employee panel: project selector, combined dashboard, PM view, Member view,
   task detail (§20).
8. **Status authority enforced server-side** ([`CORE.md`](CORE.md) §7), result
   recorded in `completed_by`. *(Built with Member → 403 on Completed; reworked
   2026-09-26 so the assignee completes their own task.)*

**Done when:** a Manager can create a project and assign a PM, and that PM can
create tasks that appear as GitHub issues — with no AI involved at all.

**Tests:** the legacy `tests/api/v1/test_tasks_attendance.py` was removed in Phase 2
(it exercised clock-in/out and the tree-era `/tasks` router); Phase 3's
`test_projects.py` replaces it, including the status-authority rules.

---

## Phase 3a — GitHub owner model ✅

*Status: built and tested 2026-09-26 (277 backend tests; frontend builds). Tested
only against the fake GitHub in `tests/conftest.py`, never real GitHub; not yet
clicked through in a browser (not required). Where the build differs from the steps below: the
create form also lost its default-branch field (the branch comes from GitHub);
collaborator problems are warnings, never failures; `system_settings` left the
Control Panel's generic CRUD; removing a PM answers 200 `{project_role, warnings}`
— all logged in [`PLANNING.md`](PLANNING.md) §2 / §5.*

- *Backend:* `api/v1/settings.py` (Admin); `services/system_settings.py` gains
  `store_setting` / `setting_source` and Fernet encryption; `github_service.py`
  gains `repo_slug`, `create_repo`, `add_collaborator`, `remove_collaborator`,
  `authenticated_login`, `organization`, `resolve_owner`; `project_service.py`
  gains `create_project`, `grant_repo_access`, `revoke_repo_access` and the
  unassigned-issue fallback.
- *Frontend:* `pages/admin/ConfigurationPage.jsx` (GitHub section), `api/settings.js`,
  `ProjectCreatePage.jsx` (slug preview, public notice), `TeamPanel.jsx` (warnings).
- *Tests:* `tests/api/v1/test_settings.py`; Phase 3a block in `test_projects.py`.
- *Follow-up (same day):* deleting a project archives its repository; Phase 0
  leftovers removed (`core/geolocation.py`, `services/attendance_service.py`,
  `layouts/DashboardLayout.jsx`, `layouts/Header.jsx`); demo seed uses the real org.

**Read [`CORE.md`](CORE.md) §4.1 first.** Decided 2026-09-26: TRACE uses one
company GitHub **Organization** (Q12) and one token, entered by the Admin, and
creates every project's repository itself, **always public** (Q13). This pulls the
GitHub part of Phase 8's Configuration screen forward, because no task can be
created without it. No schema change is needed.

1. **Secret storage.** Encrypt `system_settings` rows with `is_secret` at rest:
   Fernet from `cryptography` (add it to `requirements.txt` — it is not installed
   today), key in `.env` as `SETTINGS_ENCRYPTION_KEY`. Decrypt only inside
   `resolve_setting()`. Add the key to the production preflight
   (`Settings.production_problems()`). No API ever returns a secret — responses
   carry `"token_set": true|false`.
2. **Settings API** (Admin): `GET/PUT /admin/settings/github` over `github.owner`,
   `github.token`, `github.committer_name`, `github.committer_email`;
   `POST /admin/settings/github/test` → `GET /user` (token authenticates) and
   `GET /orgs/{org}` (organization visible). Add `("github", "owner"): "GITHUB_OWNER"`
   to `ENV_FALLBACKS` in `services/system_settings.py`, and `GITHUB_OWNER` to
   `config.py` and `.env.example`.
3. **Admin → Configuration → GitHub** in `pages/admin/ConfigurationPage.jsx`
   (a placeholder today): organization, token (write-only field, "set" indicator),
   committer name and email, Test connection.
4. **Repo creation.** `GitHubClient.create_repo(org, name, description)` →
   `POST /orgs/{org}/repos` with `private: false, auto_init: true, has_issues: true`.
   In `create_project`: slugify the name (lowercase, `[a-z0-9-]`, ≤100 chars),
   create the repo *before* committing the project row and roll back on failure —
   the same pattern as task ↔ issue in `project_service.create_task`. Name clash
   (GitHub 422 "name already exists") → 409 naming the slug. Drop `github_repo`
   from `ProjectCreate` and from the stepper's details step; show the slug on the
   review step with a "documents will be public" note. Keep `github_repo` editable
   in `ProjectUpdate` only for projects created before this phase.
5. **Collaborators.** `add_collaborator(repo, username)` →
   `PUT /repos/{repo}/collaborators/{username}` with `permission: "push"` (201 =
   invitation sent, 204 = already a collaborator); `remove_collaborator` →
   `DELETE` the same path, plus `DELETE /repos/{repo}/invitations/{id}` for a
   pending invitation. Call add from `assign_project_manager` and
   `project_service.ensure_member`; call remove when a PM is removed with no tasks
   left. A missing `github_username` is a warning, not a failure. When GitHub
   rejects an issue assignee (invitation not yet accepted), create the issue
   unassigned and warn "invitation pending" — never fail the task.
6. **Tests** against the `fake_github` fixture in `tests/conftest.py` — extend
   `FakeGitHub` with the org, repo, collaborator and invitation routes. Docs in
   the same change: flip the three 🔲 GitHub rows in `PROJECT.md` §24.

**Done when:** an Admin enters the company token once, a Manager creates a project
without typing a repository, and the Project Manager's first task opens an issue in
the repository TRACE created.

---

## Phase 4 — Visualisation ✅

1. `GET /projects/{id}/tree` graph payload, and `ProjectTreeGraph.jsx` with pan and
   zoom ([`PROJECT.md`](PROJECT.md) §21).
2. `gantt_charts` read API and `GanttChart.jsx`, driven by `chart_data`, read-only,
   showing version and `generated_reason` (§22).
3. Wire both into the Manager and Employee project views.

**Done when:** both render from real data — hand-write a `chart_data` row if Phase 5
has not landed yet.

*Status: built and tested 2026-09-26 (326 backend tests; frontend builds). Not
checked in a browser — the user decided that is not required.*

- *Spec first:* `chart_data` is defined in [`CORE.md`](CORE.md) §5.1 and enforced by
  `GanttChartData` (`app/schemas/gantt.py`) on every write.
- *Backend:* `services/gantt_service.py` — `project_tree`, the deterministic
  `build_chart_data`, `save_version` (validate + append), `snapshot`, `versions`.
  Routes in `api/v1/projects.py`: `GET /projects/{id}/tree`, `/gantt` (`?version=`,
  `null` before the first), `/gantt/versions`, guarded by `resolve_project_access`.
- *Frontend:* `components/ProjectTreeGraph.jsx` (`@xyflow/react`, new dependency,
  `base.css` only) and `components/GanttChart.jsx` (hand-built), wired into the
  Manager and Employee project pages; `statusTone` / `StatusLegend` shared.
- *Data:* the demo seed now sets planned dates and writes Gantt v1 with two
  dependencies; the local database's project 1 was given the same.
- *Tests:* `tests/api/v1/test_visualisation.py` — project-scoped role matrix,
  read-only methods, tree contents, version history, builder, schema refusals,
  and the demo seed's chart.

---

## Phase 5 — The AI pipeline

**Read [`CORE.md`](CORE.md) in full before starting.** Implement in its order.

1. The AI service layer: settings resolution from `system_settings`,
   schema-validated calls, retry on parse failure, job attribution.
   Enforce [`CORE.md`](CORE.md) §2 — no exceptions.
2. `evaluate_project` steps 1–6: extract → `project_initial_doc` → `project_doc` →
   task groups → Gantt v1 ([`CORE.md`](CORE.md) §3).
3. Re-base performance scoring on task signals (throughput, on-time rate). Attendance stays
   recorded but leaves the score's inputs.
4. PM suggestion and assignee suggestion endpoints (§3 steps 7–8, §4).
   **Suggestions only — never auto-assign.**
5. `generate_task_progress_doc` on task creation (§4).
6. `reevaluate_gantt` with its four triggers and debouncing (§5).
7. The weekly `update_project_progress_docs` roll-up (§6).
8. The **Evaluate Project** button with enqueue-and-poll UI, including a visible
   failure state.

**Done when:** uploading requirement documents and pressing Evaluate Project
produces a project document, task groups and a Gantt chart.

---

## Phase 6 — CI/CD-driven completion ❌ removed

Removed on 2026-09-26 before any of it was built (user decision, [`PLANNING.md`](PLANNING.md) §4).
Completion is manual: the task's assignee sets its status, `Completed` included, and
the Project Manager may set any status ([`CORE.md`](CORE.md) §7). What changed in the
code: `ProjectAccess.may_set_status` lets the assignee complete (`completed_by='Assignee'`),
the `cicd_events` table and model were dropped (revision `c4e1d2a7f9b3`), and the
CI/CD copy left the task page, the issue body, the landing page and Configuration.
There is no webhook, no resolver job and no CI/CD configuration section. Don't rebuild them.

---

## Phase 7 — Notifications & discussion

1. The `notifications` API, header bell, unread count, deep links.
2. Assignment, due-soon, overdue and completion notifications, in-app and via
   Mailpit ([`CORE.md`](CORE.md) §9) — including a task completed by its assignee
   reaching the Project Managers.
3. Per-task discussion threads with the visibility rules in
   [`PROJECT.md`](PROJECT.md) §11.6.
4. Re-point the existing WebSocket from group chat to notifications and discussion.
5. Set the Celery Beat schedule per [`CORE.md`](CORE.md) §8; retire the hourly
   health job and the nightly overallocation job.

**Done when:** an assignment, a due date and a completion each reach the
right people without anyone refreshing a page.

---

## Phase 8 — Admin completion

May run in parallel with Phases 4–7.

1. The Configuration screen over `system_settings` — mail and AI (GitHub
   already built in Phase 3a) — with write-only secrets and per-section connection tests.
2. Workforce consolidation into one curated UI with tabs for employees, managers,
   leaves, holidays, **attendance, shifts**, departments and designations. Every
   tab gets CRUD plus **bulk upload** that reports rejected rows instead of failing
   silently. This is where `AttendancePage.jsx` is reborn, minus clock-in/out.
3. Control Panel extended to the new tables.
4. Monitor as a page, including recent Celery job outcomes.
5. Reports — **blocked on Q7**. Ship the placeholder route and nothing more.

**Done when:** an Admin can change the AI model and the SMTP host without touching
`.env` or redeploying.

---

## Phase 9 — Polish

1. Responsive and mobile passes on all three panels.
2. Pagination on every list (employees, tasks, attendance, projects).
3. Global search wired to projects and tasks.
4. Empty and error states for every AI-dependent surface — a project with no
   evaluation yet, a failed evaluation, a task with no progress doc.
5. A sweep to confirm no page still renders a removed feature.

---

## Short-term deferrals

Items intentionally postponed within this build, as opposed to the long-horizon
work in [`PLANNING.md`](PLANNING.md) §3:

| Item | Deferred to | Why |
|------|-------------|-----|
| Admin → Reports contents | After Q7 is answered | Undefined; nothing depends on it |
| Task dependency editing | After Phase 4 | The AI infers `depends_on`; manual editing can wait |
| Bulk task creation from AI suggestions | Phase 5 follow-up | Single-task acceptance first |
| Pagination, global search | Phase 9 | Lists are short at demo scale |
| 2FA, session management, token refresh | Post-launch | Pre-existing backlog, unaffected by the re-spec |
| Docker production build | Post-launch | `APP_ENV=production` already serves a built frontend over HTTPS through the Cloudflare tunnel; containerising the app itself can wait |
