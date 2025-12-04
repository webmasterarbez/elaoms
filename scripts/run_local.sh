#!/usr/bin/env bash
#
# run_local.sh - Manage the ElevenLabs OpenMemory Integration server
#
# Commands:
#   start   - Start the server in background
#   stop    - Stop the server
#   restart - Restart the server
#   debug   - Start in foreground with debug logging
#   ngrok   - Start server + ngrok tunnel with request logging
#   status  - Show server and related services status
#   logs    - Tail the server logs
#
# Usage:
#   ./scripts/run_local.sh start
#   ./scripts/run_local.sh stop
#   ./scripts/run_local.sh restart
#   ./scripts/run_local.sh debug
#   ./scripts/run_local.sh ngrok
#   ./scripts/run_local.sh status
#   ./scripts/run_local.sh logs
#
# Environment:
#   PORT      - Server port (default: 8000)
#   HOST      - Server host (default: 0.0.0.0)
#   LOG_LEVEL - Logging level (default: info, debug for debug mode)
#
# Related Services:
#   - OpenMemory API: http://localhost:8080
#   - OpenMemory Dashboard: http://localhost:3000
#

set -e  # Exit on error

# Determine the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Change to project root
cd "${PROJECT_ROOT}"

# Configuration
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
LOG_LEVEL="${LOG_LEVEL:-info}"
PID_FILE="${PROJECT_ROOT}/.server.pid"
LOG_FILE="${PROJECT_ROOT}/logs/server.log"
NGROK_LOG_FILE="${PROJECT_ROOT}/logs/ngrok.log"

# Related services
OPENMEMORY_PORT=8080
DASHBOARD_PORT=3000

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Ensure logs directory exists
mkdir -p "${PROJECT_ROOT}/logs"

#------------------------------------------------------------------------------
# Helper Functions
#------------------------------------------------------------------------------

print_header() {
    echo -e "${GREEN}=============================================${NC}"
    echo -e "${GREEN}  ElevenLabs OpenMemory Integration Server${NC}"
    echo -e "${GREEN}=============================================${NC}"
    echo ""
}

print_status_line() {
    local service=$1
    local port=$2
    local status=$3

    if [ "$status" = "running" ]; then
        echo -e "  ${GREEN}●${NC} ${service} (port ${port}): ${GREEN}running${NC}"
    else
        echo -e "  ${RED}●${NC} ${service} (port ${port}): ${RED}stopped${NC}"
    fi
}

check_port() {
    local port=$1
    if command -v ss &> /dev/null; then
        ss -tlnp 2>/dev/null | grep -q ":${port} " && return 0
    elif command -v netstat &> /dev/null; then
        netstat -tlnp 2>/dev/null | grep -q ":${port} " && return 0
    elif command -v lsof &> /dev/null; then
        lsof -i:${port} &>/dev/null && return 0
    fi
    return 1
}

get_pid_on_port() {
    local port=$1
    if command -v ss &> /dev/null; then
        ss -tlnp 2>/dev/null | grep ":${port} " | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1
    elif command -v lsof &> /dev/null; then
        lsof -ti:${port} 2>/dev/null | head -1
    fi
}

check_prerequisites() {
    local errors=0

    # Check .env file
    if [ ! -f "${PROJECT_ROOT}/.env" ]; then
        echo -e "${RED}Error: .env file not found!${NC}"
        echo -e "${YELLOW}Please copy .env.example to .env and configure your environment variables.${NC}"
        echo "  cp .env.example .env"
        errors=1
    fi

    # Check virtual environment
    if [ -z "${VIRTUAL_ENV}" ]; then
        if [ -d "${PROJECT_ROOT}/venv" ]; then
            echo -e "${YELLOW}Activating virtual environment...${NC}"
            source "${PROJECT_ROOT}/venv/bin/activate"
        else
            echo -e "${YELLOW}Warning: No virtual environment found.${NC}"
        fi
    fi

    # Check uvicorn
    if ! command -v uvicorn &> /dev/null; then
        echo -e "${RED}Error: uvicorn not found!${NC}"
        echo -e "${YELLOW}Please install dependencies: pip install -r requirements.txt${NC}"
        errors=1
    fi

    return $errors
}

print_urls() {
    local base_url=$1
    echo -e "${CYAN}Webhook Endpoints:${NC}"
    echo -e "  POST ${base_url}/webhook/client-data"
    echo -e "  POST ${base_url}/webhook/search-data"
    echo -e "  POST ${base_url}/webhook/post-call"
    echo ""
    echo -e "${CYAN}Other Endpoints:${NC}"
    echo -e "  GET  ${base_url}/health"
    echo -e "  GET  ${base_url}/docs"
    echo ""
}

#------------------------------------------------------------------------------
# Commands
#------------------------------------------------------------------------------

