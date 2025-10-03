from datetime import datetime, timedelta
from functools import wraps
from typing import Callable

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.models.content import Content
from app.models.moderation_result import ModerationResult
from app.models.moderation_rule import ModerationRule
from app.models.project import Project
from app.models.system_settings import SystemSettings
from app.models.user import User
from app.services.database_service import db_service

admin_bp = Blueprint('admin', __name__)


def admin_required(f: Callable) -> Callable:
    """Enhanced decorator to require admin access with additional security checks"""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        # Check if user is authenticated
        if not current_user.is_authenticated:
            flash('Please log in to access admin area.', 'error')
            return redirect(url_for('auth.login'))

        # Check if user is active (prevent deactivated admin accounts)
        if not current_user.is_active:
            flash('Your account has been deactivated. Contact support.', 'error')
            return redirect(url_for('auth.logout'))

        # Check if user has admin privileges
        if not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'error')
            # Log unauthorized access attempt
            current_app.logger.warning(
                f"Unauthorized admin access attempt by user {current_user.id} ({current_user.email})"
            )
            return redirect(url_for('dashboard.index'))

        # Additional security: verify user still exists in database
        try:
            fresh_user = await db_service.get_user_by_id(current_user.id)
            if not fresh_user or not fresh_user.is_admin or not fresh_user.is_active:
                flash('Session invalid. Please log in again.', 'error')
                return redirect(url_for('auth.logout'))
        except Exception as e:
            current_app.logger.error(f"Admin access verification error: {str(e)}")
            flash('Access verification failed. Please log in again.', 'error')
            return redirect(url_for('auth.logout'))

        return await f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@admin_required  # admin_required includes login_required functionality
async def index():
    """Admin dashboard overview"""
    # Get system statistics using centralized service
    stats = await db_service.get_admin_stats()

    # Get recent activity
    recent_users = await db_service.get_recent_users(5)
    recent_projects = await db_service.get_recent_projects(5)
    recent_content = await db_service.get_recent_content_admin(10)

    # Get moderation statistics
    moderation_stats = {
        **(await db_service.get_moderation_result_stats()),
    }

    # Get system settings
    registration_enabled = SystemSettings.is_registration_enabled()

    return render_template('admin/index.html',
                           stats=stats,
                           recent_users=recent_users,
                           recent_projects=recent_projects,
                           recent_content=recent_content,
                           moderation_stats=moderation_stats,
                           registration_enabled=registration_enabled)


