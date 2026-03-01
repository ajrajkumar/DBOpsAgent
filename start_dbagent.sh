#!/bin/bash

# Function to cleanup background processes
cleanup() {
    echo "Shutting down MCP servers..."
    kill $PID1 $PID2 $PID3 2>/dev/null
    exit 0
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

# Kill any existing processes on the ports
echo "Cleaning up existing processes..."
pkill -f "/workshop/bootstrap/mcp_healthcheck_apgserver.py" 2>/dev/null
pkill -f "/workshop/bootstrap/mcp_cwlogs_apgserver.py" 2>/dev/null
pkill -f "/workshop/bootstrap/mcp_action_apgserver.py" 2>/dev/null
sleep 2

# Start MCP servers in background and store PIDs
echo "Starting MCP servers..."
python /workshop/bootstrap/mcp_healthcheck_apgserver.py >/dev/null 2>&1 &
PID1=$!

python /workshop/bootstrap/mcp_cwlogs_apgserver.py >/dev/null 2>&1 &
PID2=$!

python /workshop/bootstrap/mcp_action_apgserver.py >/dev/null 2>&1 &
PID3=$!

# Wait for servers to start
sleep 3

# Start database agent
echo "Starting Database Agent..."
python /workshop/bootstrap/dbagent_autonomous_baked.py

