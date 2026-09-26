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
| `./start.sh migrate` | Run database migrations (`start` also runs them first) |
| `./start.sh status` | Show what is running (and, in production, the public URL's status) |
| `./start.sh set-password <email>` | Set a user's password |

### Running the halves separately

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # settings come from the root .env
alembic upgrade head          # the app never creates tables itself
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install && npm run dev
```

### Tests

```bash
cd backend && .venv/bin/python -m pytest -q
```

Tests use their own database, `trace_test`, created on first run and built with
`alembic upgrade head`. They never touch your dev data. The suite also migrates a
throwaway empty database to prove a fresh checkout can reach the latest schema.
Point it elsewhere with `TEST_DATABASE_URL`.

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

PostgreSQL runs on port 5433 externally (5432 inside Docker), so it does not clash
with a Postgres already installed on the machine. Change `DB_PORT` in `.env`; the
backend derives its connection from it. Redis is on 6379.

---

## Configuration

Copy `.env.example` to `.env` at the repo root. It is the **only** env file:
Docker Compose, `start.sh`, the backend and the Vite config all read it. The backend
derives its database, Redis, MinIO and SMTP connections from the same keys Docker
Compose uses, so no value is written twice. Mail, AI provider, GitHub
and CI/CD settings are changed in the app under **Admin → Configuration** — no
redeploy needed.

### GitHub

Every project in TRACE owns a GitHub repository and every task **is** a GitHub
issue, so TRACE needs GitHub access before anyone can create a project. It works as **one company GitHub account**, not as
individual users:

1. Create a GitHub **Organization** for the company. Personal accounts are not
   supported. **Every repository TRACE creates is public**, and so are its issues
   and generated documents. Never put secrets in requirement documents.
2. Create a **fine-grained personal access token** limited to that organization,
   with *Administration*, *Contents* and *Issues* set to read/write and *Metadata*
   set to read. Don't use a classic full-access token. Give it an expiry of
   **366 days or less** — organizations can refuse longer-lived tokens, and
   TRACE's organization does (Test connection shows GitHub's 403).
3. Make sure `SETTINGS_ENCRYPTION_KEY` is set in `.env` — the token is stored
   encrypted with it. Generate one with
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
   Changing it later makes the saved token unreadable; enter the token again.
4. As Admin, open **Admin → Configuration → GitHub**: enter the organization, the
   token and (optionally) the committer name and email for the commits TRACE makes,
   **Save**, then **Test connection**. The token is never shown again — only
   whether it is set. (`GITHUB_OWNER` / `GITHUB_TOKEN` / `GITHUB_COMMITTER_*` in
   `.env` work as fallbacks.)
5. Each person who works on tasks sets their **GitHub username** under Profile.

When a Manager creates a project, TRACE creates the public repository
`<organization>/<project-name-slug>`; a name that is already taken is refused, never
reused. Appointing a Project Manager or assigning someone a task invites them to that
repository with *Write* — they must **accept GitHub's email invitation** before issues
can be assigned to them on GitHub (until then TRACE creates the issue unassigned and
says so; assign it again once they have accepted). Removing a Project Manager who holds
no tasks revokes their access. To check the whole integration against your real
organization, run `TRACE_LIVE_GITHUB=1 .venv/bin/python -m pytest -q tests/test_github_live.py -s`
in `backend/` — it creates one public `trace-smoke-<timestamp>` repo and leaves it
archived. Deleting a project **archives** its repository (it is
never deleted, so its name stays taken).

---

## Production (public URL through Cloudflare Tunnel)

`APP_ENV` in the root `.env` is `local` or `production`. The same `./start.sh start`
then does this:

| | `local` | `production` |
|---|---|---|
| Frontend | Vite dev server | `vite build`, then `vite preview` on `127.0.0.1:5173` |
| Backend | uvicorn `--reload` on `0.0.0.0` | uvicorn on `127.0.0.1`, no reload |
| Tunnel | — | `cloudflared` container (compose profile `production`) |
| Demo users + demo project | seeded | **not** seeded |

**Production refuses to start** when `CLOUDFLARE_TUNNEL_TOKEN` or `PRODUCTION_URL` is
empty, `DEBUG` is true, `JWT_SECRET_KEY` is a placeholder, `SETTINGS_ENCRYPTION_KEY`
is missing or not a Fernet key, or any account still has
its published seed password (`admin@trace.com` / `Admin@123` and the others). Fix
the last one with `./start.sh set-password <email>`.

**Tunnel routes** (Zero Trust → Networks → Tunnels → *tunnel* → Published
applications). Leave **Path** empty and set **Type** to HTTP:

| Subdomain | URL |
|---|---|
| *(blank)* | `localhost:5173` |
| `www` | `localhost:5173` |

- The URLs use `localhost`, not container names. The app runs on the host, and
  `cloudflared` uses host networking.
- `/api` is served through the same origin, so the API needs no route.
- Afterwards, check **DNS → Records** shows both names. The bare-domain record is
  sometimes not created; add it by hand as CNAME `@` →
  `<tunnel-id>.cfargotunnel.com`, **Proxied**.
- Do not route pgAdmin, the MinIO console or Mailpit unless Cloudflare Access
  sits in front of them first.

---

## Documentation

| File | For |
|------|-----|
| [`AGENTS.md`](AGENTS.md) | Anyone writing code |
| [`docs/PROJECT.md`](docs/PROJECT.md) | What the system is: roles, panels, schema, UI |
| [`docs/CORE.md`](docs/CORE.md) | How the AI automation works |
| [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) | Build phases |
| [`docs/PLANNING.md`](docs/PLANNING.md) | Decisions, open questions, future work |