@admin_bp.route('/users')
@admin_required
async def users():
    """User management page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    users = User.query.paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/<user_id>')
@admin_required
async def user_detail(user_id):
    """User detail page"""
    user = await db_service.get_user_by_id(user_id)
    if not user:
        from flask import abort
        abort(404)

    user_projects = await db_service.get_user_projects_for_admin(user_id)

    # Calculate user statistics from the optimized data
    total_content = sum(project_data['content_count'] for project_data in user_projects)
    total_rules = sum(project_data['rules_count'] for project_data in user_projects)
    total_api_keys = sum(project_data['api_keys_count'] for project_data in user_projects)

    return render_template('admin/user_detail.html',
                           user=user,
                           projects=user_projects,
                           total_content=total_content,
                           total_rules=total_rules,
                           total_api_keys=total_api_keys)


@admin_bp.route('/users/<user_id>/toggle_admin', methods=['POST'])
@admin_required
async def toggle_admin(user_id):
    """Toggle admin status for a user"""
    if current_user.id == user_id:
        flash('You cannot modify your own admin status.', 'error')
        return redirect(url_for('admin.users'))

    user_data = await db_service.toggle_user_admin_status(user_id)
    if not user_data:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))

    action = 'granted' if user_data['is_admin'] else 'revoked'
    flash(f'Admin privileges {action} for user {user_data["username"]}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<user_id>/toggle_active', methods=['POST'])
@admin_required
async def toggle_active(user_id):
    """Toggle active status for a user"""
    if current_user.id == user_id:
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('admin.users'))

    user_data = await db_service.toggle_user_active_status(user_id)
    if not user_data:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))

    action = 'activated' if user_data['is_active'] else 'deactivated'
    flash(f'User {user_data["username"]} {action}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/create', methods=['POST'])
@admin_required
async def create_user():
    """Create a new user"""
    try:
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        is_admin = request.form.get('is_admin') == '1'
        is_active = request.form.get('is_active') == '1'

        # Validation
        if not username or not email or not password:
            flash('All required fields must be filled.', 'error')
            return redirect(url_for('admin.users'))

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('admin.users'))

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return redirect(url_for('admin.users'))

        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return redirect(url_for('admin.users'))

        if User.query.filter_by(email=email).first():
            flash('Email address already exists.', 'error')
            return redirect(url_for('admin.users'))

        # Create new user using database service
        new_user = await db_service.create_user(
            username=username,
            email=email,
            password=password,
            is_admin=is_admin,
            is_active=is_active
        )

        if not new_user:
            flash('Failed to create user.', 'error')
            return redirect(url_for('admin.users'))

        role = 'admin' if is_admin else 'user'
        status = 'active' if is_active else 'inactive'
        flash(
            f'User {username} created successfully as {role} ({status}).', 'success')

        return redirect(url_for('admin.users'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error creating user: {str(e)}', 'error')
        return redirect(url_for('admin.users'))


@admin_bp.route('/users/<user_id>/delete', methods=['POST'])
@admin_required
async def delete_user(user_id):
    """Delete a user and all their data"""
    try:
        if current_user.id == user_id:
            flash('You cannot delete your own account.', 'error')
            return redirect(url_for('admin.users'))

        user = await db_service.get_user_by_id(user_id)
        username = user.username

        # Check if user has any projects
        user_projects = await db_service.get_user_projects_for_admin(user_id)
        if user_projects:
            project_count = len(user_projects)
            flash(
                f'Cannot delete user {username}. They have {project_count} project(s) that must be deleted first.', 'error')
            return redirect(url_for('admin.user_detail', user_id=user_id))

        # Delete the user
        db.session.delete(user)
        db.session.commit()

        flash(f'User {username} has been permanently deleted.', 'success')
        return redirect(url_for('admin.users'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete user error: {str(e)}")
        flash(f'Error deleting user: {str(e)}', 'error')
        return redirect(url_for('admin.users'))


@admin_bp.route('/settings/toggle-registration', methods=['POST'])
@admin_required
async def toggle_registration():
    """Toggle user registration on/off"""
    try:
        current_status = SystemSettings.is_registration_enabled()
        new_status = 'false' if current_status else 'true'

        SystemSettings.set_setting(
            'registration_enabled',
            new_status,
            'Enable or disable new user registration'
        )

        action = 'enabled' if new_status == 'true' else 'disabled'
        flash(f'User registration has been {action}.', 'success')

        current_app.logger.info(
            f"Admin {current_user.email} {action} user registration")

        return redirect(url_for('admin.index'))

    except Exception as e:
        current_app.logger.error(f"Toggle registration error: {str(e)}")
        flash(f'Error toggling registration: {str(e)}', 'error')
        return redirect(url_for('admin.index'))


@admin_bp.route('/projects')
@admin_required
async def projects():
    """All projects overview"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Get projects using database service with eager loading
    all_projects = await db_service.get_all_projects_for_admin(page=page, per_page=per_page)

    # Add counts for each project efficiently using database service
    project_stats = {}
    if all_projects:
        project_ids = [p.id for p in all_projects]

        # Get bulk statistics using database service
        bulk_stats = await db_service.get_project_bulk_stats(project_ids)

        # Create stats dict for template
        for project in all_projects:
            project_stats[project.id] = {
                'content_count': bulk_stats['content_counts'].get(project.id, 0),
                'rules_count': bulk_stats['rules_counts'].get(project.id, 0),
                'keys_count': bulk_stats['keys_counts'].get(project.id, 0)
            }

    # Create a simple pagination object
    class SimplePagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.has_prev = page > 1
            self.has_next = len(items) == per_page
            self.pages = (total + per_page - 1) // per_page  # Calculate total pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None

        def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
            """Generate page numbers for pagination display"""
            last = self.pages
            for num in range(1, last + 1):
                if num <= left_edge or \
                   (self.page - left_current - 1 < num < self.page + right_current) or \
                   num > last - right_edge:
                    yield num

    projects = SimplePagination(
        all_projects, page, per_page, len(all_projects))

    # Calculate statistics efficiently without loading related data
    total_content = Content.query.count()
    unique_owners = len(set(project.user_id for project in projects.items))

    return render_template('admin/projects.html',
                           projects=projects,
                           project_stats=project_stats,
                           total_content=total_content,
                           unique_owners=unique_owners)


