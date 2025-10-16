import re
from functools import wraps
from typing import Callable

from flask import Blueprint, current_app, jsonify, render_template, request

from app.schemas import ContentListRequest, ModerateContentRequest
from app.services.database_service import db_service
from app.services.error_tracker import error_tracker
from app.services.moderation_orchestrator import ModerationOrchestrator
from app.utils.error_handlers import (
    api_error_response,
    api_success_response,
    handle_api_error,
    validate_json_request,
    validate_query_params,
)

api_bp = Blueprint('api', __name__)


def require_api_key(f: Callable) -> Callable:
    """Decorator to require valid API key for API endpoints"""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        api_key = request.headers.get(
            'X-API-Key') or request.args.get('api_key')

        if not api_key:
            return api_error_response('API key required', 401)

        # Validate API key format
        if not _is_valid_api_key_format(api_key):
            return api_error_response('Invalid API key format', 401)

        # Clean API key (already validated by regex)
        api_key = api_key.strip()

        key_obj = await db_service.get_api_key_by_value(api_key)
        if not key_obj or not key_obj.is_active:
            return api_error_response('Invalid API key', 401)

        # Increment usage counter
        await db_service.update_api_key_usage(key_obj)

        # Add to request context
        request.api_key = key_obj
        request.project = key_obj.project

        return await f(*args, **kwargs)
    return decorated_function


@api_bp.route('/moderate', methods=['POST'])
@require_api_key
@validate_json_request(ModerateContentRequest)
@handle_api_error
async def moderate_content(validated_data=None):
    """
    Main API endpoint for content moderation
    """
    import time

    # Start timing the entire request
    request_start_time = time.time()

    # Extract validated data
    content_type = validated_data.type
    content_data = validated_data.content
    meta_data = validated_data.metadata or {}

    # Validate and sanitize content
    if not content_data or not isinstance(content_data, str):
        return api_error_response('Content is required and must be text', 400)

    max_content_size = 5000000  # 5MB limit (increased from 1MB)
    content_size_kb = len(content_data) // 1000
    current_app.logger.info(f'Content moderation request: {content_size_kb}KB')

    if len(content_data) > max_content_size:
        current_app.logger.warning(f'Content too large: {content_size_kb}KB > {max_content_size // 1000}KB')
        return api_error_response(f'Content too large (max {max_content_size // 1000}KB)', 400)

    if len(content_data.strip()) == 0:
        return api_error_response('Content cannot be empty', 400)

    # Validate content type
    if content_type not in ['text', 'markdown', 'html']:
        return api_error_response('Invalid content type', 400)

    # Sanitize metadata
    if meta_data and not isinstance(meta_data, dict):
        return api_error_response('Metadata must be a dictionary', 400)

    # Validate metadata size (defense in depth - also validated in schema)
    max_metadata_size = 10000  # 10KB limit
    if meta_data and len(str(meta_data)) > max_metadata_size:
        return api_error_response(f'Metadata too large (max {max_metadata_size // 1000}KB)', 400)

    # Additional metadata security checks
    if meta_data:
        # Prevent metadata keys that could cause issues
        forbidden_keys = ['__class__', '__module__', 'password', 'token', 'secret', 'key']
        for key in meta_data.keys():
            if any(forbidden in key.lower() for forbidden in forbidden_keys):
                return api_error_response(f'Forbidden metadata key: {key}', 400)

    # Track API user if user_id is provided in metadata
    if meta_data and 'user_id' in meta_data:
        external_user_id = str(meta_data['user_id']).strip()

        # Validate user_id format
        if not _is_valid_user_id(external_user_id):
            return api_error_response('Invalid user_id format', 400)

        # User ID already validated by regex, no HTML escaping needed for database storage
        external_user_id = external_user_id

        # Find or create API user using centralized service (returns user ID)
        api_user_id = await db_service.get_or_create_api_user(
            external_user_id=external_user_id,
            project_id=request.project.id
        )
    else:
        api_user_id = None

    # Create content record using database service
    content_id = await db_service.create_content(
        project_id=request.project.id,
        content_text=str(content_data),
        content_type=content_type,
        api_user_id=api_user_id,
        meta_data=meta_data if meta_data else None
    )

    if not content_id:
        error_msg = "Failed to create content record"
        current_app.logger.error(f"{error_msg} - Project: {request.project.id}")
        error_tracker.track_error('api', error_msg, details={'project_id': request.project.id})
        return api_error_response(error_msg, 500, error_code="CONTENT_CREATION_FAILED")

    # Start moderation process
    moderation_orchestrator = ModerationOrchestrator()
    result = await moderation_orchestrator.moderate_content(
        content_id, request_start_time)

    # Check if moderation encountered an error
    if 'error' in result:
        error_msg = result.get('error', 'Unknown moderation error')
        current_app.logger.error(f"Moderation error for content {content_id}: {error_msg}")
        error_tracker.track_error('api', error_msg, content_id=content_id)

        # ALWAYS return content_id even on error, but sanitize error message
        return jsonify({
            'success': False,
            'error': 'An error occurred during content moderation',
            'content_id': content_id,
            'status': result.get('decision', 'rejected'),
            'moderation_results': result.get('results', []),
            'error_code': 'MODERATION_ERROR'
        }), 500

    return api_success_response({
        'content_id': content_id,
        'status': result.get('decision', 'pending'),
        'moderation_results': result.get('results', [])
    })


