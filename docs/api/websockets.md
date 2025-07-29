# WebSocket Real-time Updates

AutoModerate provides real-time updates through WebSocket connections using Socket.IO, allowing you to receive instant notifications about moderation results.

## Connection

### Endpoint

```
ws://localhost:6217/socket.io/
```

AutoModerate uses Socket.IO for WebSocket communication, which provides automatic fallback options and reconnection.

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

WebSocket connections require authentication. You must be logged in to the web dashboard to establish a connection.

### Session-based Authentication

The WebSocket connection automatically uses your web dashboard session. If you're not authenticated, you'll receive an error message.

## Project Rooms

AutoModerate uses "rooms" to organize real-time updates by project. You must join a project room to receive updates for that specific project.

### Join Project Room

```javascript
socket.emit('join_project', {
    project_id: 'your-project-id'
});

// Listen for successful join
socket.on('joined_project', function(data) {
    console.log(`Joined project: ${data.project_id}`);
    console.log(`Room: ${data.room}`);
});

// Handle errors
socket.on('error', function(error) {
    console.error('Error:', error.message);
});
```

### Leave Project Room

```javascript
socket.emit('leave_project', {
    project_id: 'your-project-id'
});

socket.on('left_project', function(data) {
    console.log(`Left project: ${data.project_id}`);
});
```

## Event Types

### 1. Connection Events

#### Event: `connect`

Triggered when the client connects to the server.

```javascript
socket.on('connect', function() {
    console.log('Connected to AutoModerate');
    // You can now join project rooms
});
```

#### Event: `connected`

Server confirmation of successful connection (only for authenticated users).

```javascript
socket.on('connected', function(data) {
    console.log('Server message:', data.message);
});
```

#### Event: `disconnect`

Triggered when the client disconnects from the server.

```javascript
socket.on('disconnect', function() {
    console.log('Disconnected from AutoModerate');
    // Handle reconnection logic if needed
});
```

### 2. Project Room Events

#### Event: `joined_project`

Confirmation that you've successfully joined a project room.

```javascript
socket.on('joined_project', function(data) {
    console.log('Joined project:', data.project_id);
    console.log('Room name:', data.room);
    // You'll now receive updates for this project
});
```

#### Event: `left_project`

Confirmation that you've left a project room.

```javascript
socket.on('left_project', function(data) {
    console.log('Left project:', data.project_id);
    // You'll no longer receive updates for this project
});
```

### 3. Error Events

#### Event: `error`

Error messages from the server.

```javascript
socket.on('error', function(error) {
    console.error('WebSocket error:', error.message);
    
    // Common error messages:
    // - "Authentication required"
    // - "Project ID required"
    // - "Project not found"
    // - "Access denied - you are not a member of this project"
});
```

### 4. Moderation Update Events

#### Event: `moderation_update`

**Note**: The actual moderation update events are sent from the `WebSocketNotifier` service, but the specific event structure would need to be verified by checking the service implementation.

Based on the codebase structure, moderation updates are sent to project rooms when content is processed. To receive these updates:

