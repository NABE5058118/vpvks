"""Marshmallow schemas for request validation"""

from functools import wraps
from flask import request, jsonify
from marshmallow import ValidationError


def validate_json(schema_cls):
    """
    Decorator that validates JSON request body against a marshmallow schema class.
    Creates an instance of the schema for each request.
    
    Usage:
        @routes_bp.route('/api/users', methods=['POST'])
        @validate_json(CreateUserSchema)
        def create_user():
            # request.validated_data contains validated data
            user_id = request.validated_data['id']
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'error': 'Request must be JSON',
                    'code': 'INVALID_CONTENT_TYPE'
                }), 415

            schema = schema_cls()
            try:
                validated_data = schema.load(request.get_json())
            except ValidationError as err:
                return jsonify({
                    'error': 'Validation error',
                    'code': 'VALIDATION_ERROR',
                    'details': err.messages
                }), 422

            # Attach validated data to request for use in the route
            request.validated_data = validated_data
            return f(*args, **kwargs)
        return decorated_function
    return decorator
