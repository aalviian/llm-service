import os

from celery import Celery

# Create Celery app with minimal configuration
app = Celery("cx-service")

# Configure Celery with environment variables
app.conf.update(
    broker_url=os.environ.get("BROKER_URL", "redis://localhost:6379/0"),
    result_backend="rpc://",
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    timezone="Asia/Jakarta",
)

# Autodiscover tasks from installed apps
app.autodiscover_tasks(['autoreply'])

# Ensure tasks are properly registered
app.conf.task_routes = {
    'autoreply.tasks.*': {'queue': 'default'},
}

# Enable task tracking
app.conf.task_track_started = True
app.conf.task_send_sent_event = True
