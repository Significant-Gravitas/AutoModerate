// Content Management JavaScript

// WebSocket connection and real-time updates
let socket;
let projectId;
let currentStatusFilter;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize variables from the page
    projectId = document.querySelector('[data-project-id]')?.getAttribute('data-project-id');
    currentStatusFilter = document.querySelector('[data-status-filter]')?.getAttribute('data-status-filter') || '';
    
    // Check if projectId is available
    if (!projectId) {
        console.error('Project ID not found on page');
        return;
    }
    
    
    // Initialize WebSocket connection
    initializeWebSocket();
    
    // Handle view content button clicks
    document.querySelectorAll('.view-content-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const contentId = this.getAttribute('data-content-id');
            fetchContentDetails(contentId);
        });
    });
    
    // Handle copy ID button clicks
    document.querySelectorAll('.copy-id-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const contentId = this.getAttribute('data-content-id');
            copyToClipboard(contentId, this);
        });
    });
    
    // Handle copy modal ID button clicks
    document.addEventListener('click', function(e) {
        if (e.target.closest('.copy-modal-id-btn')) {
            const modalContentId = document.getElementById('modalContentId');
            if (modalContentId && modalContentId.value) {
                copyToClipboard(modalContentId.value, e.target.closest('.copy-modal-id-btn'));
            }
        }
    });
    
    // Calculate and display average processing time
    calculateAverageProcessingTime();
});

// Initialize WebSocket connection
function initializeWebSocket() {
    // Use the global socket if available, otherwise create a new one
    if (window.socket && window.socket.connected) {
        socket = window.socket;
        // Join the project room immediately
        socket.emit('join_project', { project_id: projectId });
    } else {
        socket = io();
        window.socket = socket; // Make it available globally
        
        socket.on('connect', function() {
            // Update global connection status
            const statusDiv = document.getElementById('connection-status');
            if (statusDiv) {
                statusDiv.innerHTML = '<span class="badge bg-success" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;"><i class="fas fa-circle"></i> <span class="connection-text">Live</span></span>';
            }
            
            // Join the project room
            socket.emit('join_project', { project_id: projectId });
        });
    }
    
    socket.on('joined_project', function(data) {
        // Project room joined successfully
    });
    
    socket.on('moderation_update', function(data) {
        handleModerationUpdate(data);
    });
    
    socket.on('disconnect', function() {
        const realtimeStatus = document.getElementById('realtimeStatus');
        if (realtimeStatus) {
            realtimeStatus.style.display = 'none';
        }
    });
    
    socket.on('error', function(data) {
        console.error('WebSocket error:', data);
        console.error('Error details:', JSON.stringify(data, null, 2));
        
        // Show user-friendly error message
        if (data && data.message) {
            console.error('WebSocket error message:', data.message);
            
            // If it's a project access error, show a specific message
            if (data.message.includes('Project not found') || data.message.includes('access denied')) {
                console.error('Project access denied - user may not own this project');
            }
        }
    });
    
    socket.on('connect_error', function(error) {
        console.error('WebSocket connection error:', error);
    });
    
    socket.on('reconnect_error', function(error) {
        console.error('WebSocket reconnection error:', error);
    });
}

// Handle real-time moderation updates
function handleModerationUpdate(data) {
    // Check if we should show this content based on current filters
    // Only filter if currentStatusFilter is not empty and not "None"
    if (currentStatusFilter && currentStatusFilter !== 'None' && data.status !== currentStatusFilter) {
        // Content doesn't match current filter, just update stats
        updateStatistics(data);
        return;
    }
    
    // Add new content row to the table
    addContentRow(data);
    
    // Update statistics
    updateStatistics(data);
    
    // Show notification
    // showNotification(`New ${data.content_type} content ${data.status}`, 'info');
}

