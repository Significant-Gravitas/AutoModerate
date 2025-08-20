import json
from datetime import datetime, timedelta
from functools import wraps

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required

from app import db
from app.models.api_key import APIKey
from app.models.content import Content
from app.models.moderation_result import ModerationResult
from app.models.moderation_rule import ModerationRule
from app.models.project import Project
from app.models.user import User

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard overview"""
    # Get system statistics
    stats = {
        'total_users': User.query.count(),
        'total_projects': Project.query.count(),
        'total_content': Content.query.count(),
        'total_rules': ModerationRule.query.count(),
        'total_api_keys': APIKey.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'admin_users': User.query.filter_by(is_admin=True).count(),
    }

    # Get recent activity
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_projects = Project.query.order_by(
        Project.created_at.desc()).limit(5).all()
    recent_content = Content.query.order_by(
        Content.created_at.desc()).limit(10).all()

    # Get moderation statistics
    moderation_stats = {
        'total_moderations': ModerationResult.query.count(),
        'approved': ModerationResult.query.filter_by(decision='approved').count(),
        'rejected': ModerationResult.query.filter_by(decision='rejected').count(),
        'flagged': ModerationResult.query.filter_by(decision='flagged').count(),
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
def users():
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
def user_detail(user_id):
    """User detail page"""
    user = User.query.get_or_404(user_id)
    user_projects = Project.query.filter_by(user_id=user_id).all()

    # Calculate user statistics
    total_content = sum(len(project.content) for project in user_projects)
    total_rules = sum(len(project.moderation_rules)
                      for project in user_projects)
    total_api_keys = sum(len(project.api_keys) for project in user_projects)

    return render_template('admin/user_detail.html',
                           user=user,
                           projects=user_projects,
                           total_content=total_content,
                           total_rules=total_rules,
                           total_api_keys=total_api_keys)


@admin_bp.route('/users/<user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    """Toggle admin status for a user"""
    if current_user.id == user_id:
        flash('You cannot modify your own admin status.', 'error')
        return redirect(url_for('admin.users'))

    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()

    action = 'granted' if user.is_admin else 'revoked'
    flash(f'Admin privileges {action} for user {user.username}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<user_id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_active(user_id):
    """Toggle active status for a user"""
    if current_user.id == user_id:
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('admin.users'))

    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()

    action = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} {action}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
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

        # Create new user
        new_user = User(
            username=username,
            email=email,
            is_admin=is_admin,
            is_active=is_active
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

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
def delete_user(user_id):
    """Delete a user and all their data"""
    try:
        if current_user.id == user_id:
            flash('You cannot delete your own account.', 'error')
            return redirect(url_for('admin.users'))

        user = User.query.get_or_404(user_id)
        username = user.username

        # Check if user has any projects
        user_projects = Project.query.filter_by(user_id=user_id).all()
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
def projects():
    """All projects overview"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    projects = Project.query.paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Calculate statistics
    total_content = sum(len(project.content) for project in projects.items)
    unique_owners = len(set(project.user_id for project in projects.items))

    return render_template('admin/projects.html',
                           projects=projects,
                           total_content=total_content,
                           unique_owners=unique_owners)


@admin_bp.route('/projects/<project_id>')
@login_required
@admin_required
def project_detail(project_id):
    """Project detail page"""
    project = Project.query.get_or_404(project_id)

    # Get project statistics
    stats = {
        'content_count': Content.query.filter_by(project_id=project_id).count(),
        'rules_count': ModerationRule.query.filter_by(project_id=project_id).count(),
        'api_keys_count': APIKey.query.filter_by(project_id=project_id).count(),
        'moderations_count': ModerationResult.query.join(Content).filter(Content.project_id == project_id).count(),
    }

    return render_template('admin/project_detail.html', project=project, stats=stats)


@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    """System logs page"""
    # This would typically connect to a logging system
    # For now, we'll show recent activity from the database
    recent_content = Content.query.order_by(
        Content.created_at.desc()).limit(50).all()
    recent_moderations = ModerationResult.query.order_by(
        ModerationResult.created_at.desc()).limit(50).all()

    return render_template('admin/logs.html',
                           recent_content=recent_content,
                           recent_moderations=recent_moderations)


@admin_bp.route('/statistics')
@login_required
@admin_required
def statistics():
    """Detailed statistics page"""
    # Get date range for statistics
    days = request.args.get('days', 30, type=int)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # User registration statistics
    user_stats = db.session.query(
        db.func.date(User.created_at).label('date'),
        db.func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date
    ).group_by(
        db.func.date(User.created_at)
    ).all()

    # Content creation statistics
    content_stats = db.session.query(
        db.func.date(Content.created_at).label('date'),
        db.func.count(Content.id).label('count')
    ).filter(
        Content.created_at >= start_date
    ).group_by(
        db.func.date(Content.created_at)
    ).all()

    # Moderation statistics
    moderation_stats = db.session.query(
        db.func.date(ModerationResult.created_at).label('date'),
        db.func.count(ModerationResult.id).label('count')
    ).filter(
        ModerationResult.created_at >= start_date
    ).group_by(
        db.func.date(ModerationResult.created_at)
    ).all()

    return render_template('admin/statistics.html',
                           user_stats=user_stats,
                           content_stats=content_stats,
                           moderation_stats=moderation_stats,
                           days=days)


@admin_bp.route('/api/stats')
@login_required
@admin_required
def api_stats():
    """API endpoint for admin statistics"""
    stats = {
        'users': {
            'total': User.query.count(),
            'active': User.query.filter_by(is_active=True).count(),
            'admin': User.query.filter_by(is_admin=True).count(),
            'recent': User.query.filter(User.created_at >= datetime.utcnow() - timedelta(days=7)).count()
        },
        'projects': {
            'total': Project.query.count(),
            'recent': Project.query.filter(Project.created_at >= datetime.utcnow() - timedelta(days=7)).count()
        },
        'content': {
            'total': Content.query.count(),
            'recent': Content.query.filter(Content.created_at >= datetime.utcnow() - timedelta(days=7)).count()
        },
        'moderations': {
            'total': ModerationResult.query.count(),
            'approved': ModerationResult.query.filter_by(decision='approved').count(),
            'rejected': ModerationResult.query.filter_by(decision='rejected').count(),
            'flagged': ModerationResult.query.filter_by(decision='flagged').count(),
            'recent': ModerationResult.query.filter(ModerationResult.created_at >= datetime.utcnow() - timedelta(days=7)).count()
        }
    }

    return jsonify(stats)
