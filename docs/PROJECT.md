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

Last revised 2026-09-21.

---

# Part 1 — Product

## 1. What TRACE is

An **AI-driven project and task management platform**. A project enters as a pile
of raw requirement documents and leaves as a delivered, CI/CD-verified set of
GitHub issues with auto-maintained documentation, a self-updating Gantt chart and
progress reports.

**In scope**
- Projects, their source documents, and their AI-generated living documentation
- Task groups (Gantt modules) and tasks, where a task **is** a GitHub issue
- AI automation: project evaluation, task suggestion, assignee suggestion, Gantt
  generation, progress-doc authoring — all of [`CORE.md`](CORE.md)
- CI/CD-driven task completion; a Member can never self-declare "done"
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
| `Project Manager` | The project's Manager | Edit `project_doc`, create task groups and tasks, assign Members, mark a task complete, trigger AI re-evaluation |
| `Member` | A Project Manager, by being assigned a task | See the project, work their tasks, push code, discuss, update their task progress — **cannot** mark a task complete |

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
  only level assigned to a person and the only level CI/CD can complete.

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
| **Control Panel** | `/admin/control-panel` | Generic CRUD over **every** table. Raw and table-driven — the escape hatch, not the daily UI. |
| **Workforce** | `/admin/workforce` | Curated UI over the whole workforce record set: employees, managers, leaves, holidays, attendance, work shifts, departments, designations. Every tab has CRUD **and bulk upload** (CSV/JSON). The same tables appear in Control Panel; this is the human view. |
| **Monitor** | `/admin/monitor` | Server and service health: API, PostgreSQL, Redis, Celery worker, Celery beat, MinIO, Mailpit, WebSocket, LLM reachability, recent Celery job outcomes. |
| **Configuration** | `/admin/configuration` | Runtime settings in the database, not only `.env`: mail/SMTP, AI provider (key, base URL, model), GitHub credentials, CI/CD webhook secret. Per-section "test connection". |
| **Reports** | `/admin/reports` | **Pending definition** — see [`PLANNING.md`](PLANNING.md) Q7. Ships as a placeholder route. |

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
| Create project | Name, description, GitHub repository, and upload of one or more **project source files** |
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
- Marking a task complete — the only human permitted to (§ [`CORE.md`](CORE.md) §7)

### 7.3 A project selected — as **Member**
- The same dashboard, **read-only** with respect to project structure
- Their assigned tasks, each task's `task_progress_doc`, and per-task discussion
- Work is reported by pushing commits that reference the GitHub issue id
- **No complete-task control anywhere**

---

## 8. Supporting features

| Feature | Requirement |
|---------|-------------|
| Task due notification | Notify assignee and Project Manager as a task approaches and passes its due date |
| Assignment notification | Notify a Member when a task is assigned to them |
| Completion notification | Notify assignee and Project Manager when the system marks a task complete |
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
| `github_repo` | `String(255)` | e.g. `org/repo`. Where issues and doc files live |
| `github_default_branch` | `String(100)` | Default `main`. Branch strategy deferred — `PLANNING.md` Q6 |
| `status` | `String(20)` | `Draft`, `Evaluating`, `Active`, `Completed`, `Archived` |
| `start_date` / `end_date` | `Date` | Planned window, maintained by the Gantt evaluator |
| `project_initial_doc` | `String(500)` | URL. AI-authored, written once |
| `project_doc` | `String(500)` | URL. Living doc; starts as a clone of the initial doc |
| `project_progress_doc` | `String(500)` | URL. Rewritten weekly by AI |
| `project_report_doc` | `String(500)` | URL. Report, AI-maintained |
| `last_evaluated_at` | `DateTime` | Last successful AI evaluation |

Has many `project_source_files`, `project_assignments`, `task_groups`; one current
`gantt_chart`.

#### The project document set

Direct mapping from the original plan to the implemented fields.

| Original plan | Column | Written by | Updated when |
|---------------|--------|-----------|--------------|
| `project_source_files` (multiple file field) | `project_source_files` table | Manager, at creation | Manager adds or removes files |
| `Project_initial_doc` — "scrapped by AI from project_source_files" | `project_initial_doc` | **AI**, [`CORE.md`](CORE.md) §3 step 3 | **Never.** Immutable snapshot of what the AI first understood, so drift from the original brief stays visible |
| `Project_doc` — "duplicate, updated as features shift" | `project_doc` | **AI** clones it, §3 step 4 | **Project Manager** edits it as features shift or are added; every save triggers Gantt re-evaluation |
| `Progress_doc` — "updated by task completioner" | `project_progress_doc` | **AI**, weekly | Reads every `task_progress_doc` and rewrites it. Completion is machine-decided, so the "task completioner" is the AI/CI-CD path — [`CORE.md`](CORE.md) §6 |
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

