#!/usr/bin/env bash
# ============================================
# TRACE — Unified Management Script
#
# Usage:
#   ./start.sh [command]
#
# Commands:
#   start    - Start Docker services & local app servers (default)
#   stop     - Stop Docker containers & local app processes
#   migrate  - Run database migrations (Alembic)
#   restart  - Restart all services (stop + start)
#   status   - Check status of containers and services
#   set-password <email> - Set a user's password
#   help     - Show this help menu
#
# APP_ENV (root .env) selects local or production; see load_app_env.
# ============================================

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"
PID_FILE="$ROOT_DIR/.trace_pids"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

# ── Environment (APP_ENV) ─────────────────────────────────────
# The one place this script decides local vs production. Everything below asks
# is_production; nothing else reads APP_ENV. Python code has its own single
# check, Settings.is_production in backend/app/config.py.
env_value() {
    # Read KEY from the root .env without sourcing it
    [ -f "$ROOT_DIR/.env" ] || return 0
    grep -E "^$1=" "$ROOT_DIR/.env" | tail -1 | cut -d= -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//'
}

load_app_env() {
    APP_ENV="${APP_ENV:-$(env_value APP_ENV)}"
    APP_ENV="${APP_ENV:-local}"
    case "$APP_ENV" in
        local|production) ;;
        *) echo -e "${RED}❌ APP_ENV must be 'local' or 'production', got '$APP_ENV'${NC}"; exit 1 ;;
    esac
    PRODUCTION_URL="$(env_value PRODUCTION_URL)"
    PRODUCTION_URL="${PRODUCTION_URL#https://}"; PRODUCTION_URL="${PRODUCTION_URL#http://}"; PRODUCTION_URL="${PRODUCTION_URL%/}"
    export APP_ENV
}

is_production() { [ "$APP_ENV" = "production" ]; }

# Compose args: the production profile adds the cloudflared tunnel
compose() {
    if is_production; then
        docker compose -f "$ROOT_DIR/docker-compose.yml" --profile production "$@"
    else
        docker compose -f "$ROOT_DIR/docker-compose.yml" "$@"
    fi
}

# Refuse to expose the stack publicly with development settings
preflight_production() {
    echo -e "${CYAN}🔒 Production preflight...${NC}"
    local failed=0
    if [ -z "$(env_value CLOUDFLARE_TUNNEL_TOKEN)" ]; then
        echo -e "${RED}  ✗ CLOUDFLARE_TUNNEL_TOKEN is empty in .env${NC}"; failed=1
    fi
    if [ -z "$PRODUCTION_URL" ]; then
        echo -e "${RED}  ✗ PRODUCTION_URL is empty in .env${NC}"; failed=1
    fi
    # Backend settings validation (DEBUG, JWT secret, ...) — see Settings._production_preflight
    if ! (cd "$BACKEND_DIR" && "$VENV_DIR/bin/python" -c "from app.config import get_settings; get_settings()" 2>&1 \
            | grep -E "^RuntimeError: |^  - " | sed "s/^/  /"; exit "${PIPESTATUS[0]}"); then
        failed=1
    fi
    if [ "$failed" -ne 0 ]; then
        echo -e "${RED}❌ Not starting in production. Fix the above, or set APP_ENV=local.${NC}"
        exit 1
    fi
    echo -e "${GREEN}  ✓ passed${NC}"
}

load_app_env

