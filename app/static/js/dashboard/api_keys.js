// API Keys Management JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Handle toggle key (activate/deactivate) button clicks
    document.querySelectorAll('.toggle-key-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const keyId = this.getAttribute('data-key-id');
            const action = this.getAttribute('data-action');
            const projectId = this.closest('[data-project-id]')?.getAttribute('data-project-id') ||
                             document.querySelector('[data-project-id]')?.getAttribute('data-project-id');

            const csrfToken = document.querySelector('input[name="csrf_token"]').value;
            fetch(`/dashboard/projects/${projectId}/api-keys/${keyId}/toggle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
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
                const csrfToken = document.querySelector('input[name="csrf_token"]').value;
                fetch(`/dashboard/projects/${projectId}/api-keys/${keyId}/delete`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
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
