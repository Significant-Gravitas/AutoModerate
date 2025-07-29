from flask import Blueprint, request, jsonify, current_app, render_template
from app.models.api_key import APIKey
from app.models.content import Content
from app.models.project import Project
from app.models.api_user import APIUser
from app.services.moderation_service import ModerationService
from app import db
from functools import wraps
import uuid

api_bp = Blueprint('api', __name__)

def require_api_key(f):
    """Decorator to require valid API key for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        key_obj = APIKey.query.filter_by(key=api_key, is_active=True).first()
        if not key_obj:
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Increment usage counter
        key_obj.increment_usage()
        
        # Add to request context
        request.api_key = key_obj
        request.project = key_obj.project
        
        return f(*args, **kwargs)
    return decorated_function

@api_bp.route('/moderate', methods=['POST'])
@require_api_key
def moderate_content():
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
            
            # Find or create API user
            api_user = APIUser.query.filter_by(
                external_user_id=external_user_id,
                project_id=request.project.id
            ).first()
            
            if not api_user:
                api_user = APIUser(
                    external_user_id=external_user_id,
                    project_id=request.project.id
                )
                db.session.add(api_user)
                db.session.flush()  # Get the ID without committing
        
        # Create content record
        content = Content(
            project_id=request.project.id,
            content_type=content_type,
            content_data=content_data,
            meta_data=meta_data,
            api_user_id=api_user.id if api_user else None
        )
        db.session.add(content)
        db.session.commit()
        
        # Start moderation process
        moderation_service = ModerationService()
        result = moderation_service.moderate_content(content.id, request_start_time)
        
        return jsonify({
            'success': True,
            'content_id': content.id,
            'status': result.get('decision', 'pending'),
            'moderation_results': result.get('results', [])
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in content moderation: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/content/<content_id>', methods=['GET'])
@require_api_key
def get_content(content_id):
    """
    Get content and its moderation results
    """
    content = Content.query.filter_by(
        id=content_id,
        project_id=request.project.id
    ).first()
    
    if not content:
        return jsonify({'error': 'Content not found'}), 404
    
    return jsonify({
        'success': True,
        'content': content.to_dict()
    })

@api_bp.route('/content', methods=['GET'])
@require_api_key
def list_content():
    """
    List content for the project with pagination
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    status = request.args.get('status')
    
    query = Content.query.filter_by(project_id=request.project.id)
    
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return jsonify({
        'success': True,
        'content': [item.to_dict() for item in pagination.items],
        'pagination': {
            'page': page,
            'pages': pagination.pages,
            'per_page': per_page,
            'total': pagination.total,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })

@api_bp.route('/stats', methods=['GET'])
@require_api_key
def get_stats():
    """
    Get moderation statistics for the project
    """
    project_id = request.project.id
    
    total_content = Content.query.filter_by(project_id=project_id).count()
    approved_content = Content.query.filter_by(project_id=project_id, status='approved').count()
    rejected_content = Content.query.filter_by(project_id=project_id, status='rejected').count()
    flagged_content = Content.query.filter_by(project_id=project_id, status='flagged').count()
    pending_content = Content.query.filter_by(project_id=project_id, status='pending').count()
    
    return jsonify({
        'success': True,
        'stats': {
            'total_content': total_content,
            'approved': approved_content,
            'rejected': rejected_content,
            'flagged': flagged_content,
            'pending': pending_content,
            'approval_rate': (approved_content / total_content * 100) if total_content > 0 else 0
        }
    })

@api_bp.route('/health', methods=['GET'])
def health_check():
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