# ── Banner Helper ─────────────────────────────────────────────
print_banner() {
    local title="$1"
    echo ""
    echo -e "${CYAN}╔═════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║         ${GREEN}TRACE — ${title}${CYAN}           ║${NC}"
    echo -e "${CYAN}╚═════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ── Function: Wait for PostgreSQL ──────────────────────────────
wait_for_db() {
    echo -e "${YELLOW}⏳ Waiting for PostgreSQL to be ready...${NC}"
    for i in $(seq 1 30); do
        if docker exec trace_db pg_isready -U trace_user -d trace_db > /dev/null 2>&1; then
            echo -e "${GREEN}✅ PostgreSQL is ready!${NC}"
            return 0
        fi
        if [ "$i" -eq 30 ]; then
            echo -e "${RED}❌ PostgreSQL failed to start. Check: docker compose logs db${NC}"
            exit 1
        fi
        sleep 1
    done
}

# ── Function: Wait for Redis ───────────────────────────────────
wait_for_redis() {
    echo -e "${YELLOW}⏳ Waiting for Redis to be ready...${NC}"
    for i in $(seq 1 15); do
        if docker exec trace_redis redis-cli ping > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Redis is ready!${NC}"
            return 0
        fi
        if [ "$i" -eq 15 ]; then
            echo -e "${RED}❌ Redis failed to start. Check: docker compose logs redis${NC}"
            exit 1
        fi
        sleep 1
    done
}

# ── Function: Check Environment ───────────────────────────────
ensure_env() {
    if [ ! -f "$VENV_DIR/bin/python" ]; then
        echo -e "${YELLOW}📦 Creating Python virtual environment...${NC}"
        python3 -m venv "$VENV_DIR"
    fi
    if [ -f "$BACKEND_DIR/requirements.txt" ]; then
        echo -e "${YELLOW}📦 Checking Python dependencies...${NC}"
        "$VENV_DIR/bin/pip" install -q -r "$BACKEND_DIR/requirements.txt"
    fi
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        echo -e "${YELLOW}📦 Installing frontend dependencies...${NC}"
        (cd "$FRONTEND_DIR" && npm ci)
    fi
}

# ── Function: Start Services ──────────────────────────────────
do_start() {
    print_banner "Starting Up ($APP_ENV)..."

    # 0. Environment prerequisites, then (production only) the preflight
    ensure_env
    if is_production; then
        preflight_production
    fi

    # 1. Start Docker Services (+ the Cloudflare tunnel in production)
    local infra="db redis pgadmin mailpit minio"
    if is_production; then infra="$infra cloudflared"; fi
    echo -e "${CYAN}🐳 Starting Docker services: $infra${NC}"
    compose up -d $infra 2>&1 | tail -8

    wait_for_db
    wait_for_redis

    echo -e "${GREEN}✅ pgAdmin  → http://localhost:5050${NC}"
    echo -e "${GREEN}✅ Mailpit  → http://localhost:8025${NC}"
    echo -e "${GREEN}✅ MinIO    → http://localhost:9001${NC}"

    # 3. Bring the schema to head — Alembic is the only thing that creates tables
    echo -e "${CYAN}⚡ Running Alembic migration (upgrade head)...${NC}"
    (cd "$BACKEND_DIR" && "$VENV_DIR/bin/alembic" upgrade head)

    # Cleanup function on Ctrl+C or EXIT in foreground
    cleanup_fg() {
        # Clear the traps first: `kill 0` below signals this shell too, and a trap
        # still set would re-enter cleanup_fg until the shell crashed.
        trap - EXIT INT TERM
        echo ""
        echo -e "${YELLOW}⏹  Shutting down TRACE local processes...${NC}"
        if [ -f "$PID_FILE" ]; then
            while read -r pid; do
                if kill -0 "$pid" 2>/dev/null; then
                    kill "$pid" 2>/dev/null || true
                fi
            done < "$PID_FILE"
            rm -f "$PID_FILE"
        fi
        kill 0 2>/dev/null || true
        wait 2>/dev/null || true
        echo -e "${GREEN}✅ Local processes stopped.${NC}"
    }
    trap cleanup_fg EXIT INT TERM

    > "$PID_FILE"

    # 3. Start Backend (FastAPI)
    echo ""
    echo -e "${CYAN}🚀 Starting Backend (FastAPI) on http://localhost:8000${NC}"
    # Production binds loopback only — the tunnel is the way in — and drops --reload
    local uvicorn_args="--reload --host 0.0.0.0 --port 8000"
    if is_production; then uvicorn_args="--host 127.0.0.1 --port 8000"; fi
    (
        cd "$BACKEND_DIR"
        exec "$VENV_DIR/bin/uvicorn" app.main:app $uvicorn_args 2>&1 | \
            sed "s/^/  [backend] /"
    ) &
    BACKEND_PID=$!
    echo "$BACKEND_PID" >> "$PID_FILE"

    sleep 3

    # 4. Start Celery Worker
    echo -e "${CYAN}⚙️  Starting Celery Worker...${NC}"
    (
        cd "$BACKEND_DIR"
        exec "$VENV_DIR/bin/celery" -A app.celery_app worker --loglevel=info 2>&1 | \
            sed "s/^/  [celery-w] /"
    ) &
    CELERY_W_PID=$!
    echo "$CELERY_W_PID" >> "$PID_FILE"

    # 5. Start Celery Beat
    echo -e "${CYAN}⏰ Starting Celery Beat...${NC}"
    (
        cd "$BACKEND_DIR"
        exec "$VENV_DIR/bin/celery" -A app.celery_app beat --loglevel=info 2>&1 | \
            sed "s/^/  [celery-b] /"
    ) &
    CELERY_B_PID=$!
    echo "$CELERY_B_PID" >> "$PID_FILE"

    # 6. Start Frontend — dev server locally; built bundle via `vite preview` in
    #    production, never the dev server on a public hostname
    if is_production; then
        echo -e "${CYAN}🏗️  Building frontend for production...${NC}"
        (cd "$FRONTEND_DIR" && npm run build 2>&1 | tail -3)
        echo -e "${CYAN}🚀 Serving built frontend (vite preview) on http://127.0.0.1:5173${NC}"
        (
            cd "$FRONTEND_DIR"
            exec npx vite preview 2>&1 | sed "s/^/  [frontend] /"
        ) &
    else
        echo -e "${CYAN}🚀 Starting Frontend (Vite) on http://localhost:5173${NC}"
        (
            cd "$FRONTEND_DIR"
            exec npm run dev 2>&1 | sed "s/^/  [frontend] /"
        ) &
    fi
    FRONTEND_PID=$!
    echo "$FRONTEND_PID" >> "$PID_FILE"

    # 7. Summary
    sleep 3
    echo ""
    echo -e "${GREEN}╔═════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          TRACE is running successfully! 🎉          ║${NC}"
    echo -e "${GREEN}╠═════════════════════════════════════════════════════╣${NC}"
    if is_production; then
    echo -e "${GREEN}║  Public   → ${CYAN}https://${PRODUCTION_URL}${NC}"
    fi
    echo -e "${GREEN}║  Frontend → ${CYAN}http://localhost:5173${GREEN}                   ║${NC}"
    echo -e "${GREEN}║  Backend  → ${CYAN}http://localhost:8000${GREEN}                   ║${NC}"
    echo -e "${GREEN}║  API Docs → ${CYAN}http://localhost:8000/docs${GREEN}              ║${NC}"
    echo -e "${GREEN}║  pgAdmin  → ${CYAN}http://localhost:5050${GREEN}                   ║${NC}"
    echo -e "${GREEN}║  Mailpit  → ${CYAN}http://localhost:8025${GREEN}                   ║${NC}"
    echo -e "${GREEN}║  MinIO    → ${CYAN}http://localhost:9001${GREEN}                   ║${NC}"
    echo -e "${GREEN}╠═════════════════════════════════════════════════════╣${NC}"
    if ! is_production; then
    echo -e "${GREEN}║  Login:                                             ║${NC}"
    echo -e "${GREEN}║    Email:    ${YELLOW}admin@trace.com${GREEN}                        ║${NC}"
    echo -e "${GREEN}║    Password: ${YELLOW}Admin@123${GREEN}                              ║${NC}"
    echo -e "${GREEN}╠═════════════════════════════════════════════════════╣${NC}"
    fi
    echo -e "${GREEN}║  Press ${RED}Ctrl+C${GREEN} or run ${CYAN}./start.sh stop${GREEN} to stop.  ║${NC}"
    echo -e "${GREEN}╚═════════════════════════════════════════════════════╝${NC}"
    echo ""

    wait
}

# ── Function: Stop Services ───────────────────────────────────
do_stop() {
    print_banner "Stopping Environment..."

    # 1. Kill background processes registered in PID_FILE
    if [ -f "$PID_FILE" ]; then
        echo -e "${YELLOW}🛑 Stopping background application processes...${NC}"
        while read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi

    # 2. Kill any matching background uvicorn/celery/vite processes — politely, then
    #    for real: a hung uvicorn reloader ignores TERM and keeps port 8000, so the
    #    next start fails with "Address already in use".
    local patterns=("uvicorn app.main:app" "celery -A app.celery_app" "vite")
    for pat in "${patterns[@]}"; do pkill -f "$pat" 2>/dev/null || true; done
    for _ in $(seq 1 20); do
        local alive=0
        for pat in "${patterns[@]}"; do pgrep -f "$pat" > /dev/null && alive=1; done
        [ "$alive" = 0 ] && break
        sleep 0.5
    done
    for pat in "${patterns[@]}"; do
        if pgrep -f "$pat" > /dev/null; then
            echo -e "${YELLOW}⚠️  '$pat' ignored TERM — killing it${NC}"
            pkill -9 -f "$pat" 2>/dev/null || true
        fi
    done

    # 3. Stop Docker Containers
    echo -e "${CYAN}🐳 Stopping Docker containers...${NC}"
    docker compose -f "$ROOT_DIR/docker-compose.yml" --profile production down --remove-orphans

    echo ""
    echo -e "${GREEN}✅ All Docker containers and TRACE services have been stopped successfully.${NC}"
    echo ""
}

# ── Function: Migrate Database ────────────────────────────────
do_migrate() {
    print_banner "Running Database Migrations..."

    # 1. Ensure DB container is running
    echo -e "${CYAN}🐳 Ensuring PostgreSQL container is running...${NC}"
    docker compose -f "$ROOT_DIR/docker-compose.yml" up -d db

    wait_for_db

    # 2. Ensure virtualenv exists
    if [ ! -f "$VENV_DIR/bin/python" ]; then
        echo -e "${YELLOW}📦 Creating Python virtual environment...${NC}"
        python3 -m venv "$VENV_DIR"
        "$VENV_DIR/bin/pip" install -q -r "$BACKEND_DIR/requirements.txt"
    fi

    # 3. Execute Alembic Upgrade
    echo -e "${CYAN}⚡ Running Alembic migration (upgrade head)...${NC}"
    (
        cd "$BACKEND_DIR"
        "$VENV_DIR/bin/alembic" upgrade head
    )

    echo ""
    echo -e "${GREEN}✅ Database migrations completed successfully!${NC}"
    echo ""
}

# ── Function: Status ──────────────────────────────────────────
do_status() {
    print_banner "Service Status"

    echo -e "${BOLD}Environment:${NC} APP_ENV=${APP_ENV}"
    if is_production; then
        echo -e "  Public URL: https://${PRODUCTION_URL}  →  $(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "https://${PRODUCTION_URL}/" || echo unreachable)"
    fi
    echo ""
    echo -e "${BOLD}Docker Containers:${NC}"
    compose ps

    echo ""
    echo -e "${BOLD}Local Services:${NC}"
    if pgrep -f "uvicorn app.main:app" > /dev/null; then
        echo -e "  Backend (FastAPI):  ${GREEN}RUNNING${NC}"
    else
        echo -e "  Backend (FastAPI):  ${RED}STOPPED${NC}"
    fi

    if pgrep -f "celery -A app.celery_app worker" > /dev/null; then
        echo -e "  Celery Worker:      ${GREEN}RUNNING${NC}"
    else
        echo -e "  Celery Worker:      ${RED}STOPPED${NC}"
    fi

    if pgrep -f "celery -A app.celery_app beat" > /dev/null; then
        echo -e "  Celery Beat:        ${GREEN}RUNNING${NC}"
    else
        echo -e "  Celery Beat:        ${RED}STOPPED${NC}"
    fi

    if pgrep -f "vite" > /dev/null; then
        echo -e "  Frontend (Vite):    ${GREEN}RUNNING${NC}"
    else
        echo -e "  Frontend (Vite):    ${RED}STOPPED${NC}"
    fi
    echo ""
}

# ── Help / Usage ──────────────────────────────────────────────
show_help() {
    echo "TRACE Control Script"
    echo ""
    echo "Usage:"
    echo "  ./start.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start    - Start Docker infrastructure and local services (default)"
    echo "  stop     - Stop Docker containers and application processes"
    echo "  migrate  - Run Alembic database migrations"
    echo "  restart  - Restart all services (stop + start)"
    echo "  status   - Show status of Docker containers and app services"
    echo "  set-password <email> - Set a user's password (prompts for it)"
    echo "  help     - Show this help message"
    echo ""
}

# ── Main Entrypoint Dispatch ──────────────────────────────────
COMMAND="${1:-start}"

case "$COMMAND" in
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    migrate)
        do_migrate
        ;;
    restart)
        do_stop
        sleep 2
        do_start
        ;;
    status)
        do_status
        ;;
    set-password)
        [ -n "$2" ] || { echo -e "${RED}Usage: ./start.sh set-password <email>${NC}"; exit 1; }
        (cd "$BACKEND_DIR" && "$VENV_DIR/bin/python" -m app.cli set-password "$2")
        ;;
    help|-h|--help)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
