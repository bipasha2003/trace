# AGENTS.md — TRACE

> Read this first, every session. Then read the **handoff** at the top of
> [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) — where the build stands, what is
> next, and the traps on this machine — then [`docs/PROJECT.md`](docs/PROJECT.md).

---

## ⚠️ The one rule that is never optional

**Every time you implement, modify, or remove a feature, you MUST update the
documentation in the same change.** Not afterwards, not in a follow-up, not "when
it settles" — in the same change, before you report the work as done.

Code and docs drift apart in one commit and take ten to reconcile. These documents
are the only thing telling the next agent what this system is supposed to be; a doc
that lies is worse than no doc, because it will be believed.

**What to update, every time:**

| You did this | Update this |
|--------------|-------------|
| Implemented, reworked or removed a feature | [`docs/PROJECT.md`](docs/PROJECT.md) §24 — flip its status (✅ 🔄 🔲 ❌ 💤) |
| Added, changed or removed a table or column | [`docs/PROJECT.md`](docs/PROJECT.md) Part 2 |
| Added, changed or removed an endpoint | §2 of this file, and [`docs/PROJECT.md`](docs/PROJECT.md) §24 |
| Changed a route, page or panel | [`docs/PROJECT.md`](docs/PROJECT.md) Part 3 |
| Changed anything about the AI pipeline, Gantt, project documents or completion | [`docs/CORE.md`](docs/CORE.md) — **this one first, before writing the code** |
| Completed phase work | [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) |
| Made a non-obvious decision, or chose between two reasonable designs | [`docs/PLANNING.md`](docs/PLANNING.md) §2 (decision) and §5 (agent log) — say what you chose **and why it was not the obvious choice** |
| Answered, or newly discovered, an open question | [`docs/PLANNING.md`](docs/PLANNING.md) §6 |
| Rejected an approach after considering it | [`docs/PLANNING.md`](docs/PLANNING.md) §4, so nobody re-proposes it |
| Changed setup, commands, ports or user-facing behaviour | [`README.md`](README.md) |
| Established a new convention or hit a trap worth naming | This file, §4 or §7 |
| Finished a session, a phase, or stopped part-way | [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) **Handoff** — phase table, test count, environment traps, known gaps. The next agent starts there |

**If a change makes a document wrong, fixing that document is part of the task —
not a separate one.** If the spec itself needs to change, change the spec *first*,
then write code to match it. Never let the code silently redefine the design.

A task is not complete until the docs describe what the code now does.

---

## 0. Before you write any code

1. **[`docs/PROJECT.md`](docs/PROJECT.md) is authoritative.** If the codebase, a
   comment, or your memory of this project contradicts it, they are what is wrong.
2. **If the task touches AI, the Gantt, project documents, or task completion,
   read [`docs/CORE.md`](docs/CORE.md) in full first.** That is the core feature and
   it has rules that override normal judgement.
3. **Check [`docs/PLANNING.md`](docs/PLANNING.md) §6** for open questions in your
   area. Each states the assumption currently in force — build to it, do not
   silently invent a different one.
4. **A large part of the current code is scheduled for removal.**
   [`docs/PROJECT.md`](docs/PROJECT.md) §24 marks it ❌. Do not extend or polish it.
5. **Never drop a table without confirmation.** In particular the workforce record
   set — `attendance` and `work_schedules` included — is **retained** and
   Admin-owned. Only its UI was removed.

6. **Documentation is part of every change** — see the rule at the top of this
   file. Work that ships without its doc update is not finished.

### Document map
| File | Purpose |
|------|---------|
| `AGENTS.md` | **This file** — conventions, stack, API map, patterns |
| [`README.md`](README.md) | End-user overview and setup |
| [`docs/PROJECT.md`](docs/PROJECT.md) | What TRACE is: roles, panels, schema, UI, feature status |
| [`docs/CORE.md`](docs/CORE.md) | The AI automation system — the core feature |
| [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) | Build phases 0–9 |
| [`docs/PLANNING.md`](docs/PLANNING.md) | Journey, decisions, rejected concepts, deferred work, open questions |

---

