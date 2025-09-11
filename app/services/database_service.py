"""
Async Centralized Database Service Layer for AutoModerate
High-performance async database operations with consistent error handling
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app import db
from app.models.api_key import APIKey
from app.models.api_user import APIUser
from app.models.content import Content
from app.models.moderation_result import ModerationResult
from app.models.moderation_rule import ModerationRule
from app.models.project import Project, ProjectMember
from app.models.user import User

logger = logging.getLogger(__name__)


class DatabaseService:
    """Async centralized database operations with consistent error handling"""

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=20)

    async def _safe_execute(self, operation_func, *args, **kwargs):
        """Execute database operation asynchronously in thread pool"""
        from flask import current_app, has_app_context

        loop = asyncio.get_event_loop()

        # If we have an app context, we need to preserve it for the thread pool
        if has_app_context():
            app = current_app._get_current_object()

            def context_operation():
                with app.app_context():
                    return operation_func(*args, **kwargs)

            try:
                return await loop.run_in_executor(self._executor, context_operation)
            except SQLAlchemyError as e:
                logger.error(f"Database error: {str(e)}")

                def rollback_operation():
                    with app.app_context():
                        db.session.rollback()
                await loop.run_in_executor(self._executor, rollback_operation)
                return None
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return None
        else:
            # No app context, run directly (shouldn't happen in normal operation)
            try:
                return await loop.run_in_executor(self._executor, operation_func, *args, **kwargs)
            except SQLAlchemyError as e:
                logger.error(f"Database error: {str(e)}")
                await loop.run_in_executor(self._executor, db.session.rollback)
                return None
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return None

    # User Operations
    async def create_user(self, username: str, email: str, password: str, is_admin: bool = False) -> Optional[User]:
        """Create a new user"""
        def _create_user():
            user = User(username=username, email=email, is_admin=is_admin)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return user

        return await self._safe_execute(_create_user)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        def _get_user():
            return User.query.filter_by(email=email).first()

        return await self._safe_execute(_get_user)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        def _get_user():
            return User.query.filter_by(username=username).first()

        return await self._safe_execute(_get_user)

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        def _get_user():
            return User.query.get(user_id)

        return await self._safe_execute(_get_user)

    async def get_user_with_projects(self, user_id: str) -> Optional[User]:
        """Get user by ID with projects and related data loaded"""
        def _get_user():
            from sqlalchemy.orm import joinedload
            return User.query.options(
                joinedload(User.projects)
                .joinedload(Project.api_keys),
                joinedload(User.projects)
                .joinedload(Project.content)
            ).filter_by(id=user_id).first()

        return await self._safe_execute(_get_user)

    async def update_user_profile(self, user: User, **kwargs) -> bool:
        """Update user profile information"""
        def _update_user():
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            db.session.commit()
            return True

        result = await self._safe_execute(_update_user)
        return result is not None

    async def delete_user(self, user: User) -> bool:
        """Delete a user"""
        def _delete_user():
            db.session.delete(user)
            db.session.commit()
            return True

        result = await self._safe_execute(_delete_user)
        return result is not None

    async def toggle_user_admin_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Toggle admin status for a user"""
        def _toggle_admin():
            user = User.query.get(user_id)
            if not user:
                return None
            user.is_admin = not user.is_admin
            db.session.commit()
            # Return the needed data as a dictionary to avoid detached instance issues
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin,
                'is_active': user.is_active
            }

        return await self._safe_execute(_toggle_admin)

    async def toggle_user_active_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Toggle active status for a user"""
        def _toggle_active():
            user = User.query.get(user_id)
            if not user:
                return None
            user.is_active = not user.is_active
            db.session.commit()
            # Return the needed data as a dictionary to avoid detached instance issues
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin,
                'is_active': user.is_active
            }

        return await self._safe_execute(_toggle_active)

    async def update_user_password(self, user_id: str, new_password: str) -> bool:
        """Update user password"""
        def _update_password():
            user = User.query.get(user_id)
            if not user:
                return False
            user.set_password(new_password)
            db.session.commit()
            return True

        result = await self._safe_execute(_update_password)
        return result is not None and result is not False

    # Project Operations
    async def create_project(self, name: str, description: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Create a new project"""
        def _create_project():
            project = Project(
                name=name, description=description, user_id=user_id)
            db.session.add(project)
            db.session.commit()
            # Return the needed data as a dictionary to avoid detached instance issues
            return {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'user_id': project.user_id,
                'is_active': project.is_active,
                'created_at': project.created_at,
                'updated_at': project.updated_at
            }

        return await self._safe_execute(_create_project)

    async def get_user_projects(self, user_id: str) -> List[Project]:
        """Get all projects accessible to a user (owned + member)"""
        def _get_projects():
            owned_project_ids = db.session.query(
                Project.id).filter_by(user_id=user_id)
            member_project_ids = db.session.query(Project.id).join(ProjectMember).filter(
                ProjectMember.user_id == user_id
            )
            all_project_ids = owned_project_ids.union(member_project_ids)
            return Project.query.filter(Project.id.in_(all_project_ids)).all()

        return await self._safe_execute(_get_projects) or []

    async def get_project_by_id(self, project_id: str) -> Optional[Project]:
        """Get project by ID"""
        def _get_project():
            return Project.query.get(project_id)

        return await self._safe_execute(_get_project)

    async def get_project_by_id_secure(self, project_id: str) -> Optional[Project]:
        """Get project by ID with 404 handling"""
        def _get_project():
            return Project.query.filter_by(id=project_id).first_or_404()

        return await self._safe_execute(_get_project)

    async def update_project(self, project: Project, **kwargs) -> bool:
        """Update project information"""
        def _update_project():
            for key, value in kwargs.items():
                if hasattr(project, key):
                    setattr(project, key, value)
            db.session.commit()
            return True

        result = await self._safe_execute(_update_project)
        return result is not None

    async def delete_project(self, project: Project) -> bool:
        """Delete a project"""
        def _delete_project():
            db.session.delete(project)
            db.session.commit()
            return True

        result = await self._safe_execute(_delete_project)
        return result is not None

    async def is_project_member(self, project_id: str, user_id: str) -> bool:
        """Check if user is a member or owner of a project"""
        def _check_membership():
            from app.models.project import ProjectMember

            # Check if user is the owner
            project = Project.query.get(project_id)
            if not project:
                return False
            if project.user_id == user_id:
                return True

            # Check if user is a member
            membership = ProjectMember.query.filter_by(
                project_id=project_id,
                user_id=user_id
            ).first()
            return membership is not None

        result = await self._safe_execute(_check_membership)
        return result is not None and result

    # Content Operations
    async def create_content(self, project_id: str, content_text: str, content_type: str = 'text',
                             api_user_id: Optional[str] = None, meta_data: Optional[dict] = None) -> Optional[str]:
        """Create new content for moderation and return content ID"""
        def _create_content():
            content = Content(
                project_id=project_id,
                content_data=content_text,
                content_type=content_type,
                api_user_id=api_user_id,
                meta_data=meta_data
            )
            db.session.add(content)
            db.session.commit()
            # Return just the ID to avoid detached instance issues
            return content.id

        return await self._safe_execute(_create_content)

    async def get_project_content(self, project_id: str, limit: int = 100, offset: int = 0) -> List[Content]:
        """Get content for a project with pagination"""
        def _get_content():
            return Content.query.filter_by(project_id=project_id)\
                .order_by(Content.created_at.desc())\
                .limit(limit).offset(offset).all()

        return await self._safe_execute(_get_content) or []

    async def get_project_content_with_filters(self, project_id: str, status: str = None, limit: int = 50,
                                               offset: int = 0) -> List[Content]:
        """Get content for a project with optional status filter"""
        def _get_content():
            query = Content.query.filter_by(project_id=project_id)
            if status:
                query = query.filter_by(status=status)
            return query.order_by(Content.created_at.desc()).limit(limit).offset(offset).all()

        return await self._safe_execute(_get_content) or []

    async def get_content_by_id(self, content_id: str) -> Optional[Content]:
        """Get content by ID"""
        def _get_content():
            return Content.query.get(content_id)

        return await self._safe_execute(_get_content)

    async def get_content_by_id_and_project(self, content_id: str, project_id: str) -> Optional[Content]:
        """Get content by ID and project ID"""
        def _get_content():
            return Content.query.filter_by(id=content_id, project_id=project_id).first()

        return await self._safe_execute(_get_content)

    # API Key Operations
    async def create_api_key(self, project_id: str, name: str, key_value: str) -> Optional[APIKey]:
        """Create new API key"""
        def _create_key():
            api_key = APIKey(project_id=project_id, name=name, key=key_value)
            db.session.add(api_key)
            db.session.commit()
            return api_key

        return await self._safe_execute(_create_key)

    async def get_api_key_by_value(self, key_value: str) -> Optional[APIKey]:
        """Get API key by value with project relationship loaded"""
        def _get_key():
            return APIKey.query.options(joinedload(APIKey.project)).filter_by(key=key_value, is_active=True).first()

        return await self._safe_execute(_get_key)

    async def get_project_api_keys(self, project_id: str) -> List[APIKey]:
        """Get all API keys for a project"""
        def _get_keys():
            return APIKey.query.filter_by(project_id=project_id).all()

        return await self._safe_execute(_get_keys) or []

    # Moderation Rule Operations
    async def create_moderation_rule(self, project_id: str, name: str, rule_type: str,
                                     rule_data: dict, action: str, priority: int = 0,
                                     description: str = '') -> Optional[Dict[str, Any]]:
        """Create new moderation rule"""
        def _create_rule():
            rule = ModerationRule(
                project_id=project_id,
                name=name,
                description=description,
                rule_type=rule_type,
                rule_data=rule_data,
                action=action,
                priority=priority
            )
            db.session.add(rule)
            db.session.commit()
            # Return the needed data as a dictionary to avoid detached instance issues
            return {
                'id': rule.id,
                'project_id': rule.project_id,
                'name': rule.name,
                'description': rule.description,
                'rule_type': rule.rule_type,
                'rule_data': rule.rule_data,
                'action': rule.action,
                'priority': rule.priority,
                'is_active': rule.is_active,
                'created_at': rule.created_at,
                'updated_at': rule.updated_at
            }

        return await self._safe_execute(_create_rule)

    async def get_project_rules(self, project_id: str) -> List[ModerationRule]:
        """Get all active moderation rules for a project"""
        def _get_rules():
            return ModerationRule.query.filter_by(project_id=project_id, is_active=True)\
                .order_by(ModerationRule.priority.desc()).all()

        return await self._safe_execute(_get_rules) or []

    async def get_rule_by_id(self, rule_id: str) -> Optional[ModerationRule]:
        """Get moderation rule by ID"""
        def _get_rule():
            return ModerationRule.query.get(rule_id)

        return await self._safe_execute(_get_rule)

    async def get_all_rules_for_project(self, project_id: str, include_inactive: bool = True) -> List[ModerationRule]:
        """Get all rules for a project"""
        def _get_rules():
            query = ModerationRule.query.filter_by(project_id=project_id)
            if not include_inactive:
                query = query.filter_by(is_active=True)
            return query.order_by(ModerationRule.priority.desc()).all()

        return await self._safe_execute(_get_rules) or []

    # Statistics and Analytics
    async def get_project_stats(self, project_id: str) -> Dict[str, Any]:
        """Get comprehensive project statistics"""
        def _get_stats():
            from datetime import datetime, timedelta

            total_content = Content.query.filter_by(
                project_id=project_id).count()
            total_rules = ModerationRule.query.filter_by(
                project_id=project_id, is_active=True).count()
            total_api_keys = APIKey.query.filter_by(
                project_id=project_id, is_active=True).count()
            flagged_content = Content.query.filter_by(
                project_id=project_id, status='flagged').count()
            approved_content = Content.query.filter_by(
                project_id=project_id, status='approved').count()

            # Recent activity (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_content = Content.query.filter(
                Content.project_id == project_id,
                Content.created_at >= week_ago
            ).count()

            return {
                'total_content': total_content,
                'total_rules': total_rules,
                'total_api_keys': total_api_keys,
                'flagged_content': flagged_content,
                'approved_content': approved_content,
                'recent_content': recent_content
            }

        return await self._safe_execute(_get_stats) or {}

    async def get_admin_stats(self) -> Dict[str, Any]:
        """Get system-wide statistics for admin dashboard"""
        def _get_stats():
            from datetime import datetime, timedelta

            week_ago = datetime.utcnow() - timedelta(days=7)

            return {
                'total_users': User.query.count(),
                'total_projects': Project.query.count(),
                'total_content': Content.query.count(),
                'total_rules': ModerationRule.query.filter_by(is_active=True).count(),
                'flagged_content': Content.query.filter_by(status='flagged').count(),
                'new_users_week': User.query.filter(User.created_at >= week_ago).count(),
                'new_content_week': Content.query.filter(Content.created_at >= week_ago).count(),
            }

        return await self._safe_execute(_get_stats) or {}

    # API User Operations
    async def get_or_create_api_user(self, external_user_id: str, project_id: str) -> Optional[APIUser]:
        """Get existing API user or create new one"""
        def _get_or_create():
            api_user = APIUser.query.filter_by(
                external_user_id=external_user_id,
                project_id=project_id
            ).first()

            if not api_user:
                api_user = APIUser(
                    external_user_id=external_user_id,
                    project_id=project_id
                )
                db.session.add(api_user)
                db.session.commit()

            return api_user

        return await self._safe_execute(_get_or_create)

    async def get_api_user_by_id(self, api_user_id: str) -> Optional[APIUser]:
        """Get API user by ID"""
        def _get_user():
            return APIUser.query.get(api_user_id)

        return await self._safe_execute(_get_user)

    # Content Query Operations
    async def get_content_counts_by_status(self, project_id: str) -> Dict[str, int]:
        """Get content counts by moderation status"""
        def _get_counts():
            total = Content.query.filter_by(project_id=project_id).count()
            approved = Content.query.filter_by(
                project_id=project_id, status='approved').count()
            rejected = Content.query.filter_by(
                project_id=project_id, status='rejected').count()
            flagged = Content.query.filter_by(
                project_id=project_id, status='flagged').count()
            pending = Content.query.filter_by(
                project_id=project_id, status='pending').count()

            return {
                'total': total,
                'approved': approved,
                'rejected': rejected,
                'flagged': flagged,
                'pending': pending
            }

        return await self._safe_execute(_get_counts) or {'total': 0, 'approved': 0, 'rejected': 0, 'flagged': 0, 'pending': 0}

    async def update_content_status(self, content_id: str, **kwargs) -> bool:
        """Update content status and flags"""
        def _update_content():
            content = Content.query.get(content_id)
            if not content:
                return False

            for key, value in kwargs.items():
                if hasattr(content, key):
                    setattr(content, key, value)

            db.session.commit()
            return True

        result = await self._safe_execute(_update_content)
        return result is not None and result is not False

    # API Key Management
    async def update_api_key_usage(self, api_key: APIKey) -> bool:
        """Update API key usage statistics"""
        def _update_usage():
            api_key.increment_usage()
            db.session.commit()
            return True

        result = await self._safe_execute(_update_usage)
        return result is not None

    # Transaction Management
    async def commit_transaction(self) -> bool:
        """Commit current transaction"""
        def _commit():
            db.session.commit()
            return True

        result = await self._safe_execute(_commit)
        return result is not None

    async def rollback_transaction(self) -> None:
        """Rollback current transaction"""
        def _rollback():
            db.session.rollback()

        await self._safe_execute(_rollback)

    # Admin-specific methods
    async def get_recent_users(self, limit: int = 5) -> List[User]:
        """Get recent users for admin dashboard"""
        def _get_recent():
            return User.query.order_by(User.created_at.desc()).limit(limit).all()

        return await self._safe_execute(_get_recent) or []

    async def get_recent_projects(self, limit: int = 5) -> List[Project]:
        """Get recent projects for admin dashboard"""
        def _get_recent():
            from sqlalchemy.orm import joinedload
            return Project.query.options(
                joinedload(Project.owner)
            ).order_by(Project.created_at.desc()).limit(limit).all()

        return await self._safe_execute(_get_recent) or []

    async def get_recent_content_admin(self, limit: int = 10) -> List[Content]:
        """Get recent content for admin dashboard"""
        def _get_recent():
            from sqlalchemy.orm import joinedload
            return Content.query.options(
                joinedload(Content.project).joinedload(Project.owner)
            ).order_by(Content.created_at.desc()).limit(limit).all()

        return await self._safe_execute(_get_recent) or []

    async def get_moderation_result_stats(self) -> Dict[str, Any]:
        """Get moderation result statistics"""
        def _get_stats():
            return {
                'total_moderations': ModerationResult.query.count(),
                'approved_decisions': ModerationResult.query.filter_by(decision='approved').count(),
                'rejected_decisions': ModerationResult.query.filter_by(decision='rejected').count(),
                'flagged_decisions': ModerationResult.query.filter_by(decision='flagged').count(),
            }

        return await self._safe_execute(_get_stats) or {}

    async def get_user_projects_for_admin(self, user_id: str) -> List[Project]:
        """Get user projects for admin view"""
        def _get_projects():
            from sqlalchemy.orm import joinedload
            return Project.query.options(
                joinedload(Project.owner),
                joinedload(Project.content),
                joinedload(Project.moderation_rules),
                joinedload(Project.api_keys)
            ).filter_by(user_id=user_id).all()

        return await self._safe_execute(_get_projects) or []

    async def get_all_projects_for_admin(self, page: int = 1, per_page: int = 20) -> List[Project]:
        """Get all projects for admin view with pagination (lightweight)"""
        def _get_projects():
            from sqlalchemy.orm import joinedload
            offset = (page - 1) * per_page
            # Only load owner data, not all content/rules/keys which can be huge
            return Project.query.options(
                joinedload(Project.owner)
            ).offset(offset).limit(per_page).all()

        return await self._safe_execute(_get_projects) or []

    async def bulk_save_objects(self, objects: List) -> bool:
        """Bulk save objects to database"""
        def _bulk_save():
            for obj in objects:
                db.session.add(obj)
            db.session.commit()
            return True

        result = await self._safe_execute(_bulk_save)
        return result is not None


# Global async database service instance
db_service = DatabaseService()
