#!/usr/bin/env bash
#
# run_local.sh - Start the ElevenLabs OpenMemory Integration server for local development
#
# This script:
# - Loads environment variables from .env file
# - Starts the uvicorn server with hot reload enabled
# - Binds to 0.0.0.0 to allow external access (ngrok tunneling)
# - Uses port 8000 by default (configurable)
#
# Usage:
#   ./scripts/run_local.sh         # Run with default settings
#   PORT=3000 ./scripts/run_local.sh   # Run on a custom port
#
# Prerequisites:
#   - Python virtual environment activated
#   - Dependencies installed: pip install -r requirements.txt
#   - .env file configured with required environment variables
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

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}ElevenLabs OpenMemory Integration Server${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""

# Check if .env file exists
if [ ! -f "${PROJECT_ROOT}/.env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo -e "${YELLOW}Please copy .env.example to .env and configure your environment variables.${NC}"
    echo ""
    echo "  cp .env.example .env"
    echo ""
    exit 1
fi

# Check if virtual environment is activated
if [ -z "${VIRTUAL_ENV}" ]; then
    echo -e "${YELLOW}Warning: No virtual environment detected.${NC}"
    echo -e "${YELLOW}Consider activating your virtual environment:${NC}"
    echo ""
    echo "  source venv/bin/activate"
    echo ""
fi

# Check if uvicorn is available
if ! command -v uvicorn &> /dev/null; then
    echo -e "${RED}Error: uvicorn not found!${NC}"
    echo -e "${YELLOW}Please install dependencies:${NC}"
    echo ""
    echo "  pip install -r requirements.txt"
    echo ""
    exit 1
fi

# Display configuration
echo -e "Configuration:"
echo -e "  - Host: ${HOST}"
echo -e "  - Port: ${PORT}"
echo -e "  - Log Level: ${LOG_LEVEL}"
echo -e "  - Hot Reload: enabled"
echo ""

# Display webhook URLs
echo -e "${YELLOW}Local Webhook URLs:${NC}"
echo -e "  - Client Data: http://${HOST}:${PORT}/webhook/client-data"
echo -e "  - Search Data: http://${HOST}:${PORT}/webhook/search-data"
echo -e "  - Post Call:   http://${HOST}:${PORT}/webhook/post-call"
echo -e "  - Health:      http://${HOST}:${PORT}/health"
echo -e "  - API Docs:    http://${HOST}:${PORT}/docs"
echo ""

echo -e "${YELLOW}For external access (ngrok tunneling):${NC}"
echo -e "  Run: ngrok http ${PORT}"
echo ""

echo -e "${GREEN}Starting server...${NC}"
echo ""

# Start uvicorn with hot reload
exec uvicorn app.main:app \
    --host "${HOST}" \
    --port "${PORT}" \
    --reload \
    --log-level "${LOG_LEVEL}" \
    --env-file "${PROJECT_ROOT}/.env"