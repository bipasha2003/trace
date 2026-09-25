# PLANNING.md — Journey, Decisions & Open Threads

> The record of *how* TRACE got to its current shape and what is still unsettled.
> [`PROJECT.md`](PROJECT.md) says what the system is; this file says why, what was
> rejected, and what was pushed over the horizon.
>
> **This is a living log, and it is not only ours.** Agents developing TRACE record
> their own planning and non-obvious decisions here (§5) so the next agent inherits
> the reasoning instead of re-deriving it.

---

## 1. Journey

### Stage 1 — Original conception
TRACE began as *Task and Resource Attendance and Comprehensive Evaluation*: a
bare-minimum HRMS bolted to an infinite task tree. The scope was framed as
"starts after an employee already exists, ends at task completion and evaluation".
Attendance, leaves, shifts and holidays were justified as inputs to task evaluation.

The task model was an **infinite tree** with roles rotating at every level —
Project Manager at the root, Team Leads at intermediate nodes, Members at the
leaves. A Team Lead at one level could be a Member at another. GitHub issues were
pushed manually from ground-level tasks, an LLM verified commits on request, and
each task tree got a chat group with tree-derived tagging rules.

### Stage 2 — Build-out
The platform was built roughly to that spec: HRMS module with GPS clock-in/out and
geo-fencing, the infinite tree with Kanban and chat, LLM commit verification,
weekly productivity scoring, and an Admin panel with generic all-tables CRUD.

A set of "Tier 1" advanced features followed: Task Health Score, an Explainable-AI
Dispute Queue, AI Subtask Decomposition, an Auto-Escalation Engine, and Cross-Tree
Overallocation Detection. Master Settings grew dynamic system roles, dynamic
navigation menus and a live role↔menu permission matrix.

All roles shared a single panel, with the sidebar filtered by that matrix.

### Stage 3 — The core re-spec *(2026-09-21)*
The project had drifted from its intent. The core feature was not the task tree —
it was supposed to be **AI-driven project delivery**. The re-spec:

- **The Manager stopped being an HR role.** Their attendance & HR panel was cut
  entirely; they now bring projects in, assign Project Managers, and watch progress.
- **Panels split by base route.** `/admin`, `/manager`, `/employee`, plus a public
  landing page at `/` for guests. The shared shell and the permission matrix that
  powered it both went.
- **A real `projects` entity appeared.** Until now "project" was just a root task —
  there was no projects table at all. Projects now own source files, four living
  markdown documents, a GitHub repo and a Gantt chart.
- **The hierarchy flattened** to Project → Task Group → Task. Task groups are the
  Gantt's modules; the infinite tree and the Team Lead role were retired.
- **Completion became machine-decided.** CI/CD triggers an AI resolution of which
  tasks a push completed. A Member can never mark their own work done.
- **AI moved to the centre.** Evaluate Project, task-group derivation, Gantt
  generation and regeneration, per-task progress documents, weekly roll-ups, and
  ranked suggestions for Project Managers and assignees — all of [`CORE.md`](CORE.md).

### Stage 4 — Documentation refactor *(2026-09-21)*
Nine scattered markdown files with overlapping and contradictory content were
consolidated into six: `AGENTS.md` and `README.md` at the root, and `PROJECT.md`,
`DEVELOPMENT.md`, `CORE.md` and `PLANNING.md` under `docs/`.

---

## 2. Decision log

