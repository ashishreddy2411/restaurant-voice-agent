#!/bin/bash
# Run the restaurant agent.
# Automatically clears port 8081 if a previous instance is still running.

VENV_PYTHON="../.venv/bin/python"

# Kill any previous agent instance holding port 8081
OLD_PID=$(lsof -ti :8081)
if [ -n "$OLD_PID" ]; then
    echo "Stopping previous agent (PID $OLD_PID)..."
    kill -9 $OLD_PID 2>/dev/null
    sleep 1
fi

echo "Starting restaurant agent (production mode — waits for SIP dispatch)..."
$VENV_PYTHON agent.py start
