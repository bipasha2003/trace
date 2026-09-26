# CORE.md — The AI Automation System

> **This is the feature TRACE exists for.** Everything in `PROJECT.md` is the
> structure that holds it up; this document is the thing itself.
>
> If you are implementing anything that touches project evaluation, task
> generation, the Gantt chart, progress documents, or task completion — read this
> file first and in full. Where any other document conflicts with it, this wins.

**Related:** [`PROJECT.md`](PROJECT.md) (roles, schema, UI) ·
[`DEVELOPMENT.md`](DEVELOPMENT.md) (build phase 5 implements this) ·
[`PLANNING.md`](PLANNING.md) (open questions and deferred AI work)

---

## 1. The pipeline in one view

```
 Manager                AI                 Project Manager        Member
   │                     │                        │                 │
   ├─ create project     │                        │                 │
   ├─ upload source ────►│                        │                 │
   ├─ "Evaluate Project" │                        │                 │
   │                     ├─ project_initial_doc   │                 │
   │                     ├─ project_doc (clone)   │                 │
   │                     ├─ task groups + Gantt   │                 │
   │                     ├─ suggest PMs ─────────►│                 │
   │◄── assigns PM ──────┤                        │                 │
   │                     ├─ suggest tasks ───────►│                 │
   │                     │                        ├─ edits project_doc
   │                     │◄── re-evaluate Gantt ──┤                 │
   │                     │                        ├─ creates task ──┤
   │                     │◄─────────────────────  │  (= GitHub issue)
   │                     ├─ task_progress_doc     │                 │
   │                     │                        ├─ assigns ──────►│
   │                     │                        │                 ├─ does the work
   │                     │                        │                 ├─ sets status → Completed
   │                     │◄──────────────────── status change ──────┤  (closes the issue)
   │                     ├─ re-evaluate Gantt, notify PMs           │
   │                     │                        │                 │
   │                     ├─ weekly: task_progress_doc ×N → project_progress_doc
   │◄── progress report ─┤                        │                 │
```

Completion is **manual**: the person doing the task marks it complete. The AI plans,
suggests and reports; it never decides that work is done (§7).

---

## 2. Ground rules — non-negotiable

1. **Every LLM call runs inside a Celery task.** A FastAPI route enqueues and
   returns a job id; it never awaits the model.
2. **Every LLM call returns structured JSON** validated against a declared schema.
   On a parse failure, retry; never persist unvalidated output. The only free-form
   field permitted is one that is explicitly a markdown document body.
3. **AI suggests people, it never assigns them.** Project Manager and assignee
   ranking produce candidate lists with reasoning. A human accepts.
4. **Every AI write is attributed and reversible.** Record which job produced a
   document version or a Gantt version. The AI never changes a task's status.
5. **AI credentials and model come from `.env`** (`OPENAI_API_KEY`, `OPENAI_MODEL`,
   `OPENAI_BASE_URL`) and are fixed there — no Admin can change them (decided
   2026-09-26; until Phase 8 the code still also checks `system_settings`, which
   holds no `ai.*` rows). *Originally:* from `system_settings` (Admin → Configuration)
   with `.env` as fallback. Never hardcode a model name at a call site.
6. **Failures are visible.** A failed evaluation puts the project or task into a
   visible error state naming the reason. It must never leave stale data looking fresh.

### 2.1 How the rules are built *(Phase 5)*

| Piece | Where | Rule |
|-------|-------|------|
| Model call | `app/services/ai_service.py` — `AIClient.chat_json()` | OpenAI SDK, JSON mode. Key, model and base URL from `.env` (rule 5; Phase 8 drops the `resolve_setting` detour). No key → the route refuses with 503 *before* enqueuing |
| Validation | `ai_service.complete(ai, Schema, system, user, context=…)` | The reply is parsed into a Pydantic model from `app/schemas/ai.py`. On a parse or validation error the errors go back to the model and it is asked again — **2 retries**, then `AIOutputInvalid`. Rules that need data (e.g. "every `user_id` is a candidate") are validators reading the validation `context`, so they retry too |
| Queue | `app/services/jobs.py` — `enqueue(name, *args)` | Routes and services enqueue by task name **after** committing. Tests replace `enqueue` with a recorder (autouse) — no test reaches Redis or a worker. Job bodies are plain `async def run_*(db, …, ai=…, github=…)` functions in `app/services/ai_jobs.py`; `app/tasks.py` only opens a session (its own engine, `NullPool` — every Celery task runs on a fresh event loop) and calls them |
| Attribution | commit messages, `gantt_charts.generated_by_job` | Every document commit says `(<job name> <job id>)`; every Gantt version stores the job id that wrote it |
| Failure state | `projects.ai_errors`, `tasks.progress_doc_error` | `ai_errors` is `{job name: {message, at}}` — a job sets its own key on failure and clears it on success. Shown on the project Overview. A task's failed progress document shows on the task page |

