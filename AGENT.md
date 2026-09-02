# 🤖 AGENT.md — TRACE System Architecture & Feature Development Report

This document outlines the complete architectural overview, features implemented, and engineering methodology executed by **Antigravity (Google DeepMind AI Assistant)** to build and finalize the **TRACE** (Task Management, HRMS & AI Task Evaluation) application according to `Overview.md`.

---

## 🌟 Executive Overview

**TRACE** is a state-of-the-art enterprise employee management and task execution system. It bridges bare-minimum **HRMS tracking** (Attendance, Leaves, Shifts, Holidays, Bulk Importing) with an **Infinite Task Tree Engine** featuring automated **GitHub Issue sync**, **LLM Commit Verification**, **Progress Propagation**, and **Tree-Based Role Rule Enforced Chat Channels**.

---

## 🏗️ Technology Stack & System Architecture

| Tier | Technologies |
| :--- | :--- |
| **Frontend** | React 18 (Vite), Glassmorphism Design Tokens, Tailwind/Vanilla CSS, Lucide & React Icons, Axios |
| **Backend API** | FastAPI (Python 3.13), Async SQLAlchemy 2.0, Pydantic V2, WebSockets |
| **Database & Cache** | PostgreSQL 16 (Alembic Migrations), Redis 7 (Broker & Result Backend) |
| **Async Task Queue** | Celery 5.5 (Prefork Worker + Celery Beat Scheduler) |
| **AI / LLM Engine** | OpenAI SDK (Async ChatCompletion & Verification Engine) |
| **Infrastructure** | Docker Compose (PostgreSQL, Redis, pgAdmin, Mailpit SMTP, MinIO S3 Storage) |
| **CLI & DevOps** | `./start.sh` Unified Shell Control Script |

---

## 🚀 Key Features Implemented by the Agent

### 1. 📅 Bare-Minimum HRMS Module & Bulk Importer
* **Daily Attendance System**: Real-time **Clock In** and **Clock Out** with browser GPS geolocation logging, location status (`office`/`remote`), and daily attendance summary metrics.
* **Employee Leaves Management**: Full lifecycle management for leaves (`Casual`, `Sick`, `Earned`, `Unpaid`). Supports applying for leaves, manager approval/rejection workflows, edit, and deletion.
* **Holiday Calendar**: Company & Public holiday manager with full Add, Edit, Delete, and Search functionality.
* **Work Shifts & Schedules**: Work shift management (shift start/end times, break minutes, employee shift assignment).
* **Bulk Dataset Importer**: Generic `/api/v1/hrms/bulk-upload` endpoint and frontend modal supporting **CSV** and **JSON** file uploads for Employees, Attendance, Leaves, Holidays, and Work Shifts.
* **Employee Directory**: Complete employee management dashboard with search, department filtering, status indicators, and full CRUD capability.

---

### 2. 🌳 Infinite Task Tree & Task Execution System (`Overview.md`)
* **Task Hierarchy Roles & Infinite Tree**:
  ```
  Task 1 (Project Manager)
     ↓
  Task 1.1 (Team Lead)  ───  Task 1.2 (Team Lead)
     ↓
  Task 1.1.1 (Ground-Level Member Task)
  ```
  Supports infinite nested child task creation, assigned Project Managers, Team Leads, and Members.
* **GitHub Issues API Integration**: Ground-level member tasks automatically push to GitHub Issues API, generating direct `#GH-xxxx` issue badges and deep links.
* **LLM Commit Verification Engine**: Developers submit git commit hashes/diffs for ground-level tasks; the LLM engine evaluates the commit against task acceptance criteria and updates completion status.
* **Progress Bubble-Up & Auto-Reporting**: When ground-level member tasks complete, the system automatically evaluates parent task completion percentage and triggers progress reports up the hierarchy to Team Leads and Project Managers.
* **Project Chat Channels with Tree Rule Enforcement**:
  * System auto-creates dedicated project chat groups for task hierarchies.
  * Role-based tagging rules:
    * `Member`: Can tag `@TeamLead` or team members.
    * `Team Lead`: Can tag `@ProjectManager` or subtask members.
    * `Project Manager`: Can tag `@Members` or `@TeamLead`.
  * Automatic rule enforcement notice appended if tagging hierarchy bounds are crossed.

