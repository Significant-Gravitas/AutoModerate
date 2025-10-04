import asyncio
import time
from typing import Any, Dict

from flask import Blueprint, request
from flask_login import current_user
from flask_socketio import disconnect, emit, join_room, leave_room

from app import socketio
from app.services.database_service import db_service

# Rate limiting for WebSocket connections
_connection_attempts = {}
_MAX_ATTEMPTS_PER_MINUTE = 10

websocket_bp = Blueprint('websocket', __name__)


def _check_rate_limit(identifier: str) -> bool:
    """Check if connection attempts exceed rate limit"""
    current_time = time.time()
    minute_ago = current_time - 60

    # Clean old entries
    _connection_attempts[identifier] = [
        attempt for attempt in _connection_attempts.get(identifier, [])
        if attempt > minute_ago
    ]

    # Check current attempt count
    attempts = len(_connection_attempts.get(identifier, []))
    if attempts >= _MAX_ATTEMPTS_PER_MINUTE:
        return False

    # Record this attempt
    _connection_attempts.setdefault(identifier, []).append(current_time)
    return True


@socketio.on('connect')
def handle_connect() -> None:
    """Handle client connection with rate limiting"""
    client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
    session_id = request.sid

    # Rate limiting check
    if not _check_rate_limit(client_ip):
        print(f"WebSocket connection rate limited for IP {client_ip}")
        emit('error', {'message': 'Too many connection attempts. Please try again later.'})
        disconnect()
        return

    if current_user.is_authenticated:
        print(f"WebSocket connected: User {current_user.id}, Session {session_id}, IP {client_ip}")
        emit('connected', {'message': 'Connected to AutoModerate'})
    else:
        print(f"WebSocket connection rejected: Unauthenticated user from IP {client_ip}")
        emit('error', {'message': 'Authentication required'})
        disconnect()


@socketio.on('disconnect')
def handle_disconnect() -> None:
    """Handle client disconnection"""
    if current_user.is_authenticated:
        print(f"WebSocket disconnected: User {current_user.id}, Session {request.sid}")
    else:
        print(f"WebSocket disconnected: Anonymous session {request.sid}")


@socketio.on('join_project')
def handle_join_project(data: Dict[str, Any]) -> None:
    """Join a project room for real-time updates"""
    import concurrent.futures

    from flask import current_app

    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return

        project_id = data.get('project_id')
        if not project_id:
            emit('error', {'message': 'Project ID required'})
            return

        # Validate project_id format (should be UUID)
        if not isinstance(project_id, str) or len(project_id) > 100:
            emit('error', {'message': 'Invalid project ID format'})
            return

        print(f"User {current_user.id} attempting to join project {project_id}")

        # Get the app reference in the main thread context
        app = current_app._get_current_object()
        user_id = current_user.id  # Get user_id in the main thread context

        def run_async_operations():
            """Run async database operations in a separate thread with app context"""
            with app.app_context():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # Verify user has access to the project (owner or member)
                    project = loop.run_until_complete(
                        db_service.get_project_by_id(project_id))
                    if not project:
                        return None, f"Project {project_id} not found"

                    # Check if user is owner or member using centralized service
                    is_member = loop.run_until_complete(
                        db_service.is_project_member(project_id, user_id))
                    return project, None if is_member else "Access denied - you are not a member of this project"
                finally:
                    loop.close()

        # Use ThreadPoolExecutor for thread-safe async operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_async_operations)
            project, error_msg = future.result(timeout=10)  # 10-second timeout

            if error_msg:
                print(error_msg)
                emit('error', {'message': error_msg})
                return

        room = f"project_{project_id}"
        join_room(room)
        print(f"User {user_id} joined room {room}")
        emit('joined_project', {'project_id': project_id, 'room': room})

    except concurrent.futures.TimeoutError:
        print(f"Timeout in join_project for user {current_user.id}")
        emit('error', {'message': 'Server timeout - please try again'})
    except Exception as e:
        # Log full error details for debugging but don't expose to client
        import traceback
        print(f"Error in join_project for user {current_user.id}: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        emit('error', {'message': 'Server error occurred'})


@socketio.on('leave_project')
def handle_leave_project(data: Dict[str, Any]) -> None:
    """Leave a project room"""
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return

        project_id = data.get('project_id')
        if not project_id:
            emit('error', {'message': 'Project ID required'})
            return

        # Validate project_id format
        if not isinstance(project_id, str) or len(project_id) > 100:
            emit('error', {'message': 'Invalid project ID format'})
            return

        room = f"project_{project_id}"
        leave_room(room)
        print(f"User {current_user.id} left room {room}")
        emit('left_project', {'project_id': project_id})

    except Exception as e:
        import traceback
        print(f"Error in leave_project for user {current_user.id}: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        emit('error', {'message': 'Server error occurred'})
