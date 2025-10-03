// Project Settings JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Copy project ID to clipboard
    window.copyToClipboard = function(text) {
        navigator.clipboard.writeText(text).then(function() {
            // Show a brief success message
            const button = event.target.closest('button');
            const originalHTML = button.innerHTML;
            button.innerHTML = '<i class="fas fa-check"></i>';
            button.classList.remove('btn-outline-secondary');
            button.classList.add('btn-success');

            setTimeout(function() {
                button.innerHTML = originalHTML;
                button.classList.remove('btn-success');
                button.classList.add('btn-outline-secondary');
            }, 1000);
        });
    };

    // Enable/disable delete button based on confirmation
    const confirmProjectNameInput = document.getElementById('confirmProjectName');
    if (confirmProjectNameInput) {
        confirmProjectNameInput.addEventListener('input', function() {
            const confirmBtn = document.getElementById('confirmDeleteBtn');
            const projectName = this.getAttribute('data-project-name');

            if (this.value === projectName) {
                confirmBtn.disabled = false;
                confirmBtn.classList.remove('btn-secondary');
                confirmBtn.classList.add('btn-danger');
            } else {
                confirmBtn.disabled = true;
                confirmBtn.classList.remove('btn-danger');
                confirmBtn.classList.add('btn-secondary');
            }
        });
    }

    // Test Discord webhook
    const testWebhookForm = document.getElementById('testWebhookForm');
    if (testWebhookForm) {
        testWebhookForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const resultDiv = document.getElementById('webhookTestResult');
            const btn = document.getElementById('testWebhookBtn');
            const originalHTML = btn.innerHTML;
            const formData = new FormData(this);

            // Show loading state
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';

            // Send test request
            fetch(this.action, {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Show result
                resultDiv.style.display = 'block';
                if (data.success) {
                    resultDiv.className = 'alert alert-success mt-3';
                    resultDiv.innerHTML = `<i class="fas fa-check-circle"></i> ${data.message}`;
                } else {
                    resultDiv.className = 'alert alert-danger mt-3';
                    resultDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${data.message}`;
                }

                // Hide result after 5 seconds
                setTimeout(() => {
                    resultDiv.style.display = 'none';
                }, 5000);
            })
            .catch(error => {
                resultDiv.style.display = 'block';
                resultDiv.className = 'alert alert-danger mt-3';
                resultDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> Error: ${error.message}`;

                setTimeout(() => {
                    resultDiv.style.display = 'none';
                }, 5000);
            })
            .finally(() => {
                // Restore button state
                btn.disabled = false;
                btn.innerHTML = originalHTML;
            });
        });
    }
});
