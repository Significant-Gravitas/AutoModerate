from functools import wraps

from flask import Blueprint, current_app, jsonify, render_template, request

from app.services.database_service import db_service
from app.services.moderation_orchestrator import ModerationOrchestrator

api_bp = Blueprint('api', __name__)


def require_api_key(f):
    """Decorator to require valid API key for API endpoints"""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        api_key = request.headers.get(
            'X-API-Key') or request.args.get('api_key')

        if not api_key:
            return jsonify({'error': 'API key required'}), 401

        key_obj = await db_service.get_api_key_by_value(api_key)
        if not key_obj or not key_obj.is_active:
            return jsonify({'error': 'Invalid API key'}), 401

        # Increment usage counter
        await db_service.update_api_key_usage(key_obj)

        # Add to request context
        request.api_key = key_obj
        request.project = key_obj.project

        return await f(*args, **kwargs)
    return decorated_function


@api_bp.route('/moderate', methods=['POST'])
@require_api_key
async def moderate_content():
    """
    Main API endpoint for content moderation
    """
    import time

    # Start timing the entire request
    request_start_time = time.time()

    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'JSON data required'}), 400

        content_type = data.get('type', 'text')
        content_data = data.get('content')
        meta_data = data.get('metadata', {})

        if not content_data:
            return jsonify({'error': 'Content data required'}), 400

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
            return jsonify({'error': 'Failed to create content record'}), 500

        # Start moderation process
        moderation_orchestrator = ModerationOrchestrator()
        result = await moderation_orchestrator.moderate_content(
            content_id, request_start_time)

        return jsonify({
            'success': True,
            'content_id': content_id,
            'status': result.get('decision', 'pending'),
            'moderation_results': result.get('results', [])
        })

    except Exception as e:
        current_app.logger.error(f"Error in content moderation: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


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
async def list_content():
    """
    List content for the project with pagination
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    status = request.args.get('status')

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