| Date | Decision | Why |
|------|----------|-----|
| 2026-09-21 | Manager loses the attendance/HR panel, becomes project-oriented | HR was never task management; it made the Manager role incoherent |
| 2026-09-21 | Panels split by base route, landing page added | One shell serving three audiences meant every screen hedged |
| 2026-09-21 | `projects` and eight other tables introduced | There was no project entity at all; the core feature had nowhere to live |
| 2026-09-21 | Infinite tree and `Team Lead` retired for a fixed three-level hierarchy | The Gantt needs a stable "module" level, which unlimited nesting cannot define |
| 2026-09-21 | Task identity = GitHub issue, 1:1, created automatically | Manual push kept the two out of sync; CI/CD completion needs them married |
| 2026-09-21 | Documents stored as GitHub repo files, URLs in the DB | Free version history, reviewable by developers, no blob columns |
| 2026-09-21 | `project_initial_doc` is write-once | Gives `project_doc` something to measure scope drift against |
| 2026-09-21 | Gantt regenerated as a new version, never patched | Auditable; `generated_reason` explains every movement |
| 2026-09-21 | AI suggests people, never assigns them | Keeps a human accountable for who does what |
| 2026-09-21 | Completion authority: AI/CI-CD or Project Manager only | Self-declared completion was the thing worth designing out |
| 2026-09-21 | Dynamic roles, menus and the permission matrix retired | Directly contradicted three hardcoded roles with fixed panels |
| 2026-09-21 | Runtime config moved to `system_settings` with `.env` fallback | Admin changes mail/AI credentials without a redeploy |
| 2026-09-21 | **Workforce record set retained in full, Admin-owned** | The HR *interfaces* were the problem, not the data. Planning needs availability |
| 2026-09-21 | Four built AI features deferred rather than deleted | Their designs are sound; they lost their context, not their value |
| 2026-09-24 | Backfill migration includes explicit column values for NOT NULL non-defaulted columns | `completion_percentage` on task_groups and `github_default_branch` on projects had NOT NULL without server defaults. The obvious choice would be to add server defaults; we chose to supply explicit values in the migration INSERT instead to avoid a third schema revision for cosmetic defaults. |
| 2026-09-24 | Model class removal paired exactly with the Alembic revision that drops its table | The obvious alternative is to remove the class in Phase 0. We did not, because alembic autogenerate would then propose a `drop_table` in Phase 0 before any backfill happened, corrupting the step sequencing described in DEVELOPMENT.md. |
| 2026-09-25 | GuestOnlyRoute redirects to role-base route; a mismatch renders /403 not a silent redirect | A silent redirect hides mis-provisioned accounts. The /403 page shows the user their actual roles so the error is actionable. This was the obvious design per PROJECT.md §4 — recorded because the implementation required getRoleBase() to be importable from both GuestOnlyRoute and LoginPage without creating a circular dep (extracted to GuestOnlyRoute.jsx and imported from there). |

---

## 3. Deferred — long horizon

Built or designed, deliberately parked. None of this enters the build before
Phase 6 ships. Short-term deferrals live in [`DEVELOPMENT.md`](DEVELOPMENT.md) instead.

### 3.1 Explainable-AI Dispute Queue *(built, removed in Phase 0)*
A "contest verdict" flow over AI decisions: structured
`{verdict, confidence, reasoning, evidence}` output, an appeal routed to the
Project Manager, and a human override stored alongside the AI verdict.
**Why it returns:** once CI/CD completes tasks automatically, a disputed
completion is a real scenario. Revisit after Phase 6.
*Was:* `EvaluationDispute` model, `/tasks/dispute`, `/tasks/disputes`.

### 3.2 Auto-Escalation Engine *(built, removed in Phase 0)*
Escalate a task that stays Red for N days, or is blocked without commit activity,
up the chain with a Mailpit email.
**Why it was parked:** it escalated along the rotating-role tree, which no longer
exists. The chain is now Member → Project Manager → Manager, so the design needs
rewriting before reuse.

### 3.3 Cross-Tree Overallocation Detection *(built, removed in Phase 0)*
Nightly detection of an employee loaded across several subtrees at once.
**Why it was parked:** it solved a problem the infinite tree created. The
equivalent question now is cross-*project* overallocation — genuinely useful, but a
different implementation.

### 3.4 Scope-Drift Detection *(designed, never built)*
Store each commit's LLM-extracted intent in `task_commit_logs`; a periodic job
flags when accumulated work drifts from the task's original scope.
**Why it returns:** the CI/CD resolver already extracts commit intent, so most of
the input exists after Phase 6. `project_initial_doc` being immutable gives it a
project-level baseline too.

### 3.5 Future ideas — not committed

