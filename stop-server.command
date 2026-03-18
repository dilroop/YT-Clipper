#!/bin/bash

# Change to the script's directory
cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================================="
echo "🎬 YTClipper - Stopping Server"
echo "=================================================="
echo ""

# Check if server is running on port 5001
if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}Stopping server...${NC}"
    echo ""

    # Kill only Python processes on port 5001
    lsof -n -i:5001 | grep "python" | awk '{print $2}' | xargs kill -9 2>/dev/null

    # Also kill any python server processes (including those from .venv)
    pkill -9 -f "python.*backend/server.py" 2>/dev/null

    sleep 1

    echo -e "${RED}✓ Server stopped!${NC}"
    echo ""
    echo "Double-click 'start-server.command' to start it again."
else
    echo -e "${YELLOW}Server is not running.${NC}"
    echo ""
    echo "Double-click 'start-server.command' to start it."
fi

echo ""
echo "Press any key to close this window..."
read -n 1 -s
