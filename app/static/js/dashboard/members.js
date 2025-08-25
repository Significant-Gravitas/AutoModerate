document.addEventListener('DOMContentLoaded', function() {
    // Handle role change modal
    const roleModal = document.getElementById('roleModal');
    if (roleModal) {
        roleModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const membershipId = button.getAttribute('data-membership-id');
            const currentRole = button.getAttribute('data-current-role');

            // Set the form action
            const form = document.getElementById('roleForm');
            form.action = `/dashboard/projects/${projectId}/members/${membershipId}/role`;

            // Set the current role in the select
            const roleSelect = document.getElementById('newRole');
            roleSelect.value = currentRole;
        });
    }

    // Handle remove member modal
    const removeMemberModal = document.getElementById('removeMemberModal');
    if (removeMemberModal) {
        removeMemberModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const membershipId = button.getAttribute('data-membership-id');
            const username = button.getAttribute('data-username');

            // Set the member name
            document.getElementById('memberName').textContent = username;

            // Set the form action
            const form = document.getElementById('removeMemberForm');
            form.action = `/dashboard/projects/${projectId}/members/${membershipId}/remove`;
        });
    }

    // Handle invitation form validation
    const inviteForm = document.querySelector('#inviteModal form');
    if (inviteForm) {
        inviteForm.addEventListener('submit', function(event) {
            const email = document.getElementById('email').value.trim();
            const role = document.getElementById('role').value;

            if (!email) {
                event.preventDefault();
                alert('Please enter an email address');
                return;
            }

            if (!isValidEmail(email)) {
                event.preventDefault();
                alert('Please enter a valid email address');
                return;
            }

            if (!role) {
                event.preventDefault();
                alert('Please select a role');
                return;
            }
        });
    }

    // Email validation function
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // Get project ID from URL
    const urlParts = window.location.pathname.split('/');
    const projectId = urlParts[2]; // /dashboard/projects/{projectId}/members
});

// Copy invitation link to clipboard
function copyInvitationLink(token) {
    const link = `${window.location.origin}/dashboard/invite/${token}`;
    navigator.clipboard.writeText(link).then(function() {
        // Show success message
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-success border-0 position-fixed';
        toast.style.top = '20px';
        toast.style.right = '20px';
        toast.style.zIndex = '9999';
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-check"></i> Invitation link copied to clipboard!
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        document.body.appendChild(toast);

        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();

        // Remove toast after it's hidden
        toast.addEventListener('hidden.bs.toast', function() {
            document.body.removeChild(toast);
        });
    }).catch(function(err) {
        console.error('Failed to copy: ', err);
        alert('Failed to copy invitation link');
    });
}
