# CX Service

Customer Experience service that provides automated email reply functionality using Large Language Models (LLM) for complaint categorization and response generation with Gmail integration.

## Features

- **🔄 Automated Email Processing**: Gmail integration with Pub/Sub webhooks for real-time email processing
- **🤖 LLM-Powered Categorization**: Fine-tuned models for complaint email classification with confidence scoring
- **📧 Smart Auto-Reply**: Automated responses for emails with [Test] prefix and high confidence scores
- **⚡ Background Processing**: Celery-based asynchronous email processing with Redis message broker
- **📊 Comprehensive Logging**: Email processing logs with confidence scores and predictions
- **🏥 Health Monitoring**: Multi-service health checks (Database, Redis, Celery)
- **📚 API Documentation**: Interactive Swagger/OpenAPI documentation with authentication
- **🛠️ Development Tools**: Code quality tools (Ruff, MyPy), pre-commit hooks, Docker support
- **🔐 OAuth2 Integration**: Google OAuth2 flow for Gmail access
- **📱 Test Endpoints**: Queue testing and environment variable validation

## Requirements

- **uv** - [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
- **Python 3.12+** - Will be managed by uv
- **PostgreSQL** - Database for storing email logs and templates
- **Redis** - Caching and Celery message broker
- **RabbitMQ** - Alternative message broker (optional)

## Quick Start

### **Option 1: Docker (Recommended)**
```bash
cd cx-service

# Copy environment variables
cp .env.example .env
# Edit .env with your configuration

# Start all services (Django, Celery, Redis, PostgreSQL)
docker-compose up --build

# Access the application
# Web: http://localhost:8000
# API Docs: http://localhost:8000/api/docs/
```

### **Option 2: Local Development**
```bash
cd cx-service

# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv sync

# Copy environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
uv run python src/manage.py migrate

# Start development server
uv run python src/manage.py runserver

# Start Celery worker (in separate terminal)
./start_celery.sh
```

## Project Structure
```
cx-service/
├── .env                          # Environment variables
├── .env.example                  # Environment template
├── .coveragerc                   # Coverage configuration
├── pyproject.toml               # Project configuration
├── uv.lock                      # Dependency lock file
├── example.png                  # API documentation screenshot
├── logs/                        # Application logs
│   ├── requests.log            # HTTP requests
│   └── app.log                 # Application logs
├── .github/                     # GitHub workflows
│   └── workflows/
│       └── quality.yml         # CI/CD pipeline
├── start_celery.sh              # Celery worker startup script
├── test_celery.sh               # Celery configuration test
├── test_coverage.sh             # Test coverage analysis
├── run-mypy                     # MyPy type checking script
└── src/                        # Django source code
    ├── manage.py               # Django management script
    ├── config/                 # Project configuration
    │   ├── settings.py         # Django settings
    │   ├── settings_celery.py  # Celery configuration
    │   ├── celery_app.py       # Celery application
    │   ├── urls.py             # Main URL routing
    │   ├── views.py            # Health check views
    │   ├── julo_models.py      # JuloDB models
    │   ├── db_router.py        # Database routing
    │   ├── wsgi.py             # WSGI application
    │   └── asgi.py             # ASGI application
    ├── swagger/                # API Documentation
    │   ├── __init__.py         # Package initialization
    │   ├── views.py            # Swagger authentication views
    │   ├── urls.py             # Swagger URL routing
    │   └── tests.py            # Swagger tests
    ├── autoreply/              # Auto-reply functionality
    │   ├── models.py           # Email logs, templates, models
    │   ├── views.py            # API endpoints
    │   ├── urls.py             # Autoreply URL routing
    │   ├── tasks.py            # Celery background tasks
    │   ├── services/           # Business logic services
    │   │   └── gmail.py        # Gmail integration service
    │   ├── llm/                # LLM integration
    │   │   └── fine_tuning.py  # Model fine-tuning
    │   ├── fine_tuned_models/  # Model storage
    │   └── tests/              # Autoreply tests
    │       ├── test_models.py  # Model tests
    │       ├── test_views.py   # View tests
    │       ├── test_tasks.py   # Task tests
    │       ├── test_services.py # Service tests
    │       └── test_*.py       # Additional test modules
    ├── tests/                  # Global test modules
    │   └── users/              # User-related tests
    ├── static/                 # Static files
    └── templates/              # HTML templates
        └── swagger/            # Swagger UI templates
            ├── login.html      # Login page
            └── docs.html       # API documentation page
```

## Configuration

### Environment Variables

The project uses environment variables for configuration. Key variables include:

```bash
# Core Django Settings
SECRET_KEY="your-secret-key"
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
TIME_ZONE=Asia/Jakarta
STATIC_URL=/static/
STATIC_ROOT=staticfiles

# Database Configuration (Default)
DB_NAME=your_database_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

# JuloDB Configuration
POSTGRESQL_OPS_NAME=julodb_name
POSTGRESQL_OPS_USER=julodb_user
POSTGRESQL_OPS_PASSWORD=julodb_password
POSTGRESQL_OPS_HOST=localhost
POSTGRESQL_OPS_PORT=5432

# Platform Database Configuration
POSTGRESQL_PLATFORM_OPS_NAME=platform_db_name
POSTGRESQL_PLATFORM_OPS_USER=platform_user
POSTGRESQL_PLATFORM_OPS_PASSWORD=platform_password
POSTGRESQL_PLATFORM_OPS_HOST=localhost
POSTGRESQL_PLATFORM_OPS_PORT=5432

# Redis Configuration
REDIS_USER=
REDIS_PASSWORD=
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1

# Redis Cacheops Configuration
REDIS_CACHEOPS_HOST=localhost
REDIS_CACHEOPS_PORT=6379
REDIS_CACHEOPS_PASSWORD=
REDIS_CACHEOPS_DB=2

# Message Broker (RabbitMQ)
BROKER_URL=amqp://guest:guest@localhost:5672//

# Google OAuth2 Credentials
CX_GOOGLE_OAUTH2_CREDENTIALS='{"web":{"client_id":"your_client_id","client_secret":"your_secret","redirect_uris":["http://localhost:8000/callback/"]}}'

# CORS Configuration
CORS_ALLOWED_ORIGINS=http://localhost:8080,http://localhost:8000
CORS_ALLOWED_ORIGIN_REGEXES=^https://.*\.vercel\.app$

# Monitoring & Observability
SENTRY_DSN=your_sentry_dsn
SENTRY_TRACES_SAMPLE_RATE=0.1
DD_TRACE_ENABLED=true
DD_SERVICE=cx-service
DD_ENV=development
DD_VERSION=1.0.0

# Logging
LOG_PATH=logs
ENVIRONMENT=local
```

## Development

## Docker Commands

```bash
# Start all services
docker-compose up --build

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f web
docker-compose logs -f celery

# Run Django commands
docker-compose exec web python src/manage.py migrate
docker-compose exec web python src/manage.py createsuperuser
docker-compose exec web python src/manage.py shell_plus

# Stop services
docker-compose down

# Rebuild specific service
docker-compose build web
```

### Local Development Commands

```bash
# Install dependencies
uv sync

# Run development server
uv run python src/manage.py runserver

# Run migrations
uv run python src/manage.py migrate

# Create migrations
uv run python src/manage.py makemigrations

# Collect static files
uv run python src/manage.py collectstatic

# Run tests
uv run python src/manage.py test

# Create superuser
uv run python src/manage.py createsuperuser

# Django shell
uv run python src/manage.py shell_plus

# Start Celery worker
./start_celery.sh

# Test Celery configuration
./test_celery.sh

# Run coverage tests
./test_coverage.sh
```

### Code Quality Tools

```bash
# Format code with Ruff
uv run ruff format .

# Lint code with Ruff
uv run ruff check .

# Type checking with MyPy
uv run mypy . or ./run-mypy

# Run all quality checks
uv run ruff check . && uv run ruff format . && uv run mypy .

# Run comprehensive test coverage
./test_coverage.sh
```

### Setup

1. **Environment Variables**
   ```bash
   DEBUG=False
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   SECRET_KEY=your-production-secret
   ```
2. **Static Files**
   ```bash
   uv run python src/manage.py collectstatic --no-input
   ```

3. **Run Migrations**
   ```bash
   uv run python src/manage.py migrate
   ```

4. **Run Django with the datadog**
   ```bash
   uv run ddtrace-run src/manage.py runserver
   ```

### Pre-Commit Hooks
```bash
# Pre Commit install
pre-commit install

# Run Format And Lint check and fix
pre-commit run ruff

# Run checking type with mypy
pre-commit run mypy
```

## Shell Scripts

The project includes several shell scripts for common tasks:

- **`start_celery.sh`** - Start Celery worker with proper configuration
- **`test_celery.sh`** - Test Celery configuration
- **`test_coverage.sh`** - Run comprehensive test coverage analysis
- **`run-mypy`** - Run MyPy type checking

Make scripts executable:
```bash
chmod +x *.sh
```

## API Documentation

The CX Service provides comprehensive API documentation through an integrated Swagger UI interface with custom styling and authentication.

### Accessing API Documentation

1. **Start the development server:**
   ```bash
   uv run python src/manage.py runserver
   ```

2. **Navigate to the API documentation:**
   ```
   http://localhost:8000/api/login/
   ```

3. **Login with JuloDB credentials** to access the interactive documentation

4. **Access Swagger UI:**
   ```
   http://localhost:8000/api/docs/
   ```

### API Documentation Features

- **🔐 Secure Access**: JuloDB authentication required
- **🔄 Interactive Testing**: Test API endpoints directly from the documentation
- **📋 Comprehensive Coverage**: All endpoints documented with examples
- **🚪 Easy Logout**: Integrated logout functionality

### API Documentation Interface

![API Documentation]
<img width="1922" height="949" alt="Screenshot 2025-07-29 at 00 48 31" src="https://github.com/user-attachments/assets/3f56b49b-4ca3-4242-aa59-8cfa7c1a7ec7" />

<img width="1885" height="952" alt="Screenshot 2025-07-29 at 00 48 06" src="https://github.com/user-attachments/assets/818ede10-c97b-4e96-9351-318cbee8e75c" />

*The Swagger UI provides an intuitive interface for exploring and testing all available API endpoints with real-time interaction capabilities.*

### Available API Endpoints

#### Health Check
- **GET** `/health-check/` - System health status

#### Gmail Integration
- **POST** `/autoreply/api/webhook/` - Gmail webhook notifications (Pub/Sub)
- **GET** `/autoreply/api/oauth2/start/` - Start OAuth2 flow
- **GET** `/autoreply/api/oauth2/callback/` - OAuth2 callback
- **POST** `/autoreply/api/gmail/watch/` - Register Gmail watch
- **POST** `/autoreply/api/gmail/stop-watch/` - Stop Gmail watch

#### Testing & Development
- **GET** `/v1/autoreply/test-queue/` - Test Celery queue functionality
- **GET** `/v1/autoreply/test-env/` - Test environment variables access

#### Email Processing
- **Automatic Processing**: Emails with `[Test]` prefix in subject
- **Confidence-based Replies**: Auto-reply for confidence > 80%
- **Manual Review**: Low confidence emails flagged for review

### Authentication

The API documentation requires JuloDB authentication:

1. Navigate to `/api/login/`
2. Enter your JuloDB username and password
3. Access the protected Swagger documentation at `/api/docs/`
4. Use the logout button to end your session

## Email Processing Workflow

1. **📨 Email Received**: Gmail sends Pub/Sub notification to webhook
2. **🔍 Subject Filter**: Only processes emails with `[Test]` prefix
3. **🤖 LLM Classification**: Categorizes email content with confidence score
4. **⚙️ Auto-Reply Logic**:
   - **High Confidence (>80%)**: Sends automatic reply
   - **Low Confidence (<80%)**: Flags for manual review
5. **📝 Logging**: Records all processing steps and results
6. **✓ Mark as Read**: Processed emails marked as read

## Environment Setup

### Required Environment Variables
```bash
# Core Django Settings
SECRET_KEY="your-secret-key"
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (Docker)
DB_HOST=db
DB_PORT=5432
DB_NAME=cx_service
DB_USER=postgres
DB_PASSWORD=postgres

# Redis (Docker)
REDIS_HOST=redis
REDIS_PORT=6379
BROKER_URL=redis://redis:6379/0

# Google Credentials
CX_GOOGLE_OAUTH2_CREDENTIALS='{"web":{"client_id":"...","client_secret":"...","redirect_uris":["..."]}}'
CX_GOOGLE_CREDENTIALS_FILE='{"type":"service_account","project_id":"..."}'
```

## Architecture

### Services
- **🌐 Django Web Server**: API endpoints and webhook handling
- **⚡ Celery Worker**: Background email processing
- **📊 Redis**: Message broker and caching
- **💾 PostgreSQL**: Data persistence
- **🔍 Gmail API**: Email integration with OAuth2

### Key Components
- **🔗 Webhook Handler**: Processes Gmail Pub/Sub notifications
- **🤖 LLM Classifier**: Fine-tuned model for email categorization
- **📧 Auto-Reply Engine**: Template-based response generation
- **📊 Health Monitoring**: Service status and diagnostics

## Development Workflow

### Code Quality
```bash
# Format code with Ruff
uv run ruff format .

# Lint code with Ruff
uv run ruff check . --fix

# Type checking with MyPy
uv run mypy . or ./run-mypy
```

### Testing
```bash
# Run all tests
uv run python src/manage.py test

# Test coverage
./test_coverage.sh

# Test Celery queue
curl -X GET http://localhost:8000/v1/autoreply/test-queue/

# Test environment variables
curl -X GET http://localhost:8000/v1/autoreply/test-env/
```

## Troubleshooting

### Common Issues

**1. Celery Tasks Not Running**
```bash
# Check Redis connection
redis-cli ping

# Test queue functionality
curl -X GET http://localhost:8000/v1/autoreply/test-queue/
```

**2. Gmail API Issues**
```bash
# Check OAuth2 credentials
curl -X GET http://localhost:8000/v1/autoreply/test-env/
```

**3. Environment Variables**
```bash
# Validate JSON format
echo $CX_GOOGLE_OAUTH2_CREDENTIALS | python -m json.tool
```