### 11.5 `gantt_charts`

Materialised and regenerated, never patched.

| Column | Type | Notes |
|--------|------|-------|
| `project_id` | FK `projects.id` | |
| `version` | `Integer` | Incremented per regeneration |
| `chart_data` | `JSONB` | Bars, dependencies, milestones — the render payload |
| `generated_reason` | `String(100)` | `initial`, `task_status_change`, `project_doc_updated`, `manual` |
| `generated_at` | `DateTime` | |

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
| `category` | `String(50)` | `mail`, `ai`, `github`, `cicd` |
| `key` | `String(100)` | |
| `value` | `Text` | Encrypted at rest for secrets |
| `is_secret` | `Boolean` | Masked in API responses |

Unique on (`category`, `key`). Resolution order: database value, then `.env` fallback.

### 11.9 `cicd_events`

Audit trail for the webhook that completes tasks.

| Column | Type | Notes |
|--------|------|-------|
| `project_id` | FK `projects.id` | |
| `provider` | `String(50)` | `github_actions`, etc. |
| `commit_sha` / `commit_message` / `branch` | | |
| `pipeline_status` | `String(30)` | `success`, `failure` |
| `payload` | `JSONB` | Raw webhook body |
| `resolved_task_ids` | `JSONB` | Tasks the AI decided this push completes — **may be several** |
| `ai_reasoning` | `Text` | Why those tasks, for auditability |
| `processed_at` | `DateTime` | |

---

## 12. Changes to `tasks`

**Add**

| Column | Type | Notes |
|--------|------|-------|
| `project_id` | FK `projects.id` | Required |
| `task_group_id` | FK `task_groups.id` | Required |
| `task_progress_doc` | `String(500)` | URL to the AI-authored steps doc |
| `assigned_to_user_id` | FK `users.id` | Replaces employee-based assignment |
| `assigned_by_user_id` | FK `users.id` | The assigning Project Manager |
| `completed_by` | `String(20)` | `AI/CICD` or `Project Manager` |
| `completed_at` | `DateTime` | |

**Keep** — `title`, `description`, `priority`, `status`, `due_date`,
`estimated_hours`, `github_issue_id`, `github_issue_url`, `commit_hash`,
`commit_verified`, `llm_verification_notes`, `health_score`, `health_reason`,
`last_health_check`.

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
> `productivity_scores` is retained but **re-based**: inputs become task throughput,
> on-time completion rate and CI/CD pass rate. Attendance is still recorded but is
> no longer a scoring input. These scores are what the AI ranks on when it suggests
> Project Managers and assignees ([`CORE.md`](CORE.md) §3).

---

## 15. Migration

The existing data is a seeded demo tree, so this can be pragmatic. One Alembic
revision per step, so a failed backfill rolls back without losing the new tables.

1. **Create** `projects`, `project_source_files`, `project_assignments`,
   `task_groups`, `gantt_charts`, `task_discussions`, `notifications`,
   `system_settings`, `cicd_events`.
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
/admin/configuration      Mail · AI · GitHub · CI/CD settings
/admin/reports            Placeholder — PLANNING.md Q7
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
requirements → AI plans the project → CI/CD verifies delivery), a feature grid, a
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
| **Control Panel** | Table picker grouped by category, then a generic data grid with create/edit/delete dialogs and filtering. Driven by the existing `MODEL_REGISTRY` pattern in `backend/app/api/v1/admin.py`. |
| **Workforce** | Tabs per §5. Purpose-built, not a raw grid: directory cards and search for people, an approve/reject queue for leaves, a calendar for holidays, a filterable log for attendance, a shift editor with employee assignment. Every tab has a **Bulk Upload** action (CSV/JSON) with a validation summary that reports rejected rows rather than failing silently. Attendance and shifts are Admin-maintained records — there is no clock-in control anywhere in the product. |
| **Monitor** | `ServiceMonitor.jsx` promoted from a header overlay to a page. Health cards for API, PostgreSQL, Redis, Celery worker, Celery beat, MinIO, Mailpit, WebSocket and LLM, plus recent Celery job outcomes. |
| **Configuration** | Sections for Mail/SMTP, AI provider, GitHub, CI/CD webhook. Secrets masked, each section with "Test connection". Writes to `system_settings`. |
| **Reports** | Placeholder page stating the report set is pending definition. |

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

