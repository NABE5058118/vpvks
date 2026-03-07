"""Utility decorators and helper functions"""

import logging
from functools import wraps
from datetime import datetime, timezone
from flask import jsonify

logger = logging.getLogger(__name__)


def get_utc_now():
    return datetime.now(timezone.utc)


def get_utc_now_naive():
    return datetime.utcnow()


def handle_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {e}", exc_info=True)
            return jsonify({'status': 'error', 'error': str(e)}), 500
    return wrapper


def require_json(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        from flask import request
        if not request.is_json:
            return jsonify({'status': 'error', 'error': 'Content-Type must be application/json'}), 400
        return f(*args, **kwargs)
    return wrapper


def validate_required_fields(*required_fields):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            from flask import request
            data = request.get_json()
            if not data:
                return jsonify({'status': 'error', 'error': 'Request body is required'}), 400
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({'status': 'error', 'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_active_subscription(user_model_class):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_id = kwargs.get('user_id')
            if not user_id:
                return jsonify({'status': 'error', 'error': 'user_id is required'}), 400
            user = user_model_class.query.filter_by(id=user_id).first()
            if not user:
                return jsonify({'status': 'error', 'error': 'User not found'}), 404
            if not user.is_subscription_active():
                return jsonify({'status': 'error', 'message': 'Подписка не активна. Пожалуйста, оплатите тариф.'}), 403
            kwargs['user'] = user
            return f(*args, **kwargs)
        return wrapper
    return decorator


def log_execution_time(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        import time
        start = time.time()
        result = f(*args, **kwargs)
        end = time.time()
        logger.info(f"{f.__name__} executed in {end - start:.3f}s")
        return result
    return wrapper
