# agent.md — TRACE Development Context

> This file is your development context. Read it at the start of every session.
> **Do not use this for project feature tracking** — that lives in `project.md`.

---

## The Golden Rule

**As we develop, ALWAYS update the documentation (`project.md`, `agent.md`, `ui.md`).**
1. **`project.md`**: Update feature status (mark completed as ✅, partial as 🔶), record architectural decisions, and document new endpoints/modules.
2. **`agent.md`**: Keep backend route references, API client maps, and dev workflows current.
3. **`ui.md`**: Document newly added UI components or page layouts.

---

## Tech Stack (Quick Reference)

| Layer | Technology |
|-------|-----------|
| Frontend | Vite + React (JSX) |
| UI Library | shadcn/ui — preset `b1tNnRXF5` (`base-mira` style) |
| CSS | Tailwind CSS v4, OKLCH design tokens |
| Icons | `lucide-react` **only** |
| Notifications | `sonner` Toaster |
| Backend | FastAPI + async SQLAlchemy 2.0 + Pydantic V2 |
| Database | PostgreSQL (Alembic migrations) |
| Cache / Queue | Redis + Celery 5 (Worker + Beat) |
| Object Storage | MinIO (S3-compatible) |
| Mail | Mailpit (SMTP catch-all) |
| AI / LLM | OpenAI SDK (via Celery task) |
| Auth | JWT access token in `localStorage` |

---

## Backend API Reference

**Base URL:** `http://localhost:8000/api/v1` (proxied via Vite)

| Module | Route Prefix | File |
|--------|-------------|------|
| Auth | `/auth` | `api/v1/auth.py` |
| Users | `/users` | `api/v1/users.py` |
| Employees + Designations | `/employees` | `api/v1/employees.py` |
| Attendance | `/attendance` | `api/v1/attendance.py` |
| HRMS (Leaves / Holidays / Shifts) | `/hrms` | `api/v1/hrms.py` |
| Master (Roles, Dynamic Menus, Permission Matrix) | `/master` | `api/v1/master.py` |
| Tasks (Tree, GitHub, LLM, Groups) | `/tasks` | `api/v1/tasks.py` |
| Productivity + Reports | `/productivity`, `/reports` | `api/v1/productivity.py` |
| Services / Health / WS / MinIO / Mail / LLM | `/services` | `api/v1/services.py` |

### Key Master API Endpoints
- `GET /api/v1/master/roles` & `POST /api/v1/master/roles` & `DELETE /api/v1/master/roles/{id}`: Dynamic system role management.
- `GET /api/v1/master/menus` & `POST /api/v1/master/menus` & `DELETE /api/v1/master/menus/{id}`: Dynamic navigation module registration.
- `GET /api/v1/master/menu-permissions` & `POST /api/v1/master/menu-permissions`: Dynamic role-menu access matrix.

### Key Task Endpoints
```
GET  /tasks/tree/hierarchy         → full infinite tree
POST /tasks/                       → create task
PUT  /tasks/{id}                   → update task
DELETE /tasks/{id}                 → delete task
POST /tasks/{id}/push-github       → push to GitHub Issues
POST /tasks/{id}/verify-commit     → LLM commit verification
GET  /tasks/{id}/evaluate-tree     → tree evaluation report
GET  /tasks/groups/list            → project chat groups
POST /tasks/groups/{id}/messages   → post to group chat
```

---

## File Structure (Frontend)

```
frontend/src/
  components/
    ui/                  ← shadcn-generated (NEVER manually edit)
    ServiceMonitor.jsx   ← infrastructure health overlay
  layouts/
    DashboardLayout.jsx  ← SidebarProvider + SidebarInset
    Sidebar.jsx          ← shadcn Sidebar primitives + NavLink
    Header.jsx           ← SidebarTrigger + search + theme toggle
  pages/
    LoginPage.jsx
    DashboardPage.jsx
    EmployeesPage.jsx
    AttendancePage.jsx
    TasksPage.jsx
    ProductivityPage.jsx
    FilesPage.jsx
    SettingsPage.jsx
    NotFoundPage.jsx
  contexts/
    AuthContext.jsx      ← JWT auth, user state
    ThemeContext.jsx     ← dark/light via .dark class
  api/
    index.js             ← re-exports all API modules
    client.js            ← axios base instance
    services.js          ← service monitor API
  lib/
    utils.js             ← cn(), getInitials(), timeAgo()
  index.css              ← shadcn token definitions ONLY
```

---

## Development Commands

```bash
# Full stack (recommended)
./start.sh start

# Stop everything
./start.sh stop

# DB migrations
./start.sh migrate

# Service status
./start.sh status

# Frontend only
cd frontend && npm run dev

# Backend only (from backend/)
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

---

## Default Credentials & URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | — |
| API Docs | http://localhost:8000/docs | — |
| pgAdmin | http://localhost:5050 | admin@trace.com / Admin@123 |
| Mailpit | http://localhost:8025 | — |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| App Login | http://localhost:5173 | admin@trace.com / Admin@123 |

---

## Layout Patterns

### Sidebar Navigation (NavLink integration)
```jsx
<SidebarMenuButton
  render={<NavLink to="/dashboard" />}
  isActive={location.pathname === '/dashboard'}
  tooltip="Dashboard"
