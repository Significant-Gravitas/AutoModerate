import secrets
from datetime import datetime, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload

from app import db
from app.models.api_key import APIKey
from app.models.content import Content
from app.models.moderation_rule import ModerationRule
from app.models.project import Project, ProjectInvitation, ProjectMember
from app.models.user import User
from app.services.database_service import db_service
from app.utils.project_access import require_project_access
from config.default_rules import create_default_rules

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
async def index():
    """Dashboard home page"""
    # Get user projects using centralized service
    projects = await db_service.get_user_projects(current_user.id)

    # Get project statistics
    total_content = 0
    total_api_keys = 0

    for project in projects:
        stats = await db_service.get_project_stats(project.id)
        project._content_count = stats.get('total_content', 0)
        project._api_key_count = stats.get('total_api_keys', 0)
        total_content += project._content_count
        total_api_keys += project._api_key_count

    total_projects = len(projects)

    # Get pending invitations for current user with joins
    pending_invitations = ProjectInvitation.query.options(
        joinedload(ProjectInvitation.project),
        joinedload(ProjectInvitation.inviter)
    ).filter_by(
        email=current_user.email,
        status='pending'
    ).filter(ProjectInvitation.expires_at > datetime.utcnow()).all()

    return render_template('dashboard/index.html',
                           projects=projects,
                           total_projects=total_projects,
                           total_content=total_content,
                           total_api_keys=total_api_keys,
                           pending_invitations=pending_invitations)


@dashboard_bp.route('/projects')
@login_required
async def projects():
    """List all user projects"""
    # Get user projects using centralized service
    projects = await db_service.get_user_projects(current_user.id)

    # Add project statistics
    for project in projects:
        stats = await db_service.get_project_stats(project.id)
        project._content_count = stats.get('total_content', 0)
        project._api_key_count = stats.get('total_api_keys', 0)
        project._rules_count = stats.get('total_rules', 0)

    return render_template('dashboard/projects.html', projects=projects)


