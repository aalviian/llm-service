#!/bin/bash

# Navigate to project root
cd "$(dirname "$0")"

# Create logs directory if it doesn't exist
mkdir -p logs

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Add src to Python path
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Enable unbuffered Python output to show all print statements
export PYTHONUNBUFFERED=1

# Start celery worker from project root with debug logging
# Redirect all output to terminal
uv run celery -A src.config.celery_app worker -l info -Q default --without-gossip --without-mingle --without-heartbeat 2>&1