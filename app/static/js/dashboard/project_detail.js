// Project detail page functionality
document.addEventListener('DOMContentLoaded', function() {
    // Join project room for real-time updates
    if (typeof socket !== 'undefined' && window.projectId) {
        socket.emit('join_project', {project_id: window.projectId});
    }

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

    // Handle copy full key in modal
    const copyButton = document.getElementById('copyFullKeyBtn');
    if (copyButton) {
        copyButton.addEventListener('click', function() {
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
            }).catch(function(err) {
                console.error('Failed to copy: ', err);
                // Fallback for older browsers
                keyInput.select();
                document.execCommand('copy');

                const button = document.getElementById('copyFullKeyBtn');
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
    }
});