>
  <LayoutDashboard />
  <span>Dashboard</span>
</SidebarMenuButton>
```

### Standard Page Shell
```jsx
<div id="page-id" className="space-y-6 max-w-[1400px]">
  {/* Page header */}
  <div className="flex items-center justify-between">
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Page Title</h1>
      <p className="text-sm text-muted-foreground">Subtitle</p>
    </div>
    <Button onClick={refresh} variant="outline" size="icon"><RefreshCw /></Button>
  </div>

  {/* Content */}
</div>
```

### Alert (success/error feedback)
```jsx
<Alert variant={msg.type === 'success' ? 'default' : 'destructive'}>
  {msg.type === 'success' ? <CheckCircle className="size-4" /> : <AlertTriangle className="size-4" />}
  <AlertDescription>{msg.text}</AlertDescription>
</Alert>
```

---

## Recent Development Progress & Updates

- **Advanced Roadmap Tier 1 Implementation**:
  - **Task Health Score & Rollup**: Added `health_score`, `health_reason`, and `last_health_check` fields to `Task` model. Added Celery Beat job `compute_task_health_and_escalate` to evaluate due dates, blocker keywords, and single-child worst health tree rollups. Exposed `GET /api/v1/tasks/health-summary` and `POST /api/v1/tasks/{id}/compute-health`.
  - **AI Subtask Decomposition**: Implemented `POST /api/v1/tasks/{id}/suggest-subtasks` invoking OpenAI SDK (with smart rule engine fallback) to generate structured subtask hierarchies, previewed in `TasksPage.jsx` modal with bulk creation capability.
  - **Explainable AI Dispute Queue**: Created `EvaluationDispute` model and endpoints (`POST /api/v1/tasks/dispute`, `GET /api/v1/tasks/disputes`, `PATCH /api/v1/tasks/disputes/{id}`). Integrated a dedicated "Dispute Queue" tab in `TasksPage.jsx` for Team Lead/PM review.
  - **Auto-Escalation Engine**: Triggered automated email alerts via Mailpit (`send_mail_task`) whenever tasks are evaluated as `Red`.
  - **Cross-Tree Overallocation Detection**: Added Celery Beat job `detect_overallocation` and `GET /api/v1/tasks/overallocations` to flag workload conflicts across rotating-role task nodes.
- **Dynamic System Roles**: Implemented database model and API routes (`POST/DELETE /api/v1/master/roles`) allowing dynamic creation and management of system roles. Added dynamic role options in `EmployeesPage.jsx` modal and `MasterPage.jsx`.
- **Dynamic Navigation Modules**: Created `SystemMenu` database model and API endpoints (`POST/DELETE /api/v1/master/menus`) for custom navigation module registration and management.
- **Dynamic Role-Menu Access Matrix**: Integrated dynamic roles and dynamic navigation modules into a real-time permission matrix table in `MasterPage.jsx`.
- **Attendance Page Fix**: Resolved runtime white screen crash in `AttendancePage.jsx` caused by undeclared notification variables (`setActionMsg`, `setBulkMsg`), missing `sonner` toast imports, and added `getDepartments` alias to `employeesApi`.
- **Select Display Formatting**: Updated assign employee select dropdown in `TasksPage.jsx` to render clean employee text (`TRACE-001 — Jane Doe`) instead of raw IDs.

---

## Anti-Patterns

```jsx
// ❌ Never do this
import { MdDashboard } from 'react-icons/md'
<div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl">
<span className="text-violet-400 bg-violet-500/20">

// ✅ Always do this
import { LayoutDashboard } from 'lucide-react'
<Card><CardContent>…</CardContent></Card>
<Badge variant="secondary">label</Badge>
```

---

## Advanced Feature Architecture Rules

- **Async LLM Workers Only:** Wrap all OpenAI SDK calls inside background Celery tasks. Never invoke LLM endpoints synchronously inside FastAPI route handlers.
- **Structured Output Enforced:** Enforce JSON schema responses (`{verdict, confidence, reasoning, evidence}`) for LLM tasks so verdict data can be queried for disputes, drift analysis, and fairness audits.
- **Celery Beat Periodic Jobs:** Batch periodic risk evaluations (Task Health Score, Scope-Drift, Overallocation queries) into scheduled Celery Beat tasks rather than ad-hoc scripts.
- **Additive Schema Design:** Maintain backwards compatibility with the recursive `parent_task_id` task tree.

---

## Document Map

| File | Purpose | Edit? |
|------|---------|-------|
| `project.md` | Feature registry, decisions, plans — **the project mirror** | ✅ Keep updated |
| `roadmap.md` | Advanced Feature Roadmap (Tier 1, Tier 2, Tier 3 proposal) | ✅ Keep updated |
| `agent.md` | This file — your dev context | ✅ Keep updated |
| `ui.md` | shadcn component usage guide | ✅ Update when patterns change |
| `Overview.md` | Original handwritten scope (historical) | ❌ Archive only |
| `Devplopment.md` | Original service notes (reference only) | ❌ Archive only |
| `AGENT.md` | Original agent report (historical) | ❌ Archive only |
| `README.md` | Quick-start guide | Update as needed |
