"""
Project access validation utilities
"""
from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user

from app.services.database_service import db_service


async def validate_project_access(project_id: str, user_id: str = None):
    """
    Validate user access to a project

    Args:
        project_id: Project ID to validate access for
        user_id: User ID to check access for (defaults to current_user.id)

    Returns:
        tuple: (project, is_member) or (None, False) if not found/no access
    """
    if user_id is None:
        user_id = current_user.id

    # Get project using database service
    project = await db_service.get_project_by_id(project_id)
    if not project:
        return None, False

    # Check if user has access to this project
    is_member = await db_service.is_project_member(project_id, user_id)
    return project, is_member


def require_project_access(f):
    """
    Decorator to require project access for routes that take project_id parameter
    Adds 'project' to the route function's keyword arguments
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        project_id = kwargs.get('project_id')
        if not project_id:
            flash('Project ID required', 'error')
            return redirect(url_for('dashboard.projects'))

        project, is_member = await validate_project_access(project_id)

        if not project:
            flash('Project not found', 'error')
            return redirect(url_for('dashboard.projects'))

        if not is_member:
            flash('You do not have access to this project', 'error')
            return redirect(url_for('dashboard.projects'))

        # Add project to kwargs for the route function
        kwargs['project'] = project
        return await f(*args, **kwargs)

    return decorated_function


def require_project_owner(f):
    """
    Decorator to require project ownership for routes that take project_id parameter
    Adds 'project' to the route function's keyword arguments
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        project_id = kwargs.get('project_id')
        if not project_id:
            flash('Project ID required', 'error')
            return redirect(url_for('dashboard.projects'))

        project, is_member = await validate_project_access(project_id)

        if not project:
            flash('Project not found', 'error')
            return redirect(url_for('dashboard.projects'))

        if not is_member:
            flash('You do not have access to this project', 'error')
            return redirect(url_for('dashboard.projects'))

        # Check if user is the project owner
        if project.user_id != current_user.id:
            flash('You must be the project owner to perform this action', 'error')
            return redirect(url_for('dashboard.project_detail', project_id=project_id))

        # Add project to kwargs for the route function
        kwargs['project'] = project
        return await f(*args, **kwargs)

    return decorated_function
