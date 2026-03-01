#!/bin/bash
# Start both MCP servers for Autonomous DBOps V2

echo "🚀 Starting Autonomous DBOps V2 MCP Servers"
echo "============================================"


# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping MCP servers..."
    if [[ -n "$AURORA_PID" ]]; then
        kill $AURORA_PID 2>/dev/null
        echo "  - Stopped Aurora MCP Server"
    fi
    if [[ -n "$CLOUDWATCH_PID" ]]; then
        kill $CLOUDWATCH_PID 2>/dev/null
        echo "  - Stopped CloudWatch MCP Server"
    fi
    echo "👋 All servers stopped"
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

echo "📡 Starting Aurora MCP Server (http://localhost:8081/mcp)..."
python mcp/aurora_server.py &
AURORA_PID=$!

echo "📡 Starting CloudWatch MCP Server (http://localhost:8082/mcp)..."
python mcp/cloudwatch_server.py &
CLOUDWATCH_PID=$!

# Wait a moment for servers to start
sleep 3

# Check if servers are running
aurora_running=false
cloudwatch_running=false

if kill -0 $AURORA_PID 2>/dev/null; then
    echo "🟢 Aurora MCP Server: Running (PID $AURORA_PID)"
    aurora_running=true
else
    echo "🔴 Aurora MCP Server: Failed to start"
fi

if kill -0 $CLOUDWATCH_PID 2>/dev/null; then
    echo "🟢 CloudWatch MCP Server: Running (PID $CLOUDWATCH_PID)"
    cloudwatch_running=true
else
    echo "🔴 CloudWatch MCP Server: Failed to start"
fi

if [[ "$aurora_running" == true && "$cloudwatch_running" == true ]]; then
    echo ""
    echo "✅ Both MCP servers are running!"
    echo "🎯 Servers use STDIO transport for MCP protocol"
    echo "💡 Press Ctrl+C to stop all servers"
    echo ""
    
    # Keep script running and monitor servers
    while true; do
        sleep 5
        
        # Check if servers are still running
        if ! kill -0 $AURORA_PID 2>/dev/null; then
            echo "⚠️  Aurora MCP Server stopped unexpectedly"
            break
        fi
        
        if ! kill -0 $CLOUDWATCH_PID 2>/dev/null; then
            echo "⚠️  CloudWatch MCP Server stopped unexpectedly"
            break
        fi
    done
else
    echo ""
    echo "❌ Some servers failed to start"
    cleanup
fi

# Wait for user interrupt
wait
