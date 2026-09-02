# Development Services

## ✅ Implemented Services

### Infrastructure (Docker Compose)
- **PostgreSQL** — Database (port 5433)
- **Redis** — Celery broker + cache (port 6379)
- **pgAdmin 4** — Auto-configured DB admin UI (port 5050)
- **Mailpit** — SMTP catch-all + Web UI, volume mounted (ports 1025/8025)
- **MinIO** — S3-compatible object storage + Console (ports 9000/9001)

### Backend Services
- **WebSocket** — Real-time chat via FastAPI WebSocket endpoint
- **Celery Worker** — Background task processing
- **Celery Beat** — Scheduled task execution
- **LLM** — OpenAI SDK with dynamic model selection

### Celery-Powered Tasks
- **Mail Send** — Email via Mailpit SMTP (Celery task)
- **File Upload** — Upload to MinIO (Celery task)
- **LLM Chat** — OpenAI SDK call (Celery task)

### Frontend — Service Monitor
- System icon (♥ monitor) in Header top-right
- Full-screen overlay with 9 health cards:
  - API Health, DB Health (+ pgAdmin link), Redis Health
  - Celery Worker Health, Celery Beat Health
  - WebSocket Chat (interactive real-time chat)
  - Mailpit (send test email + Mailpit UI link)
  - MinIO (test file upload + MinIO Console link)
  - LLM Chatbox (test OpenAI SDK via Celery)

## Service URLs
| Service   | URL                          |
|-----------|------------------------------|
| Frontend  | http://localhost:5173        |
| Backend   | http://localhost:8000        |
| API Docs  | http://localhost:8000/docs   |
| pgAdmin   | http://localhost:5050        |
| Mailpit   | http://localhost:8025        |
| MinIO     | http://localhost:9001        |
