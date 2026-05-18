#!/bin/bash
# MACD Trading Signal App - macOS/Linux Launcher
# This script sets up the environment and launches the Streamlit app

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=========================================="
echo "MACD Trading Signal - Indian Stocks"
echo "=========================================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed."
    echo "Please install Python 3.8 or higher."
    echo "Visit: https://www.python.org/downloads/"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate
echo "✓ Virtual environment activated"

# Install/upgrade requirements
echo ""
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Update stock list
echo ""
echo "Updating stock list..."
python3 update_stock_list.py

# Launch Streamlit app
echo ""
echo "=========================================="
echo "Launching MACD Trading Signal App..."
echo "=========================================="
echo ""
echo "The app will open in your browser at:"
echo "  http://localhost:8501"
echo ""
echo "To stop the app, press Ctrl+C"
echo ""

streamlit run app.py --logger.level=error