@dashboard_bp.route('/projects/create', methods=['GET', 'POST'])
@login_required
async def create_project():
    """Create a new project"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')

        if not name:
            flash('Project name is required', 'error')
            return render_template('dashboard/create_project.html')

        project = await db_service.create_project(name=name, description=description, user_id=current_user.id)
        if not project:
            flash('Failed to create project', 'error')
            return render_template('dashboard/create_project.html')

        # Add default moderation rules
        await create_default_rules(db_service, project['id'])

        # Create default API key
        import secrets
        key_value = f"am_{secrets.token_urlsafe(32)}"
        await db_service.create_api_key(
            project_id=project['id'],
            name='Default Key',
            key_value=key_value
        )

        flash('Project created successfully!', 'success')
        return redirect(url_for('dashboard.project_detail', project_id=project['id']))

    return render_template('dashboard/create_project.html')


@dashboard_bp.route('/projects/<project_id>')
@login_required
@require_project_access
async def project_detail(project_id, project=None):
    """Project detail page"""

    # Get recent content using database service
    recent_content = await db_service.get_project_content(project_id, limit=10)

    # Get API keys to avoid DetachedInstanceError in template
    api_keys = await db_service.get_project_api_keys(project_id)

    # Get stats using database service
    content_counts = await db_service.get_content_counts_by_status(project_id)

    total_content = content_counts.get('total', 0)
    approved_content = content_counts.get('approved', 0)
    rejected_content = content_counts.get('rejected', 0)
    flagged_content = content_counts.get('flagged', 0)

    stats = {
        'total': total_content,
        'approved': approved_content,
        'rejected': rejected_content,
        'flagged': flagged_content,
        'approval_rate': (approved_content / total_content * 100) if total_content > 0 else 0
    }

    return render_template('dashboard/project_detail.html',
                           project=project,
                           recent_content=recent_content,
                           api_keys=api_keys,
                           stats=stats)


@dashboard_bp.route('/projects/<project_id>/api-keys')
@login_required
@require_project_access
async def project_api_keys(project_id, project=None):
    """Manage project API keys"""
    # Get API keys to avoid DetachedInstanceError in template
    api_keys = await db_service.get_project_api_keys(project_id)
    return render_template('dashboard/api_keys.html', project=project, api_keys=api_keys)


@dashboard_bp.route('/projects/<project_id>/api-keys/create', methods=['POST'])
@login_required
@require_project_access
async def create_api_key(project_id, project=None):
    """Create new API key"""

    name = request.form.get('name')
    if not name:
        flash('API key name is required', 'error')
        return redirect(url_for('dashboard.project_api_keys', project_id=project_id))

    # Generate API key value
    key_value = f"am_{secrets.token_urlsafe(32)}"

    api_key = await db_service.create_api_key(
        project_id=project.id,
        name=name,
        key_value=key_value
    )

    if not api_key:
        flash('Failed to create API key.', 'error')
        return redirect(url_for('dashboard.project_api_keys', project_id=project_id))

    flash('API key created successfully!', 'success')
    return redirect(url_for('dashboard.project_api_keys', project_id=project_id))


@dashboard_bp.route('/projects/<project_id>/rules')
@login_required
@require_project_access
async def project_rules(project_id, project=None):
    """Manage project moderation rules"""
    rules = await db_service.get_project_rules(project_id)
    return render_template('dashboard/rules.html', project=project, rules=rules)


@dashboard_bp.route('/projects/<project_id>/rules/create', methods=['GET', 'POST'])
@login_required
async def create_rule(project_id):
    """Create new moderation rule"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has access to this project
    if not project.is_member(current_user.id):
        flash('You do not have access to this project', 'error')
        return redirect(url_for('dashboard.projects'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        rule_type = request.form.get('rule_type')
        action = request.form.get('action')
        priority = int(request.form.get('priority', 0))

        # Build rule data based on type
        rule_data = {}
        if rule_type == 'keyword':
            keywords = request.form.get('keywords', '').split(',')
            keywords = [k.strip() for k in keywords if k.strip()]
            rule_data = {
                'keywords': keywords,
                'case_sensitive': request.form.get('case_sensitive') == 'on'
            }
        elif rule_type == 'regex':
            rule_data = {
                'pattern': request.form.get('pattern', ''),
                'flags': 0  # Can be extended for regex flags
            }
        elif rule_type == 'ai_prompt':
            rule_data = {
                'prompt': request.form.get('ai_prompt', '')
            }

        rule = ModerationRule(
            project_id=project.id,
            name=name,
            description=description,
            rule_type=rule_type,
            rule_data=rule_data,
            action=action,
            priority=priority
        )
        db.session.add(rule)
        db.session.commit()

        flash('Moderation rule created successfully!', 'success')
        return redirect(url_for('dashboard.project_rules', project_id=project_id))

    return render_template('dashboard/create_rule.html', project=project)


@dashboard_bp.route('/projects/<project_id>/rules/<rule_id>/update', methods=['POST'])
@login_required
async def update_rule(project_id, rule_id):
    """Update existing moderation rule"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has access to this project
    if not project.is_member(current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    rule = ModerationRule.query.filter_by(
        id=rule_id, project_id=project.id).first_or_404()

    try:
        data = request.get_json()

        # Update basic fields
        rule.name = data.get('name', rule.name)
        rule.description = data.get('description', rule.description)
        rule.action = data.get('action', rule.action)
        rule.priority = data.get('priority', rule.priority)

        # Update rule data based on type
        if rule.rule_type == 'keyword':
            keywords = data.get('rule_data', {}).get('keywords', [])
            if isinstance(keywords, str):
                keywords = [k.strip()
                            for k in keywords.split(',') if k.strip()]
            rule.rule_data = {
                'keywords': keywords,
                'case_sensitive': data.get('rule_data', {}).get('case_sensitive', False)
            }
        elif rule.rule_type == 'regex':
            rule.rule_data = {
                'pattern': data.get('rule_data', {}).get('pattern', ''),
                'flags': data.get('rule_data', {}).get('flags', 0)
            }
        elif rule.rule_type == 'ai_prompt':
            rule.rule_data = {
                'prompt': data.get('rule_data', {}).get('prompt', '')
            }

        db.session.commit()

        return jsonify({'success': True, 'message': 'Rule updated successfully'})

    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'An error occurred while updating the rule'}), 400


@dashboard_bp.route('/projects/<project_id>/rules/<rule_id>/toggle', methods=['POST'])
@login_required
async def toggle_rule(project_id, rule_id):
    """Toggle rule active/inactive status"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has access to this project
    if not project.is_member(current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    rule = ModerationRule.query.filter_by(
        id=rule_id, project_id=project.id).first_or_404()

    try:
        data = request.get_json()
        action = data.get('action')

        if action == 'activate':
            rule.is_active = True
        elif action == 'deactivate':
            rule.is_active = False
        else:
            return jsonify({'success': False, 'error': 'Invalid action'}), 400

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Rule {"activated" if action == "activate" else "deactivated"} successfully',
            'is_active': rule.is_active
        })

    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'An error occurred while toggling the rule'}), 400


