#!/bin/bash
# Start Astro V2 API Server

cd /Users/rishimeka/Documents/Code/astrix-labs/astro
source .venv/bin/activate
cd astro-api
python -m uvicorn astro_api.main:app --port 8000
