#!/bin/bash

# bykilt development helper script
# Usage: ./dev.sh [start|stop|restart|status|logs]

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
PID_FILE="$PROJECT_DIR/bykilt.pid"
LOG_FILE="$PROJECT_DIR/bykilt.log"
PORT=7861

start() {
    echo "🚀 Starting bykilt development server..."

    # Check if already running
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "❌ Server is already running (PID: $PID)"
            echo "   Stop it first with: ./dev.sh stop"
            return 1
        else
            rm "$PID_FILE"
        fi
    fi

    # Activate venv and start server
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    "$VENV_DIR/bin/python" bykilt.py --port $PORT > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"

    echo "✅ Server started (PID: $(cat $PID_FILE))"
    echo "   UI: http://127.0.0.1:$PORT/"
    echo "   Logs: tail -f $LOG_FILE"
}

stop() {
    echo "🛑 Stopping bykilt development server..."

    if [ ! -f "$PID_FILE" ]; then
        echo "❌ No PID file found. Server may not be running."
        return 1
    fi

    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo "✅ Server stopped (PID: $PID)"
        rm "$PID_FILE"
    else
        echo "❌ Process $PID not found"
        rm "$PID_FILE"
    fi
}

restart() {
    echo "🔄 Restarting bykilt development server..."
    stop
    sleep 2
    start
}

status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "✅ Server is running (PID: $PID)"
            echo "   UI: http://127.0.0.1:$PORT/"
            echo "   Logs: $LOG_FILE"
        else
            echo "❌ Server is not running (stale PID file)"
            rm "$PID_FILE"
        fi
    else
        echo "❌ Server is not running"
    fi
}

logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo "❌ Log file not found: $LOG_FILE"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the development server"
        echo "  stop    - Stop the development server"
        echo "  restart - Restart the development server"
        echo "  status  - Show server status"
        echo "  logs    - Show server logs"
        exit 1
        ;;
esac