@dashboard_bp.route('/projects/<project_id>/rules/<rule_id>/delete', methods=['POST'])
@login_required
async def delete_rule(project_id, rule_id):
    """Delete moderation rule"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has access to this project
    if not project.is_member(current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    rule = ModerationRule.query.filter_by(
        id=rule_id, project_id=project.id).first_or_404()

    try:
        rule_name = rule.name
        db.session.delete(rule)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Rule "{rule_name}" deleted successfully'
        })

    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'An error occurred while deleting the rule'}), 400


@dashboard_bp.route('/projects/<project_id>/content')
@login_required
async def project_content(project_id):
    """View project content"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has access to this project
    if not project.is_member(current_user.id):
        flash('You do not have access to this project', 'error')
        return redirect(url_for('dashboard.projects'))

    page = request.args.get('page', 1, type=int)
    status = request.args.get('status')
    search = request.args.get('search')
    content_type = request.args.get('content_type')
    time_filter = request.args.get('time_filter')

    query = Content.query.filter_by(project_id=project.id).options(
        selectinload(Content.moderation_results)
    )

    # Apply status filter
    if status:
        query = query.filter_by(status=status)

    # Apply content type filter
    if content_type:
        query = query.filter_by(content_type=content_type)

    # Apply time filter
    if time_filter:
        from datetime import datetime, timedelta
        now = datetime.utcnow()

        if time_filter == '1h':
            time_threshold = now - timedelta(hours=1)
        elif time_filter == '24h':
            time_threshold = now - timedelta(hours=24)
        elif time_filter == '7d':
            time_threshold = now - timedelta(days=7)
        elif time_filter == '30d':
            time_threshold = now - timedelta(days=30)
        else:
            time_threshold = None

        if time_threshold:
            query = query.filter(Content.created_at >= time_threshold)

    # Apply search filter
    if search:
        search_term = search.strip()
        if search_term:
            # Check if search term looks like a content ID (UUID format)
            import re
            uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
            if re.match(uuid_pattern, search_term):
                # Search by exact content ID
                query = query.filter(Content.id == search_term)
            else:
                # Search in content data
                query = query.filter(
                    Content.content_data.contains(search_term))

    pagination = query.order_by(Content.created_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )

    # Get total project statistics (not just current page)
    total_stats = {
        'total': Content.query.filter_by(project_id=project.id).count(),
        'approved': Content.query.filter_by(project_id=project.id, status='approved').count(),
        'rejected': Content.query.filter_by(project_id=project.id, status='rejected').count(),
        'flagged': Content.query.filter_by(project_id=project.id, status='flagged').count(),
    }

    return render_template('dashboard/content.html',
                           project=project,
                           pagination=pagination,
                           total_stats=total_stats,
                           current_status=status,
                           current_search=search,
                           current_content_type=content_type,
                           current_time_filter=time_filter)


@dashboard_bp.route('/projects/<project_id>/content/<content_id>')
@login_required
async def get_content_details(project_id, content_id):
    """Get content details for modal"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has access to this project
    if not project.is_member(current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    content = Content.query.filter_by(
        id=content_id, project_id=project.id).options(
        selectinload(Content.moderation_results)
    ).first_or_404()

    return jsonify({
        'success': True,
        'content': content.to_dict()
    })


@dashboard_bp.route('/projects/<project_id>/api-keys/<key_id>/toggle', methods=['POST'])
@login_required
async def toggle_api_key(project_id, key_id):
    """Toggle API key active/inactive status"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has access to this project
    if not project.is_member(current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    api_key = APIKey.query.filter_by(
        id=key_id, project_id=project.id).first_or_404()

    try:
        data = request.get_json()
        action = data.get('action')

        if action == 'activate':
            api_key.is_active = True
        elif action == 'deactivate':
            api_key.is_active = False
        else:
            return jsonify({'success': False, 'error': 'Invalid action'}), 400

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'API key {"activated" if action == "activate" else "deactivated"} successfully',
            'is_active': api_key.is_active
        })

    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'An error occurred while creating the API key'}), 400


