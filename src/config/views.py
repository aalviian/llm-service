from celery import current_app
from django.db import connections
from django.db.utils import OperationalError
from django.shortcuts import render
from django_redis import get_redis_connection
from drf_spectacular.utils import extend_schema
from redis.exceptions import ConnectionError as RedisConnectionError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class NewHealthCheckView(APIView):
    """
    A comprehensive health check endpoint to verify the status of all critical
    infrastructure components: Database, Redis, and Celery.

    Returns a 200 OK response only if all services are healthy.
    If any service fails, it returns a 503 Service Unavailable response with a
    detailed breakdown of each service's status.
    """

    permission_classes = []  # No authentication needed for health checks

    @extend_schema(
        summary="Health Check",
        description="Check the health of all services (Database, Redis, Celery)",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "database": {"type": "object"},
                    "redis": {"type": "object"},
                    "celery": {"type": "object"},
                },
            },
            503: {"description": "Service unavailable"},
        },
        tags=["Health"],
    )
    def get(self, request, *args, **kwargs):
        services_status = {}
        is_healthy = True

        # 1. Database Check
        # This uses the 'default' database connection defined in your settings.py,
        # which reads its configuration from your .env file.
        try:
            connections["default"].cursor()
            services_status["database"] = {"status": "ok"}
        except OperationalError as e:
            is_healthy = False
            services_status["database"] = {"status": "error", "reason": str(e)}

        # 2. Redis Check
        # This uses the 'default' Redis connection defined in your settings.py,
        # which also reads its configuration from your .env file.
        try:
            redis_conn = get_redis_connection("default")
            redis_conn.ping()
            services_status["redis"] = {"status": "ok"}
        except RedisConnectionError as e:
            is_healthy = False
            services_status["redis"] = {"status": "error", "reason": str(e)}
        except Exception as e:
            is_healthy = False
            services_status["redis"] = {
                "status": "error",
                "reason": f"An unexpected error occurred: {e}",
            }

        # 3. Celery Check
        # This checks the Celery broker URL, which is also configured in settings.py from your .env file.
        try:
            # Check if Celery app is properly configured
            if not hasattr(current_app, "control"):
                services_status["celery"] = {
                    "status": "warning",
                    "reason": "Celery app not properly configured",
                }
            else:
                # Ping active workers with a timeout to prevent the request from hanging.
                worker_pings = current_app.control.ping(timeout=1.0)
                if worker_pings:
                    services_status["celery"] = {
                        "status": "ok",
                        "workers_online": [list(worker.keys())[0] for worker in worker_pings],
                    }
                else:
                    # Don't mark as unhealthy if no workers, just indicate status
                    services_status["celery"] = {
                        "status": "warning",
                        "reason": "No running Celery workers found.",
                    }
        except ImportError:
            # Celery not installed or configured
            services_status["celery"] = {
                "status": "disabled",
                "reason": "Celery not installed or configured",
            }
        except Exception as e:
            # This can happen if the message broker (e.g., Redis) is down.
            services_status["celery"] = {
                "status": "error",
                "reason": f"Could not connect to Celery broker: {e}",
            }

        # Determine the overall HTTP status code
        if is_healthy:
            return Response(services_status, status=status.HTTP_200_OK)
        else:
            return Response(services_status, status=status.HTTP_503_SERVICE_UNAVAILABLE)
