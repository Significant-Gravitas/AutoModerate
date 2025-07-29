# WebSocket Real-time Updates

AutoModerate provides real-time updates through WebSocket connections, allowing you to receive instant notifications about moderation results, statistics updates, and system events.

## Connection

### Endpoint

```
ws://localhost:6217/socket.io/
```

AutoModerate uses Socket.IO for WebSocket communication, which provides fallback options and automatic reconnection.

### JavaScript Client

```html
<script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
<script>
const socket = io('http://localhost:6217');

socket.on('connect', function() {
    console.log('Connected to AutoModerate');
});

socket.on('disconnect', function() {
    console.log('Disconnected from AutoModerate');
});
</script>
```

### Python Client

```python
import socketio

sio = socketio.Client()

@sio.event
def connect():
    print('Connected to AutoModerate')

@sio.event
def disconnect():
    print('Disconnected from AutoModerate')

sio.connect('http://localhost:6217')
```

## Authentication

WebSocket connections are automatically authenticated based on your session or API key.

### Session-based (Web Dashboard)

If you're authenticated in the web dashboard, the WebSocket connection will automatically use your session.

### API Key Authentication

For programmatic access, include your API key in the connection query:

```javascript
const socket = io('http://localhost:6217', {
    query: {
        api_key: 'your-api-key-here'
    }
});
```

## Project Rooms

AutoModerate uses "rooms" to organize real-time updates by project. Join a project room to receive updates only for that specific project.

### Join Project Room

```javascript
socket.emit('join_project', {
    project_id: 'your-project-id'
});

socket.on('joined_project', function(data) {
    console.log(`Joined project: ${data.project_id}`);
});
```

### Leave Project Room

```javascript
socket.emit('leave_project', {
    project_id: 'your-project-id'
});
```

## Event Types

### 1. Moderation Updates

Receive real-time notifications when content moderation is completed.

#### Event: `moderation_update`

```javascript
socket.on('moderation_update', function(data) {
    console.log('Content moderated:', data);
    
    // Update your UI
    updateContentStatus(data.content_id, data.status);
});
```

#### Event Data

```json
{
  "content_id": "123e4567-e89b-12d3-a456-426614174000",
  "project_id": "proj_abc123",
  "status": "approved",
  "content_type": "text",
  "content_preview": "This is some content to moderate...",
  "meta_data": {
    "user_id": "user_12345",
    "source": "comments"
  },
  "results_count": 1,
  "processing_time": 1.23,
  "moderator_type": "rule",
  "moderator_name": "AI Rule",
  "rule_name": "Spam Detection",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Usage Example

```javascript
socket.on('moderation_update', function(data) {
    const statusElement = document.getElementById(`content-${data.content_id}`);
    
    if (statusElement) {
        statusElement.className = `status ${data.status}`;
        statusElement.textContent = data.status.toUpperCase();
        
        // Show additional info
        if (data.rule_name) {
            statusElement.title = `Matched rule: ${data.rule_name}`;
        }
    }
    
    // Update statistics
    updateProjectStats({
        total: getCurrentTotal() + 1,
        [data.status]: getCurrentCount(data.status) + 1
    });
});
```

### 2. Statistics Updates

Get real-time updates to project statistics as new content is moderated.

#### Event: `stats_update`

```javascript
socket.on('stats_update', function(data) {
    console.log('Statistics updated:', data);
    updateDashboard(data);
});
```

#### Event Data

```json
{
  "total_content": 15421,
  "approved": 12937,
  "rejected": 2180,
  "flagged": 304,
  "approval_rate": 83.9,
  "rejection_rate": 14.1,
  "flag_rate": 2.0,
  "recent_activity": [
    {
      "content_id": "content_123",
      "decision": "approved",
      "timestamp": "2024-01-15T16:45:30Z"
    }
  ]
}
```

### 3. Rule Updates

Receive notifications when moderation rules are created, updated, or deleted.

#### Event: `rule_update`

```javascript
socket.on('rule_update', function(data) {
    console.log('Rule updated:', data);
    
    if (data.action === 'created') {
        addRuleToUI(data.rule);
    } else if (data.action === 'updated') {
        updateRuleInUI(data.rule);
    } else if (data.action === 'deleted') {
        removeRuleFromUI(data.rule.id);
    }
});
```

#### Event Data

```json
{
  "action": "updated",
  "rule": {
    "id": "rule_123",
    "name": "Spam Detection",
    "type": "ai_prompt",
    "is_active": true,
    "priority": 5,
    "action": "reject"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 4. System Notifications

Receive important system notifications and alerts.

#### Event: `system_notification`

```javascript
socket.on('system_notification', function(data) {
    console.log('System notification:', data);
    showNotification(data.message, data.type);
});
```

#### Event Data

```json
{
  "type": "warning",
  "message": "High volume of content detected. Processing may be delayed.",
  "timestamp": "2024-01-15T10:30:00Z",
  "persistent": false
}
```

#### Notification Types

- `info`: General information
- `warning`: Warning messages
- `error`: Error notifications
- `success`: Success confirmations

### 5. User Activity

Track user-specific activity and violations (requires user tracking).

#### Event: `user_activity`

```javascript
socket.on('user_activity', function(data) {
    console.log('User activity:', data);
    updateUserProfile(data.user_id, data.activity);
});
```

#### Event Data

```json
{
  "user_id": "user_12345",
  "activity": {
    "total_submissions": 89,
    "recent_violations": 3,
    "approval_rate": 75.3,
    "risk_score": 3.2
  },
  "triggered_by": "content_456",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Complete Implementation Example

### Frontend Dashboard

```html
<!DOCTYPE html>
<html>
<head>
    <title>AutoModerate Dashboard</title>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
</head>
<body>
    <div id="dashboard">
        <div id="stats">
            <div>Total: <span id="total-content">0</span></div>
            <div>Approved: <span id="approved-content">0</span></div>
            <div>Rejected: <span id="rejected-content">0</span></div>
            <div>Flagged: <span id="flagged-content">0</span></div>
        </div>
        
        <div id="recent-activity"></div>
        <div id="notifications"></div>
    </div>

    <script>
        const socket = io('http://localhost:6217');
        const projectId = 'your-project-id';

        // Connect and join project room
        socket.on('connect', function() {
            console.log('Connected to AutoModerate');
            socket.emit('join_project', {project_id: projectId});
        });

        // Handle moderation updates
        socket.on('moderation_update', function(data) {
            addToRecentActivity(data);
            updateStatistics();
        });

        // Handle statistics updates
        socket.on('stats_update', function(data) {
            document.getElementById('total-content').textContent = data.total_content;
            document.getElementById('approved-content').textContent = data.approved;
            document.getElementById('rejected-content').textContent = data.rejected;
            document.getElementById('flagged-content').textContent = data.flagged;
        });

        // Handle system notifications
        socket.on('system_notification', function(data) {
            showNotification(data.message, data.type);
        });

        function addToRecentActivity(data) {
            const activity = document.getElementById('recent-activity');
            const item = document.createElement('div');
            item.className = `activity-item ${data.status}`;
            item.innerHTML = `
                <span class="time">${new Date(data.timestamp).toLocaleTimeString()}</span>
                <span class="content">${data.content_preview}</span>
                <span class="status">${data.status}</span>
                ${data.rule_name ? `<span class="rule">${data.rule_name}</span>` : ''}
            `;
            activity.insertBefore(item, activity.firstChild);
            
            // Keep only last 10 items
            while (activity.children.length > 10) {
                activity.removeChild(activity.lastChild);
            }
        }

        function showNotification(message, type) {
            const notifications = document.getElementById('notifications');
            const notification = document.createElement('div');
            notification.className = `notification ${type}`;
            notification.textContent = message;
            notifications.appendChild(notification);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                notifications.removeChild(notification);
            }, 5000);
        }
    </script>