@dashboard_bp.route('/projects/<project_id>/api-keys/<key_id>/delete', methods=['POST'])
@login_required
async def delete_api_key(project_id, key_id):
    """Delete API key"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has access to this project
    if not project.is_member(current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    api_key = APIKey.query.filter_by(
        id=key_id, project_id=project.id).first_or_404()

    try:
        key_name = api_key.name
        db.session.delete(api_key)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'API key "{key_name}" deleted successfully'
        })

    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'An error occurred while deleting the API key'}), 400


@dashboard_bp.route('/projects/<project_id>/settings')
@login_required
async def project_settings(project_id):
    """Project settings page"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has access to this project
    if not project.is_member(current_user.id):
        flash('You do not have access to this project', 'error')
        return redirect(url_for('dashboard.projects'))

    # Get comprehensive stats
    total_content = Content.query.filter_by(project_id=project.id).count()
    approved_content = Content.query.filter_by(
        project_id=project.id, status='approved').count()
    rejected_content = Content.query.filter_by(
        project_id=project.id, status='rejected').count()
    flagged_content = Content.query.filter_by(
        project_id=project.id, status='flagged').count()
    rules_count = ModerationRule.query.filter_by(project_id=project.id).count()
    api_keys_count = APIKey.query.filter_by(project_id=project.id).count()

    # Get member stats
    members_count = len(project.memberships) + 1  # +1 for owner
    admin_count = len([m for m in project.memberships if m.role == 'admin'])
    pending_invitations = ProjectInvitation.query.filter_by(
        project_id=project.id,
        status='pending'
    ).filter(ProjectInvitation.expires_at > datetime.utcnow()).count()

    stats = {
        'total': total_content,
        'approved': approved_content,
        'rejected': rejected_content,
        'flagged': flagged_content,
        'rules_count': rules_count,
        'api_keys_count': api_keys_count,
        'approval_rate': (approved_content / total_content * 100) if total_content > 0 else 0,
        'members_count': members_count,
        'admin_count': admin_count,
        'pending_invitations': pending_invitations
    }

    return render_template('dashboard/project_settings.html',
                           project=project,
                           stats=stats)


@dashboard_bp.route('/projects/<project_id>/update', methods=['POST'])
@login_required
async def update_project(project_id):
    """Update project information"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has access to this project
    if not project.is_member(current_user.id):
        flash('You do not have access to this project', 'error')
        return redirect(url_for('dashboard.projects'))

    name = request.form.get('name')
    description = request.form.get('description', '')

    if not name:
        flash('Project name is required', 'error')
        return redirect(url_for('dashboard.project_settings', project_id=project_id))

    try:
        project.name = name
        project.description = description
        db.session.commit()

        flash('Project updated successfully!', 'success')
    except SQLAlchemyError:
        db.session.rollback()
        flash('Error updating project', 'error')

    return redirect(url_for('dashboard.project_settings', project_id=project_id))


@dashboard_bp.route('/projects/<project_id>/discord-settings', methods=['POST'])
@login_required
async def update_discord_settings(project_id):
    """Update Discord notification settings for a project"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has admin access
    if not project.can_manage_members(current_user.id):
        flash('You do not have permission to modify project settings', 'error')
        return redirect(url_for('dashboard.project_settings', project_id=project_id))

    discord_notifications_enabled = request.form.get('discord_notifications_enabled') == 'true'
    discord_webhook_url = request.form.get('discord_webhook_url', '').strip()

    # Validate webhook URL if provided
    if discord_webhook_url and not discord_webhook_url.startswith('https://discord.com/api/webhooks/'):
        flash('Invalid Discord webhook URL', 'error')
        return redirect(url_for('dashboard.project_settings', project_id=project_id))

    try:
        project.discord_notifications_enabled = discord_notifications_enabled
        project.discord_webhook_url = discord_webhook_url if discord_webhook_url else None
        db.session.commit()

        flash('Discord notification settings updated successfully!', 'success')
    except SQLAlchemyError:
        db.session.rollback()
        flash('Error updating Discord settings', 'error')

    return redirect(url_for('dashboard.project_settings', project_id=project_id))


