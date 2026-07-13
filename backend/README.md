# TRACE - Task and Resource Attendance and Comprehensive Evaluation System

> AI-powered Attendance, Task Management, and Productivity Evaluation System

## 🚀 Tech Stack

| Component | Technology |
|---|---|
| Backend Framework | FastAPI (Python) |
| ASGI Server | Uvicorn |
| Database | PostgreSQL |
| ORM | SQLAlchemy + Alembic |
| Authentication | JWT (PyJWT) + bcrypt |
| Background Tasks | Celery + Redis |
| Containerization | Docker + Docker Compose |

## 📁 Project Structure

```
├── app/
│   ├── main.py             # FastAPI app factory
│   ├── config.py            # Settings (pydantic-settings)
│   ├── database.py          # Async SQLAlchemy engine
│   ├── dependencies.py      # JWT auth dependency
│   ├── exceptions.py        # Custom exceptions
│   ├── middleware.py         # CORS, logging
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic schemas
│   ├── api/v1/              # Versioned API routers
│   ├── services/            # Business logic layer
│   ├── core/                # Security, RBAC, geolocation
│   └── utils/               # Helpers
├── alembic/                 # Database migrations
├── tests/                   # pytest test suite
├── docker-compose.yml       # Local dev environment
├── Dockerfile               # Production image
└── requirements.txt         # Python dependencies
```

## 🏃 Quick Start

### Option 1: Docker (Recommended)
```bash
docker compose up -d
```

### Option 2: Local Development
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis (via Docker)
docker compose up -d db redis

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login with JWT |
| POST | `/api/v1/auth/refresh` | Refresh token |
| GET | `/api/v1/users/me` | Current user profile |
| GET | `/api/v1/users` | List all users |
| POST | `/api/v1/attendance/checkin` | GPS check-in |
| POST | `/api/v1/attendance/checkout` | Check-out |
| POST | `/api/v1/tasks` | Create task |
| GET | `/api/v1/tasks` | List tasks |
| POST | `/api/v1/tasks/{id}/timer/start` | Start timer |
| POST | `/api/v1/tasks/timer/{id}/stop` | Stop timer |

## 📚 API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 Testing

```bash
pytest tests/ -v
```
