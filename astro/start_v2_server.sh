#!/bin/bash
# Start Astro V2 API Server

set -e  # Exit on error

echo "🚀 Starting Astro V2 API Server..."

# Navigate to astro root and activate virtual environment
cd /Users/rishimeka/Documents/Code/astrix-labs/astro
source .venv/bin/activate

# Install packages in editable mode (only if not already installed)
echo "📦 Installing packages in editable mode..."
pip install -q -e ./astro
pip install -q -e ./astro-api
pip install -q -e ./astro-mongodb

# Start the API server
echo "✅ Packages installed. Starting server on http://localhost:8000"
cd astro-api
python -m uvicorn astro_api.main:app --port 8000
