#!/bin/bash
"""
Start Simple Database Operations Dashboard
"""

echo "🚀 Starting Simple Database Operations Dashboard"
echo "=============================================="

# Activate virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    if [ -f "../.venv/bin/activate" ]; then
        source ../.venv/bin/activate
        echo "✅ Virtual environment activated"
    else
        echo "❌ Virtual environment not found"
        exit 1
    fi
fi

echo "🌐 Starting simple dashboard..."
echo "   Available at: http://localhost:8501"
echo ""

# Start simple dashboard
python3 -m streamlit run simple_dashboard.py --server.port 8501