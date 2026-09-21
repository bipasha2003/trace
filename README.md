# TRACE

AI-driven project and task management.

A manager uploads a project's requirement documents. The AI writes the project
documentation, breaks it into task groups, builds a Gantt chart, and suggests who
should run it. Tasks are GitHub issues, and CI/CD marks them complete.

---

## Setup

**Requirements:** Docker, Docker Compose, Python 3.13+, Node 20+.

```bash
git clone <repo-url> trace
cd trace
cp .env.example .env
./start.sh start
./start.sh migrate
```

Open http://localhost:5173 and sign in with `admin@trace.com` / `Admin@123`.

### Commands

| Command | Does |
|---------|------|
| `./start.sh start` | Start everything |
| `./start.sh stop` | Stop everything |
| `./start.sh restart` | Restart everything |
| `./start.sh migrate` | Run database migrations |
| `./start.sh status` | Show what is running |

### Running the halves separately

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install && npm run dev
```

---

## Who uses what

| Role | Goes to | Does |
|------|---------|------|
| Admin | `/admin` | Manages all data, staff records, system configuration and monitoring |
| Manager | `/manager` | Creates projects, assigns project managers, tracks progress |
| Employee | `/employee` | Runs projects as a project manager, or works tasks as a member |

Signing out returns you to the public landing page at `/`.

---

## Services

| Service | URL | Purpose |
|---------|-----|---------|
| App | http://localhost:5173 | The application |
| API docs | http://localhost:8000/docs | Interactive API reference |
| pgAdmin | http://localhost:5050 | Database admin |
| Mailpit | http://localhost:8025 | Catches all outgoing email |
| MinIO | http://localhost:9001 | File storage console |

PostgreSQL runs on port 5433 externally (5432 inside Docker); Redis on 6379.

---

## Configuration

Copy `.env.example` to `.env` for ports and credentials. Mail, AI provider, GitHub
and CI/CD settings are changed in the app under **Admin → Configuration** — no
redeploy needed.

---

## Documentation

| File | For |
|------|-----|
| [`AGENTS.md`](AGENTS.md) | Anyone writing code |
| [`docs/PROJECT.md`](docs/PROJECT.md) | What the system is: roles, panels, schema, UI |
| [`docs/CORE.md`](docs/CORE.md) | How the AI automation works |
| [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) | Build phases |
| [`docs/PLANNING.md`](docs/PLANNING.md) | Decisions, open questions, future work |
