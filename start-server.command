#!/bin/bash

# Change to the script's directory
cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================================="
echo "🎬 YTClipper - Starting Server"
echo "=================================================="
echo ""

# Check if server is already running on port 5000
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  Server is already running!${NC}"
    echo ""
    echo "Double-click 'stop-server.command' to stop it first."
    echo ""
    echo "Press any key to close this window..."
    read -n 1 -s
    exit 1
fi

echo "Starting server..."
echo ""

# Start the server
python3 backend/server.py &

sleep 3

# Get local IP
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1)

echo ""
echo "=================================================="
echo -e "${GREEN}✓ Server started successfully!${NC}"
echo "=================================================="
echo ""
echo "📱 Access from your phone:"
echo "   http://${LOCAL_IP}:5000"
echo ""
echo "💻 Access from this computer:"
echo "   http://localhost:5000"
echo ""
echo "=================================================="
echo ""
echo -e "${YELLOW}To stop the server:${NC}"
echo "   Double-click 'stop-server.command'"
echo ""
echo "Or press CTRL+C to stop now and close this window."
echo ""

# Keep terminal open and wait for server to stop
wait