cmd_start() {
    print_header
    check_prerequisites || exit 1

    if check_port ${PORT}; then
        echo -e "${YELLOW}Server already running on port ${PORT}${NC}"
        cmd_status
        return 0
    fi

    echo -e "${GREEN}Starting server on port ${PORT}...${NC}"

    nohup uvicorn app.main:app \
        --host "${HOST}" \
        --port "${PORT}" \
        --reload \
        --log-level "${LOG_LEVEL}" \
        >> "${LOG_FILE}" 2>&1 &

    local pid=$!
    echo $pid > "${PID_FILE}"

    sleep 2

    if check_port ${PORT}; then
        echo -e "${GREEN}Server started successfully (PID: ${pid})${NC}"
        echo ""
        print_urls "http://localhost:${PORT}"
        cmd_status
    else
        echo -e "${RED}Failed to start server. Check logs: ${LOG_FILE}${NC}"
        tail -20 "${LOG_FILE}"
        exit 1
    fi
}

cmd_stop() {
    echo -e "${YELLOW}Stopping server...${NC}"

    # Try PID file first
    if [ -f "${PID_FILE}" ]; then
        local pid=$(cat "${PID_FILE}")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            rm -f "${PID_FILE}"
            echo -e "${GREEN}Server stopped (PID: ${pid})${NC}"
            return 0
        fi
        rm -f "${PID_FILE}"
    fi

    # Find and kill by port
    local pid=$(get_pid_on_port ${PORT})
    if [ -n "$pid" ]; then
        kill "$pid" 2>/dev/null
        echo -e "${GREEN}Server stopped (PID: ${pid})${NC}"
        return 0
    fi

    # Kill any uvicorn processes for this app
    pkill -f "uvicorn app.main:app.*--port ${PORT}" 2>/dev/null && \
        echo -e "${GREEN}Server stopped${NC}" || \
        echo -e "${YELLOW}No server running on port ${PORT}${NC}"
}

cmd_restart() {
    cmd_stop
    sleep 1
    cmd_start
}

cmd_debug() {
    print_header
    check_prerequisites || exit 1

    # Stop any existing server
    cmd_stop 2>/dev/null || true
    sleep 1

    echo -e "${CYAN}Starting server in DEBUG mode...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo ""
    print_urls "http://localhost:${PORT}"

    echo -e "${BOLD}--- Server Logs ---${NC}"
    echo ""

    # Run in foreground with debug logging
    uvicorn app.main:app \
        --host "${HOST}" \
        --port "${PORT}" \
        --reload \
        --log-level debug \
        --access-log
}

cmd_ngrok() {
    print_header
    check_prerequisites || exit 1

    # Check if ngrok is installed
    if ! command -v ngrok &> /dev/null; then
        echo -e "${RED}Error: ngrok not found!${NC}"
        echo -e "${YELLOW}Install ngrok: https://ngrok.com/download${NC}"
        exit 1
    fi

    # Stop any existing server
    cmd_stop 2>/dev/null || true
    sleep 1

    echo -e "${CYAN}Starting server with ngrok tunnel...${NC}"
    echo ""

    # Start server in background with debug logging
    uvicorn app.main:app \
        --host "${HOST}" \
        --port "${PORT}" \
        --reload \
        --log-level debug \
        --access-log \
        >> "${LOG_FILE}" 2>&1 &

    local server_pid=$!
    echo $server_pid > "${PID_FILE}"

    sleep 2

    if ! check_port ${PORT}; then
        echo -e "${RED}Failed to start server${NC}"
        exit 1
    fi

    echo -e "${GREEN}Server started (PID: ${server_pid})${NC}"
    echo ""

    # Start ngrok
    echo -e "${CYAN}Starting ngrok tunnel...${NC}"
    ngrok http ${PORT} --log=stdout > "${NGROK_LOG_FILE}" 2>&1 &
    local ngrok_pid=$!

    sleep 3

    # Get ngrok public URL
    local ngrok_url=""
    if command -v curl &> /dev/null; then
        ngrok_url=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | \
            python3 -c "import sys,json; d=json.load(sys.stdin); print(d['tunnels'][0]['public_url'] if d.get('tunnels') else '')" 2>/dev/null || true)
    fi

    if [ -z "$ngrok_url" ]; then
        echo -e "${YELLOW}Waiting for ngrok tunnel...${NC}"
        sleep 2
        ngrok_url=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | \
            python3 -c "import sys,json; d=json.load(sys.stdin); print(d['tunnels'][0]['public_url'] if d.get('tunnels') else '')" 2>/dev/null || true)
    fi

    echo ""
    echo -e "${GREEN}=============================================${NC}"
    echo -e "${GREEN}  Services Running${NC}"
    echo -e "${GREEN}=============================================${NC}"
    echo ""

    cmd_status

    echo ""
    echo -e "${GREEN}=============================================${NC}"
    echo -e "${GREEN}  Webhook URLs for ElevenLabs${NC}"
    echo -e "${GREEN}=============================================${NC}"
    echo ""

    if [ -n "$ngrok_url" ]; then
        echo -e "${BOLD}Public (ngrok):${NC}"
        echo -e "  ${CYAN}Client Data:${NC} ${ngrok_url}/webhook/client-data"
        echo -e "  ${CYAN}Search Data:${NC} ${ngrok_url}/webhook/search-data"
        echo -e "  ${CYAN}Post Call:${NC}   ${ngrok_url}/webhook/post-call"
        echo ""
    else
        echo -e "${YELLOW}ngrok URL not available yet. Check: http://127.0.0.1:4040${NC}"
        echo ""
    fi

    echo -e "${BOLD}Local:${NC}"
    print_urls "http://localhost:${PORT}"

    echo -e "${GREEN}=============================================${NC}"
    echo -e "${GREEN}  Live Request Monitor${NC}"
    echo -e "${GREEN}=============================================${NC}"
    echo ""
    echo -e "${YELLOW}Watching for incoming requests... (Ctrl+C to stop)${NC}"
    echo ""

    # Trap to cleanup on exit
    trap 'echo ""; echo -e "${YELLOW}Shutting down...${NC}"; kill $server_pid 2>/dev/null; kill $ngrok_pid 2>/dev/null; exit 0' INT TERM

    # Tail the log file to show incoming requests
    tail -f "${LOG_FILE}" 2>/dev/null | while read line; do
        # Highlight webhook requests
        if echo "$line" | grep -qE "(POST|GET).*/webhook/"; then
            echo -e "${CYAN}${line}${NC}"
        elif echo "$line" | grep -qiE "(error|exception|failed)"; then
            echo -e "${RED}${line}${NC}"
        elif echo "$line" | grep -qiE "(warning|warn)"; then
            echo -e "${YELLOW}${line}${NC}"
        else
            echo "$line"
        fi
    done
}

