from functools import wraps

from flask import Blueprint, current_app, jsonify, render_template, request

from app.schemas import ContentListRequest, ModerateContentRequest
from app.services.database_service import db_service
from app.services.moderation_orchestrator import ModerationOrchestrator
from app.utils.error_handlers import (
    api_error_response,
    api_success_response,
    handle_api_error,
    validate_json_request,
    validate_query_params,
)

api_bp = Blueprint('api', __name__)


def require_api_key(f):
    """Decorator to require valid API key for API endpoints"""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        api_key = request.headers.get(
            'X-API-Key') or request.args.get('api_key')

        if not api_key:
            return api_error_response('API key required', 401)

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

    # Track API user if user_id is provided in metadata
    api_user = None
    if meta_data and 'user_id' in meta_data:
        external_user_id = meta_data['user_id']

        # Find or create API user using centralized service
        api_user = await db_service.get_or_create_api_user(
            external_user_id=external_user_id,
            project_id=request.project.id
        )

    # Create content record using database service
    content_id = await db_service.create_content(
        project_id=request.project.id,
        content_text=str(content_data),
        content_type=content_type,
        api_user_id=api_user.id if api_user else None,
        meta_data=meta_data if meta_data else None
    )

    if not content_id:
        current_app.logger.error("Failed to create content record")
        return api_error_response('Failed to create content record', 500)

    # Start moderation process
    moderation_orchestrator = ModerationOrchestrator()
    result = await moderation_orchestrator.moderate_content(
        content_id, request_start_time)

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
    content = await db_service.get_content_by_id_and_project(content_id, request.project.id)

    if not content:
        return jsonify({'error': 'Content not found'}), 404

    return jsonify({
        'success': True,
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


@api_bp.route('/docs')
def api_docs():
    """API Documentation page"""
    return render_template('api/docs.html')
