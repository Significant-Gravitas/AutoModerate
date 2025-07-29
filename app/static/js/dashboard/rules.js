// Rules page functionality
document.addEventListener('DOMContentLoaded', function() {
    // Store rule data in a hidden element to avoid HTML attribute issues
    const ruleDataElement = document.getElementById('ruleDataStore');
    const ruleDataStore = ruleDataElement ? JSON.parse(ruleDataElement.textContent) : {};

    // Handle view rule button clicks
    document.querySelectorAll('.view-rule-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const ruleId = this.getAttribute('data-rule-id');
            const ruleName = this.getAttribute('data-rule-name');
            const ruleType = this.getAttribute('data-rule-type');
            
            // Get rule data from the store
            const ruleData = ruleDataStore[ruleId] || {};
            console.log('Rule data (view):', ruleData); // Debug log
            
            const ruleAction = this.getAttribute('data-rule-action');
            const ruleDescription = this.getAttribute('data-rule-description');
            const rulePriority = this.getAttribute('data-rule-priority');
            
            // Populate modal
            document.getElementById('modalRuleName').textContent = ruleName;
            document.getElementById('modalRuleType').innerHTML = `<span class="badge bg-info">${ruleType}</span>`;
            document.getElementById('modalRuleDescription').textContent = ruleDescription || 'No description provided';
            document.getElementById('modalRuleAction').innerHTML = `<span class="badge bg-primary">${ruleAction}</span>`;
            document.getElementById('modalRulePriority').textContent = rulePriority;
            
            // Format rule configuration based on type
            let configHtml = '';
            if (ruleType === 'keyword') {
                configHtml = `
                    <strong>Keywords:</strong> ${ruleData.keywords ? ruleData.keywords.join(', ') : 'None'}<br>
                    <strong>Case Sensitive:</strong> ${ruleData.case_sensitive ? 'Yes' : 'No'}
                `;
            } else if (ruleType === 'regex') {
                configHtml = `
                    <strong>Pattern:</strong> <code>${ruleData.pattern || 'None'}</code><br>
                    <strong>Flags:</strong> ${ruleData.flags || 'None'}
                `;
            } else if (ruleType === 'ai_prompt') {
                configHtml = `
                    <strong>Custom Prompt:</strong><br>
                    <pre class="mt-2">${ruleData.prompt || 'None'}</pre>
                `;
            }
            
            document.getElementById('modalRuleConfig').innerHTML = configHtml;
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('ruleDetailsModal'));
            modal.show();
        });
    });

    // Handle edit rule button clicks
    document.querySelectorAll('.edit-rule-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const ruleId = this.getAttribute('data-rule-id');
            const ruleName = this.getAttribute('data-rule-name');
            const ruleType = this.getAttribute('data-rule-type');
            
            // Get rule data from the store
            const ruleData = ruleDataStore[ruleId] || {};
            
            const ruleAction = this.getAttribute('data-rule-action');
            const ruleDescription = this.getAttribute('data-rule-description');
            const rulePriority = this.getAttribute('data-rule-priority');
            
            // Populate edit form
            document.getElementById('editRuleId').value = ruleId;
            document.getElementById('editRuleName').value = ruleName;
            document.getElementById('editRuleDescription').value = ruleDescription;
            document.getElementById('editRuleAction').value = ruleAction;
            document.getElementById('editRulePriority').value = rulePriority;
            document.getElementById('editRuleType').value = ruleType;
            document.getElementById('editRuleTypeDisplay').value = ruleType.charAt(0).toUpperCase() + ruleType.slice(1);
            
            // Populate rule-specific configuration
            let configHtml = '';
            if (ruleType === 'keyword') {
                configHtml = `
                    <div class="card bg-light">
                        <div class="card-header">
                            <h6 class="mb-0">Keyword Configuration</h6>
                        </div>
                        <div class="card-body">
                            <div class="mb-3">
                                <label for="editKeywords" class="form-label">Keywords *</label>
                                <textarea class="form-control" id="editKeywords" name="keywords" rows="3" placeholder="Enter keywords, one per line or comma-separated">${ruleData.keywords ? (Array.isArray(ruleData.keywords) ? ruleData.keywords.join('\n') : ruleData.keywords) : ''}</textarea>
                                <div class="form-text">Enter keywords to match. One per line or comma-separated.</div>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="editCaseSensitive" name="case_sensitive" ${ruleData.case_sensitive ? 'checked' : ''}>
                                <label class="form-check-label" for="editCaseSensitive">
                                    Case sensitive matching
                                </label>
                            </div>
                        </div>
                    </div>
                `;
            } else if (ruleType === 'regex') {
                configHtml = `
                    <div class="card bg-light">
                        <div class="card-header">
                            <h6 class="mb-0">Regex Configuration</h6>
                        </div>
                        <div class="card-body">
                            <div class="mb-3">
                                <label for="editRegexPattern" class="form-label">Pattern *</label>
                                <input type="text" class="form-control" id="editRegexPattern" name="pattern" value="${ruleData.pattern || ''}" placeholder="Enter regex pattern">
                                <div class="form-text">Enter a valid regular expression pattern.</div>
                            </div>
                        </div>
                    </div>
                `;
            } else if (ruleType === 'ai_prompt') {
                configHtml = `
                    <div class="card bg-light">
                        <div class="card-header">
                            <h6 class="mb-0">AI Prompt Configuration</h6>
                        </div>
                        <div class="card-body">
                            <div class="mb-3">
                                <label for="editAiPrompt" class="form-label">Custom Prompt *</label>
                                <textarea class="form-control" id="editAiPrompt" name="prompt" rows="4" placeholder="Enter your custom prompt for AI analysis...">${ruleData.prompt || ''}</textarea>
                                <div class="form-text">Describe what you want the AI to analyze and how it should respond.</div>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            document.getElementById('editRuleConfig').innerHTML = configHtml;
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('editRuleModal'));
            modal.show();
        });
    });

    // Handle edit from view button
    const editFromViewBtn = document.getElementById('editFromViewBtn');
    if (editFromViewBtn) {
        editFromViewBtn.addEventListener('click', function() {
            // Close view modal and open edit modal
            bootstrap.Modal.getInstance(document.getElementById('ruleDetailsModal')).hide();
            // Find the edit button for this rule and click it
            const ruleId = document.querySelector('.view-rule-btn').getAttribute('data-rule-id');
            const editBtn = document.querySelector(`[data-rule-id="${ruleId}"].edit-rule-btn`);
            if (editBtn) {
                editBtn.click();
            }
        });
    }

    // Handle toggle rule (activate/deactivate) button clicks
    document.querySelectorAll('.toggle-rule-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const ruleId = this.getAttribute('data-rule-id');
            const action = this.getAttribute('data-action');
            const projectId = window.projectId || document.querySelector('[data-project-id]')?.getAttribute('data-project-id');
            
            if (!projectId) {
                console.error('Project ID not found');
                return;
            }
            
            fetch(`/dashboard/projects/${projectId}/rules/${ruleId}/toggle`, {
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
                alert('Error updating rule status');
            });
        });
    });

    // Handle delete rule button clicks
    document.querySelectorAll('.delete-rule-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const ruleId = this.getAttribute('data-rule-id');
            const ruleName = this.getAttribute('data-rule-name');
            
            document.getElementById('deleteRuleName').textContent = ruleName;
            document.getElementById('confirmDeleteBtn').setAttribute('data-rule-id', ruleId);
            
            const modal = new bootstrap.Modal(document.getElementById('deleteRuleModal'));
            modal.show();
        });
    });

    // Handle confirm delete
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', function() {
            const ruleId = this.getAttribute('data-rule-id');
            const projectId = window.projectId || document.querySelector('[data-project-id]')?.getAttribute('data-project-id');
            
            if (!projectId) {
                console.error('Project ID not found');
                return;
            }
            
            fetch(`/dashboard/projects/${projectId}/rules/${ruleId}/delete`, {
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
                alert('Error deleting rule');
            });
        });
    }

    // Handle edit rule form submission
    const editRuleForm = document.getElementById('editRuleForm');
    if (editRuleForm) {
        editRuleForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const ruleId = formData.get('rule_id');
            const projectId = window.projectId || document.querySelector('[data-project-id]')?.getAttribute('data-project-id');
            
            if (!projectId) {
                console.error('Project ID not found');
                return;
            }
            
            // Build rule data based on type
            const ruleType = formData.get('rule_type');
            let ruleData = {};
            
            if (ruleType === 'keyword') {
                const keywords = formData.get('keywords').split(/[,\n]/).map(k => k.trim()).filter(k => k);
                ruleData = {
                    keywords: keywords,
                    case_sensitive: formData.get('case_sensitive') === 'on'
                };
            } else if (ruleType === 'regex') {
                ruleData = {
                    pattern: formData.get('pattern'),
                    flags: 0
                };
            } else if (ruleType === 'ai_prompt') {
                ruleData = {
                    prompt: formData.get('prompt')
                };
            }
            
            const updateData = {
                name: formData.get('name'),
                description: formData.get('description'),
                action: formData.get('action'),
                priority: parseInt(formData.get('priority')),
                rule_data: ruleData
            };
            
            fetch(`/dashboard/projects/${projectId}/rules/${ruleId}/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updateData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload(); // Refresh to show updated rule
                } else {
                    alert('Error: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error updating rule');
            });
        });
    }
});