## 1. Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vite + React (JSX) |
| UI | shadcn/ui — preset `b1tNnRXF5` (`base-mira`) |
| CSS | Tailwind CSS v4, OKLCH design tokens only |
| Icons | `lucide-react` **only** |
| Toasts | `sonner` |
| Backend | FastAPI + async SQLAlchemy 2.0 + Pydantic V2 |
| Database | PostgreSQL, Alembic migrations |
| Queue | Redis + Celery 5 (worker + beat) |
| Object storage | MinIO — project source files |
| Document storage | GitHub repo files — all generated markdown |
| Mail | Mailpit SMTP |
| AI | OpenAI SDK; model and credentials from `system_settings`, `.env` fallback |
| Auth | JWT access token in `localStorage` |

---

## 2. API surface

Base URL `http://localhost:8000/api/v1`, proxied by Vite.

### Built (Phase 3)

Platform role on the route, then the caller's project role from
`app/core/project_access.py` — never re-derived inline.

```
GET    /projects                             projects visible to the caller (+ stats, PMs, my_role)
POST   /projects                             create (Manager)
GET    /projects/activity                    recent task changes across visible projects
GET    /projects/{id}                        detail: documents, source files, stats
PATCH  /projects/{id}                        edit (owner Manager); 'Evaluating' is not settable
DELETE /projects/{id}                        owner; refused while tasks are open
POST   /projects/{id}/source-files           multi-file → MinIO + text extraction; rejects reported
DELETE /projects/{id}/source-files/{fid}     owner
GET    /projects/{id}/assignments            team with project roles
POST   /projects/{id}/assignments            appoint Project Manager (owner)
DELETE /projects/{id}/assignments/{uid}      remove PM (owner); keeps them as Member if they hold tasks
GET    /projects/{id}/candidates             active Employees (owner or PM)
GET|POST          /projects/{id}/task-groups             list · create (PM)
PATCH|DELETE      /projects/{id}/task-groups/{gid}       PM; delete refused while it has tasks
GET    /projects/{id}/tasks                  list (?task_group_id=, ?mine=true)
POST   /projects/{id}/tasks                  create task + GitHub issue (PM); 503 without a token
GET    /tasks/mine                           my open tasks across projects (Employee)
GET    /tasks/{id}                           detail + can_edit + allowed_statuses
PATCH  /tasks/{id}                           details only (PM) — never status
PATCH  /tasks/{id}/assign                    assign / unassign + GitHub assignees (PM)
PATCH  /tasks/{id}/status                    completion authority enforced HERE
DELETE /tasks/{id}                           soft delete + close issue as not planned (PM)
GET    /tasks/health-summary                 Task Health totals (Admin)
POST   /tasks/compute-health                 enqueue health recompute (Admin)
```

### To build

| Module | Prefix | Purpose |
|--------|--------|---------|
| GitHub settings (Phase 3a) | `/admin/settings/github` | Owner + write-only token + test — [`docs/CORE.md`](docs/CORE.md) §4.1 |
| Gantt | `/projects/{id}/gantt` | Latest chart + version history |
| Discussions | `/tasks/{id}/discussions` | Per-task threads |
| Notifications | `/notifications` | List, mark read, unread count |
| Settings | `/admin/settings` | `system_settings` CRUD + connection tests |
| Webhooks | `/webhooks/cicd` | HMAC-signed CI/CD receiver |

```
GET   /admin/settings/github                 org, committer; token only as "set / not set"
PUT   /admin/settings/github                 token is write-only
POST  /admin/settings/github/test            token valid · organization visible
POST  /projects/{id}/evaluate                enqueue evaluate_project
GET   /projects/{id}/evaluate/status         job state
GET   /projects/{id}/suggest-managers        AI-ranked PM candidates
GET   /projects/{id}/tree                    graph payload
GET   /projects/{id}/gantt                   latest chart version
PUT   /projects/{id}/doc                     edit project_doc → triggers re-eval
GET   /projects/{id}/tasks/suggest-assignees AI-ranked Members
POST  /webhooks/cicd                         CI/CD → AI completion resolution
```

### Keep

| Module | Prefix | File |
|--------|--------|------|
| Auth | `/auth` | `api/v1/auth.py` — `register` is public but only ever creates an `Employee`; Admin / Manager accounts need an Admin token |
| Users | `/users` | `api/v1/users.py` |
| Employees + designations | `/employees` | `api/v1/employees.py` |
| HRMS (leaves, holidays, bulk upload) | `/hrms` | `api/v1/hrms.py` |
| Attendance + shifts **records** (Admin) | `/attendance`, `/hrms` | Re-homed under Workforce |
| Admin all-tables CRUD | `/admin` | `api/v1/admin.py` |
| Services / health / WS / MinIO / mail / LLM | `/services` | `api/v1/services.py` — Admin-only, except `/services/task/{id}/result`, which any signed-in role may poll |

