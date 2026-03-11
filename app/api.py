"""
Flask API Routes

REST API endpoints for triggering Celery tasks and demonstrating
OpenTelemetry tracing across HTTP requests and task execution.
"""

import logging
from typing import Any, Dict

from flask import Blueprint, jsonify, request
from opentelemetry import trace

from app.tasks import (
    add,
    multiply,
    slow_task,
    fetch_url,
    process_data,
    chain_example,
    parallel_example,
    error_task,
    health_check,
)
from app.tracing import get_tracer
from app.celery_app import celery_app

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

# Create Blueprint
api = Blueprint("api", __name__, url_prefix="/api")


@api.route("/health", methods=["GET"])
def api_health() -> Dict[str, Any]:
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "flask-api",
    })


@api.route("/task/add", methods=["POST"])
def trigger_add():
    """
    Trigger an add task.

    Body: {"x": 10, "y": 20}
    """
    data = request.get_json() or {}
    x = data.get("x", 10)
    y = data.get("y", 20)

    logger.info(f"Triggering add task: {x} + {y}")

    # Add custom span for API processing
    with tracer.start_as_current_span("prepare_add_task") as span:
        span.set_attribute("task.x", x)
        span.set_attribute("task.y", y)

        # Trigger task asynchronously
        result = add.delay(x, y)

    return jsonify({
        "task_id": result.id,
        "status": "PENDING",
        "task": "add",
        "params": {"x": x, "y": y},
    })


@api.route("/task/multiply", methods=["POST"])
def trigger_multiply():
    """
    Trigger a multiply task.

    Body: {"x": 5, "y": 10}
    """
    data = request.get_json() or {}
    x = data.get("x", 5)
    y = data.get("y", 10)

    logger.info(f"Triggering multiply task: {x} * {y}")

    result = multiply.delay(x, y)

    return jsonify({
        "task_id": result.id,
        "status": "PENDING",
        "task": "multiply",
        "params": {"x": x, "y": y},
    })


@api.route("/task/slow", methods=["POST"])
def trigger_slow_task():
    """
    Trigger a slow-running task.

    Body: {"duration": 10}
    """
    data = request.get_json() or {}
    duration = data.get("duration", 5)

    logger.info(f"Triggering slow task with duration={duration}s")

    result = slow_task.delay(duration)

    return jsonify({
        "task_id": result.id,
        "status": "PENDING",
        "task": "slow_task",
        "params": {"duration": duration},
    })


@api.route("/task/fetch", methods=["POST"])
def trigger_fetch_url():
    """
    Trigger a URL fetch task.

    Body: {"url": "https://httpbin.org/json"}
    """
    data = request.get_json() or {}
    url = data.get("url", "https://httpbin.org/json")

    logger.info(f"Triggering fetch task for URL: {url}")

    with tracer.start_as_current_span("prepare_fetch_task") as span:
        span.set_attribute("http.url", url)
        result = fetch_url.delay(url)

    return jsonify({
        "task_id": result.id,
        "status": "PENDING",
        "task": "fetch_url",
        "params": {"url": url},
    })


@api.route("/task/process", methods=["POST"])
def trigger_process_data():
    """
    Trigger a data processing task.

    Body: {"data": [1, 2, 3, 4, 5]}
    """
    data = request.get_json() or {}
    items = data.get("data", [1, 2, 3, 4, 5])

    logger.info(f"Triggering process task with {len(items)} items")

    result = process_data.delay(items)

    return jsonify({
        "task_id": result.id,
        "status": "PENDING",
        "task": "process_data",
        "params": {"data": items},
    })


@api.route("/task/chain", methods=["POST"])
def trigger_chain():
    """
    Trigger a chained task execution.

    Body: {"value": 5}
    """
    data = request.get_json() or {}
    value = data.get("value", 5)

    logger.info(f"Triggering chain task with value={value}")

    result = chain_example.delay(value)

    return jsonify({
        "task_id": result.id,
        "status": "PENDING",
        "task": "chain_example",
        "params": {"value": value},
    })


@api.route("/task/parallel", methods=["POST"])
def trigger_parallel():
    """
    Trigger parallel task execution.

    Body: {"values": [1, 2, 3, 4, 5]}
    """
    data = request.get_json() or {}
    values = data.get("values", [1, 2, 3, 4, 5])

    logger.info(f"Triggering parallel task with values={values}")

    result = parallel_example.delay(values)

    return jsonify({
        "task_id": result.id,
        "status": "PENDING",
        "task": "parallel_example",
        "params": {"values": values},
    })


@api.route("/task/error", methods=["POST"])
def trigger_error_task():
    """
    Trigger a task that may fail.

    Body: {"should_fail": true}
    """
    data = request.get_json() or {}
    should_fail = data.get("should_fail", True)

    logger.info(f"Triggering error task with should_fail={should_fail}")

    result = error_task.delay(should_fail)

    return jsonify({
        "task_id": result.id,
        "status": "PENDING",
        "task": "error_task",
        "params": {"should_fail": should_fail},
    })


@api.route("/task/sync", methods=["GET"])
def trigger_sync_add():
    """
    Execute an add task synchronously and return the result.

    Useful for demonstrating end-to-end tracing.
    """
    x, y = 10, 20

    logger.info(f"Executing sync add task: {x} + {y}")

    with tracer.start_as_current_span("sync_add_execution") as span:
        span.set_attribute("task.x", x)
        span.set_attribute("task.y", y)

        # Execute synchronously with timeout
        async_result = add.delay(x, y)
        result = async_result.get(timeout=10)

        span.set_attribute("task.result", result)

    return jsonify({
        "task_id": async_result.id,
        "status": "SUCCESS",
        "task": "add",
        "params": {"x": x, "y": y},
        "result": result,
    })


@api.route("/task/<task_id>/status", methods=["GET"])
def get_task_status(task_id: str):
    """
    Get the status of a task by ID.
    """
    logger.info(f"Checking status of task: {task_id}")

    result = celery_app.AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
    }

    if result.ready():
        if result.successful():
            response["result"] = result.result
        elif result.failed():
            response["error"] = str(result.result)
    elif result.status == "PROGRESS":
        response["progress"] = result.info

    return jsonify(response)


@api.route("/task/<task_id>/result", methods=["GET"])
def get_task_result(task_id: str):
    """
    Get the result of a completed task.

    Blocks until the task completes (with timeout).
    """
    timeout = request.args.get("timeout", 30, type=int)

    logger.info(f"Getting result for task: {task_id} (timeout={timeout}s)")

    result = celery_app.AsyncResult(task_id)

    try:
        task_result = result.get(timeout=timeout)
        return jsonify({
            "task_id": task_id,
            "status": "SUCCESS",
            "result": task_result,
        })
    except Exception as e:
        return jsonify({
            "task_id": task_id,
            "status": "ERROR",
            "error": str(e),
        }), 500
