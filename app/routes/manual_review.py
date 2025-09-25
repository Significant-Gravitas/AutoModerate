from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import desc

from app import db
from app.models.api_user import APIUser
from app.models.content import Content
from app.models.moderation_result import ModerationResult
from app.models.project import Project
from app.services.database_service import db_service

manual_review_bp = Blueprint('manual_review', __name__)


@manual_review_bp.route('/manual-review')
@login_required
async def index():
    """Manual review dashboard - shows flagged content across all projects user has access to"""
    try:
        # Get all projects the user has access to using database service
        if current_user.is_admin:
            # Admin can see all projects (with pagination for performance)
            user_projects = await db_service.get_all_projects_for_admin(page=1, per_page=1000)
        else:
            # Regular users can only see projects they're members of
            user_projects = await db_service.get_user_projects(current_user.id)

        project_ids = [p.id for p in user_projects]

        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = 50  # Limit to 50 items per page

        # Get flagged content from these projects with pagination
        flagged_content, total_flagged = await db_service.get_flagged_content_for_projects(
            project_ids, page=page, per_page=per_page)

        # Get additional statistics
        total_approved = Content.query.filter(
            Content.project_id.in_(project_ids),
            Content.status == 'approved'
        ).count()
        total_rejected = Content.query.filter(
            Content.project_id.in_(project_ids),
            Content.status == 'rejected'
        ).count()

        # Create pagination object
        has_prev = page > 1
        has_next = len(flagged_content) == per_page
        prev_num = page - 1 if has_prev else None
        next_num = page + 1 if has_next else None

        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total_flagged,
            'has_prev': has_prev,
            'has_next': has_next,
            'prev_num': prev_num,
            'next_num': next_num
        }

        return render_template('manual_review/index.html',
                               flagged_content=flagged_content,
                               total_flagged=total_flagged,
                               total_approved=total_approved,
                               total_rejected=total_rejected,
                               projects=user_projects,
                               pagination=pagination)

    except Exception as e:
        current_app.logger.error(f"Manual review index error: {str(e)}")
        flash('Error loading manual review dashboard', 'error')
        return redirect(url_for('dashboard.index'))


@manual_review_bp.route('/manual-review/<content_id>')
@login_required
async def review_content(content_id):
    """Review specific flagged content"""
    try:
        content = Content.query.get_or_404(content_id)

        # Check if user has access to this project
        if not current_user.is_admin and not content.project.is_member(current_user.id):
            flash('You do not have access to this content', 'error')
            return redirect(url_for('manual_review.index'))

        # Get moderation results for this content
        moderation_results = ModerationResult.query.filter_by(
            content_id=content.id).all()

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
async def make_decision(content_id):
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

        current_app.logger.info(
            f"Manual decision made on content {content_id}: {decision} by {current_user.username}")

        return jsonify({
            'success': True,
            'message': f'Content {decision} successfully',
            'decision': decision
        })

    except Exception as e:
        current_app.logger.error(f"Make decision error: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@manual_review_bp.route('/manual-review/bulk-decision', methods=['POST'])
@login_required
async def bulk_decision():
    """Make bulk manual decisions on multiple flagged content items"""
    try:
        data = request.get_json()
        content_ids = data.get('content_ids', [])
        decision = data.get('decision')
        reason = data.get('reason', 'Bulk manual review decision')
        notes = data.get('notes', '')

        if not content_ids:
            return jsonify({'success': False, 'error': 'No content IDs provided'}), 400

        if decision not in ['approved', 'rejected']:
            return jsonify({'success': False, 'error': 'Invalid decision'}), 400

        if not reason.strip():
            return jsonify({'success': False, 'error': 'Reason is required'}), 400

        # Get all content items and validate access
        content_items = Content.query.filter(Content.id.in_(content_ids)).all()

        if len(content_items) != len(content_ids):
            return jsonify({'success': False, 'error': 'Some content items not found'}), 404

        # Check user has access to all projects
        for content in content_items:
            if not current_user.is_admin and not content.project.is_member(current_user.id):
                return jsonify({
                    'success': False,
                    'error': f'Access denied for content in project {content.project.name}'
                }), 403

        processed_count = 0
        failed_items = []

        # Process each content item
        for content in content_items:
            try:
                # Skip if already processed (not flagged)
                if content.status != 'flagged':
                    continue

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
                        'review_notes': notes,
                        'bulk_action': True,
                        'bulk_count': len(content_ids)
                    }
                )
                db.session.add(manual_result)

                # Update API user stats if available
                if content.api_user_id:
                    api_user = APIUser.query.get(content.api_user_id)
                    if api_user:
                        api_user.update_stats(decision)

                processed_count += 1

            except Exception as item_error:
                current_app.logger.error(
                    f"Error processing content {content.id}: {str(item_error)}")
                failed_items.append(content.id)

        # Commit all changes
        db.session.commit()

        current_app.logger.info(
            f"Bulk manual decision made on {processed_count} content items: {decision} by {current_user.username}")

        response_data = {
            'success': True,
            'message': f'Successfully {decision} {processed_count} content item(s)',
            'processed_count': processed_count,
            'decision': decision
        }

        if failed_items:
            response_data['failed_items'] = failed_items
            response_data['message'] += f' ({len(failed_items)} failed)'

        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Bulk decision error: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@manual_review_bp.route('/api-users')
