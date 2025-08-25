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

// Apply saved theme immediately (before DOM loads)
(function() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-bs-theme', savedTheme);
})();

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
