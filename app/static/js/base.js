// WebSocket connection for authenticated users
function initializeWebSocket() {
    if (typeof io === 'undefined') {
        console.warn('Socket.IO not loaded');
        return;
    }

    // Don't create a new connection if one already exists
    if (window.socket && window.socket.connected) {
        console.log('WebSocket already connected');
        return window.socket;
    }

    const socket = io();
    
    socket.on('connect', function() {
        console.log('Global WebSocket connected');
        const statusDiv = document.getElementById('connection-status');
        if (statusDiv) {
            statusDiv.innerHTML = '<span class="badge bg-success" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;"><i class="fas fa-circle"></i> <span class="connection-text">Live</span></span>';
        }
    });
    
    socket.on('disconnect', function() {
        console.log('Global WebSocket disconnected');
        const statusDiv = document.getElementById('connection-status');
        if (statusDiv) {
            statusDiv.innerHTML = '<span class="badge bg-danger" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;"><i class="fas fa-circle"></i> <span class="connection-text">Disconnected</span></span>';
        }
    });
    
    socket.on('connect_error', function(error) {
        console.error('WebSocket connection error:', error);
        const statusDiv = document.getElementById('connection-status');
        if (statusDiv) {
            statusDiv.innerHTML = '<span class="badge bg-warning" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;"><i class="fas fa-circle"></i> <span class="connection-text">Error</span></span>';
        }
    });
    
    socket.on('moderation_update', function(data) {
        // Handle real-time moderation updates
        console.log('Global moderation update:', data);
        // Page-specific handlers will handle the actual updates
    });

    // Make socket available globally for other scripts
    window.socket = socket;
    return socket;
}

// Initialize WebSocket when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if user is authenticated (presence of connection status element)
    if (document.getElementById('connection-status')) {
        // Small delay to allow page-specific scripts to load first
        setTimeout(function() {
            if (!window.socket || !window.socket.connected) {
                initializeWebSocket();
            }
        }, 100);
    }
});