---

## 3. Stage 1 — Evaluate Project

**Trigger:** the Manager presses **Evaluate Project** on a project that has at least
one `project_source_file`. Re-runnable on demand.

**Endpoint:** `POST /api/v1/projects/{id}/evaluate` → enqueues `evaluate_project`.

**Job `evaluate_project(project_id)`**

| Step | Action | Output |
|------|--------|--------|
| 1 | Extract text from every `project_source_files` row (pdf / docx / md / txt) | `project_source_files.extracted_text` |
| 2 | LLM: summarise the requirements into a structured project document | markdown body |
| 3 | Commit that markdown to the project's GitHub repo | `projects.project_initial_doc` = file URL |
| 4 | Commit the identical content to a second repo file | `projects.project_doc` = file URL |
| 5 | LLM: derive **task groups** with duration estimates | `task_groups` rows |
| 6 | Build the Gantt chart from those groups | `gantt_charts` v1, `generated_reason='initial'` |
| 7 | Rank and **suggest Project Managers** | suggestion payload — not persisted as an assignment |
| 8 | **Suggest tasks** per group, with candidate assignees | suggestion payload — reviewed before creation |
| 9 | `projects.status='Active'`, stamp `last_evaluated_at` | |

**As built (Phase 5)** — `run_evaluate_project` in `app/services/ai_jobs.py`:
- **Who and when.** Only the owning Manager. Refused (409) while the project is
  already `Evaluating`, has no source file with extracted text, or **already has
  tasks** — re-running replaces every task group, which is only safe before work is
  planned into them. After that, the project document and §5 keep the plan current.
- **State.** The route sets `status='Evaluating'` and commits before enqueuing.
  Success → `Active`. Failure → back to `Draft` (or `Active` if it was evaluated
  before), `ai_errors.evaluate_project` names the step that failed, and nothing from
  the failed run is kept in the database. `GET /projects/{id}/evaluate/status` →
  `{state: idle | running | failed, error, last_evaluated_at}`; the UI polls it.
- **Step 1** already happened at upload (`extraction.py`); the job reads
  `extracted_text` (capped at 60 000 characters in total).
- **Steps 3–4** commit the same markdown to `docs/project_initial_doc.md` and
  `docs/project_doc.md` on the default branch. A re-run rewrites both — the old
  brief stays in the files' git history.
- **Step 5** validation: 1–20 groups, unique names, 1–365 days each, `depends_on`
  names an *earlier* group. The names become ids in `task_groups.depends_on`
  (JSONB list of task-group ids), so every later re-plan keeps them.
- **Step 6** schedules the groups (§5 scheduling rule) from the project's
  `start_date` (set to today if empty), sets `end_date` if empty, and writes
  version 1 through `gantt_service.snapshot(..., "initial")`.
- **Steps 7–8 run on demand, not inside this job.** A ranking stored at evaluation
  time is stale by the time a person reads it, and CORE never persists suggestions.
  So: `POST /projects/{id}/suggest-managers` (owner),
  `POST /projects/{id}/tasks/suggest-assignees` (PM, with the draft task's title and
  description) and `POST /projects/{id}/task-groups/{gid}/suggest-tasks` (PM) each
  enqueue a job and return `{job_id}`; the result is read from
  `GET /services/task/{job_id}/result`. Nothing is written.

### Schemas

Step 5 — task groups:
```json
{
  "task_groups": [
    {
      "name": "string",
      "description": "string",
      "sequence": 1,
      "estimated_duration_days": 10,
      "depends_on": ["name of an earlier group"]
    }
  ]
}
```

Steps 7 and 8 — people suggestions:
```json
{
  "suggestions": [
    { "user_id": 1, "score": 0.0, "reasoning": "string", "evidence": ["string"] }
  ]
}
```