| Idea | Value | Earliest |
|------|-------|----------|
| Chat-ops in task discussion (`@trace create task …`) | Natural-language task creation | After Phase 7 |
| Reusable project templates | Instantiate a standard task-group structure | After Phase 3 |
| Cross-project workload view | Successor to §3.3 | After Phase 5 |
| Contribution heatmap | Commits + completions per person over time | After Phase 6 |
| Critical-path overlay on the Gantt | Projected completion dates from dependencies | After Phase 4 |
| Whiteboard / voice → project docs | Multimodal intake into `project_source_files` | After Phase 5 |
| AI fairness audit | Check suggestion scores for systematic bias | After Phase 5 |
| Multi-provider CI/CD (GitLab, Jenkins) | Beyond GitHub Actions | After Phase 6 |

**Rule for everything in §3:** it does not enter the build until the phase it
depends on has shipped. When it does, it moves into [`PROJECT.md`](PROJECT.md) §24
with a status and gets a proper spec — this section is not a specification.

---

## 4. Rejected concepts

Considered during the re-spec and deliberately not adopted. Recorded so they are
not re-proposed without new information.

| Rejected | Instead | Why |
|----------|---------|-----|
| Keeping the infinite task tree under a Project | Fixed Project → Task Group → Task | A Gantt module has to sit at a known depth. With unlimited nesting, "which level is a module?" has no answer |
| Deleting the workforce tables outright | Retain them, Admin-owned, with bulk upload | Destroys data that planning needs; the interfaces were the problem |
| Keeping the role↔menu permission matrix | Hardcoded roles, code-defined per-panel menus | Three fixed panels and a configurable menu system solve the same problem twice, and disagree when they drift |
| A `*_doc_versions` table | Repo files, `git log` as history | Re-implements version control inside the database |
| Letting Members mark their own tasks complete | AI via CI/CD, or the Project Manager | Self-declared completion is precisely what this system exists to replace |
| Patching the Gantt chart in place | Regenerate as a new version | No audit trail, and no way to answer "why did this date move?" |
| AI auto-assigning people | AI suggests, a human accepts | Accountability for who does what must stay with a person |
| A separate "add members to project" step | Assignment to a task grants membership | An extra gate with no decision behind it (Q8 — revisit if roster control is wanted) |
| Storing markdown bodies in DB columns | GitHub file URLs | Documents are developer artefacts; they belong where developers review them |

---

## 5. Agent planning log

Agents developing TRACE append here: non-obvious decisions, discovered
constraints, and things the docs did not anticipate. Newest last. Keep entries
short — a decision, and the reason it was not the obvious choice.