### Remove

| Endpoint | Why |
|----------|-----|
| `/attendance` clock-in / clock-out / geo-fence | No employee HR self-service. The **read + CRUD** endpoints stay |
| `/master/roles`, `/master/menus`, `/master/menu-permissions` | Dynamic roles and matrix removed |
| `/tasks/groups/*` | Group chat replaced by discussions |
| `/tasks/tree/hierarchy`, `/tasks/{id}/evaluate-tree` | Infinite tree removed |
| `/tasks/disputes*`, `/tasks/overallocations` | Deferred |
| Legacy `/tasks` CRUD, `/tasks/{id}/push-github`, `/verify-commit`, timers, comments | Removed in Phase 3: generic `PATCH` let anyone complete a task; push-github faked URLs. Replaced by the routes above; discussions return in Phase 7 |

---

## 3. Frontend structure

```
frontend/src/
  layouts/
    AdminLayout.jsx        ← sidebar shell, static menu
    ManagerLayout.jsx      ← topbar only + project selector
    EmployeeLayout.jsx     ← topbar only + project selector
  components/
    ui/                    ← shadcn-generated, NEVER hand-edit (Base UI: `render`, not `asChild`)
    ProjectSelector.jsx    ← topbar selector; the URL is the selected project
    project/               ← ProjectOverview · TaskBoard · TeamPanel · status badges · NotYetAvailable
    ProjectTreeGraph.jsx
    GanttChart.jsx
    NotificationBell.jsx
    ServiceMonitor.jsx
  pages/
    LandingPage.jsx · LoginPage.jsx · ForbiddenPage.jsx
    admin/    ControlPanelPage · WorkforcePage · MonitorPage · ConfigurationPage · ReportsPage
    manager/  ManagerDashboardPage · ProjectCreatePage · ProjectDetailPage
    employee/ EmployeeDashboardPage · ProjectDetailPage · TaskDetailPage
  contexts/
    AuthContext.jsx        ← JWT + platform role
    ThemeContext.jsx
  lib/project.js           ← apiError, formatDate, isOverdue …
  api/                     ← one module per backend router
```

---

## 4. Non-negotiable conventions

**Backend**
- Every LLM call is a Celery task. A route enqueues and returns a job id; it never
  awaits the model.
- Every LLM response is validated against a declared JSON schema. Retry on parse
  failure; never persist unvalidated output.
- Authorisation is two-layer: platform role on the route, then project role via
  `project_assignments`. Never rely on the frontend to hide a capability.
  **Every new route declares a guard** (`require_admin`, `require_roles(...)` or
  `require_any_role` from `app/core/permissions.py`). The only unauthenticated
  routes are `/health` and `/auth/{login,refresh,register}`.
- **GitHub:** every call goes through `app/services/github_service.py`; every
  credential through `resolve_setting()` (database, then `.env`). Secrets are
  **write-only** — no API ever returns one. Tests use the `fake_github` fixture;
  an autouse fixture blocks real GitHub and MinIO in every test.
- A task and its GitHub issue change together or not at all: call GitHub *before*
  committing, and roll back explicitly if it fails.
- Responses tell the UI what the caller may do (`can_edit`, `allowed_statuses`),
  derived from the same `ProjectAccess` check the API enforces. The UI never
  re-derives authority.
- **Completion authority is enforced in the API layer.** A Member calling
  `PATCH /tasks/{id}/status` with `Completed` gets a 403, always.
  ([`docs/CORE.md`](docs/CORE.md) §7)
- Schema changes ship as Alembic revisions, one concern per revision. **Alembic is
  the only thing that creates tables** — never `Base.metadata.create_all` in app
  code; `tests/test_migrations.py` fails if it comes back.
- Every change ships with tests (`backend/tests/`). New routes get a row in the
  role matrix in `tests/api/v1/test_route_guards.py`; the static audit there
  already fails any route without a guard.