@login_required
async def api_users():
    """View API users and their moderation history"""
    try:
        # Get all projects the user has access to
        user_projects = []
        if current_user.is_admin:
            user_projects = Project.query.all()
        else:
            user_projects = [
                p for p in Project.query.all() if p.is_member(current_user.id)]

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


@manual_review_bp.route('/api-users/external/<external_user_id>')
@login_required
async def api_user_by_external_id(external_user_id):
    """Redirect to API user detail by external user ID"""
    try:
        # Get all projects the user has access to
        user_projects = []
        if current_user.is_admin:
            user_projects = Project.query.all()
        else:
            user_projects = [
                project for project in current_user.projects
                if project.is_member(current_user.id)
            ]

        if not user_projects:
            flash('You do not have access to any projects', 'error')
            return redirect(url_for('manual_review.index'))

        project_ids = [project.id for project in user_projects]

        # Find API user by external user ID within accessible projects
        api_user = APIUser.query.filter(
            APIUser.external_user_id == external_user_id,
            APIUser.project_id.in_(project_ids)
        ).first()

        if not api_user:
            flash(f'API user with ID "{external_user_id}" not found in your accessible projects', 'error')
            return redirect(url_for('manual_review.api_users'))

        # Redirect to the internal ID route
        return redirect(url_for('manual_review.api_user_detail', user_id=api_user.id))

    except Exception as e:
        current_app.logger.error(f"External API user lookup error: {str(e)}")
        flash('An error occurred while looking up the user', 'error')
        return redirect(url_for('manual_review.api_users'))


@manual_review_bp.route('/api-users/<user_id>')
@login_required
async def api_user_detail(user_id):
    """View detailed information about a specific API user"""
    try:
        api_user = APIUser.query.get_or_404(user_id)

        # Check if user has access to this project
        if not current_user.is_admin and not api_user.project.is_member(current_user.id):
            flash('You do not have access to this user', 'error')
            return redirect(url_for('manual_review.api_users'))

        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = 20  # Show 20 content items per page

        # Get paginated content from this API user
        content_pagination = Content.query.filter_by(
            api_user_id=user_id
        ).order_by(desc(Content.created_at)).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return render_template('manual_review/api_user_detail.html',
                               api_user=api_user,
                               content_items=content_pagination.items,
                               pagination=content_pagination)

    except Exception as e:
        current_app.logger.error(f"API user detail error: {str(e)}")
        flash('Error loading user details', 'error')
        return redirect(url_for('manual_review.api_users'))


@manual_review_bp.route('/manual-review/api-users/<user_id>/content/<content_id>')
@login_required
async def get_api_user_content_details(user_id, content_id):
    """Get content details for modal in API user detail page"""
    try:
        api_user = APIUser.query.get_or_404(user_id)

        # Check if user has access to this project
        if not current_user.is_admin and not api_user.project.is_member(current_user.id):
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        content = Content.query.filter_by(
            id=content_id, api_user_id=user_id).first_or_404()

        return jsonify({
            'success': True,
            'content': content.to_dict()
        })

    except Exception as e:
        current_app.logger.error(
            f"Get API user content details error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
