#!/bin/bash

# Navigate to project root
cd "$(dirname "$0")"

echo "Running comprehensive tests for autoreply app..."

# Run tests with coverage
uv run coverage run \
    --source=src/autoreply,src/swagger \
    --omit=src/autoreply/migrations/*,src/autoreply/tests/*,src/swagger/tests.py,src/config/* \
    src/manage.py test autoreply.tests swagger.tests -v 2

# Generate detailed coverage report
echo ""
echo "=================================================="
echo "COVERAGE REPORT"
echo "=================================================="

uv run coverage report --show-missing

# Generate HTML report
uv run coverage html

echo ""
echo "HTML coverage report: htmlcov/index.html"

# Check coverage percentage
COVERAGE=$(uv run coverage report --format=total)

echo ""
echo "Total Coverage: ${COVERAGE}%"

if [ "$COVERAGE" -eq 100 ]; then
    echo "🎉 SUCCESS: 100% coverage achieved!"
    exit 0
else
    echo "❌ Coverage is ${COVERAGE}%, need to reach 100%"
    exit 1
fi