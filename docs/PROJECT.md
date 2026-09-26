# PROJECT.md — TRACE

> **T**ask and **R**esource **A**ttendance and **C**omprehensive **E**valuation
>
> The complete documentation of what TRACE is: roles, panels, structure, schema and
> UI. **This document is authoritative.** Where the codebase disagrees with it, the
> codebase is what is wrong.

**Companion documents**
| File | Purpose |
|------|---------|
| [`CORE.md`](CORE.md) | The AI automation system — the core feature. Authoritative for anything it covers |
| [`DEVELOPMENT.md`](DEVELOPMENT.md) | Phase-by-phase build instructions |
| [`PLANNING.md`](PLANNING.md) | Journey, decisions, open questions, rejected and deferred work |
| [`../AGENTS.md`](../AGENTS.md) | Conventions and context for agents writing the code |
| [`../README.md`](../README.md) | End-user overview and setup |

Last revised 2026-09-26.

---

# Part 1 — Product

## 1. What TRACE is

An **AI-driven project and task management platform**. A project enters as a pile
of raw requirement documents and leaves as a delivered, tracked set of
GitHub issues with auto-maintained documentation, a self-updating Gantt chart and
progress reports.

**In scope**
- Projects, their source documents, and their AI-generated living documentation
- Task groups (Gantt modules) and tasks, where a task **is** a GitHub issue
- AI automation: project evaluation, task suggestion, assignee suggestion, Gantt
  generation, progress-doc authoring — all of [`CORE.md`](CORE.md)
- Manual task completion: the assignee marks their own task complete (no CI/CD or
  AI involvement — [`CORE.md`](CORE.md) §7)
- Per-task discussion, notifications, progress and completion reporting
- A workforce record set, Admin-owned, because planning and assignment need to
  know who exists and who is available

**Out of scope**
- Payroll, recruitment, onboarding, performance appraisal as an HR process
- Employee-facing HR workflows — clock-in/out, shift self-service, leave
  application. The **records** live on (§9.1); the interfaces do not.
- Anything that makes TRACE an HRMS rather than a task manager

---

## 2. Roles

### 2.1 Platform roles — exactly three, hardcoded

| Role | Base route | Purpose |
|------|-----------|---------|
| `Admin` | `/admin` | Platform operator. Owns all data, configuration and monitoring. Does not participate in project delivery. |
| `Manager` | `/manager` | Brings projects in. Creates projects, uploads source documents, assigns Project Managers, watches progress. |
| `Employee` | `/employee` | Delivers the work, as a **Project Manager** or a **Member**, per project. |

These three are hardcoded. There is **no** dynamic role creation, **no** dynamic
menu registration and **no** role↔menu permission matrix — menus are defined in
code per panel. The previously seeded `Platform Admin` and `Staff` roles are
retired (`Platform Admin` → `Admin`, `Staff` → `Employee`).

### 2.2 Project roles — per project, Employees only

| Project role | Assigned by | Can |
|--------------|-------------|-----|
| `Project Manager` | The project's Manager | Edit `project_doc`, create task groups and tasks, assign Members, set any task's status (complete, cancel), trigger AI re-evaluation |
| `Member` | A Project Manager, by being assigned a task | See the project, work their tasks, push code, discuss, update their tasks' status — **including marking them complete** |

The same Employee may be a Project Manager on one project and a Member on another
at the same time. The panel's project selector is what scopes the role.

> **Removed:** the `Team Lead` project role and the infinite rotating-role task
> tree. See §9.

---

## 3. Project structure

Fixed at three levels. Unlimited nesting is gone.

```
Project                       ← created by a Manager, owns a GitHub repo
└── Task Group                ← AI-generated; one Gantt "module"
    └── Task                  ← one GitHub issue; assigned to exactly one Member
```

- A **Task Group** is the planning unit and carries the Gantt bar: start date, end
  date, and a completion percentage rolled up from its tasks.
- A **Task** is the atomic unit of work, mirrored 1:1 as a GitHub issue. It is the
  only level assigned to a person, and the only level whose status a person sets.

### 3.1 Project tree graph
Every project exposes a **graph view** — Project → Task Groups → Tasks → assignees,
rendered as a node graph, not a nested list. Node colour carries status. This is
the primary "what does this project look like" visual, available to the Manager,
Project Managers and Members (read-only for Members).

---

## 4. Routing and panel separation

Panels are fully separated by base route. There is no shared shell across roles.

| Route | Audience | Notes |
|-------|----------|-------|
| `/` | **Guests only** | Public landing page |
| `/login` | Guests | Sign in |
| `/admin/**` | `Admin` | Sidebar layout |
| `/manager/**` | `Manager` | Topbar only, no sidebar |
| `/employee/**` | `Employee` | Topbar only, no sidebar |

**Redirect rules**
- A logged-in user hitting `/` goes straight to their own base route.
- A logged-out user hitting a panel route goes to `/login`, then to their base route.
- A user hitting another role's panel gets a **403 page**, not a silent redirect —
  a mis-provisioned account should be visible, not hidden.
- The backend mirrors all of this: every panel endpoint is guarded by platform
  role, and every project endpoint additionally by the caller's project role.

---

## 5. Admin panel (`/admin`) — sidebar