// Add new content row to the table
function addContentRow(data) {
    const tbody = document.getElementById('contentTableBody');
    
    if (!tbody) {
        return;
    }
    
    const newRow = document.createElement('tr');
    newRow.setAttribute('data-content-id', data.content_id);
    newRow.classList.add('table-info'); // Highlight new content
    
    // Remove highlight after 5 seconds
    setTimeout(() => {
        newRow.classList.remove('table-info');
    }, 5000);
    
    // Create status badge
    let statusBadge = '';
    if (data.status === 'approved') {
        statusBadge = '<span class="badge bg-success">Approved</span>';
    } else if (data.status === 'rejected') {
        statusBadge = '<span class="badge bg-danger">Rejected</span>';
    } else if (data.status === 'flagged') {
        statusBadge = '<span class="badge bg-warning">Flagged</span>';
    } else {
        statusBadge = '<span class="badge bg-secondary">Pending</span>';
    }
    
    // Create content type badge
    const contentTypeBadge = `<span class="badge bg-info">${data.content_type.charAt(0).toUpperCase() + data.content_type.slice(1)}</span>`;
    
    // Create moderation results badges
    let resultsHtml = '';
    if (data.results_count > 0) {
        // Use the moderator information from the WebSocket update
        let badgeClass = 'bg-secondary';
        let moderatorText = 'Unknown';
        
        if (data.moderator_type === 'rule') {
            badgeClass = 'bg-info';
            moderatorText = 'Rule';
        } else if (data.moderator_type === 'rule_system') {
            badgeClass = 'bg-success';
            moderatorText = 'Rule System';
        } else if (data.moderator_type === 'ai') {
            badgeClass = 'bg-primary';
            moderatorText = 'AI';
        } else if (data.moderator_name) {
            moderatorText = data.moderator_name;
        }
        
        let title = moderatorText;
        if (data.rule_name) {
            title += `: ${data.rule_name}`;
        }
        
        resultsHtml = `<span class="badge ${badgeClass}" title="${title}">${moderatorText}</span>`;
        if (data.results_count > 1) {
            resultsHtml += `<span class="badge bg-light text-dark">+${data.results_count - 1}</span>`;
        }
    } else {
        resultsHtml = '<span class="text-muted">No results</span>';
    }
    
    // Format timestamp to match server format (YYYY-MM-DD HH:MM)
    const date = new Date(data.timestamp);
    const timestamp = date.getFullYear() + '-' + 
                     String(date.getMonth() + 1).padStart(2, '0') + '-' + 
                     String(date.getDate()).padStart(2, '0') + ' ' + 
                     String(date.getHours()).padStart(2, '0') + ':' + 
                     String(date.getMinutes()).padStart(2, '0');
    
    // Check if content has metadata (we'll need to fetch this)
    let metadataHtml = '';
    if (data.meta_data && Object.keys(data.meta_data).length > 0) {
        metadataHtml = `
            <small class="text-muted d-block" style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                <i class="fas fa-info-circle"></i> Has metadata
            </small>
        `;
    }
    
    // Format processing time
    let processingTimeHtml = '<small class="text-muted">N/A</small>';
    if (data.processing_time !== null && data.processing_time !== undefined) {
        if (data.processing_time < 1) {
            processingTimeHtml = `<small class="text-success">${(data.processing_time * 1000).toFixed(0)}ms</small>`;
        } else {
            processingTimeHtml = `<small class="text-primary">${data.processing_time.toFixed(2)}s</small>`;
        }
    }
    
    newRow.innerHTML = `
        <td>
            <div class="d-flex align-items-center">
                <code class="text-muted small me-2" style="font-size: 0.75em; word-break: break-all;">${data.content_id.substring(0, 8)}...</code>
                <button class="btn btn-sm btn-outline-secondary copy-id-btn" 
                        data-content-id="${data.content_id}" 
                        title="Copy Content ID">
                    <i class="fas fa-copy"></i>
                </button>
            </div>
        </td>
        <td>${contentTypeBadge}</td>
        <td style="max-width: 300px; min-width: 200px;">
            <div class="content-preview" style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                ${data.content_preview}
            </div>
            ${metadataHtml}
        </td>
        <td>${statusBadge}</td>
        <td>${resultsHtml}</td>
        <td>${processingTimeHtml}</td>
        <td><small>${timestamp}</small></td>
        <td>
            <div class="btn-group btn-group-sm">
                <button class="btn btn-outline-primary btn-sm view-content-btn"
                        data-content-id="${data.content_id}"
                        title="View Details">
                    <i class="fas fa-eye"></i>
                </button>
            </div>
        </td>
    `;
    
    // Add event listeners to the new buttons
    const viewBtn = newRow.querySelector('.view-content-btn');
    viewBtn.addEventListener('click', function() {
        const contentId = this.getAttribute('data-content-id');
        fetchContentDetails(contentId);
    });
    
    const copyBtn = newRow.querySelector('.copy-id-btn');
    copyBtn.addEventListener('click', function() {
        const contentId = this.getAttribute('data-content-id');
        copyToClipboard(contentId, this);
    });
    
    // Insert at the top of the table
    if (tbody.firstChild) {
        tbody.insertBefore(newRow, tbody.firstChild);
    } else {
        tbody.appendChild(newRow);
    }
    
    // Limit to 25 items - remove excess rows from the bottom
    const maxItems = 25;
    const rows = tbody.querySelectorAll('tr');
    if (rows.length > maxItems) {
        // Remove excess rows from the bottom
        for (let i = maxItems; i < rows.length; i++) {
            rows[i].remove();
        }
    }
    
    // Update showing count to reflect actual displayed items
    const showingCount = document.getElementById('showingCount');
    if (showingCount) {
        const actualCount = tbody.querySelectorAll('tr').length;
        showingCount.textContent = actualCount;
    }
}

