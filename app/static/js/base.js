// WebSocket connection for authenticated users
let reconnectionAttempts = 0;
const MAX_RECONNECTION_DELAY = 30000; // 30 seconds max delay

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

    // Configure Socket.IO with automatic reconnection
    const socket = io({
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
        reconnectionDelayMax: MAX_RECONNECTION_DELAY,
        timeout: 20000,
        transports: ['websocket', 'polling'] // Try websocket first, fallback to polling
    });

    socket.on('connect', function() {
        console.log('Global WebSocket connected');
        reconnectionAttempts = 0; // Reset reconnection counter on successful connect
        
        const statusDiv = document.getElementById('connection-status');
        if (statusDiv) {
            statusDiv.innerHTML = '<span class="badge bg-success" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;"><i class="fas fa-circle"></i> <span class="connection-text">Live</span></span>';
        }
        
        // Trigger a custom event that page-specific scripts can listen to
        window.dispatchEvent(new CustomEvent('websocket-reconnected'));
    });

    socket.on('disconnect', function(reason) {
        console.log('Global WebSocket disconnected. Reason:', reason);
        const statusDiv = document.getElementById('connection-status');
        if (statusDiv) {
            statusDiv.innerHTML = '<span class="badge bg-danger" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;"><i class="fas fa-circle"></i> <span class="connection-text">Disconnected</span></span>';
        }
        
        // If disconnect was due to server-side (io server disconnect or io client disconnect)
        // the client will automatically attempt to reconnect
        if (reason === 'io server disconnect') {
            // Server forcefully disconnected, manually reconnect
            console.log('Server disconnected socket, attempting manual reconnect...');
            socket.connect();
        }
    });

    socket.on('reconnect_attempt', function(attemptNumber) {
        reconnectionAttempts = attemptNumber;
        console.log(`WebSocket reconnection attempt ${attemptNumber}`);
        
        const statusDiv = document.getElementById('connection-status');
        if (statusDiv) {
            statusDiv.innerHTML = '<span class="badge bg-warning" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;"><i class="fas fa-circle"></i> <span class="connection-text">Reconnecting...</span></span>';
        }
    });

    socket.on('reconnect', function(attemptNumber) {
        console.log(`WebSocket reconnected after ${attemptNumber} attempts`);
        reconnectionAttempts = 0;
        
        const statusDiv = document.getElementById('connection-status');
        if (statusDiv) {
            statusDiv.innerHTML = '<span class="badge bg-success" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;"><i class="fas fa-circle"></i> <span class="connection-text">Live</span></span>';
        }
    });

    socket.on('reconnect_error', function(error) {
        console.error('WebSocket reconnection error:', error);
        const statusDiv = document.getElementById('connection-status');
        if (statusDiv) {
            const delay = Math.min(1000 * Math.pow(2, reconnectionAttempts), MAX_RECONNECTION_DELAY);
            const delaySec = Math.round(delay / 1000);
            statusDiv.innerHTML = `<span class="badge bg-warning" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;"><i class="fas fa-circle"></i> <span class="connection-text">Retry in ${delaySec}s</span></span>`;
        }
    });

    socket.on('reconnect_failed', function() {
        console.error('WebSocket reconnection failed after all attempts');
        const statusDiv = document.getElementById('connection-status');
        if (statusDiv) {
            statusDiv.innerHTML = '<span class="badge bg-danger" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;"><i class="fas fa-circle"></i> <span class="connection-text">Failed</span></span>';
        }
    });

    socket.on('connect_error', function(error) {
        console.error('WebSocket connection error:', error);
        const statusDiv = document.getElementById('connection-status');
        if (statusDiv) {
            statusDiv.innerHTML = '<span class="badge bg-warning" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;"><i class="fas fa-circle"></i> <span class="connection-text">Error</span></span>';
        }
    });

    socket.on('error', function(error) {
        console.error('WebSocket error:', error);
        // Don't disconnect on errors, let Socket.IO handle reconnection
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

// Dark mode functionality
function initializeDarkMode() {
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    const darkModeToggleMobile = document.getElementById('dark-mode-toggle-mobile');

    // Get saved theme preference or default to 'light'
    const savedTheme = localStorage.getItem('theme') || 'light';

    // Update icons to match current theme
    if (darkModeToggle) updateToggleIcon(savedTheme);
    if (darkModeToggleMobile) updateMobileToggleIcon(savedTheme);

    // Add click event listener for desktop toggle
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            toggleTheme();
        });
    }

    // Add click event listener for mobile toggle
    if (darkModeToggleMobile) {
        darkModeToggleMobile.addEventListener('click', function() {
            toggleTheme();
        });
    }

    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        // Apply new theme
        document.documentElement.setAttribute('data-bs-theme', newTheme);

        // Save preference
        localStorage.setItem('theme', newTheme);

        // Update both icons
        if (darkModeToggle) updateToggleIcon(newTheme);
        if (darkModeToggleMobile) updateMobileToggleIcon(newTheme);
    }
}

