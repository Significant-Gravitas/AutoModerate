"""
Error handling utilities for consistent error responses
"""
import logging
from functools import wraps

from flask import flash, jsonify, redirect, request, url_for
from pydantic import BaseModel, ValidationError

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


def validate_json_request(schema_class: BaseModel):
    """
    Decorator to validate JSON request data against a Pydantic schema
    Adds 'validated_data' to the route function's keyword arguments
    """
    def decorator(f):
        @wraps(f)
        async def decorated_function(*args, **kwargs):
            try:
                # Get JSON data from request
                json_data = request.get_json()
                if json_data is None:
                    return api_error_response(
                        "JSON data required",
                        400,
                        "MISSING_JSON_DATA"
                    )

                # Validate against schema
                validated_data = schema_class(**json_data)

                # Add validated data to kwargs
                kwargs['validated_data'] = validated_data

                return await f(*args, **kwargs)

            except ValidationError as e:
                # Format Pydantic validation errors
                error_details = []
                for error in e.errors():
                    field = '.'.join(str(loc) for loc in error['loc'])
                    error_details.append(f"{field}: {error['msg']}")

                return api_error_response(
                    "Invalid input data",
                    400,
                    "VALIDATION_ERROR",
                    {"field_errors": error_details}
                )
            except Exception as e:
                logger.error(f"Validation error in {f.__name__}: {str(e)}")
                return api_error_response("Internal server error", 500)

        return decorated_function
    return decorator


def validate_query_params(schema_class: BaseModel):
    """
    Decorator to validate query parameters against a Pydantic schema
    Adds 'validated_params' to the route function's keyword arguments
    """
    def decorator(f):
        @wraps(f)
        async def decorated_function(*args, **kwargs):
            try:
                # Get query parameters
                query_data = request.args.to_dict()

                # Convert common query param types
                for key, value in query_data.items():
                    # Try to convert numbers
                    if value.isdigit():
                        query_data[key] = int(value)
                    elif value.lower() in ('true', 'false'):
                        query_data[key] = value.lower() == 'true'

                # Validate against schema
                validated_params = schema_class(**query_data)

                # Add validated params to kwargs
                kwargs['validated_params'] = validated_params

                return await f(*args, **kwargs)

            except ValidationError as e:
                # Format Pydantic validation errors
                error_details = []
                for error in e.errors():
                    field = '.'.join(str(loc) for loc in error['loc'])
                    error_details.append(f"{field}: {error['msg']}")

                return api_error_response(
                    "Invalid query parameters",
                    400,
                    "VALIDATION_ERROR",
                    {"field_errors": error_details}
                )
            except Exception as e:
                logger.error(f"Query param validation error in {f.__name__}: {str(e)}")
                return api_error_response("Internal server error", 500)

        return decorated_function
    return decorator