| Date | Agent / phase | Note |
|------|---------------|------|
| 2026-09-21 | Phase 0 expansion | Cleanup inventory built from an actual sweep of the codebase rather than from the spec. Two traps surfaced that the spec did not anticipate: (a) deleting a model class in Phase 0 while its table still exists makes the next `alembic --autogenerate` propose an unbackfilled drop — so model deletion moved to Phase 1, paired with each table drop; (b) `compute_task_health_and_escalate` bundles a retained feature (Task Health Score) with a deferred one (Auto-Escalation), so the job is split rather than kept or deleted wholesale. Also found ~9 unused shadcn template components, `data/mock.js` and `hooks/useApi.js` never imported, and `.trace_pids` + a 1.5 MB unrelated PDF tracked in git. |
| 2026-09-21 | Doc refactor | Nine overlapping docs consolidated to six. `Overview.md`, `Devplopment.md` and the original `AGENT.md` were mined for anything unique before deletion: the push-with-issue-id convention went to [`CORE.md`](CORE.md) §7; the Celery `imports=["app.tasks"]` registration and the `/services/task/{id}/result` polling endpoint went to [`../AGENTS.md`](../AGENTS.md). Nothing else in them was unique. |
| 2026-09-21 | Phase 0 execution | Ground cleared: dead routes, master.py, template scaffolding components, and deferred features (tree hierarchy, disputes, group chat, overallocations, clock-in/out) removed from API and frontend. Rebuilt TasksPage with clean Kanban/List views and health risk indicators. Fixed async MissingGreenlet in EmployeeService by chaining eager load for user roles. All retained workforce and health endpoints verified at 200 OK, full stack starts clean, and browser login verified. |
| 2026-09-24 | Phase 1 execution | New `project.py` model file created with all 9 new tables (projects, project_source_files, project_assignments, task_groups, gantt_charts, task_discussions, notifications, system_settings, cicd_events). Task model updated: 7 new columns added, all tree columns dropped (parent_task_id, team_lead_id, project_manager_id, task_level_role, tree_path, assigned_to, assigned_by). github_username added to User. Three Alembic revisions: (1) create tables + alter tasks, (2) backfill + drop tree cols, (3) drop deprecated tables + migrate roles. Non-obvious: the `completion_percentage` and `github_default_branch` columns had NOT NULL without server defaults, so the backfill INSERTs had to supply explicit values. model class removal was paired exactly with the revision that drops each table. Seeds rewritten: 1 Admin + 1 Manager + 3 Employees + 1 demo project. Autogenerate diff confirmed clean. |
| 2026-09-25 | Phase 2 execution | Three panel layouts built (AdminLayout with collapsible sidebar, ManagerLayout and EmployeeLayout topbar-only). GuestOnlyRoute and RoleRoute guards added; cross-panel mismatch → /403. LoginPage updated to resolve role-base route from getRoleBase(). LandingPage built marketing-quality with hero, problem, 3-step how-it-works, 8-feature grid, CTA, footer. Admin sidebar rewritten static 5-item. MonitorPage promoted to /admin/monitor page. Stub pages for all panel routes created so App.jsx routing is complete. Non-obvious: getRoleBase() lives in GuestOnlyRoute.jsx and is imported by both GuestOnlyRoute and LoginPage — this avoids creating an AuthContext dependency in the route guard while still keeping the role-→-route mapping in one place. |

---

## 6. Open questions

Each carries the assumption currently written into the docs, so implementation is
never blocked. When an answer differs, change the doc and the code together and
update the row. **Answered questions stay here** rather than being deleted, so the
reasoning behind a decision remains visible.

| # | Topic | Status |
|---|-------|--------|
| Q1 | Task hierarchy depth | Assumed |
| Q2 | Attendance / shifts tables | ✅ Answered 2026-09-21 |
| Q3 | Dynamic roles & menu matrix | Assumed |
| Q4 | Existing Tier-1 AI features | Assumed |
| Q5 | Group chat vs per-task discussion | Assumed |
| Q6 | GitHub repo & branch strategy | Assumed |
| Q7 | Admin → Reports contents | **Blocked — needs an answer** |
| Q8 | Member roster vs task assignment | Assumed |
| Q9 | GitHub account mapping | Assumed |
| Q10 | Who approves leaves | Assumed |
| Q11 | Manager ↔ project ownership | Assumed |

### Q1 — How deep does the task hierarchy go?
The codebase implements an **infinite** tree with roles rotating per level. The new
requirements describe task groups as "modules for the Gantt chart" and name only
Project Manager and Member; `Team Lead` is never mentioned.
**Assumption:** flattened to **three fixed levels** — Project → Task Group → Task.
`Team Lead`, `parent_task_id` recursion and rotating-role logic are removed.
**If wrong:** nesting means `tasks.parent_task_id` survives and the Gantt module
becomes "depth-1 child" rather than a `task_groups` table — a substantial change to
[`PROJECT.md`](PROJECT.md) §11.4 and §12.

### Q2 — Do attendance, clock-in/out and shifts survive? ✅ **Answered**
**Answer (2026-09-21):** the **tables stay**. The whole workforce record set is
retained and **Admin-managed** under Workforce, with CRUD and bulk upload on every
tab. Removed is the *interface*: the Manager HR panel, employee clock-in/out
capture, and geo-fence enforcement. Recorded coordinates remain as plain data.
Performance scoring is re-based on task and CI/CD signals; attendance is recorded
but is not a scoring input.
*Documented in [`PROJECT.md`](PROJECT.md) §5, §9.1, §14, §18.*

