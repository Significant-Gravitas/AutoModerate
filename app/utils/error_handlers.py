"""
Error handling utilities for consistent error responses
"""
import logging
from functools import wraps

from flask import flash, jsonify, redirect, url_for

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Custom exception for API errors with structured response data"""

    def __init__(self, message, status_code=400, error_code=None, details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}


def api_error_response(message, status_code=400, error_code=None, details=None):
    """Generate standardized API error response"""
    response_data = {
        'success': False,
        'error': message
    }

    if error_code:
        response_data['error_code'] = error_code

    if details:
        response_data['details'] = details

    return jsonify(response_data), status_code


def api_success_response(data=None, message=None):
    """Generate standardized API success response"""
    response_data = {'success': True}

    if message:
        response_data['message'] = message

    if data:
        response_data.update(data)

    return jsonify(response_data)


def handle_api_error(f):
    """Decorator to handle API errors consistently"""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except APIError as e:
            logger.warning(f"API error in {f.__name__}: {e.message}")
            return api_error_response(
                e.message,
                e.status_code,
                e.error_code,
                e.details
            )
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {str(e)}")
            return api_error_response("Internal server error", 500)

    return decorated_function


def web_error_handler(f):
    """Decorator to handle web route errors consistently"""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}")
            flash("An unexpected error occurred. Please try again.", 'error')
            # Try to redirect to a sensible default
            return redirect(url_for('dashboard.index'))

    return decorated_function


def validate_required_fields(data, required_fields):
    """Validate required fields are present in data"""
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
            missing_fields.append(field)

    if missing_fields:
        raise APIError(
            f"Missing required fields: {', '.join(missing_fields)}",
            status_code=400,
            error_code="MISSING_REQUIRED_FIELDS",
            details={"missing_fields": missing_fields}
        )