**Create project** — a stepper: details (name, description, GitHub repo) → upload
source files (multi-file drop zone) → review → create. On create, offer
**Evaluate Project** immediately.

## 20. Employee panel UI

Same topbar and selector pattern. The selector lists every project the Employee is
assigned to, annotated with their project role.

**"All"** — aggregate progress across their projects, **My Tasks** grouped by due
state, an overdue callout, recent notifications.

**A project selected — Project Manager** — tabs **Overview · Tree · Gantt · Tasks ·
Project Doc · Team**:
- *Tasks* — board grouped by task group, with **Create Task**. The dialog calls the
  assignee-suggestion endpoint and shows ranked Members with reasoning. Completing
  a task happens here, behind a confirmation that records
  `completed_by='Project Manager'`.
- *Project Doc* — markdown editor over `project_doc`. Saving triggers Gantt
  re-evaluation; say so in the UI *before* saving.
- *Team* — the project's Members.

**A project selected — Member** — tabs **Overview · Tree · Gantt · My Tasks**.
Read-only with respect to project structure. No create-task control, and **no
complete-task control anywhere** — the task view instead explains that completion
is confirmed by CI/CD.

**Task detail** — description, linked GitHub issue, the rendered
`task_progress_doc` with its step checklist, status timeline, CI/CD events that
referenced the task, and the discussion thread. The status control is disabled for
Members with an explanatory tooltip, and the view states the
push-with-the-issue-id convention ([`CORE.md`](CORE.md) §7).

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

## 22. Gantt chart

Renders `gantt_charts.chart_data` at the latest version. One bar per **task group**,
expandable to its tasks, with a today marker, dependency arrows and a completion
overlay per bar. Read-only everywhere — it is regenerated, never dragged. Show the
version number and `generated_reason` so users understand why it moved.

## 23. Existing pages — disposition

| Current file | Disposition |
|--------------|-------------|
| `pages/AttendancePage.jsx` | **Rebuild** as Admin → Workforce tabs. Clock-in/out controls, geolocation capture and the Manager HR view go; the attendance log, leave queue, holiday calendar and shift editor stay as Admin record-keeping |
| `pages/MasterPage.jsx` | **Delete** — dynamic roles, dynamic menus and the permission matrix are removed |
| `pages/DashboardPage.jsx` | **Replace** with three panel dashboards |
| `pages/TasksPage.jsx` | **Replace** — infinite tree, group chat and dispute queue give way to project / task-group / task views |
| `pages/EmployeesPage.jsx` | **Move** into Admin → Workforce |
| `pages/ProductivityPage.jsx` | **Fold** into Admin → Reports; scores become an AI input, not a headline page |
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
| Three hardcoded platform roles | 🔄 | DB seeds four; collapse to three |
| Panel separation `/admin` `/manager` `/employee` | 🔲 | All roles share one shell today |
| Public landing page at `/` | 🔲 | `/` currently redirects to `/dashboard` |
| Guest-only + role-route guards, `/403` | 🔲 | |
| Project-scoped authorisation | 🔲 | Via `project_assignments` |
| Dynamic roles / menus / permission matrix | ❌ | Contradicts hardcoded roles |
| User registration, profile update | ✅ | |
| `github_username` on user | 🔲 | Required to assign issues — `PLANNING.md` Q9 |
| Token refresh, 2FA, session management | 🔲 | Unchanged backlog |

### Projects *(new core)*
| Feature | Status | Notes |
|---------|--------|-------|
| `projects` table + CRUD | 🔲 | **No project entity exists today** — "project" is a root task |
| `project_source_files` multi-upload (MinIO) | 🔲 | |
| The four project documents | 🔲 | GitHub repo file URLs |
| Project Manager assignment / removal | 🔲 | With AI suggestions |
| Manager combined + per-project dashboards | 🔲 | |
| Project tree graph | 🔲 | |
| Gantt chart, versioned | 🔲 | |

### Task groups & tasks
| Feature | Status | Notes |
|---------|--------|-------|
| `task_groups` | 🔲 | |
| Task CRUD scoped to a group | 🔄 | Exists; re-parent from tree to group |
| Task ↔ GitHub issue 1:1 on creation | 🔄 | Manual button today; must be automatic |
| GitHub issue assignment to Member | 🔄 | Blocked on Q9 |
| `task_progress_doc` per task | 🔲 | |
| Completion authority enforcement | 🔲 | [`CORE.md`](CORE.md) §7 |
| Per-task discussion | 🔲 | Replaces group chat |
| Infinite tree, `Team Lead`, rotating roles | ❌ | Flattened to three levels |
| Kanban board | 🔄 | Regroup by task group |
| Project group chat + tagging rules | ❌ | Replaced |