### Ranking inputs

| Suggestion | Ranked on |
|------------|-----------|
| Project Manager (step 7) | Projects delivered, on-time delivery rate, average task completion rate across their projects |
| Task assignee (step 8, and Stage 2) | Tasks completed, on-time rate, similarity of past task subject matter |

The inputs are computed live from `tasks` and `projects` at suggestion time
(`scoring_service.candidate_stats`) — the same task signals the weekly
`productivity_scores` stores (§8) — and the latest weekly score is added as
evidence when one exists. Candidates are capped at 25, pre-sorted by completed
tasks, and each carries its last 10 completed task titles (subject-matter
similarity). The model may only return candidate ids (validated). Attendance is
recorded in the system but is deliberately **not** a ranking input.

Step 8's task suggestions:
```json
{
  "tasks": [
    { "title": "string", "description": "string",
      "priority": "Low | Medium | High | Critical", "estimated_hours": 8 }
  ]
}
```
The Project Manager reviews them in the Create Task dialog; accepting one fills the
form, it does not create the task.

---

## 4. Stage 2 — Task creation

**Trigger:** a Project Manager creates a task, manually or by accepting a Stage 1 suggestion.

**Endpoint:** `POST /api/v1/projects/{id}/tasks`

1. Persist the `tasks` row against its `task_group_id`.
2. **Create the GitHub issue** in `projects.github_repo`; store `github_issue_id`
   and `github_issue_url`. Task creation *is* issue creation — the two are never
   allowed to drift apart: both happen in one request, and a GitHub failure rolls
   the task back. With no GitHub token configured, task creation is refused (503).
3. If a Member is assigned: **assign the GitHub issue** to their mapped GitHub
   account, upsert a `project_assignments` row with role `Member`, and emit a
   `task_assigned` notification. A Member with no `github_username` — or who has
   not yet accepted the repository invitation (§4.1) — gets an unassigned issue
   and the Project Manager gets a warning, never a failure.
4. Enqueue `generate_task_progress_doc`.

Status follows the issue: `Completed` / `Cancelled` close it (`completed` /
`not_planned`), reopening a task reopens it, deleting a task closes it as
`not_planned`.

### 4.1 GitHub access — one owner, one token *(decided 2026-09-26; built in Phase 3a)*

TRACE acts on GitHub as **one company account**, not as individual users.

