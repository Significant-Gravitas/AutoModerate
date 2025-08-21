import secrets
from datetime import datetime, timedelta

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from app import db
from app.models.api_key import APIKey
from app.models.content import Content
from app.models.moderation_rule import ModerationRule
from app.models.project import Project, ProjectInvitation, ProjectMember
from app.models.user import User
from app.services.database_service import db_service

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
        default_rules = [
            {
                "name": "Fraud & Impersonation",
                "description": "Content that misrepresents identity, scams users, or spreads fraudulent schemes.",
                "rule_type": "ai_prompt",
                "rule_data": {"prompt": "Content that misrepresents identity, scams users, or spreads fraudulent schemes."},
                "action": "reject",
                "priority": 100,
                "is_active": True,
            },
            {
                "name": "Phishing & Unauthorized Data Collection",
                "description": "Any attempt to collect user data unlawfully, including deceptive AI-generated content designed to steal credentials.",
                "rule_type": "ai_prompt",
                "rule_data": {"prompt": "Any attempt to collect user data unlawfully, including deceptive AI-generated content designed to steal credentials."},
                "action": "reject",
                "priority": 100,
                "is_active": True,
            },
            {
                "name": "Misleading AI Content",
                "description": "AI-generated content that spreads false information, deepfakes, or impersonates individuals without disclosure.",
                "rule_type": "ai_prompt",
                "rule_data": {"prompt": "AI-generated content that spreads false information, deepfakes, or impersonates individuals without disclosure."},
                "action": "reject",
                "priority": 100,
                "is_active": True,
            },
            {
                "name": "Illegal Content",
                "description": "Content that violates applicable laws, including terrorism, child exploitation, and financial crimes.",
                "rule_type": "ai_prompt",
                "rule_data": {"prompt": "Content that violates applicable laws, including terrorism, child exploitation, and financial crimes."},
                "action": "reject",
                "priority": 100,
                "is_active": True,
            },
            {
                "name": "Spam & Unsolicited Promotions",
                "description": "Unwanted advertising, excessive marketing, and pyramid schemes.",
                "rule_type": "ai_prompt",
                "rule_data": {"prompt": "Unwanted advertising, excessive marketing, and pyramid schemes."},
                "action": "reject",
                "priority": 100,
                "is_active": True,
            },
        ]
        # Add default moderation rules using database service
        for rule in default_rules:
            await db_service.create_moderation_rule(
                project_id=project.id,
                name=rule["name"],
                rule_type=rule["rule_type"],
                rule_content=str(rule["rule_data"]),
                action=rule["action"],
                priority=rule["priority"]
            )

        # Create default API key
        import secrets
        key_value = f"ak_{secrets.token_urlsafe(32)}"
        await db_service.create_api_key(
            project_id=project.id,
            name='Default Key',
            key_value=key_value
        )

        flash('Project created successfully!', 'success')
        return redirect(url_for('dashboard.project_detail', project_id=project.id))

    return render_template('dashboard/create_project.html')


@dashboard_bp.route('/projects/<project_id>')
@login_required
async def project_detail(project_id):
    """Project detail page"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has access to this project
    if not project.is_member(current_user.id):
        flash('You do not have access to this project', 'error')
        return redirect(url_for('dashboard.projects'))

    # Get recent content
    recent_content = Content.query.filter_by(project_id=project.id).order_by(
        Content.created_at.desc()).limit(10).all()

    # Get stats
    total_content = Content.query.filter_by(project_id=project.id).count()
    approved_content = Content.query.filter_by(
        project_id=project.id, status='approved').count()
    rejected_content = Content.query.filter_by(
        project_id=project.id, status='rejected').count()
    flagged_content = Content.query.filter_by(
        project_id=project.id, status='flagged').count()

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
                           stats=stats)


@dashboard_bp.route('/projects/<project_id>/api-keys')
@login_required
async def project_api_keys(project_id):
    """Manage project API keys"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has access to this project
    if not project.is_member(current_user.id):
        flash('You do not have access to this project', 'error')
        return redirect(url_for('dashboard.projects'))
    return render_template('dashboard/api_keys.html', project=project)


@dashboard_bp.route('/projects/<project_id>/api-keys/create', methods=['POST'])
@login_required
async def create_api_key(project_id):
    """Create new API key"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has access to this project
    if not project.is_member(current_user.id):
        flash('You do not have access to this project', 'error')
        return redirect(url_for('dashboard.projects'))

    name = request.form.get('name')
    if not name:
        flash('API key name is required', 'error')
        return redirect(url_for('dashboard.project_api_keys', project_id=project_id))

    api_key = APIKey(name=name, project_id=project.id)
    db.session.add(api_key)
    db.session.commit()

    flash('API key created successfully!', 'success')
    return redirect(url_for('dashboard.project_api_keys', project_id=project_id))


@dashboard_bp.route('/projects/<project_id>/rules')
@login_required
async def project_rules(project_id):
    """Manage project moderation rules"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has access to this project
    if not project.is_member(current_user.id):
        flash('You do not have access to this project', 'error')
        return redirect(url_for('dashboard.projects'))
    rules = ModerationRule.query.filter_by(project_id=project.id).order_by(
        ModerationRule.priority.desc()).all()
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

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


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

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


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

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


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

    query = Content.query.filter_by(project_id=project.id)
    if status:
        query = query.filter_by(status=status)

    pagination = query.order_by(Content.created_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )

    return render_template('dashboard/content.html',
                           project=project,
                           pagination=pagination,
                           current_status=status)


@dashboard_bp.route('/projects/<project_id>/content/<content_id>')
@login_required
async def get_content_details(project_id, content_id):
    """Get content details for modal"""
    project = Project.query.filter_by(id=project_id).first_or_404()

    # Check if user has access to this project
    if not project.is_member(current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    content = Content.query.filter_by(
        id=content_id, project_id=project.id).first_or_404()

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

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


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

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


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
    except Exception:
        db.session.rollback()
        flash('Error updating project', 'error')

    return redirect(url_for('dashboard.project_settings', project_id=project_id))


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

    db.session.delete(membership)
    db.session.commit()

    flash(f'Member {membership.user.username} removed from project', 'success')
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