@api_bp.route('/content/<content_id>', methods=['GET'])
@require_api_key
async def get_content(content_id):
    """
    Get content and its moderation results
    """
    # Validate and sanitize content_id
    if not content_id or not _is_valid_uuid(content_id):
        return api_error_response('Invalid content ID format', 400)

    content_id = content_id.strip()

    content = await db_service.get_content_by_id_and_project(content_id, request.project.id)

    if not content:
        return api_error_response('Content not found', 404)

    return api_success_response({
        'content': content.to_dict()
    })


@api_bp.route('/content', methods=['GET'])
@require_api_key
@validate_query_params(ContentListRequest)
async def list_content(validated_params=None):
    """
    List content for the project with pagination
    """
    page = validated_params.page
    per_page = validated_params.per_page
    status = validated_params.status

    offset = (page - 1) * per_page
    content_items = await db_service.get_project_content_with_filters(
        project_id=request.project.id,
        status=status,
        limit=per_page,
        offset=offset
    )

    return jsonify({
        'success': True,
        'content': [item.to_dict() for item in content_items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'has_more': len(content_items) == per_page
        }
    })


@api_bp.route('/stats', methods=['GET'])
@require_api_key
async def get_stats():
    """
    Get moderation statistics for the project
    """
    project_id = request.project.id

    stats = await db_service.get_content_counts_by_status(project_id)
    total = stats['total']
    approved = stats['approved']

    return jsonify({
        'success': True,
        'stats': {
            'total_content': total,
            'approved': approved,
            'rejected': stats['rejected'],
            'flagged': stats['flagged'],
            'pending': stats['pending'],
            'approval_rate': (approved / total * 100) if total > 0 else 0
        }
    })


@api_bp.route('/health', methods=['GET'])
async def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'healthy',
        'service': 'AutoModerate API',
        'version': '1.0.0'
    })


@api_bp.route('/test/error', methods=['GET'])
async def test_error():
    """
    Test endpoint to trigger various exceptions for error monitoring (e.g., Sentry).

    Usage:
        GET /api/test/error                      - Triggers ZeroDivisionError (default)
        GET /api/test/error?type=divide_by_zero  - Triggers ZeroDivisionError
        GET /api/test/error?type=key_error       - Triggers KeyError
        GET /api/test/error?type=value_error     - Triggers ValueError
        GET /api/test/error?type=type_error      - Triggers TypeError
        GET /api/test/error?type=index_error     - Triggers IndexError
        GET /api/test/error?type=attribute_error - Triggers AttributeError

    WARNING: This endpoint is for testing purposes only. Remove or disable in production.
    """
    error_type = request.args.get('type', 'divide_by_zero').strip().lower()

    current_app.logger.info(f"Test error endpoint triggered with type: {error_type}")

    if error_type == 'divide_by_zero':
        1 / 0  # ZeroDivisionError
    elif error_type == 'key_error':
        d = {}
        return d['nonexistent_key']  # KeyError
    elif error_type == 'value_error':
        int('not a number')  # ValueError
    elif error_type == 'type_error':
        None + 5  # TypeError
    elif error_type == 'index_error':
        lst = []
        return lst[999]  # IndexError
    elif error_type == 'attribute_error':
        obj = None
        return obj.some_attribute  # AttributeError
    else:
        return api_error_response(
            f'Unknown error type: {error_type}. Available types: '
            'divide_by_zero, key_error, value_error, type_error, index_error, attribute_error',
            400
        )

    return jsonify({'status': 'no error triggered'})


def _is_valid_api_key_format(api_key):
    """Validate API key format"""
    if not api_key or len(api_key) < 10 or len(api_key) > 100:
        return False
    # API keys should start with 'am_' prefix
    if not api_key.startswith('am_'):
        return False
    # Only alphanumeric and underscores after prefix
    return re.match(r'^am_[a-zA-Z0-9_-]+$', api_key) is not None


def _is_valid_uuid(uuid_string):
    """Validate UUID format"""
    if not uuid_string or len(uuid_string) != 36:
        return False
    uuid_regex = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return re.match(uuid_regex, uuid_string.lower()) is not None


def _is_valid_user_id(user_id):
    """Validate external user ID format"""
    if not user_id or len(user_id) < 1 or len(user_id) > 255:
        return False
    # Allow alphanumeric, hyphens, underscores, dots - but not starting with special chars
    if user_id[0] in '._-':
        return False
    # More restrictive pattern to prevent injection
    return re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$', user_id) is not None


@api_bp.route('/docs')
def api_docs() -> str:
    """API Documentation page"""
    return render_template('api/docs.html')
