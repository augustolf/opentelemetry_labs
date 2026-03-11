"""
Flask Application Entry Point

OpenTelemetry instrumentation is handled automatically by `opentelemetry-instrument`.
"""

import logging
import os

from flask import Flask, jsonify

from app.api import api

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """
    Application factory for Flask.

    Returns:
        Configured Flask application instance
    """
    # Create Flask app
    app = Flask(__name__)

    # Configuration
    app.config.update(
        DEBUG=os.getenv("FLASK_DEBUG", "false").lower() == "true",
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret-key"),
        JSON_SORT_KEYS=False,
    )

    # Register blueprints
    app.register_blueprint(api)

    # Root routes
    @app.route("/")
    def index():
        """Root endpoint with API information."""
        return jsonify({
            "service": "opentelemetry-celery-lab",
            "version": "1.0.0",
            "endpoints": {
                "health": "/api/health",
                "tasks": {
                    "add": "POST /api/task/add",
                    "multiply": "POST /api/task/multiply",
                    "slow": "POST /api/task/slow",
                    "fetch": "POST /api/task/fetch",
                    "process": "POST /api/task/process",
                    "chain": "POST /api/task/chain",
                    "parallel": "POST /api/task/parallel",
                    "error": "POST /api/task/error",
                    "sync": "GET /api/task/sync",
                },
                "status": "GET /api/task/<task_id>/status",
                "result": "GET /api/task/<task_id>/result",
            },
            "tracing": {
                "jaeger_ui": "http://localhost:16686",
                "flower_ui": "http://localhost:5555",
                "rabbitmq_ui": "http://localhost:15672",
            },
        })

    @app.route("/health")
    def health():
        """Simple health check endpoint."""
        return jsonify({"status": "healthy"})

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found", "status": 404}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({"error": "Internal server error", "status": 500}), 500

    logger.info("Flask application created and configured")
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    # Development server
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        debug=True,
    )
