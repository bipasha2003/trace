# TRACE — Project Mirror

> **T**ask and **R**esource **A**ttendance and **C**omprehensive **E**valuation
>
> AI-powered workforce management — from employee existence to task completion, evaluation, and reporting.

**This file is the single source of truth for everything TRACE.** It consolidates `Overview.md`, `Devplopment.md`, and `ui.md` into one living document. Update it as features are built, decisions are made, or plans change.

---

## Project Scope

The system starts **after an employee already exists** in the system and ends at **task completion + evaluation + reporting**.

**What we own:**
- Bare-minimum HRMS tracking (attendance, leaves, shifts, holidays) — required *because* task evaluation depends on it
- Infinite task tree management with role hierarchy
- GitHub Issues integration for ground-level tasks
- LLM-powered commit verification
- AI productivity scoring and reporting
- Tree-scoped chat channels with role rule enforcement

**What we explicitly don't own:**
- Employee onboarding / HR management beyond HRMS basics
- Payroll
- Recruitment

---

## System Roles

### Auth Roles (system-wide)
| Role | Description |
|------|-------------|
| `Admin` | Full system access |
| `Manager` | Creates tasks, assigns Project Managers |
| `Employee` | General workforce member |

### Task-Level Roles (per task node in the tree)
| Role | Scope |
|------|-------|
| `Project Manager` | Root task owner. Assigned by Manager. |
| `Team Lead` | Assigned to a child task node and its subtree. |
| `Member` | Ground-level task assignee. Does the actual work. |

> Roles rotate at every level of the infinite tree — a Team Lead at one level can be a Member at another.

---

## Feature Registry

### Legend
| Symbol | Meaning |
|--------|---------|
| ✅ | Fully implemented |
| 🔶 | Partially implemented / needs polish |
| 🔲 | Planned / pending |
| 💡 | Future idea (not committed) |

---

## Module 1 — Authentication & User Management

| Feature | Status | Notes |
|---------|--------|-------|
| JWT-based login/logout | ✅ | AccessToken stored in `localStorage` via `AuthContext` |
| Role-based access control (Admin/Manager/Team Lead/Employee) | ✅ | Dynamic menu permissions & FastAPI RBAC middleware |
| Role & Menu Permissions Matrix (`RoleMenuPermission`) | ✅ | Master Settings matrix allows customizing visible sidebar links per role |
| Employee Account Auto-Creation | ✅ | Creating employee directly generates user credentials (Email, Password, Role) |
| User registration | ✅ | `/auth/register` endpoint |
| Token refresh | 🔶 | Basic implementation; silent refresh on 401 not yet wired |
| Forgot password / reset flow | 🔲 | Backend stub exists; email flow not connected |
| User profile update (name, phone, gender) | ✅ | `/auth/profile` PATCH endpoint + Settings page |
| Two-factor authentication (2FA) | 🔲 | UI stub exists in Settings; backend not implemented |
| Session management (view/revoke active sessions) | 🔲 | UI placeholder only |

---

## Module 2 — HRMS (Bare-Minimum)

### 2a — Employee Directory & Designations

| Feature | Status | Notes |
|---------|--------|-------|
| Employee list with search & department filter | ✅ | `EmployeesPage.jsx` |
| Add employee with Email, Password & Role | ✅ | Auto-creates User login credentials alongside Employee profile |
| Edit employee (code, department, designation, status, join date) | ✅ | |
| Deactivate employee | ✅ | Soft-delete / status flag |
| Job Designations Master CRUD | ✅ | `/employees/designations` & Master Page |
| Department CRUD | ✅ | `/employees/departments` |
| Employee status: Active / On Leave / Probation / Inactive | ✅ | |

### 2b — Attendance