function updateToggleIcon(theme) {
    const icon = document.querySelector('#dark-mode-toggle i');
    if (!icon) return;

    if (theme === 'dark') {
        icon.className = 'fas fa-sun';
        document.getElementById('dark-mode-toggle').title = 'Switch to light mode';
    } else {
        icon.className = 'fas fa-moon';
        document.getElementById('dark-mode-toggle').title = 'Switch to dark mode';
    }
}

function updateMobileToggleIcon(theme) {
    const icon = document.querySelector('#dark-mode-toggle-mobile i');
    if (!icon) return;

    if (theme === 'dark') {
        icon.className = 'fas fa-sun';
        document.getElementById('dark-mode-toggle-mobile').title = 'Switch to light mode';
    } else {
        icon.className = 'fas fa-moon';
        document.getElementById('dark-mode-toggle-mobile').title = 'Switch to dark mode';
    }
}

// Sidebar collapse functionality
function initializeSidebarToggle() {
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    const mobileSidebar = document.getElementById('mobile-sidebar');
    const mainContent = document.getElementById('main-content');
    const sidebarOverlay = document.getElementById('sidebar-overlay');

    if (!sidebarToggle || !mainContent) return;

    // Get saved sidebar state or default to 'expanded'
    const savedSidebarState = localStorage.getItem('sidebarState') || 'expanded';

    // Apply saved state on desktop only
    if (window.innerWidth >= 768) {
        if (savedSidebarState === 'collapsed') {
            sidebar.classList.add('sidebar-collapsed');
            mainContent.classList.add('content-expanded');
            updateSidebarToggleIcon(true);
        }
    }

    // Add click event listener
    sidebarToggle.addEventListener('click', function() {
        const isDesktop = window.innerWidth >= 768;

        if (isDesktop) {
            // Desktop behavior: hide/show sidebar
            const isCollapsed = sidebar.classList.contains('sidebar-collapsed');

            if (isCollapsed) {
                sidebar.classList.remove('sidebar-collapsed');
                mainContent.classList.remove('content-expanded');
                localStorage.setItem('sidebarState', 'expanded');
                updateSidebarToggleIcon(false);
            } else {
                sidebar.classList.add('sidebar-collapsed');
                mainContent.classList.add('content-expanded');
                localStorage.setItem('sidebarState', 'collapsed');
                updateSidebarToggleIcon(true);
            }
        } else {
            // Mobile behavior: toggle overlay sidebar
            if (mobileSidebar) {
                const isVisible = mobileSidebar.classList.contains('show');
                console.log('Mobile sidebar toggle - Current state:', isVisible ? 'visible' : 'hidden');

                if (isVisible) {
                    mobileSidebar.classList.remove('show');
                    if (sidebarOverlay) sidebarOverlay.classList.remove('show');
                    console.log('Hiding mobile sidebar');
                } else {
                    mobileSidebar.classList.add('show');
                    if (sidebarOverlay) sidebarOverlay.classList.add('show');
                    console.log('Showing mobile sidebar');
                }
            }
        }
    });

    // Close sidebar when clicking overlay (mobile)
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function() {
            if (mobileSidebar) {
                mobileSidebar.classList.remove('show');
                sidebarOverlay.classList.remove('show');
            }
        });
    }

    // Handle window resize
    window.addEventListener('resize', function() {
        const isDesktop = window.innerWidth >= 768;

        if (isDesktop) {
            // Remove mobile classes
            if (mobileSidebar) mobileSidebar.classList.remove('show');
            if (sidebarOverlay) sidebarOverlay.classList.remove('show');

            // Apply saved desktop state
            if (sidebar && localStorage.getItem('sidebarState') === 'collapsed') {
                sidebar.classList.add('sidebar-collapsed');
                mainContent.classList.add('content-expanded');
                updateSidebarToggleIcon(true);
            } else if (sidebar) {
                sidebar.classList.remove('sidebar-collapsed');
                mainContent.classList.remove('content-expanded');
                updateSidebarToggleIcon(false);
            }
        } else {
            // Mobile: remove desktop classes
            if (sidebar) {
                sidebar.classList.remove('sidebar-collapsed');
                mainContent.classList.remove('content-expanded');
            }
            updateSidebarToggleIcon(false);
        }
    });
}

function updateSidebarToggleIcon(isCollapsed) {
    const icon = document.querySelector('#sidebar-toggle i');
    if (!icon) return;

    if (isCollapsed) {
        icon.className = 'fas fa-chevron-right';
        document.getElementById('sidebar-toggle').title = 'Show sidebar';
    } else {
        icon.className = 'fas fa-chevron-left';
        document.getElementById('sidebar-toggle').title = 'Hide sidebar';
    }
}

// Initialize WebSocket when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize dark mode functionality
    initializeDarkMode();

    // Initialize sidebar toggle functionality
    initializeSidebarToggle();

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
