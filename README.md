# TRACE — Full-Stack Monorepo

> **T**ask and **R**esource **A**ttendance and **C**omprehensive **E**valuation

AI-powered workforce management system with geo-fenced attendance, task tracking, and productivity scoring.

---

## Project Structure

```
TRACE/
├── backend/              # FastAPI backend (Python)
│   ├── app/              # Application package
│   │   ├── api/v1/       # REST API endpoints
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   ├── core/         # Security, RBAC
│   │   └── utils/        # Helpers
│   ├── alembic/          # Database migrations
│   ├── tests/            # Pytest test suite
│   ├── Dockerfile        # Backend container
│   ├── requirements.txt  # Python dependencies
│   └── .env              # Backend environment variables
│
├── frontend/             # React frontend (Vite)
│   ├── src/
│   │   ├── api/          # Axios client & service modules
│   │   ├── layouts/      # DashboardLayout, Sidebar, Header
│   │   ├── pages/        # Route-level page components
│   │   └── assets/       # Static assets
│   ├── Dockerfile        # Frontend container
│   ├── package.json      # Node dependencies
│   └── vite.config.js    # Vite configuration
│
├── docker-compose.yml    # Root orchestration (all services)
├── .env                  # Root env (DB creds, port mappings)
└── .gitignore            # Root gitignore
```

## Quick Start

### With Docker (recommended)

```bash
# Start all services
docker compose up --build

# Access:
#   Frontend  → http://localhost:5173
#   Backend   → http://localhost:8000
#   API Docs  → http://localhost:8000/docs
```

### Without Docker (local dev)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Services

| Service       | Port  | Description                     |
|---------------|-------|---------------------------------|
| Frontend      | 5173  | React (Vite) dev server         |
| Backend API   | 8000  | FastAPI REST API                |
| PostgreSQL    | 5432  | Primary database                |
| Redis         | 6379  | Celery broker                   |
| Celery Worker | —     | Background task processing      |
| Celery Beat   | —     | Periodic task scheduler         |
# trace