- Celery tasks must be registered — `imports=["app.tasks"]` in `celery_app.py`, or
  discovery silently fails.

- **There is one env file: the repo-root `.env`** (template `.env.example`).
  Compose, `start.sh`, the backend and the Vite config all read it — never add a
  `backend/.env` or `frontend/.env`. The backend *derives* `DATABASE_URL`,
  `REDIS_URL`, `MINIO_*` and `SMTP_PORT` from the Compose keys (`POSTGRES_*`,
  `DB_PORT`, `MINIO_ROOT_*`, …); add a new key once, never a second copy of a value.
- **`APP_ENV` (`local` | `production`) is checked in exactly two places:**
  `Settings.is_production` in `backend/app/config.py` for all Python, and
  `is_production` in `start.sh` for process orchestration. Never compare
  `APP_ENV` anywhere else — ask those. The frontend never branches on it.
- Production refusals are raised from `get_settings()`, not a pydantic validator —
  a `ValidationError` echoes every settings value, secrets included.

**Frontend**
- `lucide-react` icons only. No `react-icons`.
- shadcn components and Tailwind tokens only. No glassmorphism, no raw colour
  utilities (`text-violet-400`, `bg-white/10`), no custom CSS files.
- `components/ui/**` is generated — never hand-edit it.
- Every page responsive and correct in both themes.

---

## 5. Patterns

### Page shell
```jsx
<div id="page-id" className="space-y-6 max-w-[1400px]">
  <div className="flex items-center justify-between">
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Page Title</h1>
      <p className="text-sm text-muted-foreground">Subtitle</p>
    </div>
    <Button onClick={refresh} variant="outline" size="icon"><RefreshCw /></Button>
  </div>
</div>
```

### Role-guarded route
```jsx
<Route element={<RoleRoute role="Manager"><ManagerLayout /></RoleRoute>}>
  <Route path="/manager" element={<ManagerDashboardPage />} />
  <Route path="/manager/projects/:id" element={<ProjectDetailPage />} />
</Route>
```

### Enqueue-and-poll — every AI action
Celery job results are polled via `GET /api/v1/services/task/{job_id}/result`
(~1.5s interval), the same mechanism the Service Monitor uses.
```jsx
const { data } = await projectsApi.evaluate(projectId)   // → { job_id }
const poll = setInterval(async () => {
  const { data: s } = await projectsApi.evaluateStatus(projectId)
  if (s.state === 'SUCCESS') { clearInterval(poll); refresh(); toast.success('Project evaluated') }
  if (s.state === 'FAILURE') { clearInterval(poll); toast.error(s.error) }
}, 1500)
```

---

## 6. Commands

```bash
./start.sh start     # full stack
./start.sh stop
./start.sh restart
./start.sh migrate   # alembic
./start.sh status
./start.sh set-password <email>

cd frontend && npm run dev
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
cd backend && .venv/bin/python -m pytest -q   # own DB `trace_test`, migrated by Alembic
```

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | `admin@trace.com` / `Admin@123` |
| API docs | http://localhost:8000/docs | — |
| pgAdmin | http://localhost:5050 | `admin@trace.com` / `Admin@123` |
| Mailpit | http://localhost:8025 | — |
| MinIO console | http://localhost:9001 | `minioadmin` / `minioadmin` |

---

## 7. Anti-patterns

```jsx
// ❌ never
import { MdDashboard } from 'react-icons/md'
<div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl">
<span className="text-violet-400 bg-violet-500/20">

// ✅ always
import { LayoutDashboard } from 'lucide-react'
<Card><CardContent>…</CardContent></Card>
<Badge variant="secondary">label</Badge>
```

```python
# ❌ never — blocks the request, unparseable output
result = await openai.chat.completions.create(...)
return {"text": result.choices[0].message.content}

# ✅ always — queued, schema-validated
job = evaluate_project.delay(project_id)
return {"job_id": job.id}
```

```python
# ❌ never — builds tables no revision knows about; a fresh DB can't reach head
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)

# ✅ always — Alembic owns the schema; start.sh runs `alembic upgrade head`
```

```python
# ❌ never — trusts the client about who may complete a task
task.status = payload.status

# ✅ always — authority enforced server-side
if payload.status == "Completed" and not caller_may_complete(user, task):
    raise HTTPException(403, "Completion is confirmed by CI/CD or the Project Manager")
```
