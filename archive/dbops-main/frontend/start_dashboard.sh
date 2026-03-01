#!/bin/bash
"""
Start Autonomous Database Operations Dashboard
Streamlit frontend for database performance analysis
"""

echo "🚀 Starting Autonomous Database Operations Dashboard"
echo "=================================================="

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not detected. Activating..."
    if [ -f "../venv/bin/activate" ]; then
        source ../venv/bin/activate
        echo "✅ Virtual environment activated"
    else
        echo "❌ Virtual environment not found. Please run from project root:"
        echo "   source venv/bin/activate"
        exit 1
    fi
fi

# Check if MCP servers are running
echo "🔍 Checking MCP server status..."

# Check Aurora MCP server (port 8081)
if curl -s -f http://localhost:8081/mcp > /dev/null 2>&1; then
    echo "✅ Aurora MCP server is running (port 8081)"
else
    echo "⚠️  Aurora MCP server not detected on port 8081"
    echo "   Start with: ./mcp/start_mcp_servers.sh"
fi

# Check CloudWatch MCP server (port 8080)
if curl -s -f http://localhost:8080/mcp > /dev/null 2>&1; then
    echo "✅ CloudWatch MCP server is running (port 8080)"
else
    echo "⚠️  CloudWatch MCP server not detected on port 8080"
    echo "   Start with: ./mcp/start_mcp_servers.sh"
fi

# Check AWS credentials
if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    echo "⚠️  AWS_ACCESS_KEY_ID not set"
    echo "   Set with: export AWS_ACCESS_KEY_ID=your_key"
fi

if [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "⚠️  AWS_SECRET_ACCESS_KEY not set"
    echo "   Set with: export AWS_SECRET_ACCESS_KEY=your_secret"
fi

echo ""
echo "🌐 Starting Streamlit dashboard..."
echo "   Dashboard will be available at: http://localhost:8501"
echo "   Press Ctrl+C to stop"
echo ""

# Start Streamlit dashboard
streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0