</body>
</html>
```

### Backend Integration

```python
from flask_socketio import emit, join_room, leave_room
from flask import request
from app import socketio

@socketio.on('join_project')
def handle_join_project(data):
    project_id = data['project_id']
    
    # Verify user has access to this project
    if verify_project_access(request.sid, project_id):
        join_room(f'project_{project_id}')
        emit('joined_project', {'project_id': project_id})
    else:
        emit('error', {'message': 'Access denied to project'})

@socketio.on('leave_project')
def handle_leave_project(data):
    project_id = data['project_id']
    leave_room(f'project_{project_id}')
    emit('left_project', {'project_id': project_id})

# Send updates from your moderation service
def send_moderation_update(project_id, content_data):
    socketio.emit('moderation_update', content_data, 
                  room=f'project_{project_id}')

def send_stats_update(project_id, stats_data):
    socketio.emit('stats_update', stats_data, 
                  room=f'project_{project_id}')
```

## Error Handling

### Connection Errors

```javascript
socket.on('connect_error', function(error) {
    console.error('Connection failed:', error);
    showErrorMessage('Failed to connect to AutoModerate');
});

socket.on('disconnect', function(reason) {
    console.log('Disconnected:', reason);
    if (reason === 'io server disconnect') {
        // Server disconnected, reconnect manually
        socket.connect();
    }
});
```

### Event Error Handling

```javascript
socket.on('error', function(error) {
    console.error('Socket error:', error);
    showErrorMessage(error.message || 'An error occurred');
});

// Handle specific errors
socket.on('authentication_failed', function(data) {
    console.error('Authentication failed:', data.message);
    redirectToLogin();
});

socket.on('project_access_denied', function(data) {
    console.error('Project access denied:', data.message);
    showErrorMessage('You do not have access to this project');
});
```

## Performance Considerations

### Connection Management

```javascript
// Reconnection configuration
const socket = io('http://localhost:6217', {
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 5,
    maxReconnectionAttempts: 5,
    timeout: 20000
});

// Heartbeat to keep connection alive
setInterval(() => {
    if (socket.connected) {
        socket.emit('heartbeat');
    }
}, 30000);
```

### Event Throttling

```javascript
// Throttle frequent updates
let statsUpdateTimeout;
socket.on('stats_update', function(data) {
    clearTimeout(statsUpdateTimeout);
    statsUpdateTimeout = setTimeout(() => {
        updateDashboard(data);
    }, 100); // Update at most every 100ms
});
```

## Security Considerations

### Input Validation

```javascript
socket.on('moderation_update', function(data) {
    // Validate data structure
    if (!data.content_id || !data.status) {
        console.error('Invalid moderation update data');
        return;
    }
    
    // Sanitize content preview
    const sanitizedPreview = sanitizeHTML(data.content_preview);
    updateUI(data.content_id, sanitizedPreview, data.status);
});
```

### Rate Limiting

WebSocket events are rate-limited to prevent abuse:
- **Connection limit**: 10 connections per IP
- **Event limit**: 100 events per minute per connection
- **Room limit**: 50 rooms per connection

## Next Steps

- [Moderation API](moderation.md) - Submit content for moderation
- [Statistics API](statistics.md) - Get detailed analytics
- [Project Management](projects.md) - Configure rules and settings