@dashboard_bp.route('/projects/<project_id>/test-webhook', methods=['POST'])
@login_required
async def test_discord_webhook(project_id):
    """Test Discord webhook configuration"""
    from app.services.notifications.discord_notifier import DiscordNotifier

    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has admin access
    if not project.can_manage_members(current_user.id):
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    # Determine webhook URL
    webhook_url = project.discord_webhook_url
    if not webhook_url:
        # Try to use global webhook from environment
        from flask import current_app
        webhook_url = current_app.config.get('DISCORD_WEBHOOK_URL')

    if not webhook_url:
        return jsonify({
            'success': False,
            'message': 'No webhook URL configured. Please add a webhook URL or set DISCORD_WEBHOOK_URL in your environment.'
        }), 400

    # Send test notification
    notifier = DiscordNotifier(webhook_url)
    success = notifier.send_test_notification(project_name=project.name)

    if success:
        return jsonify({
            'success': True,
            'message': 'Test notification sent successfully! Check your Discord channel.'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to send test notification. Please check your webhook URL and try again.'
        }), 500


@dashboard_bp.route('/projects/<project_id>/delete', methods=['POST'])
@login_required
async def delete_project(project_id):
    """Delete a project"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Only the owner can delete the project
    if project.user_id != current_user.id:
        flash('Only the project owner can delete the project', 'error')
        return redirect(url_for('dashboard.project_settings', project_id=project_id))

    # Delete the project (cascade will handle related data)
    db.session.delete(project)
    db.session.commit()

    flash('Project deleted successfully!', 'success')
    return redirect(url_for('dashboard.projects'))


@dashboard_bp.route('/projects/<project_id>/analytics')
@login_required
@require_project_access
async def project_analytics(project_id, project):
    """Project-specific analytics dashboard"""
    from datetime import datetime, timedelta

    # Get date range for statistics
    days = request.args.get('days', 30, type=int)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Get all analytics data from database service
    analytics_data = await db_service.get_project_analytics_stats(project_id, start_date, end_date)

    return render_template('dashboard/project_analytics.html',
                           project=project,
                           days=days,
                           **analytics_data)


# Project Member Management Routes


@dashboard_bp.route('/projects/<project_id>/members')
@login_required
async def project_members(project_id):
    """Manage project members"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has access to this project
    if not project.is_member(current_user.id):
        flash('You do not have access to this project', 'error')
        return redirect(url_for('dashboard.projects'))

    # Get all members including the owner
    members = []
    if project.owner:
        members.append({
            'user': project.owner,
            'role': 'owner',
            'joined_at': project.created_at,
            'is_owner': True
        })

    # Add project members
    for membership in project.memberships:
        members.append({
            'user': membership.user,
            'role': membership.role,
            'joined_at': membership.joined_at,
            'is_owner': False,
            'membership_id': membership.id
        })

    # Get pending invitations
    pending_invitations = ProjectInvitation.query.filter_by(
        project_id=project_id,
        status='pending'
    ).filter(ProjectInvitation.expires_at > datetime.utcnow()).all()

    return render_template('dashboard/members.html',
                           project=project,
                           members=members,
                           pending_invitations=pending_invitations)


@dashboard_bp.route('/projects/<project_id>/invite', methods=['POST'])
@login_required
async def invite_member(project_id):
    """Invite a user to the project"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user can manage members
    if not project.can_manage_members(current_user.id):
        flash('You do not have permission to invite members', 'error')
        return redirect(url_for('dashboard.project_members', project_id=project_id))

    email = request.form.get('email')
    role = request.form.get('role', 'member')

    if not email:
        flash('Email is required', 'error')
        return redirect(url_for('dashboard.project_members', project_id=project_id))

    # Check if user is already a member
    user = User.query.filter_by(email=email).first()
    if user and project.is_member(user.id):
        flash('User is already a member of this project', 'error')
        return redirect(url_for('dashboard.project_members', project_id=project_id))

    # Check if invitation already exists
    existing_invitation = ProjectInvitation.query.filter_by(
        project_id=project_id,
        email=email,
        status='pending'
    ).first()

    if existing_invitation:
        flash('An invitation has already been sent to this email', 'error')
        return redirect(url_for('dashboard.project_members', project_id=project_id))

    # Create invitation
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)

    invitation = ProjectInvitation(
        project_id=project_id,
        email=email,
        invited_by=current_user.id,
        role=role,
        token=token,
        expires_at=expires_at
    )

    db.session.add(invitation)
    db.session.commit()

    flash(f'Invitation sent to {email}', 'success')
    return redirect(url_for('dashboard.project_members', project_id=project_id))


@dashboard_bp.route('/projects/<project_id>/invitations/<invitation_id>/cancel', methods=['POST'])
@login_required
async def cancel_invitation(project_id, invitation_id):
    """Cancel a pending invitation"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user can manage members
    if not project.can_manage_members(current_user.id):
        flash('You do not have permission to cancel invitations', 'error')
        return redirect(url_for('dashboard.project_members', project_id=project_id))

    invitation = ProjectInvitation.query.filter_by(
        id=invitation_id,
        project_id=project_id
    ).first_or_404()

    invitation.status = 'cancelled'
    db.session.commit()

    flash('Invitation cancelled', 'success')
    return redirect(url_for('dashboard.project_members', project_id=project_id))