```javascript
// First, join a project room
socket.emit('join_project', {project_id: 'your-project-id'});

// Then listen for moderation updates
socket.on('moderation_update', function(data) {
    console.log('Content moderated:', data);
    // Update your UI based on the moderation result
});
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
        <div id="status">Status: <span id="connection-status">Connecting...</span></div>
        <div id="project-info"></div>
        <div id="notifications"></div>
    </div>

    <script>
        const socket = io('http://localhost:6217');
        const projectId = 'your-project-id'; // Replace with actual project ID

        // Connection handling
        socket.on('connect', function() {
            document.getElementById('connection-status').textContent = 'Connected';
            console.log('Connected to AutoModerate');
            
            // Join project room after connecting
            socket.emit('join_project', {project_id: projectId});
        });

        socket.on('disconnect', function() {
            document.getElementById('connection-status').textContent = 'Disconnected';
            console.log('Disconnected from AutoModerate');
        });

        // Authentication confirmation
        socket.on('connected', function(data) {
            console.log('Authenticated:', data.message);
        });

        // Project room events
        socket.on('joined_project', function(data) {
            console.log('Joined project:', data.project_id);
            document.getElementById('project-info').innerHTML = 
                `<p>Joined project: ${data.project_id}</p><p>Room: ${data.room}</p>`;
        });

        socket.on('left_project', function(data) {
            console.log('Left project:', data.project_id);
            document.getElementById('project-info').innerHTML = 
                `<p>Left project: ${data.project_id}</p>`;
        });

        // Error handling
        socket.on('error', function(error) {
            console.error('WebSocket error:', error.message);
            showNotification('Error: ' + error.message, 'error');
        });

        // Moderation updates (if implemented)
        socket.on('moderation_update', function(data) {
            console.log('Moderation update:', data);
            showNotification(`Content ${data.content_id}: ${data.status}`, 'info');
        });

        function showNotification(message, type) {
            const notifications = document.getElementById('notifications');
            const notification = document.createElement('div');
            notification.className = `notification ${type}`;
            notification.textContent = message;
            notifications.appendChild(notification);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notifications.removeChild(notification);
                }
            }, 5000);
        }

        // Handle page unload
        window.addEventListener('beforeunload', function() {
            if (projectId) {
                socket.emit('leave_project', {project_id: projectId});
            }
        });
    </script>
</body>
</html>
```

## Error Handling

### Connection Errors

```javascript
socket.on('connect_error', function(error) {
    console.error('Connection failed:', error);
    document.getElementById('connection-status').textContent = 'Connection Failed';
});

socket.on('disconnect', function(reason) {
    console.log('Disconnected:', reason);
    document.getElementById('connection-status').textContent = 'Disconnected';
    
    if (reason === 'io server disconnect') {
        // Server disconnected, attempt manual reconnection
        socket.connect();
    }
});
```

### Authentication Errors

```javascript
socket.on('error', function(error) {
    console.error('Socket error:', error);
    
    if (error.message === 'Authentication required') {
        // Redirect to login page
        window.location.href = '/auth/login';
    } else if (error.message.includes('Access denied')) {
        // User doesn't have access to the project
        showNotification('You do not have access to this project', 'error');
    }
});
```

## Access Control

### Project Membership

Only users who are members of a project can join that project's room. The server checks:

1. **Authentication**: User must be logged in
2. **Project Existence**: Project must exist in the database
3. **Membership**: User must be either:
   - The project owner, OR
   - A project member

### Error Messages

- `"Authentication required"`: User is not logged in
- `"Project ID required"`: No project_id provided in join_project event
- `"Project not found"`: Project doesn't exist
- `"Access denied - you are not a member of this project"`: User lacks permission

## Performance Considerations

### Connection Management

```javascript
// Configure reconnection
const socket = io('http://localhost:6217', {
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 5,
    timeout: 20000
});

// Track connection state
let isConnected = false;
socket.on('connect', () => isConnected = true);
socket.on('disconnect', () => isConnected = false);
```

### Room Management

```javascript
// Keep track of joined rooms
let joinedProjects = new Set();

function joinProject(projectId) {
    if (!joinedProjects.has(projectId)) {
        socket.emit('join_project', {project_id: projectId});
        joinedProjects.add(projectId);
    }
}

function leaveProject(projectId) {
    if (joinedProjects.has(projectId)) {
        socket.emit('leave_project', {project_id: projectId});
        joinedProjects.delete(projectId);
    }
}

// Clean up on disconnect
socket.on('disconnect', () => {
    joinedProjects.clear();
});
```

## Security Considerations

### Authentication

- WebSocket connections require web dashboard authentication
- No API key authentication is currently supported for WebSocket connections
- Users can only join rooms for projects they have access to

### Input Validation

```javascript
// Always validate project IDs
function joinProject(projectId) {
    if (!projectId || typeof projectId !== 'string') {
        console.error('Invalid project ID');
        return;
    }
    
    socket.emit('join_project', {project_id: projectId});
}
```

## Next Steps

- [API Documentation](moderation.md) - Submit content for moderation
- [Installation Guide](../guides/installation.md) - Set up AutoModerate
- [Architecture Guide](../guides/architecture.md) - Understand the system