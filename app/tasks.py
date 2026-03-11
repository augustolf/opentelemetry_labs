"""
Celery Tasks

Example tasks demonstrating OpenTelemetry tracing:
- Simple tasks with manual spans
- Tasks that make HTTP requests
- Tasks that call other tasks (chaining)
- Long-running tasks with progress tracking
"""

import logging
import random
import time
from typing import Any, Dict, List

import requests
from celery import chain, group
from opentelemetry import trace

from app.celery_app import celery_app
from app.tracing import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


@celery_app.task(bind=True, name="tasks.add")
def add(self, x: int, y: int) -> int:
    """
    Simple addition task.

    Demonstrates basic task with automatic tracing.
    """
    logger.info(f"Adding {x} + {y}")
    result = x + y
    logger.info(f"Result: {result}")
    return result


@celery_app.task(bind=True, name="tasks.multiply")
def multiply(self, x: int, y: int) -> int:
    """
    Simple multiplication task.
    """
    logger.info(f"Multiplying {x} * {y}")
    result = x * y
    logger.info(f"Result: {result}")
    return result


@celery_app.task(bind=True, name="tasks.slow_task")
def slow_task(self, duration: int = 5) -> Dict[str, Any]:
    """
    Simulates a slow-running task.

    Demonstrates:
    - Manual span creation
    - Progress updates
    - Custom span attributes
    """
    logger.info(f"Starting slow task with duration={duration}s")

    with tracer.start_as_current_span("slow_task_processing") as span:
        span.set_attribute("task.duration", duration)
        span.set_attribute("task.id", self.request.id)

        # Simulate work in steps
        steps = 5
        for i in range(steps):
            with tracer.start_as_current_span(f"step_{i+1}") as step_span:
                step_duration = duration / steps
                step_span.set_attribute("step.number", i + 1)
                step_span.set_attribute("step.duration", step_duration)

                time.sleep(step_duration)

                # Update task progress
                progress = ((i + 1) / steps) * 100
                self.update_state(
                    state="PROGRESS",
                    meta={"progress": progress, "step": i + 1, "total_steps": steps}
                )
                logger.info(f"Progress: {progress:.0f}%")

    return {
        "status": "completed",
        "duration": duration,
        "task_id": self.request.id,
    }


@celery_app.task(bind=True, name="tasks.fetch_url")
def fetch_url(self, url: str) -> Dict[str, Any]:
    """
    Fetches content from a URL.

    Demonstrates:
    - Outbound HTTP request tracing (via requests instrumentation)
    - Error handling in tasks
    - Custom span events
    """
    logger.info(f"Fetching URL: {url}")

    current_span = trace.get_current_span()
    current_span.set_attribute("http.url", url)

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        result = {
            "url": url,
            "status_code": response.status_code,
            "content_length": len(response.content),
            "content_type": response.headers.get("Content-Type", "unknown"),
        }

        current_span.set_attribute("http.status_code", response.status_code)
        current_span.add_event("fetch_completed", {"content_length": len(response.content)})

        logger.info(f"Successfully fetched {url}: {response.status_code}")
        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch {url}: {str(e)}")
        current_span.set_attribute("error", True)
        current_span.set_attribute("error.message", str(e))
        current_span.add_event("fetch_failed", {"error": str(e)})
        raise


@celery_app.task(bind=True, name="tasks.process_data")
def process_data(self, data: List[Any]) -> Dict[str, Any]:
    """
    Processes a list of data items.

    Demonstrates:
    - Processing multiple items with individual spans
    - Aggregating results
    """
    logger.info(f"Processing {len(data)} items")

    results = []
    with tracer.start_as_current_span("batch_processing") as span:
        span.set_attribute("batch.size", len(data))

        for i, item in enumerate(data):
            with tracer.start_as_current_span(f"process_item_{i}") as item_span:
                item_span.set_attribute("item.index", i)
                item_span.set_attribute("item.value", str(item))

                # Simulate processing
                time.sleep(random.uniform(0.1, 0.5))
                processed = {"original": item, "processed": f"processed_{item}"}
                results.append(processed)

                logger.info(f"Processed item {i}: {item}")

    return {
        "total_items": len(data),
        "processed_items": len(results),
        "results": results,
    }


@celery_app.task(bind=True, name="tasks.chain_example")
def chain_example(self, value: int) -> int:
    """
    Example task that chains multiple operations.

    Demonstrates context propagation across chained tasks.
    """
    logger.info(f"Chain task received: {value}")

    # Create a chain: add(value, 10) -> multiply(result, 2)
    task_chain = chain(
        add.s(value, 10),
        multiply.s(2),
    )

    # Execute chain and wait for result
    result = task_chain.apply_async()

    return result.get(timeout=30)


@celery_app.task(bind=True, name="tasks.parallel_example")
def parallel_example(self, values: List[int]) -> List[int]:
    """
    Example task that executes tasks in parallel.

    Demonstrates parallel execution with context propagation.
    """
    logger.info(f"Parallel task received: {values}")

    # Create a group of add tasks
    task_group = group(add.s(v, v) for v in values)

    # Execute group and wait for results
    result = task_group.apply_async()

    return result.get(timeout=30)


@celery_app.task(bind=True, name="tasks.error_task")
def error_task(self, should_fail: bool = True) -> str:
    """
    Task that demonstrates error handling and tracing.
    """
    logger.info(f"Error task called with should_fail={should_fail}")

    current_span = trace.get_current_span()
    current_span.set_attribute("task.should_fail", should_fail)

    if should_fail:
        # Simulate random errors
        error_types = [
            ValueError("Invalid value provided"),
            RuntimeError("Unexpected runtime error"),
            ConnectionError("Failed to connect to service"),
        ]
        error = random.choice(error_types)

        current_span.set_attribute("error", True)
        current_span.set_attribute("error.type", type(error).__name__)
        current_span.set_attribute("error.message", str(error))

        logger.error(f"Task failed with error: {error}")
        raise error

    return "Task completed successfully"


@celery_app.task(bind=True, name="tasks.health_check")
def health_check(self) -> Dict[str, Any]:
    """
    Health check task for monitoring.
    """
    logger.info("Running health check")

    return {
        "status": "healthy",
        "task_id": self.request.id,
        "timestamp": time.time(),
    }
