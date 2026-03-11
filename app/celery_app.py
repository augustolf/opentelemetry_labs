"""
Celery Application Configuration

Configures Celery with RabbitMQ broker and OpenTelemetry instrumentation.
"""

import os
from celery import Celery

# Import tracing setup
from app.tracing import setup_tracing, setup_metrics, setup_logging, instrument_celery, instrument_requests

# Initialize OpenTelemetry before creating Celery app
setup_tracing()
setup_metrics()
setup_logging()
instrument_celery()
instrument_requests()

# Get broker URL from environment
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "rpc://")

# Create Celery application
celery_app = Celery(
    "tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Result settings
    result_expires=3600,  # Results expire after 1 hour

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=2,

    # Retry settings
    broker_connection_retry_on_startup=True,

    # Task tracking
    task_track_started=True,
    task_send_sent_event=True,

    # Task routes (optional - for task routing)
    # task_routes={
    #     'app.tasks.heavy_task': {'queue': 'heavy'},
    #     'app.tasks.quick_task': {'queue': 'quick'},
    # },
)

# Optional: Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Example: Run health check every 5 minutes
    # 'health-check-every-5-minutes': {
    #     'task': 'app.tasks.health_check',
    #     'schedule': 300.0,
    # },
}
