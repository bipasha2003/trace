# DEVELOPMENT.md — Build Phases

> Step-by-step requirements for agents building TRACE, in dependency order.
>
> **Before starting any phase:** read [`PROJECT.md`](PROJECT.md) for what you are
> building, [`CORE.md`](CORE.md) if the phase touches AI or completion, and
> [`PLANNING.md`](PLANNING.md) for the open questions in that area. Conventions are
> in [`../AGENTS.md`](../AGENTS.md).

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
Phase 0 ─► Phase 1 ─► Phase 2 ─┐
                     Phase 3 ─┼─► Phase 4 ─► Phase 5 ─► Phase 6 ─► Phase 7
                              └─────────────────────────────────► Phase 8 ─► Phase 9
```
Phase 8 needs only 0–2 and may run in parallel with 4–7. Phase 6 must not start
before Phase 5 — completion resolution depends on the AI service layer.

---

## Phase 0 — Clear the ground

The re-spec invalidated a large amount of working code. Removing it is **not
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

## Phase 1 — Schema

Follow [`PROJECT.md`](PROJECT.md) §15. One Alembic revision per step.

1. Create `projects`, `project_source_files`, `project_assignments`, `task_groups`,
   `gantt_charts`, `task_discussions`, `notifications`, `system_settings`,
   `cicd_events` (§11).
2. Alter `tasks` — add `project_id`, `task_group_id`, `task_progress_doc`,
   `assigned_to_user_id`, `assigned_by_user_id`, `completed_by`, `completed_at` (§12).
3. Add `github_username` to the user record (Q9).
4. Backfill the existing seeded tree into projects / task groups / tasks.
5. Drop `parent_task_id`, `team_lead_id`, `project_manager_id`, `task_level_role`,
   `tree_path` — **only after** verifying the backfill.
6. **Delete the model classes Phase 0 deliberately left behind, each in the same
   revision that drops its table** — `ProjectGroup`, `ProjectGroupMessage`,
   `EvaluationDispute`, `TaskCommitLog` in `models/task.py`, and `SystemMenu`,
   `RoleMenuPermission` in `models/employee.py`. Update `models/__init__.py`
   exports and the `MODEL_REGISTRY` in `admin.py` at the same time. Never leave a
   window where the class is gone but the table is not.
7. Migrate role rows: `Platform Admin` → `Admin`, `Staff` → `Employee`, repoint
   `user_roles`, then delete the obsolete `roles` rows.
8. Reseed: one Admin, one Manager, several Employees, one demo project.

**Done when:** `./start.sh migrate` runs clean, `alembic revision --autogenerate`
produces an empty diff, and the demo project renders in Swagger.

---

## Phase 2 — Panel separation & landing page

Frontend-led. Nothing here needs AI.

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

## Phase 3 — Projects, without AI

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
8. **Completion authority enforced server-side** ([`CORE.md`](CORE.md) §7): Member
   403, Project Manager allowed, result recorded in `completed_by`.

**Done when:** a Manager can create a project and assign a PM, and that PM can
create tasks that appear as GitHub issues — with no AI involved at all.

---

## Phase 4 — Visualisation

1. `GET /projects/{id}/tree` graph payload, and `ProjectTreeGraph.jsx` with pan and
   zoom ([`PROJECT.md`](PROJECT.md) §21).
2. `gantt_charts` read API and `GanttChart.jsx`, driven by `chart_data`, read-only,
   showing version and `generated_reason` (§22).
3. Wire both into the Manager and Employee project views.

**Done when:** both render from real data — hand-write a `chart_data` row if Phase 5
has not landed yet.

---

## Phase 5 — The AI pipeline

**Read [`CORE.md`](CORE.md) in full before starting.** Implement in its order.

1. The AI service layer: settings resolution from `system_settings`,
   schema-validated calls, retry on parse failure, job attribution.
   Enforce [`CORE.md`](CORE.md) §2 — no exceptions.
2. `evaluate_project` steps 1–6: extract → `project_initial_doc` → `project_doc` →
   task groups → Gantt v1 ([`CORE.md`](CORE.md) §3).
3. Re-base performance scoring on task and CI/CD signals. Attendance stays
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

## Phase 6 — CI/CD-driven completion

**Read [`CORE.md`](CORE.md) §7.** Do not start before Phase 5.

1. `POST /webhooks/cicd`, HMAC-verified, persisting `cicd_events`.
2. `resolve_cicd_completion` — the AI maps a push to **one or more** tasks. High
   confidence completes; low confidence goes to `In Review` for the Project Manager.
3. On completion: set `completed_by='AI/CICD'`, notify, re-evaluate the Gantt.
4. Build the project's own GitHub Actions pipeline that calls the webhook. This is
   itself a task, and by definition the Project Manager closes it manually.
5. Surface the push-with-the-issue-id convention in the task detail UI.

**Done when:** a push referencing an issue closes its task in TRACE without a human
touching the status.

---

## Phase 7 — Notifications & discussion

1. The `notifications` API, header bell, unread count, deep links.
2. Assignment, due-soon, overdue and completion notifications, in-app and via
   Mailpit ([`CORE.md`](CORE.md) §9).
3. Per-task discussion threads with the visibility rules in
   [`PROJECT.md`](PROJECT.md) §11.6.
4. Re-point the existing WebSocket from group chat to notifications and discussion.
5. Set the Celery Beat schedule per [`CORE.md`](CORE.md) §8; retire the hourly
   health job and the nightly overallocation job.

**Done when:** an assignment, a due date and a system completion each reach the
right people without anyone refreshing a page.

---

## Phase 8 — Admin completion

May run in parallel with Phases 4–7.

1. The Configuration screen over `system_settings` — mail, AI, GitHub, CI/CD —
   with masked secrets and per-section connection tests.
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
| Docker production build, HTTPS | Post-launch | Dev mode is sufficient until Phase 6 lands |