### Q3 — Do dynamic roles and the role↔menu matrix survive?
Master Settings supports arbitrary system roles, custom navigation modules and a
live permission matrix. The new spec says three *hardcoded* roles with fixed menus.
Both cannot be true.
**Assumption:** dynamic roles, dynamic menus and the matrix are **removed**;
`Platform Admin` → `Admin`, `Staff` → `Employee`.
**If wrong:** the middle ground is hardcoded roles plus a per-panel menu visibility
toggle, in which case `RoleMenuPermission` stays.

### Q4 — What happens to the built Tier-1 AI features?
**Assumption:**

| Feature | Disposition |
|---------|-------------|
| AI Subtask Decomposition | **Reused** as Stage 1 task-group/task generation |
| LLM Commit Verification | **Reused** as the CI/CD completion resolver |
| Skill-aware assignment | **Promoted** to required (PM and assignee suggestion) |
| Task Health Score | **Kept** as a progress-reporting input |
| Dispute Queue · Auto-Escalation · Overallocation · Scope-Drift | **Deferred** to §3 |

**Confirm** you are happy to park the four rather than delete them.

### Q5 — Project group chat, per-task discussion, or both?
Built today: auto-created project group chat with tree-based tagging rules. The new
spec asks only for per-task discussion between assignee and assigner. The tagging
rules depended on the tree, which is gone.
**Assumption:** per-task discussion **replaces** group chat;
`project_groups` / `project_group_messages` are dropped.
**Decide:** drop group chat, or keep a project-level channel alongside task threads.

### Q6 — Repository and branch strategy
Tasks are GitHub issues and the project documents are repo files, so every project
needs a repo. The branching model was explicitly deferred.
**Assumption:** **one repository per project**, on `projects.github_repo`, entered
by the Manager at creation. Documents are committed to the default branch.
Per-task or per-feature branching is **deferred**.
**Also unanswered:** does TRACE create the repo, or does the Manager supply an
existing one? The docs assume **supply an existing one**.
**Open for later discussion:** a branch per task named from the issue id (the
resolver would key on the branch rather than the commit message); monorepo projects
sharing one repository; PR-merge rather than successful deploy as the completion signal.

### Q7 — What goes in Admin → Reports? *(blocking for that screen only)*
Noted as "to be discussed". Three candidates were named:

| Report | Audience | Open question |
|--------|----------|---------------|
| Project completion report | Manager, Admin | Overlaps `project_report_doc` — the same artefact surfaced, or a separate dashboard? |
| Employee performance report | Admin | Which metrics? Task and CI/CD signals feed scoring today; attendance is recorded but deliberately excluded — should the report use it? |
| Progress report by time interval | Manager, Admin | An interval picker over `gantt_charts` history and task status changes |

**Assumption:** `/admin/reports` ships as a **placeholder**. Nothing else depends on it.

### Q8 — How does someone become a project Member?
The Manager assigns Project Managers; nothing says how Members join.
**Assumption:** **no separate roster step**. A Project Manager may assign any
Employee to a task; doing so creates the `project_assignments` row with role
`Member`, and that grants project visibility.
**If wrong:** add an explicit "add members to project" step before task assignment.

### Q9 — GitHub account mapping
Assigning a task must assign the GitHub issue, which needs a GitHub username per
user. No such field exists today.
**Assumption:** add `github_username` to the user record; Admin maintains it under
Workforce, users can set their own under Settings. If missing, the issue is created
but left unassigned, with a warning.

### Q10 — Who approves leaves now?
Leave approval lived in the Manager HR panel, which is gone. Leaves remain in
Admin → Workforce.
**Assumption:** **Admin** approves leaves in Workforce. Employees have no leave
application UI, so leaves are recorded on their behalf, including via bulk upload.
**If wrong:** employees need a leave-request surface in `/employee`, which the
current panel spec does not include.

### Q11 — Can two Managers share a project?
**Assumption:** **one owning Manager per project**, no co-ownership, and Managers
cannot see each other's projects. Admin sees everything.