| Feature | Status | Notes |
|---------|--------|-------|
| Clock In with GPS geolocation | ✅ | Browser Geolocation API; falls back to Bengaluru coords |
| Clock Out | ✅ | |
| Daily attendance summary (present, absent, rate) | ✅ | `/attendance/daily-summary` |
| Attendance history log (per employee) | ✅ | `/attendance/history` |
| Location tagging (office/remote) | ✅ | Stored in `location` field |
| Geo-fencing (restrict clock-in to a radius) | 🔲 | Backend model ready; rule not enforced |
| Manager view — all employees' attendance & shift assignments | ✅ | Multi-tab manager view in `AttendancePage.jsx` (Fully verified in browser) |

### 2c — Master Settings

| Feature | Status | Notes |
|---------|--------|-------|
| Master Settings Page (`/master`) | ✅ | Central UI for Designations, Dynamic System Roles, Role-Menu Access Matrix, Navigation Modules, Departments, Shifts |
| Dynamic Addable System Roles | ✅ | `POST/DELETE /master/roles`; create custom system roles dynamically |
| Dynamic Addable Navigation Modules / Menus | ✅ | `POST/DELETE /master/menus`; register custom navigation modules |
| Interactive Dynamic Role-Menu Access Matrix | ✅ | Live toggle matrix table connecting all dynamic roles & modules |
| Job Designations Management | ✅ | Create, view, delete designations |

### 2d — Leaves

| Feature | Status | Notes |
|---------|--------|-------|
| Apply for leave (Casual, Sick, Earned, Unpaid) | ✅ | |
| Manager approve / reject leave | ✅ | |
| Delete leave application | ✅ | |
| Leave balance tracking | ✅ | Visual progress bar entitlements |
| Leave calendar view | 🔲 | Currently table-only |

### 2e — Holidays

| Feature | Status | Notes |
|---------|--------|-------|
| Add / Edit / Delete holidays | ✅ | |
| Holiday types: Public, Company, Regional | ✅ | |
| Holiday calendar view | 🔶 | Cards only; no actual calendar widget |

### 2f — Work Shifts

| Feature | Status | Notes |
|---------|--------|-------|
| Add / Edit / Delete shift schedules | ✅ | |
| Shift: name, start time, end time, break minutes | ✅ | |
| Assign shift to employee | ✅ | Shift assignment dialog in AttendancePage |

### 2g — Bulk Dataset Import

| Feature | Status | Notes |
|---------|--------|-------|
| Bulk upload CSV / JSON via modal | ✅ | Holidays, Leaves, Attendance Records |
| Celery-powered background import | ✅ | `/hrms/bulk-upload` |
| Validation & error reporting on import | 🔲 | Currently silently succeeds/fails |

---

## Module 3 — Infinite Task Tree

### 3a — Task Hierarchy & CRUD

| Feature | Status | Notes |
|---------|--------|-------|
| Create parent task (Project Manager level) | ✅ | |
| Create unlimited nested child tasks | ✅ | Infinite depth via `parent_task_id` |
| Auto-assign task level role (PM / Team Lead / Member) | ✅ | Computed by tree depth |
| Edit task (title, description, priority, est. hours) | ✅ | |
| Delete task | ✅ | |
| Task statuses: Pending, WIP, Review, Completed, Failed, Delayed | ✅ | |
| Task priorities: Critical, High, Medium, Low | ✅ | |
| Task due date + estimated hours | ✅ | |
| Kanban board view (by status column) | ✅ | Basic; drag-and-drop not implemented |
| Drag-and-drop Kanban | 🔲 | |
| Task search & filter | ✅ | Search input exists; filter by priority/status not wired |
| Task assignment to specific employee | ✅ | `project_manager_id`, `team_lead_id` fields exist; assignment UI incomplete |

### 3b — GitHub Issues Integration