| Piece | Rule |
|-------|------|
| **Owner** | One GitHub **Organization** per TRACE installation (Q12) — per-repo *Write* permission, central removal. Personal accounts are not supported. Stored as `system_settings` `github.owner` (the organization login) |
| **Token** | Entered by the Admin in **Admin → Configuration → GitHub**, stored as `github.token` — `is_secret`, **encrypted at rest**, **write-only**: never returned by any API, only shown masked. `.env` `GITHUB_TOKEN` is the fallback. Organizations may cap fine-grained token lifetime (the live one refuses tokens valid for more than **366 days** with a 403) — Test connection surfaces GitHub's message verbatim |
| **Token scope** | A **fine-grained** token limited to that owner: Administration *read/write* (create repos), Contents *read/write* (commit documents), Issues *read/write*, Metadata *read*. Not a classic full-access token |
| **Test connection** | Checks the token authenticates and can see the organization, before any project depends on it. (A fine-grained token's permissions cannot be read back, so repo-creation rights are proven by the first project creation, which must fail with a precise message) |
| **Repositories** | **TRACE creates one repo per project** when the Manager creates the project: `<org>/<project-slug>`, **always public** (Q13). The Manager no longer types a repo. A name clash is reported (409), never silently reused. The slug is the name lower-cased with every run of other characters turned into `-`, trimmed, ≤100 chars (`github_service.repo_slug`). The repo is created **before** the project row and `auto_init`ed, so documents can be committed at once; its default branch is whatever GitHub gives it. No repo → no project |
| **Public by design** | Because every repo is public, issues, generated documents (including `project_initial_doc`, the AI's summary of the requirements) and commit history are world-readable. Source files stay private in MinIO. TRACE is an educational project; say so in the UI where requirements are uploaded, and never put secrets in them |
| **Collaborators** | When someone joins a project — appointed Project Manager, or assigned a task (every assignment re-invites; GitHub treats it as a no-op for existing collaborators) — TRACE **invites their `github_username`** to the repo with *Write*. GitHub emails an invitation they must accept; until then GitHub refuses them as an issue assignee, so the issue is created (or re-assigned) **unassigned** with an "invitation pending" warning, and the PM assigns again once it is accepted. A PM who leaves the project (removed, holding no tasks) has the access revoked and any pending invitation withdrawn. Members are never removed and there is no resend-invitation action — out of scope for this educational project (`PLANNING.md` §4); assigning a task again re-invites. **Invitation and revocation never fail the change that triggered them** — a missing username or a GitHub refusal comes back as a warning; issue creation, by contrast, still rolls the task back |
| **Deletion** | Deleting a project **archives** its repository (read-only; the token has no delete right), *before* the row is soft-deleted — archive fails → the project is not deleted. A repo already gone (404) does not block. Only repos under the configured organization are archived; a hand-entered pre-3a repo is left alone. The archived repo keeps its name, so a new project with the same name gets a 409 |
| **Commit identity** | Commits TRACE makes (generated documents) carry `github.committer_name` / `github.committer_email` |

Every GitHub call goes through `app/services/github_service.py`, and every
credential through `resolve_setting()` (database value, then `.env`). A GitHub
App — short-lived tokens, not tied to a person — is the long-term replacement for
the token (`PLANNING.md` §3.5).

**Job `generate_task_progress_doc(task_id)`** — the LLM writes the task's
step-by-step plan and completion checklist, commits it to the repo, and stores the
URL on `tasks.task_progress_doc`. *As built:* enqueued after the task (and its
issue) is committed; the file is `docs/tasks/task-<id>.md`, rendered from the JSON
below as a markdown checklist; a failure sets `tasks.progress_doc_error`. The task
page reads it through `GET /tasks/{id}/progress-doc`. It is written once — the
checklist is not ticked off automatically (the assignee's status is the record).

```json
{
  "steps": [{ "order": 1, "title": "string", "detail": "string", "done": false }],
  "acceptance_criteria": ["string"],
  "completion_status": "not_started"
}
```

**Assignee suggestion:** `GET /api/v1/projects/{id}/tasks/suggest-assignees?title=…`
returns ranked Members with reasoning, for the task creation dialog.

---

## 5. Stage 3 — Continuous Gantt re-evaluation

**Job `reevaluate_gantt(project_id, reason)`** — writes a **new `gantt_charts`
version**. It never patches the previous one, so every change is auditable and the
UI can show *why* the chart moved.

| Trigger | `reason` |
|---------|----------|
| Task status → `Completed` | `task_status_change` |
| Task becomes `Overdue` (nightly sweep) | `task_status_change` |
| `project_doc` saved with changed features | `project_doc_updated` |
| Project Manager presses re-evaluate | `manual` |

Debounce: coalesce triggers for the same project inside a short window, so a bulk
status update produces one regeneration rather than twenty.

**As built (Phase 5)** — `gantt_service.request_reevaluation(project_id, reason)`
is the one trigger call:
- **Triggers.** `project_service.set_status` when a task enters or leaves
  `Completed`; `mark_overdue_tasks` once per project with newly overdue tasks;
  `PUT /projects/{id}/documents/doc` when the content actually changed;
  `POST /projects/{id}/gantt/reevaluate` (Project Manager — the manual button).
- **Debounce.** Each trigger enqueues `reevaluate_gantt(project_id, reason,
  requested_at)` with a 30-second countdown (0 for manual). When the job runs it
  does nothing if a version was generated *after* its `requested_at` — the first
  job of a burst covers the rest. No lock, no Redis key.
- **What it does.** Re-schedules the groups and writes a new version. For
  `project_doc_updated` it first asks the AI (with the new document and every
  group's progress) for revised durations of unfinished groups and for new groups
  covering features no group covers (`created_by='AI'`); if that call fails the
  schedule is still rebuilt without it and `ai_errors.reevaluate_gantt` says so.
- **Scheduling rule** (`gantt_service.schedule`), in `sequence` order: a group
  starts at its `planned_start_date` (else the project start), moved to the day
  after its latest dependency ends if that is later; it lasts
  `estimated_duration_days` (else its current planned span, else 7). A `Completed`
  group ends on its `actual_end_date`; an unfinished group whose end has passed is
  stretched to today, so the slip pushes its dependants. The result is written back
  to `planned_start_date` / `planned_end_date` — the *plan* is the current
  forecast; the Gantt versions are its history.
- `recompute_group` stamps `actual_start_date` when a group first leaves `Pending`
  and `actual_end_date` when it becomes `Completed` (cleared if it reopens).

### 5.1 `chart_data` — the one shape every Gantt version has *(defined 2026-09-26, Phase 4)*

Whatever writes a `gantt_charts` row — Stage 1 step 6, `reevaluate_gantt`, or a
hand-written row — writes exactly this, and validates it first against
`GanttChartData` in `app/schemas/gantt.py` (§2 rule 2). The renderer
(`GanttChart.jsx`) reads nothing else: it never joins live task data, so what a
version shows is what was true when it was generated.

```json
{
  "schema": 1,
  "range": { "start": "2026-09-01", "end": "2026-12-31" },
  "bars": [
    {
      "task_group_id": 12,
      "name": "Backend Foundation",
      "sequence": 1,
      "start": "2026-09-01",
      "end": "2026-09-30",
      "completion": 40.0,
      "status": "In Progress",
      "tasks": [
        { "task_id": 31, "title": "Auth API", "status": "Completed",
          "due": "2026-09-15", "assignee": "Alice" }
      ]
    }
  ],
  "dependencies": [ { "from": 12, "to": 14 } ],
  "milestones":   [ { "name": "Project end", "date": "2026-12-31" } ]
}
```

| Field | Rule |
|-------|------|
| `schema` | `1`. Bump it — and teach the renderer both — if the shape ever changes |
| `range` | The timeline shown; `start ≤` every bar start and milestone, `end ≥` every bar end and milestone |
| `bars[]` | One per **task group**, ordered by `sequence`. `start ≤ end`, both dates. `completion` 0–100. `status` is a task-group status (`Pending`, `In Progress`, `Completed`, `Blocked`) |
| `bars[].tasks[]` | The group's tasks, drawn when a bar is expanded. `due` and `assignee` (a display name) may be `null`; a task has no start date, so it is drawn as a marker on `due`. Cancelled tasks are left out |
| `dependencies[]` | Task-group ids: `to` cannot start before `from` ends. Both ids must be bars in this chart; no self-links |
| `milestones[]` | Named dates. May be empty |

**Deterministic builder** — `gantt_service.build_chart_data()` turns the current
task groups and tasks into this shape without the AI: a group's bar is its
`planned_start_date` → `planned_end_date`; a group missing either is laid after the
previous bar (from the project's `start_date`, else today) for its
`estimated_duration_days`, else 7 days. The project's `end_date`, if set, is a
milestone. Its dependencies are the groups' `task_groups.depends_on` ids (added in
Phase 5), limited to groups in the chart. The AI's contribution is those
dependencies plus the durations it writes into the task groups; the dates come from
the §5 scheduling rule.

---

## 6. Stage 4 — Weekly progress roll-up

**Schedule:** Celery Beat, weekly.

**Job `update_project_progress_docs()`** — for each active project, read every
`tasks.task_progress_doc` in it plus current task statuses, then have the LLM
rewrite `projects.project_progress_doc` and refresh `projects.project_report_doc`.
Both are committed to the repo; the DB stores their URLs.

*As built (Phase 5):* Beat runs it Mondays 07:00 over every `Active` project, one
`update_project_progress_doc(project_id)` job each. The owning Manager or a Project
Manager can run it for one project now: `POST /projects/{id}/progress-report`. Files
`docs/project_progress_doc.md` and `docs/project_report_doc.md`; schema
`{"progress_markdown": "…", "report_markdown": "…"}`. Each task's progress document
is read back from GitHub (a missing one is skipped). The Progress Report tab reads
both through `GET /projects/{id}/documents/{progress|report}`.

---

## 7. Task status and completion — manual

*(Changed 2026-09-26: CI/CD-driven, AI-resolved completion was removed from the
design — `PLANNING.md` §4. There is no webhook, no `cicd_events` table and no
resolver job.)*

The person doing a task keeps its status current in TRACE, and marks it
**Completed** when the work is done. No pipeline and no AI decides that.

```
Member works on the task (commits may reference the issue, #N — GitHub links them)
        ↓
PATCH /api/v1/tasks/{id}/status  { "status": "Completed" }
        ↓
completed_by = 'Assignee', completed_at set, the GitHub issue is closed
        ↓
task-group roll-up  +  notifications  +  reevaluate_gantt(reason='task_status_change')
```

Setting any open status again reopens the issue and clears `completed_by` /
`completed_at`.

### Status authority

Enforced in the API layer (`ProjectAccess.may_set_status`), not only in the UI.
Responses carry `allowed_statuses`, derived from the same check.

| Actor | May set |
|-------|---------|
| The task's **assignee** | `Pending`, `In Progress`, `In Review`, `Blocked`, **`Completed`** → `completed_by='Assignee'` |
| The project's **Project Manager** | Any status except `Overdue`, on any task in the project → `completed_by='Project Manager'` |
| Another Member of the project | Nothing — 403 |
| Manager / Admin | Nothing. They observe. (Admin retains raw Control Panel CRUD as an escape hatch) |
| The system | `Overdue` only, from the nightly sweep (§8) |

`Cancelled` stays with the Project Manager: dropping a task is a scope decision,
not a report of work done. `In Review` is an ordinary hand-off status — the
assignee's way of saying "done, please look" — and carries no automation.

---

## 8. Scheduled jobs

| Job | Cadence | Purpose |
|-----|---------|---------|
| `mark_overdue_tasks` | nightly | Flip past-due tasks to `Overdue`, notify, trigger Gantt re-evaluation |
| `task_due_reminders` | daily | Due-soon notifications |
| `update_project_progress_docs` | weekly | Stage 4 roll-up |
| `compute_performance_scores` | weekly | Refresh the scores §3 ranks on |

Retire from the existing schedule: `compute_task_health_and_escalate` (hourly) and
`detect_overallocation` (nightly) — both deferred, see [`PLANNING.md`](PLANNING.md).

*As built (Phase 5):* `mark_overdue_tasks` replaced the pre-re-spec
`mark_delayed_tasks` (which wrote a `Delayed` status that no longer exists). It
flips open past-due tasks (`Pending`, `In Progress`, `In Review`, `Blocked`) to
`Overdue` and requests a Gantt re-evaluation per affected project; its
notifications arrive with Phase 7. `compute_all_weekly_scores` is the weekly
scoring job, re-based on task signals: `task_score` = completed ÷ assigned tasks due
that week, `deadline_score` = completed on or before the due date ÷ completed,
`final_score` = the mean of the two. `att_score` and `active_time_score` are left
empty. `task_due_reminders` is Phase 7.

---

## 9. Notifications emitted by this system

| Event | Recipients | Channel |
|-------|-----------|---------|
| Task assigned | Assignee | In-app + email |
| Task due soon / overdue | Assignee + the project's Project Managers | In-app + email |
| Task completed | The project's Project Managers, and the assignee if someone else completed it | In-app + email |
| Discussion reply | Other participants in the thread | In-app |
| Project evaluation finished (or failed) | The Manager who triggered it | In-app + email |

Email goes through the existing Mailpit/SMTP Celery task. In-app notifications are
`notifications` rows, delivered over the existing WebSocket channel.

---

## 10. Documents this system owns

| Document | Written by | Updated when |
|----------|-----------|--------------|
| `projects.project_initial_doc` | AI, Stage 1 step 3 | **Never** — immutable snapshot of the original brief |
| `projects.project_doc` | AI clones it, Stage 1 step 4 | Project Manager edits it; each save triggers §5 |
| `projects.project_progress_doc` | AI | Weekly, §6 |
| `projects.project_report_doc` | AI | Weekly, §6 |
| `tasks.task_progress_doc` | AI, on task creation | Kept current as work progresses |
| `gantt_charts.chart_data` | AI | §3 step 6, then §5 |

All `*_doc` columns hold **GitHub repository file URLs**, never markdown bodies.
The file's git history *is* its version history — do not build a versions table.

Each document lives at a fixed path on the default branch (`docs/<column>.md`,
tasks at `docs/tasks/task-<id>.md`); TRACE reads it back from that path through
`github_service.read_file`, never by parsing the stored URL.
`GET /projects/{id}/documents/{initial|doc|progress|report}` returns `{url, content}`
to anyone who can see the project; `PUT /projects/{id}/documents/doc` (Project
Manager) commits a new `project_doc` and, when it changed, triggers §5.
