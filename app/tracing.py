"""
OpenTelemetry Tracing Configuration

This module sets up OpenTelemetry instrumentation for:
- Flask (HTTP requests/responses)
- Celery (task execution)
- Requests (outbound HTTP calls)
- Logging (structured logs with trace correlation)
"""

import logging
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# Metrics (optional - uncomment to enable)
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

# Logs
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter


logger = logging.getLogger(__name__)


def get_resource() -> Resource:
    """Create OpenTelemetry resource with service information."""
    service_name = os.getenv("OTEL_SERVICE_NAME", "unknown-service")
    service_version = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
    environment = os.getenv("DEPLOYMENT_ENVIRONMENT", "development")

    return Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": environment,
    })


def setup_tracing() -> None:
    """Configure OpenTelemetry tracing with OTLP exporter."""
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")

    # Create resource
    resource = get_resource()

    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)

    # Create OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=f"{otlp_endpoint}/v1/traces",
    )

    # Add batch processor
    tracer_provider.add_span_processor(
        BatchSpanProcessor(otlp_exporter)
    )

    # Set global tracer provider
    trace.set_tracer_provider(tracer_provider)

    logger.info(f"Tracing configured with endpoint: {otlp_endpoint}")


def setup_metrics() -> None:
    """Configure OpenTelemetry metrics with OTLP exporter."""
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")

    # Create resource
    resource = get_resource()

    # Create OTLP metric exporter
    metric_exporter = OTLPMetricExporter(
        endpoint=f"{otlp_endpoint}/v1/metrics",
    )

    # Create metric reader
    metric_reader = PeriodicExportingMetricReader(
        exporter=metric_exporter,
        export_interval_millis=60000,  # Export every 60 seconds
    )

    # Create meter provider
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader],
    )

    # Set global meter provider
    metrics.set_meter_provider(meter_provider)

    logger.info(f"Metrics configured with endpoint: {otlp_endpoint}")


def setup_logging() -> None:
    """Configure OpenTelemetry logging with OTLP exporter."""
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")

    # Create resource
    resource = get_resource()

    # Create logger provider
    logger_provider = LoggerProvider(resource=resource)

    # Create OTLP log exporter
    log_exporter = OTLPLogExporter(
        endpoint=f"{otlp_endpoint}/v1/logs",
    )

    # Add batch processor
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(log_exporter)
    )

    # Set global logger provider
    set_logger_provider(logger_provider)

    # Add OpenTelemetry handler to root logger
    handler = LoggingHandler(
        level=logging.INFO,
        logger_provider=logger_provider,
    )
    logging.getLogger().addHandler(handler)

    logger.info(f"Logging configured with endpoint: {otlp_endpoint}")


def instrument_flask(app) -> None:
    """Instrument Flask application."""
    FlaskInstrumentor().instrument_app(app)
    logger.info("Flask instrumentation enabled")


def instrument_celery() -> None:
    """Instrument Celery for task tracing."""
    CeleryInstrumentor().instrument()
    logger.info("Celery instrumentation enabled")


def instrument_requests() -> None:
    """Instrument requests library for outbound HTTP tracing."""
    RequestsInstrumentor().instrument()
    logger.info("Requests instrumentation enabled")


def instrument_logging() -> None:
    """Instrument logging for trace correlation."""
    LoggingInstrumentor().instrument(
        set_logging_format=True,
        log_level=logging.INFO,
    )
    logger.info("Logging instrumentation enabled")


def init_telemetry(flask_app=None) -> None:
    """
    Initialize all OpenTelemetry components.

    Args:
        flask_app: Optional Flask application instance to instrument
    """
    # Configure logging first for better visibility
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s] - %(message)s',
    )

    # Setup exporters
    setup_tracing()
    setup_metrics()
    setup_logging()

    # Instrument libraries
    instrument_celery()
    instrument_requests()
    instrument_logging()

    # Instrument Flask if provided
    if flask_app:
        instrument_flask(flask_app)

    logger.info("OpenTelemetry initialization complete")


def get_tracer(name: str = __name__):
    """Get a tracer instance for manual instrumentation."""
    return trace.get_tracer(name)


def get_meter(name: str = __name__):
    """Get a meter instance for custom metrics."""
    return metrics.get_meter(name)
