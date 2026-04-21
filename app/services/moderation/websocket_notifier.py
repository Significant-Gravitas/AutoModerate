import logging
import threading
from datetime import datetime

from flask import current_app

logger = logging.getLogger(__name__)


class WebSocketNotifier:
    """Handles WebSocket notifications for moderation updates"""

    def send_update_async(self, content, decision, results, total_time):
        """Send WebSocket update in background thread"""
        try:
            content_data = {
                'id': content.id,
                'project_id': content.project_id,
                'content_type': content.content_type,
                'content_data': content.content_data,
                'meta_data': content.meta_data,
                # content.updated_at is the pre-update timestamp on the
                # detached ORM instance; the fresh moderation decision happens
                # right now, so use a current timestamp for the UI.
                'updated_at': datetime.utcnow().isoformat(),
            }

            app = current_app._get_current_object()
            threading.Thread(
                target=self._send_websocket_update,
                args=(app, content_data, decision, results, total_time),
                daemon=True
            ).start()
        except Exception as e:
            current_app.logger.error(
                f"[ws] Failed to start WebSocket thread: {str(e)}", exc_info=True)

    def _send_websocket_update(self, app, content_data, decision, results, total_time):
        """Send WebSocket update with proper Flask context"""
        room = f'project_{content_data["project_id"]}'
        try:
            with app.app_context():
                from app import socketio

                # Get moderator info from first result
                moderator_type = 'unknown'
                moderator_name = 'Unknown'
                rule_name = None

                if results:
                    first_result = results[0]
                    moderator_type = first_result.get(
                        'moderator_type', 'unknown')
                    if moderator_type == 'rule':
                        moderator_name = 'Rule'
                        rule_name = first_result.get(
                            'rule_name', 'Unknown Rule')
                    elif moderator_type == 'ai':
                        moderator_name = 'AI'
                    else:
                        moderator_name = moderator_type.title()

                # Build update data
                content_text = content_data['content_data']
                update_data = {
                    'content_id': content_data['id'],
                    'project_id': content_data['project_id'],
                    'status': decision,
                    'content_type': content_data['content_type'],
                    'content_preview': content_text[:100] + '...' if len(content_text) > 100 else content_text,
                    'meta_data': content_data['meta_data'],
                    'results_count': len(results),
                    'processing_time': total_time or 0.0,
                    'moderator_type': moderator_type,
                    'moderator_name': moderator_name,
                    'rule_name': rule_name,
                    'timestamp': content_data['updated_at']
                }

                socketio.emit('moderation_update', update_data, room=room)

        except Exception as e:
            try:
                app.logger.error(
                    f"[ws] Emit failed for room {room}: {str(e)}", exc_info=True)
            except Exception:
                logger.error(f"[ws] Emit failed for room {room}: {str(e)}")

    def send_content_created(self, content):
        """Emit a 'content_received' event so the UI can show the row in a
        pending state immediately when the API accepts a submission, before
        the (potentially slow) moderation pass completes.
        """
        room = f'project_{content.project_id}'
        try:
            content_data = {
                'content_id': content.id,
                'project_id': content.project_id,
                'status': 'pending',
                'content_type': content.content_type,
                'content_preview': (content.content_data[:100] + '...')
                if len(content.content_data) > 100 else content.content_data,
                'meta_data': content.meta_data,
                'results_count': 0,
                'processing_time': 0.0,
                'moderator_type': 'pending',
                'moderator_name': 'Processing…',
                'rule_name': None,
                'timestamp': datetime.utcnow().isoformat(),
            }
            app = current_app._get_current_object()

            def _run():
                try:
                    with app.app_context():
                        from app import socketio
                        socketio.emit('content_received', content_data, room=room)
                except Exception as inner:
                    try:
                        app.logger.error(
                            f"[ws] content_received emit failed for room {room}: {str(inner)}", exc_info=True)
                    except Exception:
                        logger.error(
                            f"[ws] content_received emit failed for room {room}: {str(inner)}")

            threading.Thread(target=_run, daemon=True).start()
        except Exception as e:
            current_app.logger.error(
                f"[ws] Failed to schedule content_received emit: {str(e)}", exc_info=True)

    def send_stats_update(self, project_id, stats):
        """Send statistics update via WebSocket"""
        try:
            from app import socketio
            socketio.emit('stats_update', stats, room=f'project_{project_id}')
        except Exception as e:
            current_app.logger.error(f"Stats WebSocket error: {str(e)}")

    def send_rule_update(self, project_id, rule_data, action='updated'):
        """Send rule update notification"""
        try:
            from app import socketio
            update_data = {
                'action': action,  # 'created', 'updated', 'deleted'
                'rule': rule_data,
                'timestamp': rule_data.get('updated_at', '')
            }
            socketio.emit('rule_update', update_data,
                          room=f'project_{project_id}')
        except Exception as e:
            current_app.logger.error(f"Rule update WebSocket error: {str(e)}")