@dashboard_bp.route('/projects/<project_id>/members/<membership_id>/remove', methods=['POST'])
@login_required
async def remove_member(project_id, membership_id):
    """Remove a member from the project"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user can manage members
    if not project.can_manage_members(current_user.id):
        flash('You do not have permission to remove members', 'error')
        return redirect(url_for('dashboard.project_members', project_id=project_id))

    membership = ProjectMember.query.filter_by(
        id=membership_id,
        project_id=project_id
    ).first_or_404()

    # Cannot remove the owner
    if membership.user_id == project.user_id:
        flash('Cannot remove the project owner', 'error')
        return redirect(url_for('dashboard.project_members', project_id=project_id))

    # Store username before deletion
    username = membership.user.username

    db.session.delete(membership)
    db.session.commit()

    flash(f'Member {username} removed from project', 'success')
    return redirect(url_for('dashboard.project_members', project_id=project_id))


@dashboard_bp.route('/projects/<project_id>/members/<membership_id>/role', methods=['POST'])
@login_required
async def update_member_role(project_id, membership_id):
    """Update a member's role"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user can manage members
    if not project.can_manage_members(current_user.id):
        flash('You do not have permission to update member roles', 'error')
        return redirect(url_for('dashboard.project_members', project_id=project_id))

    membership = ProjectMember.query.filter_by(
        id=membership_id,
        project_id=project_id
    ).first_or_404()

    role = request.form.get('role')
    if role not in ['admin', 'member']:
        flash('Invalid role', 'error')
        return redirect(url_for('dashboard.project_members', project_id=project_id))

    membership.role = role
    db.session.commit()

    flash(f'Member role updated to {role}', 'success')
    return redirect(url_for('dashboard.project_members', project_id=project_id))

# Invitation acceptance route (public route)


@dashboard_bp.route('/invite/<token>')
async def accept_invitation(token):
    """Accept a project invitation"""
    invitation = ProjectInvitation.query.filter_by(token=token).first_or_404()

    if invitation.status != 'pending':
        flash('This invitation is no longer valid', 'error')
        return redirect(url_for('auth.login'))

    if invitation.expires_at.replace(tzinfo=None) < datetime.utcnow():
        invitation.status = 'expired'
        db.session.commit()
        flash('This invitation has expired', 'error')
        return redirect(url_for('auth.login'))

    # Check if user is logged in
    if not current_user.is_authenticated:
        flash('Please log in to accept the invitation', 'info')
        return redirect(url_for('auth.login'))

    # Check if user email matches invitation
    if current_user.email != invitation.email:
        flash('This invitation was sent to a different email address', 'error')
        return redirect(url_for('dashboard.index'))

    # Check if user is already a member
    project = invitation.project
    if project.is_member(current_user.id):
        invitation.status = 'accepted'
        db.session.commit()
        flash('You are already a member of this project', 'info')
        return redirect(url_for('dashboard.project_detail', project_id=project.id))

    # Add user as member
    membership = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role=invitation.role
    )

    invitation.status = 'accepted'
    db.session.add(membership)
    db.session.commit()

    flash(
        f'You have successfully joined the project "{project.name}"', 'success')
    return redirect(url_for('dashboard.project_detail', project_id=project.id))


@dashboard_bp.route('/invite/<token>/decline', methods=['POST'])
@login_required
async def decline_invitation(token):
    """Decline a project invitation"""
    invitation = ProjectInvitation.query.filter_by(token=token).first_or_404()

    if invitation.status != 'pending':
        flash('This invitation is no longer valid', 'error')
        return redirect(url_for('dashboard.index'))

    if current_user.email != invitation.email:
        flash('This invitation was sent to a different email address', 'error')
        return redirect(url_for('dashboard.index'))

    invitation.status = 'declined'
    db.session.commit()

    flash('Invitation declined', 'info')
    return redirect(url_for('dashboard.index'))
