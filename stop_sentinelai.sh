#!/usr/bin/env bash
# ============================================================
#  SentinelAI - Stop Script (Linux / macOS)
#  Stops only the processes started by launch_sentinelai.sh.
#  Uses PID files for precision — never kills unrelated processes.
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="$SCRIPT_DIR/.sentinelai_pids"
LOG_DIR="$SCRIPT_DIR/.sentinelai_logs"

echo ""
echo " ==================================="
echo "  SentinelAI - Stopping Services..."
echo " ==================================="
echo ""

FOUND_BACKEND=0
FOUND_FRONTEND=0

# ------------------------------------------------------------
#  Stop Backend
# ------------------------------------------------------------
if [ -f "$PID_DIR/backend.pid" ]; then
    BACKEND_PID="$(cat "$PID_DIR/backend.pid")"
    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "  Stopping Backend (PID $BACKEND_PID) and all child processes..."
        kill -- -"$BACKEND_PID" 2>/dev/null || kill "$BACKEND_PID" 2>/dev/null || true
        # Wait briefly for graceful shutdown
        sleep 1
        # Force kill if still running
        kill -0 "$BACKEND_PID" 2>/dev/null && kill -9 "$BACKEND_PID" 2>/dev/null || true
        FOUND_BACKEND=1
    fi
    rm -f "$PID_DIR/backend.pid"
fi

if [ "$FOUND_BACKEND" -eq 0 ]; then
    echo "  [INFO] No SentinelAI Backend process found (already stopped or never started)."
fi

# ------------------------------------------------------------
#  Stop Frontend
# ------------------------------------------------------------
if [ -f "$PID_DIR/frontend.pid" ]; then
    FRONTEND_PID="$(cat "$PID_DIR/frontend.pid")"
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "  Stopping Frontend (PID $FRONTEND_PID) and all child processes..."
        kill -- -"$FRONTEND_PID" 2>/dev/null || kill "$FRONTEND_PID" 2>/dev/null || true
        sleep 1
        kill -0 "$FRONTEND_PID" 2>/dev/null && kill -9 "$FRONTEND_PID" 2>/dev/null || true
        FOUND_FRONTEND=1
    fi
    rm -f "$PID_DIR/frontend.pid"
fi

if [ "$FOUND_FRONTEND" -eq 0 ]; then
    echo "  [INFO] No SentinelAI Frontend process found (already stopped or never started)."
fi

# ------------------------------------------------------------
#  Clean up
# ------------------------------------------------------------
rm -rf "$PID_DIR" "$LOG_DIR"

echo ""
echo " ==================================="
echo "  SentinelAI stopped."
echo " ==================================="
echo ""
