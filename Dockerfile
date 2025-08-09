# Use Python 3.12 slim image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_CACHE_DIR=/tmp/uv-cache

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies
RUN uv sync

# Copy project files
COPY . .

# Create logs directory
RUN mkdir -p logs

# Collect static files
RUN uv run python src/manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f ${BASE_URL:-http://localhost:8000}/health-check/ || exit 1

# Default command
CMD ["uv", "run", "python", "src/manage.py", "runserver", "0.0.0.0:8000"]