---

### 3. 📡 System Observability & Service Monitoring
* **Live Service Monitor**: Dashboard tracking health of API, PostgreSQL, Redis, Celery Worker, Celery Beat, Mailpit SMTP, MinIO Storage, LLM Config, and WebSockets.
* **Celery Task Discovery & Polling**: Fixed task discovery by registering `imports=["app.tasks"]` in `celery_app.py`. Implemented polling mechanism (`/api/v1/services/task/{id}/result` every 1.5s) so mail sending and file uploads cleanly transition from **"Queued"** to **"Completed"**.

---

### 4. 🛠️ Unified CLI Management Script (`./start.sh`)
Centralized command-line utility for managing the entire TRACE environment:
- `./start.sh start` — Launches Docker containers, checks Python dependencies, starts FastAPI backend, Celery worker, Celery beat, and Vite frontend.
- `./start.sh stop` — Gracefully terminates backend processes and stops Docker containers.
- `./start.sh restart` — Performs a complete clean restart of all services.
- `./start.sh migrate` — Runs database migrations via Alembic.
- `./start.sh status` — Checks running status of containers, processes, and ports.

---

## 🛠️ How the AI Agent Developed the Project

1. **System Analysis & Requirement Extraction**:
   - Read and analyzed `Overview.md` to extract explicit requirements: bare-minimum HRMS, task hierarchy roles, infinite subtasks, GitHub issue pushing, LLM verification, progress reporting, tree-based chat rule enforcement, and bulk dataset importing.

2. **Backend Database Model & Schema Expansion**:
   - Created `backend/app/models/hrms.py` (`Leave`, `Holiday`).
   - Extended `backend/app/models/task.py` with hierarchical fields (`project_manager_id`, `team_lead_id`, `task_level_role`, `github_issue_id`, `commit_verified`) and added `ProjectGroup` & `ProjectGroupMessage` models.
   - Updated `backend/app/models/__init__.py` to expose all models to SQLAlchemy & Alembic.

3. **API Endpoints & Business Logic**:
   - Built `backend/app/api/v1/hrms.py` (Leaves, Holidays, Shifts CRUD & Bulk Importer).
   - Enhanced `backend/app/api/v1/tasks.py` (Tree hierarchy endpoint `/tasks/tree/hierarchy`, `/push-github`, `/verify-commit`, `/evaluate-tree`, and `/groups/list`).
   - Mounted routes into `backend/app/api/v1/router.py`.

4. **Database Migration & Seeding**:
   - Executed SQL ALTER statements and database table initializations.
   - Enhanced `backend/app/seeds.py` to seed sample task tree structures (Project Manager → Team Lead → Member), public holidays, work schedules, and default admin credentials.

5. **Frontend UI Components & Design System**:
   - Created `frontend/src/api/hrms.js` and updated `frontend/src/api/tasks.js`.
   - Built a unified `AttendancePage.jsx` supporting Attendance Clock-In/Out, Leaves, Holidays, Shifts, and Bulk Upload modals with full Add/Edit/Delete capabilities.
   - Built an interactive `TasksPage.jsx` featuring Infinite Task Tree view, Kanban board, Tree Chat channels with rule enforcement, GitHub issue badges, LLM verification modal, and full task CRUD.
   - Built `EmployeesPage.jsx` with full employee CRUD, search, and department filters.
   - Fixed `ServiceMonitor.jsx` task polling mechanism.

6. **End-to-End Verification**:
   - Restarted full service stack with `./start.sh restart`.
   - Verified PostgreSQL database tables, seed script execution, FastAPI endpoint responses, and Celery task execution.

---

## 🔑 Default Credentials & Access Endpoints

- **Frontend Application**: `http://localhost:5173`
- **FastAPI API Documentation**: `http://localhost:8000/docs`
- **Mailpit SMTP Console**: `http://localhost:8025`
- **MinIO Object Storage Console**: `http://localhost:9001`
- **pgAdmin**: `http://localhost:5050`
- **Admin Account**: `admin@trace.com` / `Admin@123`

---

*Generated by Antigravity AI — Pair-programmed with the USER for TRACE.*
