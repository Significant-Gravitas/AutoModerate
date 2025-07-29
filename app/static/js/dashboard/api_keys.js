// API Keys Management JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Handle API key display clicks
    document.querySelectorAll('.api-key-display').forEach(function(element) {
        element.addEventListener('click', function() {
            const fullKey = this.getAttribute('data-full-key');
            document.getElementById('fullApiKey').value = fullKey;
            document.getElementById('exampleKey').textContent = fullKey;
            
            const modal = new bootstrap.Modal(document.getElementById('apiKeyModal'));
            modal.show();
        });
    });

    // Handle copy to clipboard
    document.querySelectorAll('.copy-key-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const key = this.getAttribute('data-key');
            navigator.clipboard.writeText(key).then(function() {
                // Show success feedback
                const icon = button.querySelector('i');
                const originalClass = icon.className;
                icon.className = 'fas fa-check';
                button.classList.add('btn-success');
                button.classList.remove('btn-outline-primary');
                
                setTimeout(function() {
                    icon.className = originalClass;
                    button.classList.remove('btn-success');
                    button.classList.add('btn-outline-primary');
                }, 2000);
            });
        });
    });

    // Handle copy full key in modal
    document.getElementById('copyFullKeyBtn').addEventListener('click', function() {
        const keyInput = document.getElementById('fullApiKey');
        keyInput.select();
        navigator.clipboard.writeText(keyInput.value).then(function() {
            const button = document.getElementById('copyFullKeyBtn');
            const icon = button.querySelector('i');
            const originalHTML = button.innerHTML;
            
            button.innerHTML = '<i class="fas fa-check"></i> Copied!';
            button.classList.add('btn-success');
            button.classList.remove('btn-outline-secondary');
            
            setTimeout(function() {
                button.innerHTML = originalHTML;
                button.classList.remove('btn-success');
                button.classList.add('btn-outline-secondary');
            }, 2000);
        });
    });

    // Handle toggle key (activate/deactivate) button clicks
    document.querySelectorAll('.toggle-key-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const keyId = this.getAttribute('data-key-id');
            const action = this.getAttribute('data-action');
            const projectId = this.closest('[data-project-id]')?.getAttribute('data-project-id') || 
                             document.querySelector('[data-project-id]')?.getAttribute('data-project-id');
            
            fetch(`/dashboard/projects/${projectId}/api-keys/${keyId}/toggle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ action: action })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload(); // Refresh to show updated status
                } else {
                    alert('Error: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error updating API key status');
            });
        });
    });

    // Handle delete key button clicks
    document.querySelectorAll('.delete-key-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const keyId = this.getAttribute('data-key-id');
            const keyName = this.getAttribute('data-key-name');
            const projectId = this.closest('[data-project-id]')?.getAttribute('data-project-id') || 
                             document.querySelector('[data-project-id]')?.getAttribute('data-project-id');
            
            if (confirm(`Are you sure you want to delete the API key "${keyName}"? This action cannot be undone.`)) {
                fetch(`/dashboard/projects/${projectId}/api-keys/${keyId}/delete`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        location.reload(); // Refresh to show updated list
                    } else {
                        alert('Error: ' + data.error);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error deleting API key');
                });
            }
        });
    });
}); 