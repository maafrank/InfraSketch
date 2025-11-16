#!/bin/bash

# Script to run both frontend and backend locally for testing
# This launches both servers in the background and shows their output

set -e  # Exit on error

echo "🚀 Starting InfraSketch local development servers..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please create a .env file with ANTHROPIC_API_KEY"
    exit 1
fi

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down servers...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    echo -e "${GREEN}✅ Servers stopped${NC}"
}

trap cleanup EXIT INT TERM

# Start backend
echo -e "${BLUE}📦 Starting backend (Python/FastAPI)...${NC}"
cd backend
python3 -m uvicorn app.main:app --reload --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID) - http://127.0.0.1:8000${NC}"
echo "  Log: backend.log"
echo ""

# Wait a moment for backend to start
sleep 2

# Start frontend
echo -e "${BLUE}📦 Starting frontend (React/Vite)...${NC}"
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID) - http://localhost:5173${NC}"
echo "  Log: frontend.log"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Both servers are running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "📍 URLs:"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://127.0.0.1:8000"
echo "  API Docs: http://127.0.0.1:8000/docs"
echo ""
echo "📝 Logs:"
echo "  Backend:  tail -f backend.log"
echo "  Frontend: tail -f frontend.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"
echo ""

# Show combined logs (with prefixes)
tail -f backend.log frontend.log 2>/dev/null | awk '
    /^==> backend.log <==/ { prefix="[BACKEND] "; next }
    /^==> frontend.log <==/ { prefix="[FRONTEND] "; next }
    /^$/ { next }
    { print prefix $0 }
' || {
    # Fallback if tail -f multiple files doesn't work
    echo "Monitoring logs... (view backend.log and frontend.log for details)"
    while true; do
        sleep 1
    done
}
