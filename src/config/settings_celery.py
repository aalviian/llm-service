import os
import sys

# Add the parent directory (src) to Python path first
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Ensure logs directory exists
project_root = os.path.dirname(parent_dir)
logs_dir = os.path.join(project_root, "logs")
os.makedirs(logs_dir, exist_ok=True)

# Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Initialize Django
import django

django.setup()

from celery import Celery
from django.conf import settings

app = Celery("config")

# Load Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Setup Custom queue
app.conf.task_queues = {}
app.conf.beat_schedule = {}

# Auto-discover tasks from installed apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
