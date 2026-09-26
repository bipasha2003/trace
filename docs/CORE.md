# CORE.md — The AI Automation System

> **This is the feature TRACE exists for.** Everything in `PROJECT.md` is the
> structure that holds it up; this document is the thing itself.
>
> If you are implementing anything that touches project evaluation, task
> generation, the Gantt chart, progress documents, or task completion — read this
> file first and in full. Where any other document conflicts with it, this wins.

**Related:** [`PROJECT.md`](PROJECT.md) (roles, schema, UI) ·
[`DEVELOPMENT.md`](DEVELOPMENT.md) (build phases 5 and 6 implement this) ·
[`PLANNING.md`](PLANNING.md) (open questions and deferred AI work)

---

## 1. The pipeline in one view

```
 Manager                AI                 Project Manager        Member          CI/CD
   │                     │                        │                 │               │
   ├─ create project     │                        │                 │               │
   ├─ upload source ────►│                        │                 │               │
   ├─ "Evaluate Project" │                        │                 │               │
   │                     ├─ project_initial_doc   │                 │               │
   │                     ├─ project_doc (clone)   │                 │               │
   │                     ├─ task groups + Gantt   │                 │               │
   │                     ├─ suggest PMs ─────────►│                 │               │
   │◄── assigns PM ──────┤                        │                 │               │
   │                     ├─ suggest tasks ───────►│                 │               │
   │                     │                        ├─ edits project_doc              │
   │                     │◄── re-evaluate Gantt ──┤                 │               │
   │                     │                        ├─ creates task ──┤               │
   │                     │◄─────────────────────  │  (= GitHub issue)               │
   │                     ├─ task_progress_doc     │                 │               │
   │                     │                        ├─ assigns ──────►│               │
   │                     │                        │                 ├─ pushes ─────►│
   │                     │◄──────────────────── webhook ────────────┼───────────────┤
   │                     ├─ resolve which task(s) the push completed │               │
   │                     ├─ mark Completed, notify, re-evaluate Gantt│               │
   │                     │                        │                 │               │
   │                     ├─ weekly: task_progress_doc ×N → project_progress_doc      │
   │◄── progress report ─┤                        │                 │               │
```

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
   document version, a Gantt version, or a status change.
5. **AI credentials and model come from `system_settings`** (Admin → Configuration)
   with `.env` as fallback. Never hardcode a model name at a call site.
6. **Failures are visible.** A failed evaluation puts the project or task into a
   visible error state naming the reason. It must never leave stale data looking fresh.

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
| Task assignee (step 8, and Stage 2) | Tasks completed, on-time rate, CI/CD first-pass rate, similarity of past task subject matter |

Both read `productivity_scores`, which is refreshed weekly (§8). Attendance is
recorded in the system but is deliberately **not** a ranking input.

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
URL on `tasks.task_progress_doc`.

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

---

## 6. Stage 4 — Weekly progress roll-up

**Schedule:** Celery Beat, weekly.

**Job `update_project_progress_docs()`** — for each active project, read every
`tasks.task_progress_doc` in it plus current task statuses, then have the LLM
rewrite `projects.project_progress_doc` and refresh `projects.project_report_doc`.
Both are committed to the repo; the DB stores their URLs.

---

## 7. Stage 5 — CI/CD-driven completion

This is what makes completion machine-decided rather than self-declared.

```
member pushes commit(s) referencing the GitHub issue id
        ↓
GitHub Actions runs the project's CI/CD pipeline
        ↓
on a successful deploy, the pipeline POSTs to TRACE
        ↓
POST /api/v1/webhooks/cicd      (HMAC-signed with the configured secret)
        ↓
persist a cicd_events row  →  enqueue resolve_cicd_completion(event_id)
        ↓
LLM maps the push to task(s) — POSSIBLY MORE THAN ONE
        ↓
matched tasks → Completed, completed_by='AI/CICD', completed_at set
        ↓
notifications  +  reevaluate_gantt(reason='task_status_change')
```

**Convention that makes this work:** a Member should always push with the GitHub
issue id in the commit message. The resolver can fall back to diff analysis, but
the issue reference is what makes the mapping reliable. Surface this convention in
the task detail UI.

**Job `resolve_cicd_completion(event_id)`**
```json
{
  "completed_tasks": [
    { "task_id": 1, "confidence": 0.0, "reasoning": "string",
      "evidence": ["commit sha", "issue ref"] }
  ],
  "partial_tasks": [ { "task_id": 2, "reasoning": "string" } ]
}
```

- `completed_tasks` above the confidence threshold → `Completed`.
- `partial_tasks` and low-confidence matches → `In Review`, surfaced to the Project
  Manager rather than closed silently.
- Only events with `pipeline_status == 'success'` may complete anything.
- **A single push may complete several tasks.** Handle the list, never just the
  first match.

### Completion authority

Enforce this in the API layer, not only in the UI.

| Actor | May set a task to `Completed`? |
|-------|-------------------------------|
| Member | **No — ever.** `PATCH /tasks/{id}/status` with `Completed` returns 403 |
| AI via the CI/CD webhook | Yes → `completed_by='AI/CICD'` |
| Project Manager | Yes → `completed_by='Project Manager'` |
| Manager / Admin | No. They observe. (Admin retains raw Control Panel CRUD as an escape hatch) |

> Building the CI/CD pipeline is itself a project task, and by definition cannot be
> closed by CI/CD. That is precisely why the Project Manager override exists — it is
> not a convenience, it is a bootstrap requirement.

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

---

## 9. Notifications emitted by this system

| Event | Recipients | Channel |
|-------|-----------|---------|
| Task assigned | Assignee | In-app + email |
| Task due soon / overdue | Assignee + the project's Project Managers | In-app + email |
| Task completed by the system | Assignee + the project's Project Managers | In-app + email |
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
