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
   allowed to drift apart.
3. If a Member is assigned: **assign the GitHub issue** to their mapped GitHub
   account, upsert a `project_assignments` row with role `Member`, and emit a
   `task_assigned` notification.
4. Enqueue `generate_task_progress_doc`.

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