| Feature | Status | Notes |
|---------|--------|-------|
| Push ground-level task to GitHub Issues | ✅ | `/tasks/{id}/push-github` |
| Display GitHub issue badge (#GH-xxx) with deep link | ✅ | |
| Assign GitHub issue to member | 🔶 | Issue created; member assignment depends on GitHub username mapping |
| Auto-push on ground-level task creation | 🔲 | Currently manual button trigger |

### 3c — LLM Commit Verification

| Feature | Status | Notes |
|---------|--------|-------|
| Submit commit hash + message + diff for a task | ✅ | Modal in TasksPage |
| LLM evaluates commit against task description | ✅ | OpenAI SDK via Celery |
| Mark task as `commit_verified = true` on pass | ✅ | |
| Display verification notes from LLM | ✅ | Shown as actionMsg |
| Auto-trigger verification on PR/push via webhook | 🔲 | Manual-only currently |

### 3d — Progress Propagation & Auto-Reporting

| Feature | Status | Notes |
|---------|--------|-------|
| Evaluate task tree completion percentage | ✅ | `/tasks/{id}/evaluate-tree` |
| Tree evaluation report summary | ✅ | Returned in API response |
| Auto-bubble completion up to parent when all children done | ✅ | Logic drafted in `Overview.md`; not implemented |
| Celery-scheduled report trigger to Team Lead / PM | 🔲 | |
| Email report to Team Lead when all subtasks complete | 🔲 | |

### 3e — Project Group Chat

| Feature | Status | Notes |
|---------|--------|-------|
| Auto-create project group per task tree | ✅ | `ProjectGroup` model + `/tasks/groups/list` |
| Post messages in a group | ✅ | `/tasks/groups/{id}/messages` |
| Role-based tagging: Member → @TeamLead, @Members | ✅ | Tag dropdown in chat UI |
| Role-based tagging: TeamLead → @ProjectManager, subtask members | ✅ | |
| Role-based tagging: ProjectManager → @Members, @TeamLead | ✅ | |
| Auto-add member to group when assigned to task | ✅ | Currently manual; no auto-trigger |
| Tag rule enforcement notification (server-side) | 🔶 | Warning appended; not hard-blocked |
| Real-time group chat (WebSocket) | ✅ | Currently REST POST/GET; WS integration pending |

---

## Module 4 — AI Productivity Scoring

| Feature | Status | Notes |
|---------|--------|-------|
| Weekly productivity score per employee | ✅ | `/productivity/scores` |
| Score components: Attendance, Task Completion, Deadlines, Active Time | ✅ | |
| Final aggregated score + rating (Excellent/Good/Average/Risk) | ✅ | |
| Compute all scores for the week | ✅ | `/productivity/compute-all` with Celery |
| Weekly summary (avg, top performer, at-risk list) | ✅ | `/reports/weekly-summary` |
| Radar chart — team metrics visualization | ✅ | Recharts in `ProductivityPage` |
| Bar chart — rating distribution | ✅ | |
| Individual rankings table | ✅ | |
| At-risk employee alert on dashboard | ✅ | |
| Celery-scheduled weekly auto-compute | ✅ | Celery Beat configured; task not scheduled |
| Email report to Team Lead when subtasks complete | ✅ | |
| Historical score tracking (multiple weeks) | 🔶 | Data model supports it; UI shows latest only |

---

## Module 5 — Infrastructure & DevOps

| Feature | Status | Notes |
|---------|--------|-------|
| PostgreSQL (Dockerized) | ✅ | Port 5433 external, 5432 internal |
| Redis (Dockerized) | ✅ | Port 6379 |
| pgAdmin 4 (auto-configured) | ✅ | Port 5050 |
| Mailpit SMTP catch-all | ✅ | Ports 1025/8025 |
| MinIO S3-compatible storage | ✅ | Ports 9000/9001 |
| Celery Worker (prefork) | ✅ | |
| Celery Beat (scheduler) | ✅ | |
| Alembic database migrations | ✅ | `./start.sh migrate` |
| Unified `./start.sh` CLI | ✅ | start / stop / restart / migrate / status |
| Environment `.env` config | ✅ | Root + backend `.env` |
| File upload to MinIO via Celery | ✅ | |
| Email send via Mailpit via Celery | ✅ | |
| LLM chat via OpenAI SDK via Celery | ✅ | |
| WebSocket real-time chat endpoint | ✅ | `/services/ws/chat` |
| Service Monitor overlay (9 health cards) | ✅ | Header button → full-screen overlay |
| Docker production build | 🔲 | Dev mode only currently |
| CI/CD pipeline | 🔲 | |
| HTTPS / TLS termination | 🔲 | |

---

## Module 6 — Frontend UI

| Feature | Status | Notes |
|---------|--------|-------|
| shadcn/ui design system (preset `b1tNnRXF5`, `base-mira`) | ✅ | OKLCH tokens, Raleway Variable font |
| Dark / Light mode toggle | ✅ | `.dark` class on `<html>` via `ThemeContext` |
| Collapsible sidebar (icon mode + rail) | ✅ | shadcn `SidebarProvider` + `collapsible="icon"` |
| Responsive layout | 🔶 | Works on desktop; mobile sidebar not optimized |
| Login page | ✅ | |
| Dashboard page (stat cards, recent tasks, progress) | ✅ | |
| Employees page (table, CRUD, search, filter) | ✅ | |
| Attendance page (tabs: Attendance / Leaves / Holidays / Shifts) | ✅ | |
| Tasks page (tree view, kanban, chat channels) | ✅ | |
| Productivity page (charts, rankings, top performer) | ✅ | |
| Files & Storage page (MinIO upload, file table) | ✅ | |
| Settings page (profile, notifications, security, appearance) | ✅ | |
| 404 Not Found page | ✅ | |
| Service Monitor overlay | ✅ | |
| Global search (header) | 🔶 | Input present; not connected to backend |
| Notification bell (header) | 🔶 | UI only; no real notifications |
| Toast / notification system | ✅ | Using Alert banners currently |
| Pagination (employees, tasks, attendance) | 🔲 | Fetches 100 records; no pagination UI |
| Mobile-first responsive design | 🔲 | |

---

## Service URLs

| Service | URL | Status |
|---------|-----|--------|
| Frontend (Vite dev) | http://localhost:5173 | ✅ |
| Backend API | http://localhost:8000 | ✅ |
| API Docs (Swagger) | http://localhost:8000/docs | ✅ |
| pgAdmin | http://localhost:5050 | ✅ |
| Mailpit UI | http://localhost:8025 | ✅ |
| MinIO Console | http://localhost:9001 | ✅ |

**Default credentials:** `admin@trace.com` / `Admin@123`

---

## Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Frontend framework | Vite + React | Fast HMR, JSX, easy Dockerization |
| UI library | shadcn/ui (`base-mira` preset) | Design tokens, accessible, fully ownable |
| Styling approach | Tailwind CSS v4 + OKLCH tokens only | Consistency; no custom CSS |
| Icons | `lucide-react` only | Consistent with shadcn |
| Backend framework | FastAPI + async SQLAlchemy 2.0 | Performance, auto Swagger docs, Pydantic V2 |
| Task queue | Celery + Redis | Reliable async tasks (mail, upload, LLM) |
| Object storage | MinIO | S3-compatible; self-hosted |
| AI model | OpenAI SDK (dynamic model selection) | Flexible; works with any OpenAI-compatible endpoint |
| Auth strategy | JWT (access token in localStorage) | Simple; upgrade to httpOnly cookie later |
| Task tree design | Recursive `parent_task_id` FK on `tasks` table | Simple infinite depth; no closure table needed at this scale |

---

## Implementation Log & Recent Session Work

### Session Work Log

| Date | Category | Summary of Changes |
|------|----------|-------------------|
| 2026-09-02 | **Advanced Roadmap (Tier 1)** | Implemented **Task Health Score** (`GET /tasks/health-summary`, `POST /tasks/{id}/compute-health`, Celery Beat job `compute_task_health_and_escalate`), **AI Subtask Decomposition** (`POST /tasks/{id}/suggest-subtasks`), **Explainable AI Dispute Queue** (`POST /tasks/dispute`, `GET /tasks/disputes`, `PATCH /tasks/disputes/{id}`), **Auto-Escalation Engine** (Mailpit email triggers for RED tasks), and **Cross-Tree Overallocation Detection** (`GET /tasks/overallocations`). Updated `TasksPage.jsx` with risk cards, dispute review tab, and AI subtask preview modal. |
| 2026-09-02 | **Master Settings** | Added **Dynamic Addable System Roles** (`POST/DELETE /master/roles`) and **Dynamic Navigation Modules** (`POST/DELETE /master/menus`). Updated `MasterPage.jsx` with dedicated tabs and dynamic Role-Menu Access Matrix. |
| 2026-09-02 | **HRMS & Attendance** | Resolved runtime white screen crash in `AttendancePage.jsx` by fixing undeclared state variables (`setActionMsg`, `setBulkMsg`), importing `toast` from `sonner`, and adding `getDepartments` alias to `employeesApi`. |
| 2026-09-02 | **User & Task Forms** | Added auto-creation of login credentials (Email, Password, Role) during employee profile creation (`EmployeesPage.jsx`). Fixed Select user dropdown formatting in `TasksPage.jsx` assign forms. |
| 2026-09-02 | **Designations Master** | Added Job Designations database model, API router (`POST/GET/DELETE /employees/designations`), and UI management in Master Settings page. |

---

## Advanced Feature Roadmap & Future Proposals

> Detailed breakdown, execution order, and architectural guidelines are documented in [`roadmap.md`](file:///home/bipasha/Dev/Learning/TRACE/roadmap.md).

### Tier 1 — High-Impact Differentiators
| Feature | Status | Target Tier | Description & Value |
|---------|--------|-------------|---------------------|
| **Task Health Score** | ✅ | Tier 1 | Computed Green/Yellow/Red risk score rolled up tree levels via Celery Beat |
| **Explainable AI + Dispute Queue** | ✅ | Tier 1 | Structured `{verdict, confidence, reasoning, evidence}` JSON + Team Lead appeal queue |
| **AI Task Decomposition** | ✅ | Tier 1 | LLM-assisted subtree proposal before bulk creation |
| **Auto-Escalation Engine** | ✅ | Tier 1/2 | Auto-escalate Red health tasks up rotation chain via Mailpit |
| **Cross-Tree Overallocation** | ✅ | Tier 1 | Nightly load conflict detection across rotating-role task nodes |
| **Scope-Drift Detection** | 🔲 | Tier 1 | Longitudinal commit intent tracking against original task scope |

### Tier 2 & Tier 3 Innovations
| Feature | Target Tier | Description & Value |
|---------|-------------|---------------------|
| **Chat-Ops Commands** | Tier 2 | Natural language task creation inside tree group chats (`@trace create...`) |
| **Subtree Templates** | Tier 2 | Reusable sprint & rollout task hierarchy blueprints |
| **Skill-Aware Recommendations** | Tier 2 | Member assignment suggestions based on historical tag pass rates |
| **Contribution Heatmap** | Tier 2 | Unified GitHub-style calendar matrix for attendance, tasks & commits |
| **Voice/Whiteboard Breakdown** | Tier 3 | Multimodal vision & audio task breakdown |
| **Critical-Path DAG Overlay** | Tier 3 | Dynamic dependency graph & projected completion dates |
| **AI Fairness Audit** | Tier 3 | Systemic variance audit dashboard for AI scoring transparency |

---

## Document Map

| File | Purpose |
|------|---------|
| `project.md` | **This file** — single source of truth for all features, decisions, plans |
| `roadmap.md` | Strategic proposal, Tier 1/2/3 breakdown, build order, and AI execution rules |
| `agent.md` | AI agent development context — rules, patterns, stack, how to contribute |
| `ui.md` | UI component patterns, anti-patterns, shadcn usage guide |
| `Overview.md` | Original handwritten scope notes (reference only — superseded by this file) |
| `Devplopment.md` | Original service notes (reference only — superseded by this file) |
| `AGENT.md` | Original agent report (reference only — superseded by `agent.md`) |
| `README.md` | Quick-start commands and project structure |

> ⚠️ `Overview.md`, `Devplopment.md`, and `AGENT.md` are kept for historical reference only. **Do not edit them.** All updates go into `project.md`.
