#!/bin/bash
# Script to run the Manga Tracker API server

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set default values if not in .env
API_HOST=${API_HOST:-0.0.0.0}
API_PORT=${API_PORT:-8008}

# Run the API server
echo "Starting Manga Tracker API on $API_HOST:$API_PORT"
echo "API Documentation: http://localhost:$API_PORT/docs"
echo "ReDoc: http://localhost:$API_PORT/redoc"
echo ""

uvicorn api.main:app --reload --host "$API_HOST" --port "$API_PORT"