### AI automation — see [`CORE.md`](CORE.md)
| Feature | Status | Notes |
|---------|--------|-------|
| Evaluate Project → doc + groups + Gantt | 🔲 | `CORE.md` §3 |
| AI suggests Project Managers | 🔲 | |
| AI suggests tasks + assignees | 🔄 | Reuses AI Subtask Decomposition |
| AI generates `task_progress_doc` | 🔲 | |
| Gantt re-evaluation triggers | 🔲 | `CORE.md` §5 |
| Weekly progress roll-up | 🔲 | `CORE.md` §6 |
| CI/CD webhook → AI completion | 🔲 | One push may complete several tasks |
| LLM commit verification | 🔄 | Becomes the CI/CD completion resolver |
| Performance scoring | 🔄 | Re-base on task + CI/CD signals |
| Task Health Score | ✅ | Retained as a progress-reporting input |
| Dispute Queue · Auto-Escalation · Overallocation · Scope-Drift | 💤 | Deferred — [`PLANNING.md`](PLANNING.md) |

### Notifications
| Feature | Status | Notes |
|---------|--------|-------|
| `notifications` table + in-app centre | 🔲 | Header bell is UI-only today |
| Assignment / due / completion notifications | 🔲 | In-app + Mailpit |
| Discussion reply notification | 🔲 | |

### Admin panel
| Feature | Status | Notes |
|---------|--------|-------|
| Control Panel — all-tables CRUD | ✅ | Extend to the new tables |
| Workforce — full record set | 🔄 | Exists split across pages; consolidate |
| Bulk upload on every Workforce tab | 🔄 | `/hrms/bulk-upload` exists; extend + report rejected rows |
| Monitor page | 🔄 | Promote from header overlay |
| Configuration via `system_settings` | 🔲 | `.env` only today |
| Reports | 🔲 | Placeholder — **Q7 blocks the contents** |

### Workforce (Admin-owned records)
| Feature | Status | Notes |
|---------|--------|-------|
| Employee directory, departments, designations | ✅ | Move under Workforce |
| Leaves | 🔄 | Approval moves to Admin — Q10 |
| Holidays | ✅ | |
| Attendance **records** | 🔄 | Table retained; rebuilt as an Admin log |
| Work shifts / schedules | 🔄 | Table retained; Admin-managed editor |
| Employee clock-in/out UI, geo-fencing | ❌ | No employee HR self-service |
| Manager's attendance & HR panel | ❌ | Removed outright |

### Infrastructure
| Feature | Status | Notes |
|---------|--------|-------|
| PostgreSQL, Redis, pgAdmin, Mailpit, MinIO | ✅ | Docker Compose |
| Celery worker + beat | ✅ | Schedule re-pointed, [`CORE.md`](CORE.md) §8 |
| Alembic migrations, `./start.sh` | ✅ | |
| WebSocket endpoint | ✅ | Re-point from group chat to notifications/discussion |
| GitHub API integration | 🔄 | Issue create/assign + repo file commit |
| CI/CD receiver webhook (HMAC) | 🔲 | |
| The project's own CI/CD pipeline | 🔲 | Explicitly a task in the build |

### Frontend foundation
| Feature | Status | Notes |
|---------|--------|-------|
| shadcn/ui + Tailwind v4 OKLCH tokens | ✅ | |
| Dark / light mode | ✅ | |
| Three panel layouts | 🔲 | |
| Landing page | 🔲 | |
| Project selector topbar | 🔲 | |
| Gantt + graph components | 🔲 | |
| Toasts (`sonner`) | ✅ | |
| Responsive / mobile | 🔄 | Desktop only today |

---

## 25. Architectural decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Project hierarchy | Project → Task Group → Task, fixed depth | The Gantt needs a stable module level; infinite nesting made modules undefinable |
| Task identity | A task **is** a GitHub issue | One source of truth for work items; enables CI/CD-driven completion |
| Document storage | Markdown in the project's GitHub repo, URL in the DB | Docs get version history for free and stay reviewable by developers |
| Source file storage | MinIO | Binary requirement docs are not repo content |
| Completion authority | AI via CI/CD, or Project Manager | Prevents self-declared completion; the PM override exists for tasks that precede CI/CD |
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
