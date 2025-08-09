#!/bin/bash

# Navigate to project root
cd "$(dirname "$0")"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Add src to Python path
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

echo "Testing Celery configuration..."

# Test the simplified Celery app
if uv run python -c "
import sys
sys.path.insert(0, 'src')
try:
    from config.celery_app import app
    print('✅ Celery configuration loaded successfully')
    print(f'Celery app: {app}')
    print(f'Broker URL: {app.conf.broker_url}')
except Exception as e:
    print(f'❌ Error loading Celery: {e}')
    sys.exit(1)
"; then
    echo "🎉 Celery test passed!"
    exit 0
else
    echo "❌ Celery test failed!"
    exit 1
fi