// Update statistics
function updateStatistics(data) {
    const totalElement = document.getElementById('totalContent');
    const approvedElement = document.getElementById('approvedContent');
    const rejectedElement = document.getElementById('rejectedContent');
    const flaggedElement = document.getElementById('flaggedContent');
    const totalCountElement = document.getElementById('totalCount');
    
    // Check if required elements exist
    if (!totalElement || !totalCountElement) {
        return;
    }
    
    try {
        // Update total
        const currentTotal = parseInt(totalElement.textContent) || 0;
        totalElement.textContent = currentTotal + 1;
        totalCountElement.textContent = currentTotal + 1;
        
        // Update status-specific counts
        if (data.status === 'approved' && approvedElement) {
            const currentApproved = parseInt(approvedElement.textContent) || 0;
            approvedElement.textContent = currentApproved + 1;
        } else if (data.status === 'rejected' && rejectedElement) {
            const currentRejected = parseInt(rejectedElement.textContent) || 0;
            rejectedElement.textContent = currentRejected + 1;
        } else if (data.status === 'flagged' && flaggedElement) {
            const currentFlagged = parseInt(flaggedElement.textContent) || 0;
            flaggedElement.textContent = currentFlagged + 1;
        }
    } catch (error) {
        // Silent error handling
    }
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Fetch content details for modal
function fetchContentDetails(contentId) {
    // Get modal elements
    const modalContentId = document.getElementById('modalContentId');
    const modalContentType = document.getElementById('modalContentType');
    const modalContentStatus = document.getElementById('modalContentStatus');
    const modalContentData = document.getElementById('modalContentData');
    const modalContentMetadata = document.getElementById('modalContentMetadata');
    const modalModerationResults = document.getElementById('modalModerationResults');
    const modalContentCreated = document.getElementById('modalContentCreated');
    const modalElement = document.getElementById('contentDetailsModal');
    
    // Check if all modal elements exist
    if (!modalContentId || !modalContentType || !modalContentStatus || !modalContentData || 
        !modalContentMetadata || !modalModerationResults || !modalContentCreated || !modalElement) {
        alert('Error: Modal elements not found. Please refresh the page.');
        return;
    }
    
    // Show loading state
    modalContentId.value = contentId; // Set content ID immediately
    modalContentType.innerHTML = '<span class="text-muted">Loading...</span>';
    modalContentStatus.innerHTML = '<span class="text-muted">Loading...</span>';
    modalContentData.innerHTML = '<span class="text-muted">Loading...</span>';
    modalContentMetadata.innerHTML = '<span class="text-muted">Loading...</span>';
    modalModerationResults.innerHTML = '<span class="text-muted">Loading...</span>';
    modalContentCreated.innerHTML = '<span class="text-muted">Loading...</span>';
    
    // Show modal first
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
    
    // Fetch content details via AJAX
    fetch(`/dashboard/projects/${projectId}/content/${contentId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const content = data.content;
                
                // Populate modal with fetched data
                modalContentType.innerHTML = `<span class="badge bg-info">${content.content_type}</span>`;
                
                let statusBadge = '';
                if (content.status === 'approved') {
                    statusBadge = '<span class="badge bg-success">Approved</span>';
                } else if (content.status === 'rejected') {
                    statusBadge = '<span class="badge bg-danger">Rejected</span>';
                } else if (content.status === 'flagged') {
                    statusBadge = '<span class="badge bg-warning">Flagged</span>';
                } else {
                    statusBadge = '<span class="badge bg-secondary">Pending</span>';
                }
                modalContentStatus.innerHTML = statusBadge;
                
                modalContentData.textContent = content.content_data;
                modalContentCreated.textContent = content.created_at;
                
                // Format metadata
                if (content.meta_data && Object.keys(content.meta_data).length > 0) {
                    modalContentMetadata.innerHTML = `<pre>${JSON.stringify(content.meta_data, null, 2)}</pre>`;
                } else {
                    modalContentMetadata.innerHTML = '<em class="text-muted">No metadata</em>';
                }
                
                // Format moderation results
                let resultsHtml = '';
                if (content.moderation_results && content.moderation_results.length > 0) {
                    content.moderation_results.forEach(function(result) {
                        let badgeClass = 'bg-secondary';
                        if (result.moderator_type === 'ai') badgeClass = 'bg-primary';
                        else if (result.moderator_type === 'rule') badgeClass = 'bg-info';
                        
                        // Format processing time
                        let processingTimeText = 'N/A';
                        if (result.processing_time !== null && result.processing_time !== undefined) {
                            if (result.processing_time < 1) {
                                processingTimeText = (result.processing_time * 1000).toFixed(0) + 'ms';
                            } else {
                                processingTimeText = result.processing_time.toFixed(2) + 's';
                            }
                        }
                        
                        resultsHtml += `
                            <div class="border rounded p-3 mb-2">
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <span class="badge ${badgeClass}">${result.moderator_type.toUpperCase()}</span>
                                    <span class="badge bg-${result.decision === 'approved' ? 'success' : result.decision === 'rejected' ? 'danger' : 'warning'}">${result.decision}</span>
                                </div>
                                <p class="mb-1"><strong>Reason:</strong> ${result.reason || 'No reason provided'}</p>
                                <p class="mb-1"><strong>Confidence:</strong> ${result.confidence ? (result.confidence * 100).toFixed(1) + '%' : 'N/A'}</p>
                                <p class="mb-0"><strong>Processing Time:</strong> ${processingTimeText}</p>
                            </div>
                        `;
                    });
                } else {
                    resultsHtml = '<em class="text-muted">No moderation results</em>';
                }
                modalModerationResults.innerHTML = resultsHtml;
            } else {
                // Handle error
                modalContentType.innerHTML = '<span class="text-danger">Error loading content</span>';
                modalContentStatus.innerHTML = '<span class="text-danger">Error</span>';
                modalContentData.innerHTML = '<span class="text-danger">Failed to load content details</span>';
            }
        })
        .catch(error => {
            modalContentType.innerHTML = '<span class="text-danger">Error loading content</span>';
            modalContentStatus.innerHTML = '<span class="text-danger">Error</span>';
            modalContentData.innerHTML = '<span class="text-danger">Failed to load content details</span>';
        });
}

// Calculate average processing time from visible content
function calculateAverageProcessingTime() {
    const processingTimeElements = document.querySelectorAll('td:nth-child(6) small'); // Processing time column, 6th column (after adding Content ID), small tags
    let totalTime = 0;
    let count = 0;
    
    processingTimeElements.forEach(function(element) {
        const text = element.textContent.trim();
        if (text && text !== 'N/A' && text !== '-' && text !== '') {
            // Extract numeric value from text like "4.15s" or "250ms"
            const match = text.match(/(\d+\.?\d*)(ms|s)/);
            if (match) {
                let time = parseFloat(match[1]);
                if (match[2] === 'ms') {
                    time = time / 1000; // Convert ms to seconds
                }
                totalTime += time;
                count++;
            }
        }
    });
    
    const avgElement = document.getElementById('avgProcessingTime');
    if (avgElement && count > 0) {
        const avgTime = totalTime / count;
        if (avgTime < 1) {
            avgElement.textContent = Math.round(avgTime * 1000) + 'ms';
        } else {
            avgElement.textContent = avgTime.toFixed(2) + 's';
        }
    }
}

// Copy text to clipboard with visual feedback
function copyToClipboard(text, button) {
    navigator.clipboard.writeText(text).then(function() {
        // Show success feedback
        const originalIcon = button.querySelector('i');
        const originalTitle = button.title;
        
        originalIcon.className = 'fas fa-check';
        button.title = 'Copied!';
        button.classList.remove('btn-outline-secondary');
        button.classList.add('btn-success');
        
        setTimeout(function() {
            originalIcon.className = 'fas fa-copy';
            button.title = originalTitle;
            button.classList.remove('btn-success');
            button.classList.add('btn-outline-secondary');
        }, 1000);
    }).catch(function(err) {
        // Fallback for older browsers
        console.error('Could not copy text: ', err);
        alert('Content ID: ' + text);
    });
}

// Clean up WebSocket connection when page unloads
window.addEventListener('beforeunload', function() {
    if (socket) {
        socket.disconnect();
    }
});
