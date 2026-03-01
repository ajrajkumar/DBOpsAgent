#!/bin/bash
"""
Start Autonomous Database Operations Dashboard
Root-level startup script for Streamlit frontend
"""

echo "🚀 Starting Autonomous Database Operations Dashboard"
echo "=================================================="

# Check if we're in the project root
if [ ! -d "frontend" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    echo "   Current directory: $(pwd)"
    echo "   Expected: autonomous-dbops-v2/"
    exit 1
fi

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not detected. Activating..."
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
        echo "✅ Virtual environment activated"
    else
        echo "❌ Virtual environment not found. Please create it first:"
        echo "   python -m venv .venv"
        echo "   source .venv/bin/activate"
        echo "   pip install -r requirements.txt"
        exit 1
    fi
fi

# Check if required packages are installed
echo "🔍 Checking dependencies..."
python3 -c "import streamlit, pandas, plotly" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Installing frontend dependencies..."
    python3 -m pip install streamlit pandas plotly requests
fi

# Check if MCP servers are running
echo "🔍 Checking MCP server status..."

# Check if MCP server ports are listening
if lsof -i :8081 > /dev/null 2>&1; then
    echo "✅ Aurora MCP server is running (port 8081)"
else
    echo "⚠️  Aurora MCP server not detected on port 8081"
    echo "   Start with: ./mcp/start_mcp_servers.sh"
fi

if lsof -i :8080 > /dev/null 2>&1; then
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

# Change to frontend directory and start Streamlit
cd frontend
python3 -m streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0