| Menu | Route | Contents |
|------|-------|----------|
| **Control Panel** | `/admin/control-panel` | Generic CRUD over every table **except `system_settings`**, which holds encrypted secrets and is served only by Configuration. Raw and table-driven — the escape hatch, not the daily UI. |
| **Workforce** | `/admin/workforce` | Curated UI over the whole workforce record set: employees, managers, leaves, holidays, attendance, work shifts, departments, designations. Every tab has CRUD **and bulk upload** (CSV/JSON). The same tables appear in Control Panel; this is the human view. |
| **Monitor** | `/admin/monitor` | Server and service health: API, PostgreSQL, Redis, Celery worker, Celery beat, MinIO, Mailpit, WebSocket, LLM reachability, recent Celery job outcomes. |
| **Configuration** | `/admin/configuration` | Runtime settings in the database, not only `.env`: mail/SMTP and GitHub (the company's owner + token — [`CORE.md`](CORE.md) §4.1). Per-section "test connection". **No AI section** — the LLM configuration is fixed in `.env` (user decision 2026-09-26); the model may be shown read-only. |
| ~~**Reports**~~ | ~~`/admin/reports`~~ | **Removed** (Q7, 2026-09-26). Reports are a **Download report** action on the Manager and Employee dashboards — the project → task group → task tree for a date range ([`PLANNING.md`](PLANNING.md) Q7). No scheduled report. |

---

## 6. Manager panel (`/manager`) — no sidebar

**Layout:** a topbar only, carrying a **project selector** that defaults to **"All"**.

### 6.1 "All" selected (default)
Combined dashboard across every project this Manager owns: project counts,
aggregate progress, per-project progress, at-risk projects, recent activity, and a
prominent **New Project** action.

### 6.2 A specific project selected
Detailed single-project view: the tree graph, the Gantt chart, task group and task
breakdown, assigned Project Managers, progress report.

### 6.3 Manager actions
| Action | Description |
|--------|-------------|
| Create project | Name, description, and upload of one or more **project source files**. TRACE creates the project's public GitHub repository itself |
| Evaluate Project | Triggers the AI pipeline — [`CORE.md`](CORE.md) §3 |
| Assign / remove Project Managers | From the Employee pool, with AI-ranked suggestions |
| View progress | Per-project and combined |
| View progress report | The AI-maintained `project_progress_doc` and `project_report_doc` |

A Manager has **no** HR, attendance or leave functionality. That surface belongs to
the Admin.

---

## 7. Employee panel (`/employee`) — no sidebar

**Layout:** a topbar with the same project selector pattern, defaulting to **"All"**.
What the panel offers depends on the Employee's role in the selected project.

### 7.1 "All" selected (either project role)
Combined dashboard over every project they belong to: aggregate progress, their
open tasks, due and overdue tasks, recent notifications.

### 7.2 A project selected — as **Project Manager**
- Full project dashboard: tree graph, Gantt, task groups, task board
- **Task creation** — which creates the GitHub issue
- Member assignment per task, with AI-ranked suggestions
- Editing `project_doc`, which triggers Gantt re-evaluation
- Setting any task's status — completing one on someone's behalf, or cancelling it ([`CORE.md`](CORE.md) §7)

### 7.3 A project selected — as **Member**
- The same dashboard, **read-only** with respect to project structure
- Their assigned tasks, each task's `task_progress_doc`, and per-task discussion
- They keep their own tasks' status current and **mark them complete** when done;
  commits may reference the GitHub issue id, but nothing reads them automatically

---

## 8. Supporting features

| Feature | Requirement |
|---------|-------------|
| Task due notification | Notify assignee and Project Manager as a task approaches and passes its due date |
| Assignment notification | Notify a Member when a task is assigned to them |
| Completion notification | Notify the Project Managers when a task is marked complete (and the assignee, if the PM completed it) |
| Per-task discussion | Threaded discussion on each task between its assignee(s) and its assigner. Replaces the old project-wide group chat |
| Gantt chart | Auto-created and auto-updated; never hand-maintained |
| Project tree graph | Node-graph of Project → Task Group → Task → assignee |

---

## 9. Removed, and retained

### 9.1 Retained: the workforce record set

Removing the HR *panels* did not remove the HR *data*. These tables stay, and the
**Admin owns them** through Workforce (§5) with full CRUD **and bulk upload**:

`employees` · `employee_details` · `departments` · `designations` ·
`leaves` · `holidays` · `attendance` · `work_schedules`

What changed is only who touches them and how: no Manager HR panel, no employee
self-service, no GPS capture, no geo-fence enforcement. Attendance and shift rows
are Admin-maintained — typically bulk-imported from whatever actually captures
them — because planning needs to know who is available.

### 9.2 Removed

| Removed | Reason | Disposition |
|---------|--------|-------------|
| Manager's Attendance & HR panel | Not task management | Delete route, page, manager-facing endpoints. Data moves to Admin → Workforce |
| Employee clock-in/out UI, geo-fence enforcement | No employee HR self-service | Remove the capture UI and the geo-fence check. Records remain |
| Employee-facing leave application | Same | Leaves are recorded and approved by the Admin |
| `Team Lead` project role | Hierarchy is three fixed levels | Remove the role, `team_lead_id`, all rotating-role logic |
| Infinite task tree (`parent_task_id` recursion) | Replaced by Project → Task Group → Task | Migrate existing rows, §15 |
| Dynamic system roles | Roles are hardcoded | Remove endpoints and the Master Settings tab |
| Dynamic navigation menus (`SystemMenu`) | Menus are per-panel, in code | Remove endpoints, model, tab |
| Role↔menu permission matrix | Superseded by panel separation | Remove model, endpoints, matrix UI |
| `Platform Admin`, `Staff` roles | Only three roles exist | Migrate to `Admin` / `Employee` |
| Project group chat + tree tagging rules | Replaced by per-task discussion | Remove models and chat UI |
| Combined single-panel shell | Replaced by three panels | Rebuild as three layouts |

---

# Part 2 — Data model

## 10. Conventions

- Tables `snake_case`, plural. Every table keeps the existing `BaseModelMixin`
  (id, timestamps, soft delete).
- Markdown-document columns hold **GitHub repository file URLs**, never bodies.
  Names are normalised to snake_case throughout: `project_initial_doc`,
  `project_doc`, `project_progress_doc`, `project_report_doc`, `task_progress_doc`.

## 11. New tables

### 11.1 `projects`

| Column | Type | Notes |
|--------|------|-------|
| `name` | `String(255)` | |
| `description` | `Text` | |
| `created_by_user_id` | FK `users.id` | The **Manager** who created it |
| `github_repo` | `String(255)` | `owner/repo`. Where issues and doc files live. **Created by TRACE** under the configured owner when the project is created ([`CORE.md`](CORE.md) §4.1) |
| `github_default_branch` | `String(100)` | Default `main`. Branch strategy deferred — `PLANNING.md` Q6 |
| `status` | `String(20)` | `Draft`, `Evaluating`, `Active`, `Completed`, `Archived` |
| `start_date` / `end_date` | `Date` | Planned window, maintained by the Gantt evaluator |
| `project_initial_doc` | `String(500)` | URL. AI-authored, written once |
| `project_doc` | `String(500)` | URL. Living doc; starts as a clone of the initial doc |
| `project_progress_doc` | `String(500)` | URL. Rewritten weekly by AI |
| `project_report_doc` | `String(500)` | URL. Report, AI-maintained |
| `last_evaluated_at` | `DateTime` | Last successful AI evaluation |
| `ai_errors` | `JSONB` | `{job name: {message, at}}` — why an AI job on this project last failed; each job clears its own key on success ([`CORE.md`](CORE.md) §2.1). Added Phase 5 |

Has many `project_source_files`, `project_assignments`, `task_groups`; one current
`gantt_chart`.

#### The project document set

Direct mapping from the original plan to the implemented fields.

| Original plan | Column | Written by | Updated when |
|---------------|--------|-----------|--------------|
| `project_source_files` (multiple file field) | `project_source_files` table | Manager, at creation | Manager adds or removes files |
| `Project_initial_doc` — "scrapped by AI from project_source_files" | `project_initial_doc` | **AI**, [`CORE.md`](CORE.md) §3 step 3 | **Never.** Immutable snapshot of what the AI first understood, so drift from the original brief stays visible |
| `Project_doc` — "duplicate, updated as features shift" | `project_doc` | **AI** clones it, §3 step 4 | **Project Manager** edits it as features shift or are added; every save triggers Gantt re-evaluation |
| `Progress_doc` — "updated by task completioner" | `project_progress_doc` | **AI**, weekly | Reads every `task_progress_doc` and current task statuses — which the task completioners (assignees) set by hand — and rewrites it. [`CORE.md`](CORE.md) §6 |
| `ProjectReport_doc` — "updated by task completioner" | `project_report_doc` | **AI** | Same weekly job; this is what the Manager reads |
| "Automatic gantt chart creation and updation by task completion" | `gantt_charts` table, versioned | **AI** | Created at §3 step 6; regenerated on completion, overdue, `project_doc` edit, or on demand — [`CORE.md`](CORE.md) §5 |
| *(implied, per task)* | `tasks.task_progress_doc` | **AI**, on task creation | Steps + checklist, kept current — [`CORE.md`](CORE.md) §4 |

Two consequences worth stating outright:
- **`project_initial_doc` is write-once, `project_doc` is the living one.** They
  start identical. If both were editable there would be nothing to measure drift
  against, which is the only reason to carry two fields.
- **A document is a repo file, so it already has history.** Do not add a
  `*_doc_versions` table — `git log` on the file *is* the version history.

### 11.2 `project_source_files`

| Column | Type | Notes |
|--------|------|-------|
| `project_id` | FK `projects.id` | |
| `file_name` | `String(255)` | |
| `storage_key` | `String(500)` | MinIO object key |
| `content_type` | `String(100)` | |
| `size_bytes` | `BigInteger` | |
| `extracted_text` | `Text` | Populated by extraction so the AI need not re-parse |
| `uploaded_by_user_id` | FK `users.id` | |

> Source files live in **MinIO**. Only generated markdown lives in GitHub. Do not
> conflate the two.

### 11.3 `project_assignments`

Who is on a project, in what role. The single source of truth for project-scoped
authorisation.

| Column | Type | Notes |
|--------|------|-------|
| `project_id` | FK `projects.id` | |
| `user_id` | FK `users.id` | Must be a platform `Employee` |
| `project_role` | `String(30)` | `Project Manager` or `Member` |
| `assigned_by_user_id` | FK `users.id` | Manager for PMs, Project Manager for Members |

Unique on (`project_id`, `user_id`). A Member row is created automatically the
first time that user is assigned a task in the project.

### 11.4 `task_groups`

One Gantt module.

| Column | Type | Notes |
|--------|------|-------|
| `project_id` | FK `projects.id` | |
| `name` / `description` | `String(255)` / `Text` | |
| `sequence` | `Integer` | Display / dependency order |
| `estimated_duration_days` | `Integer` | AI estimate |
| `planned_start_date` / `planned_end_date` | `Date` | The Gantt bar |
| `actual_start_date` / `actual_end_date` | `Date` | |
| `completion_percentage` | `Numeric(5,2)` | Rolled up from tasks |
| `status` | `String(20)` | `Pending`, `In Progress`, `Completed`, `Blocked` |
| `created_by` | `String(20)` | `AI` or `Human` |
| `depends_on` | `JSONB` | Ids of the groups this one waits for — from the AI plan, reused by every re-plan ([`CORE.md`](CORE.md) §5). Added Phase 5 |

`planned_*` is the current forecast, rewritten by each Gantt re-plan; `actual_*` is
stamped by the task roll-up (first leaves `Pending` / becomes `Completed`).

### 11.5 `gantt_charts`

Materialised and regenerated, never patched.

| Column | Type | Notes |
|--------|------|-------|
| `project_id` | FK `projects.id` | |
| `version` | `Integer` | Incremented per regeneration |
| `chart_data` | `JSONB` | Bars, dependencies, milestones — the render payload. Shape fixed by [`CORE.md`](CORE.md) §5.1 (`GanttChartData`); written only through `gantt_service.save_version()`, which validates it |
| `generated_reason` | `String(100)` | `initial`, `task_status_change`, `project_doc_updated`, `manual` |
| `generated_at` | `DateTime` | |
| `generated_by_job` | `String(64)` | The Celery job id that wrote it (`CORE.md` §2 rule 4). Added Phase 5 |

History is kept; the newest version is live.

### 11.6 `task_discussions`

| Column | Type | Notes |
|--------|------|-------|
| `task_id` | FK `tasks.id` | |
| `user_id` | FK `users.id` | |
| `parent_id` | FK self, nullable | Threading |
| `message` | `Text` | |

Visible to: the task's assignee, its assigner, the project's Project Managers, and
the owning Manager.

### 11.7 `notifications`

| Column | Type | Notes |
|--------|------|-------|
| `user_id` | FK `users.id` | Recipient |
| `type` | `String(50)` | `task_assigned`, `task_due`, `task_completed`, `discussion_reply`, `project_evaluated` |
| `title` / `body` | `String(255)` / `Text` | |
| `link` | `String(500)` | Deep link into the right panel |
| `is_read` | `Boolean` | |
| `related_task_id` / `related_project_id` | FK, nullable | |

### 11.8 `system_settings`

Backs Admin → Configuration.

| Column | Type | Notes |
|--------|------|-------|
| `category` | `String(50)` | `mail`, `github` (`ai` is never stored — the LLM configuration is fixed in `.env`) |
| `key` | `String(100)` | |
| `value` | `Text` | For secrets, a Fernet token (key `SETTINGS_ENCRYPTION_KEY` in `.env`), decrypted only inside `resolve_setting()` |
| `is_secret` | `Boolean` | Set by `store_setting()` for the keys in `SECRET_SETTINGS`. Never returned by any API — responses say only whether it is set, and from where |

Unique on (`category`, `key`). Resolution order: database value, then `.env` fallback
(`app/services/system_settings.py`). Written only through `store_setting()` — the
Control Panel's generic CRUD does not list this table, because it would return
secrets and write them unencrypted. If `SETTINGS_ENCRYPTION_KEY` changes, saved
secrets can no longer be decrypted and must be entered again (a clear 503 says so).

GitHub keys ([`CORE.md`](CORE.md) §4.1):

| Key | Secret | `.env` fallback | Purpose |
|-----|--------|-----------------|---------|
| `github.owner` | no | `GITHUB_OWNER` | The organization every project repo lives under |
| `github.token` | **yes** — encrypted, write-only | `GITHUB_TOKEN` | Fine-grained token scoped to that owner |
| `github.api_url` | no | `GITHUB_API_URL` | `https://api.github.com`; GitHub Enterprise otherwise. Not on the Configuration screen |
| `github.committer_name` / `github.committer_email` | no | `GITHUB_COMMITTER_NAME` / `_EMAIL` | Identity on the commits TRACE makes |

---

## 12. Changes to `tasks`

**Add**

| Column | Type | Notes |
|--------|------|-------|
| `project_id` | FK `projects.id` | Required |
| `task_group_id` | FK `task_groups.id` | Required |
| `task_progress_doc` | `String(500)` | URL to the AI-authored steps doc |
| `progress_doc_error` | `Text` | Why the AI could not write it — shown on the task page. Added Phase 5 |
| `assigned_to_user_id` | FK `users.id` | Replaces employee-based assignment |
| `assigned_by_user_id` | FK `users.id` | The assigning Project Manager |
| `completed_by` | `String(20)` | `Assignee` or `Project Manager` — who set `Completed` ([`CORE.md`](CORE.md) §7) |
| `completed_at` | `DateTime` | |

**Keep** — `title`, `description`, `priority`, `status`, `due_date`,
`estimated_hours`, `github_issue_id`, `github_issue_url`, `commit_hash`,
`commit_verified`, `llm_verification_notes`, `health_score`, `health_reason`,
`last_health_check`. (`commit_hash`, `commit_verified` and
`llm_verification_notes` are legacy and unused since CI/CD completion was removed;
they stay as recorded values.)

**Drop** — `parent_task_id`, `team_lead_id`, `project_manager_id`,
`task_level_role`, `tree_path`.

**Statuses** — `Pending`, `In Progress`, `In Review`, `Completed`, `Blocked`,
`Overdue`, `Cancelled`.

---

## 13. Tables removed

| Table | Reason |
|-------|--------|
| `project_groups`, `project_group_messages` | Group chat replaced by `task_discussions` |
| `system_menus` | Menus are code-defined per panel |
| `role_menu_permissions` | Panel separation replaces the matrix |
| `evaluation_disputes`, `task_commit_logs` | Deferred — see [`PLANNING.md`](PLANNING.md) |
| `cicd_events` | Created in Phase 1, dropped 2026-09-26: CI/CD-driven completion was removed ([`CORE.md`](CORE.md) §7) |

## 14. Tables retained unchanged

`users`, `profiles`, `roles`, `user_roles`, `employees`, `employee_details`,
`departments`, `designations`, `leaves`, `holidays`, `attendance`,
`work_schedules`, `task_types`, `task_details`, `task_comments`,
`task_time_logs`, `productivity_scores`, `time_zones`.

> The workforce record set is retained **in full**, `attendance` and
> `work_schedules` included (§9.1). Only the UI was removed. The
> `geo_latitude` / `geo_longitude` columns stay as recorded values; nothing
> validates against them any more.
>
> `productivity_scores` is retained but **re-based** (done, Phase 5 — [`CORE.md`](CORE.md) §8): inputs become task throughput
> and on-time completion rate. Attendance is still recorded but is
> no longer a scoring input. These scores are what the AI ranks on when it suggests
> Project Managers and assignees ([`CORE.md`](CORE.md) §3).

---

## 15. Migration

The existing data is a seeded demo tree, so this can be pragmatic. One Alembic
revision per step, so a failed backfill rolls back without losing the new tables.

1. **Create** `projects`, `project_source_files`, `project_assignments`,
   `task_groups`, `gantt_charts`, `task_discussions`, `notifications`,
   `system_settings`, `cicd_events` (`cicd_events` was dropped again on 2026-09-26
   with CI/CD completion — revision `c4e1d2a7f9b3`).
2. **Backfill**: each current root task (`parent_task_id IS NULL`) → a `projects`
   row; each depth-1 child → a `task_groups` row; every remaining descendant → a
   `tasks` row on its nearest ancestor group. Tasks deeper than depth 2 are
   flattened up to the group, not dropped.
3. **Migrate roles**: `Platform Admin` → `Admin`, `Staff` → `Employee`; repoint
   `user_roles`; delete the obsolete rows.
4. **Migrate assignments**: `project_manager_id` / `team_lead_id` →
   `project_assignments` rows with role `Project Manager`; `assigned_to` →
   `tasks.assigned_to_user_id` (resolve `employees.id` → `users.id`).
5. **Alter** `tasks` per §12.
6. **Drop** the §13 tables last, after verifying the backfill.

---

# Part 3 — UI specification

Stack constraints (shadcn/ui, Tailwind v4 tokens, `lucide-react` only) are in
[`../AGENTS.md`](../AGENTS.md) and are non-negotiable.

## 16. Route map

```
/                         Landing page          guests only
/login                    Sign in               guests only
/403                      Wrong panel           authenticated

/admin                    → redirect /admin/control-panel
/admin/control-panel      All-tables CRUD
/admin/workforce          Employees · Managers · Leaves · Holidays ·
                          Attendance · Shifts · Departments & Designations
/admin/monitor            Service & server health
/admin/configuration      Mail · AI · GitHub settings
(no /admin/reports — reports are a dashboard download, PLANNING.md Q7)
/admin/settings           Own profile

/manager                  Combined dashboard ("All" selected)
/manager/projects/new     Create project
/manager/projects/:id     Single project detail
/manager/settings         Own profile

/employee                 Combined dashboard ("All" selected)
/employee/projects/:id    Single project — PM view or Member view by project role
/employee/tasks/:taskId   Task detail + discussion
/employee/settings        Own profile
```

**Guards**
- `<GuestOnlyRoute>` on `/` and `/login`; an authenticated user goes to their base route.
- `<RoleRoute role="Admin|Manager|Employee">` wraps each panel; a mismatch renders
  `/403`, not a redirect.
- Project routes additionally resolve the caller's `project_assignments` row. No
  assignment → 403.

## 17. Landing page (`/`)

Public, marketing-quality, and the only page a logged-out visitor sees besides
`/login`. It must be genuinely well designed — this is the product's front door.

Sections: hero (headline, subline, "Get started" → `/login`), the problem it
solves, a three-step how-it-works mirroring the core flow (Manager uploads
requirements → AI plans the project → the team delivers, task by task), a feature grid, a
footer. Fully responsive, light/dark aware, built from the same tokens as the rest
of the app so it does not read as a bolted-on site.

## 18. Admin panel UI

Reuse the shadcn `Sidebar` shell, but the item list is **static and code-defined** —
there is no permission-matrix lookup.

```
Control Panel   Database
Workforce       Users
Monitor         Activity
Configuration   Settings2
Reports         FileBarChart
```

| Screen | Notes |
|--------|-------|
| **Control Panel** | Table picker grouped by category, then a generic data grid with create/edit/delete dialogs and filtering. Driven by the existing `MODEL_REGISTRY` pattern in `backend/app/api/v1/admin.py`. `system_settings` is deliberately not in it. |
| **Workforce** | Tabs per §5. Purpose-built, not a raw grid: directory cards and search for people, an approve/reject queue for leaves, a calendar for holidays, a filterable log for attendance, a shift editor with employee assignment. Every tab has a **Bulk Upload** action (CSV/JSON) with a validation summary that reports rejected rows rather than failing silently. Attendance and shifts are Admin-maintained records — there is no clock-in control anywhere in the product. |
| **Monitor** | `ServiceMonitor.jsx` promoted from a header overlay to a page. Health cards for API, PostgreSQL, Redis, Celery worker, Celery beat, MinIO, Mailpit, WebSocket and LLM, plus recent Celery job outcomes. |
| **Configuration** | Sections for Mail/SMTP and GitHub — **no AI provider section** (fixed in `.env`). Secrets are write-only (masked, never returned), each section with "Test connection". Writes to `system_settings`. **GitHub is built (Phase 3a)** — organization, token (a password field showing only *Not set / Set here / Set in .env*; blank keeps it, "Clear saved token" falls back to `.env`), committer name and email. *Test connection* runs against the **saved** settings (disabled while there are unsaved edits) and reports two checks: token authenticates, organization visible. Repos are always public, so there is no visibility setting. Mail remains a Phase 8 placeholder; the AI placeholder card is removed in Phase 8. |
| ~~**Reports**~~ | Removed — see the dashboard **Download report** (Q7). |

## 19. Manager panel UI

```
┌──────────────────────────────────────────────────────────────┐
│ TRACE   [ Project: All ▾ ]              🔔  ☾  ProtapB ▾     │
└──────────────────────────────────────────────────────────────┘
```

The selector is a shadcn `Combobox`, default **"All"**, listing only projects this
Manager created.

**"All"** — stat row (total / active / completed projects, overall completion,
at-risk count), a **New Project** primary action, a per-project card grid with
progress bars and Project Manager avatars, and a recent-activity feed.

**A project selected** — tabs **Overview · Tree · Gantt · Progress Report · Team**:
- *Overview* — status, dates, source files, the four document links, and the
  **Evaluate Project** button showing job state (idle / running / failed with reason)
- *Tree* — the project graph (§21)
- *Gantt* — read-only chart with version and last-generated reason
- *Progress Report* — rendered `project_progress_doc` / `project_report_doc`
- *Team* — assign and remove Project Managers, with AI suggestions (score +
  reasoning) inline

*As built (Phase 5):* the Overview opens with an **AI evaluation** card — the
button (owner only; disabled without source text, and once the project has tasks),
"Evaluating…" while it runs (polled every 2 s), and one alert per entry in
`ai_errors`. *Progress Report* renders both documents with a **Rewrite now**
button. *Team* has **Suggest with AI**: a ranked list with score, reasoning and the
numbers behind it, each with its own *Assign* button.

**Create project** — a stepper: details (name, description) → upload source files
(multi-file drop zone) → review → create. The repository is **created by TRACE** as
`<org>/<project-slug>` (public) and shown on the review step; the Manager does not
type one ([`CORE.md`](CORE.md) §4.1). The upload step says plainly that generated
documents will be public. On create, offer **Evaluate Project** immediately.

*As built (Phase 3a):* the details step shows the slug as the name is typed (the
server computes the real one); the source-files and review steps both carry the
"repository is public" notice. There is no branch field — the default branch is
whatever GitHub gives the new repo (it stays editable on the project, as does
`github_repo` for projects created before Phase 3a). A name clash comes back as a
409 toast naming `<org>/<slug>`; nothing is created. The **team panel** toasts
the GitHub warnings from appointing or removing a Project Manager (no GitHub
username, invitation refused).

## 20. Employee panel UI

Same topbar and selector pattern. The selector lists every project the Employee is
assigned to, annotated with their project role.

**"All"** — aggregate progress across their projects, **My Tasks** grouped by due
state, an overdue callout, recent notifications.

**A project selected — Project Manager** — tabs **Overview · Tree · Gantt · Tasks ·
Project Doc · Team**:
- *Tasks* — board grouped by task group, with **Create Task**. The dialog calls the
  assignee-suggestion endpoint and shows ranked Members with reasoning. The PM can
  set any task's status, including completing it on someone's behalf
  (`completed_by='Project Manager'`) and cancelling it.
- *Project Doc* — markdown editor (edit / preview) over `project_doc`. Saving triggers Gantt
  re-evaluation; say so in the UI *before* saving.
- *Team* — the project's Members.

**A project selected — Member** — tabs **Overview · Tree · Gantt · My Tasks**.
Read-only with respect to project structure. No create-task control. On **their
own** tasks a Member sets the status — Pending, In Progress, In Review, Blocked and
**Completed** (behind a confirmation; `completed_by='Assignee'`). Cancelling is the
Project Manager's call.

*As built (Phase 5):* the Create Task dialog has **Suggest tasks for this group**
(fills title, description and priority) and **Suggest assignees** (ranked Members,
*Pick* fills the assignee) — neither creates or assigns anything. The PM's Gantt
tab has **Re-plan now**. The Project Doc tab states the re-plan before saving; an
unchanged save commits nothing.

**Task detail** — description, linked GitHub issue, the rendered
`task_progress_doc` with its step checklist, status timeline and the discussion
thread. The status buttons are exactly the server's `allowed_statuses`; anyone who
is neither the assignee nor the Project Manager sees none
([`CORE.md`](CORE.md) §7).

## 21. Project tree graph

```
        ┌──────────┐
        │ Project  │
        └────┬─────┘
     ┌───────┼────────┐
  ┌──▼──┐ ┌──▼──┐ ┌───▼──┐        Task Groups (Gantt modules)
  │ TG1 │ │ TG2 │ │ TG3  │
  └──┬──┘ └──┬──┘ └──┬───┘
   ┌─┴─┐   ┌─┴─┐   ┌─┴─┐
   │T1 │   │T3 │   │T5 │          Tasks → GitHub issues, one assignee each
   └───┘   └───┘   └───┘
```

Node colour encodes status (pending / in progress / completed / blocked /
overdue). Task nodes show the assignee avatar; clicking one opens its detail. Pan
and zoom required. Available to all three audiences, read-only for Members.

*As built (Phase 4):* `GET /projects/{id}/tree` returns project → task groups (by
`sequence`) → tasks (deleted ones left out, cancelled ones shown faded) with
assignee, due date, `overdue` and issue URL — a live read, no stored snapshot.
Groups are laid out as columns, each group's tasks hanging off a rail beneath it.
Selecting a task opens a small panel with its status, assignee, due date, a link
to the GitHub issue and — in the Employee panel — *Open task*. The Manager has no
task detail page, so the panel is the detail there. Zoom buttons, fit-to-view and
a status legend; nothing is draggable.

## 22. Gantt chart

Renders `gantt_charts.chart_data` at the latest version. One bar per **task group**,
expandable to its tasks, with a today marker, dependency arrows and a completion
overlay per bar. Read-only everywhere — it is regenerated, never dragged. Show the
version number and `generated_reason` so users understand why it moved.

*As built (Phase 4):* `GET /projects/{id}/gantt` (latest, or `?version=N`; JSON
`null` before the first version) and `GET /projects/{id}/gantt/versions`. The
chart renders only its stored `chart_data`, so an older version shows what was true
then — a version picker lets anyone look back. A task has no start date, so an
expanded group shows each task as a marker on its due date. The day scale adapts
to the range and the chart scrolls sideways with the group names pinned. Until
Phase 5 generates versions, a project without a hand-written row shows "No Gantt
chart yet".

*As built (Phase 5):* versions are written by Evaluate Project (v1, `initial`) and
by every re-plan (`CORE.md` §5). A Project Manager with hand-made groups and no
chart can press **Re-plan now** to draw them.

## 23. Existing pages — disposition

| Current file | Disposition |
|--------------|-------------|
| `pages/AttendancePage.jsx` | **Rebuild** as Admin → Workforce tabs. Clock-in/out controls, geolocation capture and the Manager HR view go; the attendance log, leave queue, holiday calendar and shift editor stay as Admin record-keeping |
| `pages/MasterPage.jsx` | **Delete** — dynamic roles, dynamic menus and the permission matrix are removed |
| `pages/DashboardPage.jsx` | **Replace** with three panel dashboards |
| `pages/TasksPage.jsx` | **Replace** — infinite tree, group chat and dispute queue give way to project / task-group / task views |
| `pages/EmployeesPage.jsx` | **Move** into Admin → Workforce |
| `pages/ProductivityPage.jsx` | **Delete** (Phase 8) — there is no Reports page to fold it into (Q7); scores are an AI input, not a headline page |
| `pages/FilesPage.jsx` | **Delete as a menu** — uploads happen inside project creation; MinIO remains a backing service |
| `pages/AdminPanelPage.jsx` | **Keep** — becomes Admin → Control Panel |
| `components/ServiceMonitor.jsx` | **Keep** — becomes Admin → Monitor |
| `layouts/Sidebar.jsx` | **Rewrite** as the Admin-only sidebar with a static item list |
| `layouts/DashboardLayout.jsx` | **Split** into `AdminLayout`, `ManagerLayout`, `EmployeeLayout` |

---

# Part 4 — Status

## 24. Feature registry

**Legend** — ✅ built & aligned · 🔄 built, needs rework · 🔲 to build · ❌ built, to be removed · 💤 deferred

### Auth, roles & panels
| Feature | Status | Notes |
|---------|--------|-------|
| JWT login/logout | ✅ | Token in `localStorage` via `AuthContext` |
| Three hardcoded platform roles | ✅ | Collapsed to Admin, Manager, Employee |
| Panel separation `/admin` `/manager` `/employee` | ✅ | Three layouts, RoleRoute, GuestOnlyRoute, 403 page |
| Public landing page at `/` | ✅ | Hero, problem, how-it-works, feature grid, footer |
| Guest-only + role-route guards, `/403` | ✅ | GuestOnlyRoute + RoleRoute; mismatch → /403, never silent redirect |
| Platform-role guard on every route | ✅ | Phase 2 step 6. Workforce, productivity and service-health endpoints are Admin-only |
| Project-scoped authorisation | ✅ | `app/core/project_access.py` — Admin reads all, Manager owns theirs, Employee via `project_assignments` |
| Dynamic roles / menus / permission matrix | ❌ | Tables dropped Phase 1 |
| User registration, profile update | ✅ | Self-registration always creates an `Employee`; only an Admin may create Admin / Manager accounts |
| `github_username` on user | ✅ | Added Phase 1; Admin + user-settings editable |
| Token refresh, 2FA, session management | 🔲 | Unchanged backlog |

### Projects *(new core)*
| Feature | Status | Notes |
|---------|--------|-------|
| `projects` table + CRUD | ✅ | Manager-owned (Q11); delete refused while tasks are open, and archives the repo |
| `project_source_files` multi-upload (MinIO) | ✅ | pdf / docx / md / txt, 20 MB each; text extracted at upload; rejects reported per file |
| The four project documents | ✅ | Phase 5. Repo files `docs/<column>.md`; `GET /projects/{id}/documents/{kind}` reads them back; `PUT …/documents/doc` (PM) edits `project_doc` |
| Project Manager assignment / removal | ✅ | Plain picker or AI-ranked suggestions (Phase 5); a removed PM holding tasks stays as Member |
| Manager combined + per-project dashboards | ✅ | Tree and Gantt tabs (Phase 4); Evaluate Project card and Progress Report tab (Phase 5) |
| GitHub owner model — one company owner + token | ✅ | Phase 3a. Admin → Configuration → GitHub; token Fernet-encrypted at rest, write-only; `/admin/settings/github` + `/test`. Production refuses to start without `SETTINGS_ENCRYPTION_KEY` |
| Repo created by TRACE per project | ✅ | Phase 3a. `<org>/<name-slug>`, public, `auto_init`; created before the row; clash → 409; no token or org → 503; token without Administration → precise 502 |
| Repo archived on project delete | ✅ | Phase 3a follow-up. Archive before soft-delete; failure keeps the project; only repos under the organization. API only — there is no delete-project button |
| Member removal, resend invitation | ❌ | Not planned — educational scope (`PLANNING.md` §4). Re-assigning a task re-invites |
| Collaborator invite on joining a project | ✅ | Phase 3a. *Write* on PM appointment and on every task assignment (idempotent); revoked, with any pending invitation withdrawn, when a PM leaves. Never blocks the change — problems are warnings. Pending invitation → issue created unassigned + warning; assign again once accepted. No invite UI of its own |
| Project tree graph | ✅ | Phase 4. `GET /projects/{id}/tree` (live read) → `ProjectTreeGraph.jsx` (`@xyflow/react`, pan/zoom); Manager, Admin, PMs and Members, read-only |
| Gantt chart, versioned | ✅ | Phase 4: `chart_data` schema (`CORE.md` §5.1, validated on every write), builder, read API + version history, `GanttChart.jsx`. Phase 5: v1 from Evaluate Project, re-plans from `reevaluate_gantt`, job id on every version |

### Task groups & tasks
| Feature | Status | Notes |
|---------|--------|-------|
| `task_groups` | ✅ | Table + model created Phase 1 |
| Task CRUD scoped to a group | ✅ | Project Manager only; details and status have separate endpoints |
| Task ↔ GitHub issue 1:1 on creation | ✅ | Same request; GitHub failure rolls the task back; no token → 503. Complete/cancel/delete close the issue |
| GitHub issue assignment to Member | ✅ | Via `users.github_username` (Q9, self-service in Profile); missing username → unassigned issue + warning |
| `task_progress_doc` per task | ✅ | Phase 5: written by the AI after task creation; rendered on the task page |
| Status authority enforcement | ✅ | `ProjectAccess.may_set_status`: the assignee sets their own task's status, **Completed included** (`completed_by='Assignee'`); the PM any status; others 403. Reworked 2026-09-26 — Members were previously refused Completed |
| Per-task discussion | ✅ | `task_discussions` table created Phase 1 |
| Infinite tree, `Team Lead`, rotating roles | ❌ | Flattened to three levels |
| Task board grouped by task group | ✅ | Replaces the old Kanban (`TasksPage.jsx` deleted) |
| Project group chat + tagging rules | ❌ | Replaced |

### AI automation — see [`CORE.md`](CORE.md)
| Feature | Status | Notes |
|---------|--------|-------|
| AI service layer | ✅ | Phase 5. `ai_service.complete` — schema-validated, 2 retries, settings from `.env` (fixed; Phase 8 removes the DB lookup); jobs via `jobs.enqueue`; failures in `ai_errors` (`CORE.md` §2.1) |
| Evaluate Project → doc + groups + Gantt | ✅ | Phase 5. `POST /projects/{id}/evaluate` + `/evaluate/status`; refused once the project has tasks (`CORE.md` §3 "As built") |
| AI suggests Project Managers | ✅ | Phase 5. On demand, `POST /projects/{id}/suggest-managers` → job result; never persisted |
| AI suggests tasks + assignees | ✅ | Phase 5. `…/task-groups/{gid}/suggest-tasks`, `…/tasks/suggest-assignees`; fill the Create Task form only |
| AI generates `task_progress_doc` | ✅ | Phase 5. After task creation; failure → `tasks.progress_doc_error` |
| Gantt re-evaluation triggers | ✅ | Phase 5. Completion (and reopening), overdue sweep, `project_doc` save, PM button; 30 s debounce (`CORE.md` §5) |
| Weekly progress roll-up | ✅ | Phase 5. Beat, Mondays 07:00; `POST /projects/{id}/progress-report` for now |
| CI/CD webhook → AI completion | ❌ | Removed 2026-09-26 — completion is manual ([`CORE.md`](CORE.md) §7, [`PLANNING.md`](PLANNING.md) §4). `cicd_events` dropped |
| LLM commit verification | ❌ | Was to become the CI/CD resolver; removed with it |
| Performance scoring | ✅ | Phase 5. Re-based on task signals (throughput, on-time rate); attendance and active time are no longer inputs. Live `candidate_stats` feed the AI rankings |
| Task Health Score | ✅ | Retained as a progress-reporting input |
| Dispute Queue · Auto-Escalation · Overallocation · Scope-Drift | 💤 | Deferred — [`PLANNING.md`](PLANNING.md) |

### Notifications
| Feature | Status | Notes |
|---------|--------|-------|
| `notifications` table + in-app centre | 🔲 | Table created Phase 1; API + bell in Phase 7 |
| Assignment / due / completion notifications | 🔲 | In-app + Mailpit |
| Discussion reply notification | 🔲 | |

### Admin panel
| Feature | Status | Notes |
|---------|--------|-------|
| Control Panel — all-tables CRUD | ✅ | Extended to all new Phase-1 tables, except `system_settings` (removed in Phase 3a — secrets) |
| Workforce — full record set | 🔄 | Exists split across pages; consolidate |
| Bulk upload on every Workforce tab | 🔄 | `/hrms/bulk-upload` exists; extend + report rejected rows |
| Monitor page | ✅ | Promoted from header overlay to /admin/monitor full page |
| Configuration via `system_settings` | 🔄 | Resolution (DB → `.env`), secret encryption and the **GitHub** section built (Phase 3a). Mail section in Phase 8. **No AI section** — LLM configuration fixed in `.env` |
| Reports — dashboard download by date range | 🔲 | Phase 8 (Q7 answered 2026-09-26). Replaces the Admin → Reports page and the weekly report email, both ❌ |

### Workforce (Admin-owned records)
| Feature | Status | Notes |
|---------|--------|-------|
| Employee directory, departments, designations | ✅ | Move under Workforce |
| Leaves | 🔄 | Approval moves to Admin — Q10 |
| Holidays | ✅ | |
| Attendance **records** | 🔄 | Table retained; rebuilt as an Admin log. `GET /attendance/all` fixed — it crashed on columns that no longer exist |
| Work shifts / schedules | 🔄 | Table retained; Admin-managed editor |
| Employee clock-in/out UI, geo-fencing | ❌ | Removed (routes, geolocation & UI cleared in Phase 0) |
| Manager's attendance & HR panel | ❌ | Removed outright (cleared in Phase 0) |

### Infrastructure
| Feature | Status | Notes |
|---------|--------|-------|
| PostgreSQL, Redis, pgAdmin, Mailpit, MinIO | ✅ | Docker Compose |
| Celery worker + beat | ✅ | Schedule re-pointed, [`CORE.md`](CORE.md) §8 |
| Alembic migrations, `./start.sh` | ✅ | Alembic is the only schema owner; an empty DB reaches head (tested). `start` migrates first |
| Backend test suite | ✅ | Own `trace_test` DB built by migrations; route-guard audit + role matrix; migration-chain test |
| WebSocket endpoint | ✅ | Re-point from group chat to notifications/discussion |
| GitHub API integration | ✅ | `github_service.py`: repo create, collaborator add / remove (+ invitation withdrawal), token and organization checks, issue create / assign / open-close, file commit |
| CI/CD receiver webhook (HMAC) | ❌ | Removed with CI/CD completion (2026-09-26) |
| Single root `.env` | ✅ | The only env file; backend derives DB / Redis / MinIO / SMTP settings from the Compose keys |
| `APP_ENV` local / production separation | ✅ | Two checks only: `Settings.is_production` and `start.sh`. Production preflight refuses placeholders and seeded passwords |
| Public hosting via Cloudflare Tunnel | ✅ | `cloudflared` compose service (profile `production`, host networking); routes in README |

### Frontend foundation
| Feature | Status | Notes |
|---------|--------|-------|
| shadcn/ui + Tailwind v4 OKLCH tokens | ✅ | |
| Dark / light mode | ✅ | |
| Three panel layouts | ✅ | AdminLayout (sidebar) + ManagerLayout + EmployeeLayout (topbar only) |
| Landing page | ✅ | Public marketing page at / with hero, how-it-works, feature grid |
| Project selector topbar | ✅ | `components/ProjectSelector.jsx`, URL-driven |
| Gantt + graph components | ✅ | `components/GanttChart.jsx` (hand-built, tokens only), `components/ProjectTreeGraph.jsx` (`@xyflow/react` base styles only) |
| Toasts (`sonner`) | ✅ | |
| Responsive / mobile | 🔄 | Desktop only today |

---

## 25. Architectural decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Project hierarchy | Project → Task Group → Task, fixed depth | The Gantt needs a stable module level; infinite nesting made modules undefinable |
| Task identity | A task **is** a GitHub issue | One source of truth for work items; developers see their work where the code lives |
| Document storage | Markdown in the project's GitHub repo, URL in the DB | Docs get version history for free and stay reviewable by developers |
| Source file storage | MinIO | Binary requirement docs are not repo content |
| Completion authority | The assignee, or the Project Manager | The person doing the work knows when it is done; automating that (CI/CD + AI) was more machinery than an educational project needs |
| Gantt maintenance | Regenerate a new version, never patch | Reproducible and auditable; `generated_reason` explains every change |
| `project_initial_doc` immutable | Write-once | Gives `project_doc` something to measure scope drift against |
| AI execution | Celery only, structured JSON only | Keeps request handlers fast; makes verdicts queryable and auditable |
| AI authority | Suggests people, never assigns them | Keeps a human accountable for assignment |
| Role model | Three hardcoded platform roles + per-project roles | Panel separation replaces the dynamic permission matrix |
| Runtime config | `system_settings` table, `.env` fallback | Admin changes mail/AI credentials without a redeploy |
| Workforce data | Retained, Admin-owned | Planning needs availability; the HR *interfaces* were the problem, not the data |

## 26. Service URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| pgAdmin | http://localhost:5050 |
| Mailpit | http://localhost:8025 |
| MinIO console | http://localhost:9001 |

Default login: `admin@trace.com` / `Admin@123`
