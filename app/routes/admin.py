from datetime import datetime, timedelta
from functools import wraps
from typing import Callable

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models.content import Content
from app.models.moderation_result import ModerationResult
from app.models.moderation_rule import ModerationRule
from app.models.project import Project
from app.models.user import User
from app.services.database_service import db_service

admin_bp = Blueprint('admin', __name__)


def admin_required(f: Callable) -> Callable:
    """Decorator to require admin access"""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard.index'))
        return await f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@login_required
@admin_required
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

    return render_template('admin/index.html',
                           stats=stats,
                           recent_users=recent_users,
                           recent_projects=recent_projects,
                           recent_content=recent_content,
                           moderation_stats=moderation_stats)


@admin_bp.route('/users')
@login_required
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
@login_required
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
@login_required
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
    flash(f'Admin privileges {action} for user {
          user_data["username"]}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<user_id>/toggle_active', methods=['POST'])
@login_required
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
@login_required
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
@login_required
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
        flash(f'Error deleting user: {str(e)}', 'error')
        return redirect(url_for('admin.user_detail', user_id=user_id))


@admin_bp.route('/projects')
@login_required
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
@login_required
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
@login_required
@admin_required
async def api_stats():
    """API endpoint for admin statistics"""
    stats = await db_service.get_api_stats()

    return jsonify(stats)
