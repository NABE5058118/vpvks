"""Global error handler middleware for Flask application"""

import logging
import traceback
from flask import jsonify

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """Register global error handlers for Flask application"""

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error):
        """Catch-all handler for unhandled exceptions"""
        error_id = id(error)
        logger.error(
            f"Unhandled exception #{error_id}: {str(error)}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        return jsonify({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'error_id': error_id
        }), 500

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found errors"""
        return jsonify({
            'error': 'Resource not found',
            'code': 'NOT_FOUND'
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle 405 Method Not Allowed errors"""
        return jsonify({
            'error': 'Method not allowed',
            'code': 'METHOD_NOT_ALLOWED'
        }), 405

    @app.errorhandler(400)
    def handle_bad_request(error):
        """Handle 400 Bad Request errors"""
        return jsonify({
            'error': 'Bad request',
            'code': 'BAD_REQUEST',
            'message': str(error.description) if hasattr(error, 'description') else None
        }), 400

    @app.errorhandler(422)
    def handle_validation_error(error):
        """Handle 422 Unprocessable Entity errors (marshmallow validation)"""
        messages = error.messages if hasattr(error, 'messages') else {}
        return jsonify({
            'error': 'Validation error',
            'code': 'VALIDATION_ERROR',
            'details': messages
        }), 422

    @app.errorhandler(429)
    def handle_rate_limit(error):
        """Handle 429 Too Many Requests errors"""
        return jsonify({
            'error': 'Too many requests',
            'code': 'RATE_LIMITED',
            'message': 'Please try again later'
        }), 429

    app.logger.info("Global error handlers registered successfully")
