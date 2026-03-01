#!/usr/bin/env python3
"""
Setup script for Autonomous DBOps V2
"""

import os
import subprocess
import sys

def setup_project():
    """Initialize the project following all rules"""
    print("🚀 Setting up Autonomous DBOps V2...")
    
    # Create virtual environment
    print("📦 Creating virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", "venv"])
    
    # Install dependencies
    print("📥 Installing dependencies...")
    if os.name == 'nt':  # Windows
        pip_path = "venv\\Scripts\\pip"
    else:  # Unix/Linux/macOS
        pip_path = "venv/bin/pip"
    
    subprocess.run([pip_path, "install", "-r", "requirements.txt"])
    
    # Create directories
    print("📁 Creating project structure...")
    os.makedirs("backups", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    print("✅ Setup complete!")
    print("\n🎯 Next steps:")
    print("1. Set AWS credentials with Secrets Manager access")
    print("2. Start MCP servers (port 8082)")
    print("3. Run: streamlit run frontend/app.py")

if __name__ == "__main__":
    setup_project()
