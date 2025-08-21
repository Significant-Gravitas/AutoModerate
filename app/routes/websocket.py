import asyncio

from flask import Blueprint
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room

from app import socketio
from app.services.database_service import db_service

websocket_bp = Blueprint('websocket', __name__)


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    if current_user.is_authenticated:
        emit('connected', {'message': 'Connected to AutoModerate'})
    else:
        emit('error', {'message': 'Authentication required'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    pass


@socketio.on('join_project')
def handle_join_project(data):
    """Join a project room for real-time updates"""
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return

        project_id = data.get('project_id')
        if not project_id:
            emit('error', {'message': 'Project ID required'})
            return

        print(f"User {current_user.id} attempting to join project {project_id}")

        # Verify user has access to the project (owner or member)
        project = asyncio.run(db_service.get_project_by_id(project_id))
        if not project:
            print(f"Project {project_id} not found")
            emit('error', {'message': 'Project not found'})
            return

        # Check if user is owner or member using centralized service
        is_member = asyncio.run(
            db_service.is_project_member(project_id, current_user.id))
        if not is_member:
            print(
                f"User {current_user.id} is not a member of project {project_id}")
            emit(
                'error', {'message': 'Access denied - you are not a member of this project'})
            return

        room = f"project_{project_id}"
        join_room(room)
        print(f"User {current_user.id} joined room {room}")
        emit('joined_project', {'project_id': project_id, 'room': room})

    except Exception as e:
        print(f"Error in join_project: {str(e)}")
        emit('error', {'message': f'Server error: {str(e)}'})


@socketio.on('leave_project')
def handle_leave_project(data):
    """Leave a project room"""
    if not current_user.is_authenticated:
        return

    project_id = data.get('project_id')
    if project_id:
        room = f"project_{project_id}"
        leave_room(room)
        emit('left_project', {'project_id': project_id})
