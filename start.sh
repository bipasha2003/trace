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
#   help     - Show this help menu
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
    print_banner "Starting Up..."

    # 1. Start Docker Services
    echo -e "${CYAN}🐳 Starting Docker infrastructure (DB, Redis, pgAdmin, Mailpit, MinIO)...${NC}"
    docker compose -f "$ROOT_DIR/docker-compose.yml" up -d db redis pgadmin mailpit minio 2>&1 | tail -8

    wait_for_db
    wait_for_redis

    echo -e "${GREEN}✅ pgAdmin  → http://localhost:5050${NC}"
    echo -e "${GREEN}✅ Mailpit  → http://localhost:8025${NC}"
    echo -e "${GREEN}✅ MinIO    → http://localhost:9001${NC}"

    # 2. Check Virtualenv & Node modules
    ensure_env

    # Cleanup function on Ctrl+C or EXIT in foreground
    cleanup_fg() {
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
    (
        cd "$BACKEND_DIR"
        exec "$VENV_DIR/bin/uvicorn" app.main:app --reload --host 0.0.0.0 --port 8000 2>&1 | \
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

    # 6. Start Frontend (Vite)
    echo -e "${CYAN}🚀 Starting Frontend (Vite) on http://localhost:5173${NC}"
    (
        cd "$FRONTEND_DIR"
        exec npm run dev 2>&1 | sed "s/^/  [frontend] /"
    ) &
    FRONTEND_PID=$!
    echo "$FRONTEND_PID" >> "$PID_FILE"

    # 7. Summary
    sleep 3
    echo ""
    echo -e "${GREEN}╔═════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          TRACE is running successfully! 🎉          ║${NC}"
    echo -e "${GREEN}╠═════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║  Frontend → ${CYAN}http://localhost:5173${GREEN}                   ║${NC}"
    echo -e "${GREEN}║  Backend  → ${CYAN}http://localhost:8000${GREEN}                   ║${NC}"
    echo -e "${GREEN}║  API Docs → ${CYAN}http://localhost:8000/docs${GREEN}              ║${NC}"
    echo -e "${GREEN}║  pgAdmin  → ${CYAN}http://localhost:5050${GREEN}                   ║${NC}"
    echo -e "${GREEN}║  Mailpit  → ${CYAN}http://localhost:8025${GREEN}                   ║${NC}"
    echo -e "${GREEN}║  MinIO    → ${CYAN}http://localhost:9001${GREEN}                   ║${NC}"
    echo -e "${GREEN}╠═════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║  Login:                                             ║${NC}"
    echo -e "${GREEN}║    Email:    ${YELLOW}admin@trace.com${GREEN}                        ║${NC}"
    echo -e "${GREEN}║    Password: ${YELLOW}Admin@123${GREEN}                              ║${NC}"
    echo -e "${GREEN}╠═════════════════════════════════════════════════════╣${NC}"
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

    # 2. Kill any matching background uvicorn/celery/vite processes
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "celery -A app.celery_app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true

    # 3. Stop Docker Containers
    echo -e "${CYAN}🐳 Stopping Docker containers...${NC}"
    docker compose -f "$ROOT_DIR/docker-compose.yml" down --remove-orphans

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

    echo -e "${BOLD}Docker Containers:${NC}"
    docker compose -f "$ROOT_DIR/docker-compose.yml" ps

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
