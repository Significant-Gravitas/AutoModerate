from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from app.models.content import Content
from app.models.project import Project
from app.models.api_user import APIUser
from app.models.moderation_result import ModerationResult
from app import db
from sqlalchemy import desc
import json

manual_review_bp = Blueprint('manual_review', __name__)

@manual_review_bp.route('/manual-review')
@login_required
def index():
    """Manual review dashboard - shows flagged content across all projects user has access to"""
    try:
        # Get all projects the user has access to
        user_projects = []
        if current_user.is_admin:
            # Admin can see all projects
            user_projects = Project.query.all()
        else:
            # Regular users can only see projects they're members of
            user_projects = [p for p in Project.query.all() if p.is_member(current_user.id)]
        
        project_ids = [p.id for p in user_projects]
        
        # Get flagged content from these projects
        flagged_content = Content.query.filter(
            Content.project_id.in_(project_ids),
            Content.status == 'flagged'
        ).order_by(desc(Content.created_at)).all()
        
        # Get statistics
        total_flagged = len(flagged_content)
        total_approved = Content.query.filter(
            Content.project_id.in_(project_ids),
            Content.status == 'approved'
        ).count()
        total_rejected = Content.query.filter(
            Content.project_id.in_(project_ids),
            Content.status == 'rejected'
        ).count()
        
        return render_template('manual_review/index.html', 
                             flagged_content=flagged_content,
                             total_flagged=total_flagged,
                             total_approved=total_approved,
                             total_rejected=total_rejected,
                             projects=user_projects)
        
    except Exception as e:
        current_app.logger.error(f"Manual review index error: {str(e)}")
        flash('Error loading manual review dashboard', 'error')
        return redirect(url_for('dashboard.index'))

@manual_review_bp.route('/manual-review/<content_id>')
@login_required
def review_content(content_id):
    """Review specific flagged content"""
    try:
        content = Content.query.get_or_404(content_id)
        
        # Check if user has access to this project
        if not current_user.is_admin and not content.project.is_member(current_user.id):
            flash('You do not have access to this content', 'error')
            return redirect(url_for('manual_review.index'))
        
        # Get moderation results for this content
        moderation_results = ModerationResult.query.filter_by(content_id=content.id).all()
        
        # Get API user info if available
        api_user = None
        if content.api_user_id:
            api_user = APIUser.query.get(content.api_user_id)
        
        return render_template('manual_review/review_content.html',
                             content=content,
                             moderation_results=moderation_results,
                             api_user=api_user)
        
    except Exception as e:
        current_app.logger.error(f"Review content error: {str(e)}")
        flash('Error loading content for review', 'error')
        return redirect(url_for('manual_review.index'))

@manual_review_bp.route('/manual-review/<content_id>/decision', methods=['POST'])
@login_required
def make_decision(content_id):
    """Make a manual decision on flagged content"""
    try:
        content = Content.query.get_or_404(content_id)
        
        # Check if user has access to this project
        if not current_user.is_admin and not content.project.is_member(current_user.id):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        data = request.get_json()
        decision = data.get('decision')
        reason = data.get('reason', 'Manual review decision')
        
        if decision not in ['approved', 'rejected']:
            return jsonify({'success': False, 'error': 'Invalid decision'}), 400
        
        # Update content status
        content.status = decision
        
        # Create manual moderation result
        manual_result = ModerationResult(
            content_id=content.id,
            decision=decision,
            confidence=1.0,  # Manual decisions have 100% confidence
            reason=reason,
            moderator_type='manual',
            moderator_id=current_user.id,
            processing_time=0.0,
            details={
                'manual_reviewer': current_user.username,
                'reviewer_id': current_user.id,
                'review_notes': data.get('notes', '')
            }
        )
        db.session.add(manual_result)
        
        # Update API user stats if available
        if content.api_user_id:
            api_user = APIUser.query.get(content.api_user_id)
            if api_user:
                api_user.update_stats(decision)
        
        db.session.commit()
        
        current_app.logger.info(f"Manual decision made on content {content_id}: {decision} by {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': f'Content {decision} successfully',
            'decision': decision
        })
        
    except Exception as e:
        current_app.logger.error(f"Make decision error: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@manual_review_bp.route('/api-users')
@login_required
def api_users():
    """View API users and their moderation history"""
    try:
        # Get all projects the user has access to
        user_projects = []
        if current_user.is_admin:
            user_projects = Project.query.all()
        else:
            user_projects = [p for p in Project.query.all() if p.is_member(current_user.id)]
        
        project_ids = [p.id for p in user_projects]
        
        # Get API users from these projects
        api_users = APIUser.query.filter(
            APIUser.project_id.in_(project_ids)
        ).order_by(desc(APIUser.last_seen)).all()
        
        return render_template('manual_review/api_users.html', api_users=api_users)
        
    except Exception as e:
        current_app.logger.error(f"API users error: {str(e)}")
        flash('Error loading API users', 'error')
        return redirect(url_for('dashboard.index'))

@manual_review_bp.route('/api-users/<user_id>')
@login_required
def api_user_detail(user_id):
    """View detailed information about a specific API user"""
    try:
        api_user = APIUser.query.get_or_404(user_id)
        
        # Check if user has access to this project
        if not current_user.is_admin and not api_user.project.is_member(current_user.id):
            flash('You do not have access to this user', 'error')
            return redirect(url_for('manual_review.api_users'))
        
        # Get all content from this API user
        content_items = Content.query.filter_by(api_user_id=user_id).order_by(desc(Content.created_at)).all()
        
        return render_template('manual_review/api_user_detail.html',
                             api_user=api_user,
                             content_items=content_items)
        
    except Exception as e:
        current_app.logger.error(f"API user detail error: {str(e)}")
        flash('Error loading user details', 'error')
        return redirect(url_for('manual_review.api_users'))

@manual_review_bp.route('/manual-review/api-users/<user_id>/content/<content_id>')
@login_required
def get_api_user_content_details(user_id, content_id):
    """Get content details for modal in API user detail page"""
    try:
        api_user = APIUser.query.get_or_404(user_id)
        
        # Check if user has access to this project
        if not current_user.is_admin and not api_user.project.is_member(current_user.id):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        content = Content.query.filter_by(id=content_id, api_user_id=user_id).first_or_404()
        
        return jsonify({
            'success': True,
            'content': content.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"Get API user content details error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