cmd_status() {
    echo -e "${BOLD}Service Status:${NC}"
    echo ""

    # FastAPI Server
    if check_port ${PORT}; then
        print_status_line "FastAPI Server" "${PORT}" "running"
    else
        print_status_line "FastAPI Server" "${PORT}" "stopped"
    fi

    # OpenMemory API
    if check_port ${OPENMEMORY_PORT}; then
        print_status_line "OpenMemory API" "${OPENMEMORY_PORT}" "running"
    else
        print_status_line "OpenMemory API" "${OPENMEMORY_PORT}" "stopped"
    fi

    # OpenMemory Dashboard
    if check_port ${DASHBOARD_PORT}; then
        print_status_line "OpenMemory Dashboard" "${DASHBOARD_PORT}" "running"
    else
        print_status_line "OpenMemory Dashboard" "${DASHBOARD_PORT}" "stopped"
    fi

    # ngrok
    if check_port 4040; then
        local ngrok_url=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | \
            python3 -c "import sys,json; d=json.load(sys.stdin); print(d['tunnels'][0]['public_url'] if d.get('tunnels') else '')" 2>/dev/null || true)
        if [ -n "$ngrok_url" ]; then
            echo -e "  ${GREEN}●${NC} ngrok tunnel: ${GREEN}${ngrok_url}${NC}"
        else
            print_status_line "ngrok" "4040" "running"
        fi
    else
        print_status_line "ngrok" "4040" "stopped"
    fi

    echo ""
}

cmd_logs() {
    if [ ! -f "${LOG_FILE}" ]; then
        echo -e "${YELLOW}No log file found at ${LOG_FILE}${NC}"
        exit 1
    fi

    echo -e "${CYAN}Tailing logs... (Ctrl+C to stop)${NC}"
    echo ""

    tail -f "${LOG_FILE}" | while read line; do
        if echo "$line" | grep -qE "(POST|GET).*/webhook/"; then
            echo -e "${CYAN}${line}${NC}"
        elif echo "$line" | grep -qiE "(error|exception|failed)"; then
            echo -e "${RED}${line}${NC}"
        elif echo "$line" | grep -qiE "(warning|warn)"; then
            echo -e "${YELLOW}${line}${NC}"
        else
            echo "$line"
        fi
    done
}

cmd_help() {
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  start   - Start the server in background"
    echo "  stop    - Stop the server"
    echo "  restart - Restart the server"
    echo "  debug   - Start in foreground with debug logging"
    echo "  ngrok   - Start server + ngrok tunnel with live request monitoring"
    echo "  status  - Show server and related services status"
    echo "  logs    - Tail the server logs"
    echo ""
    echo "Environment Variables:"
    echo "  PORT      - Server port (default: 8000)"
    echo "  HOST      - Server host (default: 0.0.0.0)"
    echo "  LOG_LEVEL - Logging level (default: info)"
    echo ""
    echo "Related Services:"
    echo "  OpenMemory API:       http://localhost:8080"
    echo "  OpenMemory Dashboard: http://localhost:3000"
    echo ""
    echo "Examples:"
    echo "  $0 start              # Start server on port 8000"
    echo "  PORT=9000 $0 start    # Start server on port 9000"
    echo "  $0 ngrok              # Start with ngrok tunnel"
    echo "  $0 debug              # Start in debug mode"
    echo ""
}

#------------------------------------------------------------------------------
# Main
#------------------------------------------------------------------------------

case "${1:-}" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    debug)
        cmd_debug
        ;;
    ngrok)
        cmd_ngrok
        ;;
    status)
        cmd_status
        ;;
    logs)
        cmd_logs
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        if [ -n "${1:-}" ]; then
            echo -e "${RED}Unknown command: $1${NC}"
            echo ""
        fi
        cmd_help
        exit 1
        ;;
esac
