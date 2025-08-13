import threading
from flask import current_app

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
                'updated_at': content.updated_at.isoformat()
            }
            
            app = current_app._get_current_object()
            threading.Thread(
                target=self._send_websocket_update,
                args=(app, content_data, decision, results, total_time),
                daemon=True
            ).start()
        except Exception as e:
            current_app.logger.error(f"Failed to start WebSocket thread: {str(e)}")
    
    def _send_websocket_update(self, app, content_data, decision, results, total_time):
        """Send WebSocket update with proper Flask context"""
        try:
            with app.app_context():
                from app import socketio
                
                # Get moderator info from first result
                moderator_type = 'unknown'
                moderator_name = 'Unknown'
                rule_name = None
                
                if results:
                    first_result = results[0]
                    moderator_type = first_result.get('moderator_type', 'unknown')
                    if moderator_type == 'rule':
                        moderator_name = 'Rule'
                        rule_name = first_result.get('rule_name', 'Unknown Rule')
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
                
                socketio.emit('moderation_update', update_data, room=f'project_{content_data["project_id"]}')
                # WebSocket update sent
                
        except Exception as e:
            try:
                app.logger.error(f"WebSocket error: {str(e)}")
            except:
                print(f"WebSocket error: {str(e)}")
    
    def send_stats_update(self, project_id, stats):
        """Send statistics update via WebSocket"""
        try:
            from app import socketio
            socketio.emit('stats_update', stats, room=f'project_{project_id}')
            # Stats update sent
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
            socketio.emit('rule_update', update_data, room=f'project_{project_id}')
            # Rule notification sent
        except Exception as e:
            current_app.logger.error(f"Rule update WebSocket error: {str(e)}")