@admin_bp.route('/analytics')
@admin_required
async def analytics():
    """Comprehensive analytics dashboard"""
    # Get date range for statistics
    days = request.args.get('days', 30, type=int)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Overall system stats
    system_stats = await db_service.get_analytics_stats()

    # Time series data for charts
    user_registrations = db.session.query(
        db.func.date(User.created_at).label('date'),
        db.func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date
    ).group_by(
        db.func.date(User.created_at)
    ).order_by('date').all()

    content_submissions = db.session.query(
        db.func.date(Content.created_at).label('date'),
        db.func.count(Content.id).label('count')
    ).filter(
        Content.created_at >= start_date
    ).group_by(
        db.func.date(Content.created_at)
    ).order_by('date').all()

    # Moderation decision breakdown
    moderation_decisions = db.session.query(
        ModerationResult.decision,
        db.func.count(ModerationResult.id).label('count')
    ).filter(
        ModerationResult.created_at >= start_date
    ).group_by(ModerationResult.decision).all()

    # API usage by project
    api_usage = db.session.query(
        Project.name,
        db.func.count(Content.id).label('requests')
    ).select_from(Project).join(
        Content, Project.id == Content.project_id
    ).filter(
        Content.created_at >= start_date
    ).group_by(Project.id).order_by(db.func.count(Content.id).desc()).limit(10).all()

    # Content type distribution
    content_types = db.session.query(
        Content.content_type,
        db.func.count(Content.id).label('count')
    ).filter(
        Content.created_at >= start_date
    ).group_by(Content.content_type).all()

    # Processing time stats
    processing_stats = db.session.query(
        db.func.avg(ModerationResult.processing_time).label('avg_time'),
        db.func.min(ModerationResult.processing_time).label('min_time'),
        db.func.max(ModerationResult.processing_time).label('max_time')
    ).filter(
        ModerationResult.created_at >= start_date,
        ModerationResult.processing_time.isnot(None)
    ).first()

    # Top active users (by content submissions)
    from app.models.api_user import APIUser
    top_users = db.session.query(
        APIUser.external_user_id,
        db.func.count(Content.id).label('submissions'),
        db.func.sum(db.case(
            (ModerationResult.decision == 'approved', 1),
            else_=0
        )).label('approved'),
        db.func.sum(db.case(
            (ModerationResult.decision == 'rejected', 1),
            else_=0
        )).label('rejected')
    ).select_from(APIUser).join(
        Content, APIUser.id == Content.api_user_id
    ).join(
        ModerationResult, Content.id == ModerationResult.content_id
    ).filter(
        Content.created_at >= start_date
    ).group_by(APIUser.external_user_id).order_by(
        db.func.count(Content.id).desc()
    ).limit(10).all()

    # Rule effectiveness - simplified approach
    rule_stats = db.session.query(
        ModerationRule.name,
        db.func.count(ModerationResult.id).label('triggered'),
        ModerationRule.rule_type
    ).select_from(ModerationRule).join(
        ModerationResult, ModerationRule.id == ModerationResult.moderator_id
    ).filter(
        ModerationResult.created_at >= start_date,
        ModerationResult.moderator_type == 'rule',
        ModerationResult.moderator_id.isnot(None)
    ).group_by(ModerationRule.id).order_by(
        db.func.count(ModerationResult.id).desc()
    ).limit(10).all()

    return render_template('admin/analytics.html',
                           system_stats=system_stats,
                           user_registrations=user_registrations,
                           content_submissions=content_submissions,
                           moderation_decisions=moderation_decisions,
                           api_usage=api_usage,
                           content_types=content_types,
                           processing_stats=processing_stats,
                           top_users=top_users,
                           rule_stats=rule_stats,
                           days=days)


@admin_bp.route('/api/stats')
@admin_required
async def api_stats():
    """API endpoint for admin statistics"""
    stats = await db_service.get_api_stats()

    return jsonify(stats)


@admin_bp.route('/system-health')
@admin_required
async def system_health():
    """System health monitoring page"""
    import time

    import psutil

    from app.services.ai.result_cache import ResultCache
    from app.services.error_tracker import error_tracker
    from app.services.moderation.rule_cache import RuleCache

    # Get system metrics
    process = psutil.Process()
    memory_info = process.memory_info()

    # Calculate uptime (approximation based on process start time)
    uptime_seconds = time.time() - process.create_time()
    uptime_hours = round(uptime_seconds / 3600, 1)

    # Get CPU usage with interval (required for accurate reading)
    cpu_percent = round(process.cpu_percent(interval=0.5), 2)

    # Format memory display (show GB if over 1024 MB)
    memory_mb = memory_info.rss / 1024 / 1024
    total_memory_mb = psutil.virtual_memory().total / 1024 / 1024

    # Format used memory
    if memory_mb >= 1024:
        memory_used_display = f"{round(memory_mb / 1024, 2)} GB"
    else:
        memory_used_display = f"{round(memory_mb, 2)} MB"

    # Format total memory
    if total_memory_mb >= 1024:
        memory_total_display = f"{round(total_memory_mb / 1024, 2)} GB"
    else:
        memory_total_display = f"{round(total_memory_mb, 2)} MB"

    memory_display = f"{memory_used_display} / {memory_total_display}"

    system_stats = {
        'memory_used': memory_display,
        'memory_used_mb': round(memory_mb, 2),
        'memory_percent': round(process.memory_percent(), 2),
        'cpu_percent': cpu_percent,
        'threads': process.num_threads(),
        'uptime_hours': uptime_hours
    }

    # Get cache stats
    result_cache = ResultCache()
    rule_cache = RuleCache()

    cache_stats = {
        'ai_cache': result_cache.get_cache_stats(),
        'rule_cache': rule_cache.get_cache_stats()
    }

    # Get database connection pool stats
    db_stats = {
        'pool_size': current_app.config['SQLALCHEMY_ENGINE_OPTIONS']['pool_size'],
        'checked_out': db.engine.pool.checkedout(),
        'overflow': db.engine.pool.overflow()
    }

    # Get error tracking stats
    error_stats = error_tracker.get_error_stats()
    recent_errors = error_tracker.get_recent_errors(limit=20)

    return render_template('admin/system_health.html',
                           system_stats=system_stats,
                           cache_stats=cache_stats,
                           db_stats=db_stats,
                           error_stats=error_stats,
                           recent_errors=recent_errors)
