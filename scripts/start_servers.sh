#!/bin/bash
# MangaTaro - Start API and Frontend servers

set -e

# Project directory
PROJECT_DIR="/data/mangataro"
cd "$PROJECT_DIR"

# Load nvm for npm
export NVM_DIR="/home/ubuntu/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Activate virtual environment
source .venv/bin/activate

# Function to cleanup on exit
cleanup() {
    echo "Stopping MangaTaro servers..."
    pkill -P $$ || true
    exit 0
}

trap cleanup SIGTERM SIGINT

# Start API server in background
echo "Starting API server on port 8008..."
uvicorn api.main:app --host 0.0.0.0 --port 8008 &
API_PID=$!

# Start frontend server in background
echo "Starting frontend server on port 4343..."
cd frontend
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

echo "MangaTaro started successfully!"
echo "API: http://localhost:8008"
echo "Frontend: http://localhost:4343"

# Wait for both processes
wait $API_PID $FRONTEND_PID
