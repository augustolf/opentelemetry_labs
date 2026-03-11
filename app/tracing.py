"""
OpenTelemetry Helpers

Provides convenience functions for manual instrumentation (custom spans/metrics)
on top of the automatic instrumentation provided by `opentelemetry-instrument`.

All SDK initialization, exporter configuration and library instrumentation
(Flask, Celery, requests, logging) is handled automatically by the
`opentelemetry-instrument` agent — no manual setup is needed.
"""

from opentelemetry import trace, metrics


def get_tracer(name: str = __name__):
    """Get a tracer instance for manual span creation."""
    return trace.get_tracer(name)


def get_meter(name: str = __name__):
    """Get a meter instance for custom metrics."""
    return metrics.get_meter(name)
    return metrics.get_meter(name)
