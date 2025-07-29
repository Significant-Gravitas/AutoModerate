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
}); 