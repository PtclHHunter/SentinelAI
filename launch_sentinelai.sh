#!/usr/bin/env bash
# ============================================================
#  SentinelAI - One-Click Launcher (Linux / macOS)
#  Starts backend + frontend and opens the dashboard.
#  No installation, no admin rights, no internet required.
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
PID_DIR="$SCRIPT_DIR/.sentinelai_pids"
LOG_DIR="$SCRIPT_DIR/.sentinelai_logs"

echo ""
echo " ==================================="
echo "  SentinelAI - Starting Services..."
echo " ==================================="
echo ""

# ------------------------------------------------------------
#  Check Python
# ------------------------------------------------------------
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    # Verify it's Python 3, not Python 2
    PY_VER="$(python --version 2>&1)"
    if echo "$PY_VER" | grep -q "Python 3"; then
        PYTHON_CMD="python"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "  [ERROR] Python 3 not found."
    echo "  Install Python 3.10+ from https://www.python.org"
    echo "  and ensure it is added to your PATH."
    echo ""
    exit 1
fi

PY_VER="$($PYTHON_CMD --version 2>&1)"
echo "  [OK] Found: $PY_VER"

# ------------------------------------------------------------
#  Check Node.js
# ------------------------------------------------------------
NODE_CMD=""
if command -v node &> /dev/null; then
    NODE_CMD="node"
fi

if [ -z "$NODE_CMD" ]; then
    echo "  [ERROR] Node.js not found."
    echo "  Install Node.js 18+ LTS from https://nodejs.org"
    echo "  and ensure it is added to your PATH."
    echo ""
    exit 1
fi

NODE_VER="$($NODE_CMD --version 2>&1)"
echo "  [OK] Found: Node.js $NODE_VER"

# ------------------------------------------------------------
#  Check npm
# ------------------------------------------------------------
NPM_CMD=""
if command -v npm &> /dev/null; then
    NPM_CMD="npm"
fi

if [ -z "$NPM_CMD" ]; then
    echo "  [ERROR] npm not found."
    echo "  It should be installed alongside Node.js."
    echo "  Reinstall from https://nodejs.org"
    echo ""
    exit 1
fi

echo "  [OK] Found: npm $($NPM_CMD --version 2>&1)"

# ------------------------------------------------------------
#  Verify backend dependencies exist (do NOT install)
# ------------------------------------------------------------
if ! "$PYTHON_CMD" -c "import fastapi, uvicorn, sqlalchemy" 2>/dev/null; then
    echo ""
    echo "  [ERROR] Backend Python dependencies are missing."
    echo "  Follow the README setup instructions:"
    echo "    cd backend"
    echo "    pip3 install -r requirements.txt"
    echo ""
    exit 1
fi
echo "  [OK] Backend dependencies ready"

# ------------------------------------------------------------
#  Verify frontend dependencies exist (do NOT install)
# ------------------------------------------------------------
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo ""
    echo "  [ERROR] Frontend node_modules not found."
    echo "  Follow the README setup instructions:"
    echo "    cd frontend"
    echo "    npm install"
    echo ""
    exit 1
fi
echo "  [OK] Frontend dependencies ready"

# ------------------------------------------------------------
#  Seed IOC database if it does not exist
# ------------------------------------------------------------
if [ ! -f "$BACKEND_DIR/data/sentinel.db" ]; then
    echo ""
    echo "  [INFO] First run detected - seeding demo IOC database..."
    cd "$BACKEND_DIR"
    "$PYTHON_CMD" seed_data.py
    cd "$SCRIPT_DIR"
fi

# ------------------------------------------------------------
#  Prepare PID and log directories
# ------------------------------------------------------------
mkdir -p "$PID_DIR" "$LOG_DIR"

# Clean up stale PID files
rm -f "$PID_DIR/backend.pid" "$PID_DIR/frontend.pid"

# ------------------------------------------------------------
#  Start Backend
# ------------------------------------------------------------
echo ""
echo "  [STARTING] Backend on http://127.0.0.1:8000 ..."
cd "$BACKEND_DIR"
"$PYTHON_CMD" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PID_DIR/backend.pid"
cd "$SCRIPT_DIR"

# ------------------------------------------------------------
#  Start Frontend
# ------------------------------------------------------------
echo "  [STARTING] Frontend on http://localhost:5173 ..."
cd "$FRONTEND_DIR"
"$NPM_CMD" run dev > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "$FRONTEND_PID" > "$PID_DIR/frontend.pid"
cd "$SCRIPT_DIR"

# ------------------------------------------------------------
#  Wait for services to start, then open browser
# ------------------------------------------------------------
echo ""
echo "  Waiting 6 seconds for services to start..."
sleep 6

echo "  Opening dashboard in your browser..."
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5173/dashboard 2>/dev/null &
elif command -v open &> /dev/null; then
    open http://localhost:5173/dashboard
else
    echo "  (Could not auto-open browser. Navigate to http://localhost:5173/dashboard)"
fi

echo ""
echo " ==================================="
echo "  SentinelAI is running!"
echo " ==================================="
echo ""
echo "  Frontend:  http://localhost:5173/dashboard"
echo "  Backend:   http://127.0.0.1:8000/docs"
echo ""
echo "  Backend PID:  $BACKEND_PID"
echo "  Frontend PID: $FRONTEND_PID"
echo ""
echo "  To stop, run: ./stop_sentinelai.sh"
echo ""
