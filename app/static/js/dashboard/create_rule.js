// Create Rule Form JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Handle rule type selection
    document.querySelectorAll('input[name="rule_type"]').forEach(function(radio) {
        radio.addEventListener('change', function() {
            // Hide all config sections
            document.querySelectorAll('.rule-config').forEach(function(config) {
                config.style.display = 'none';
            });
            
            // Remove active class from all cards
            document.querySelectorAll('.rule-type-card').forEach(function(card) {
                card.classList.remove('border-primary', 'bg-light');
            });
            
            // Show selected config section
            const selectedType = this.value;
            const configSection = document.getElementById(selectedType + '_config');
            if (configSection) {
                configSection.style.display = 'block';
            }
            
            // Highlight selected card
            const selectedCard = document.querySelector(`[data-rule-type="${selectedType}"]`);
            if (selectedCard) {
                selectedCard.classList.add('border-primary', 'bg-light');
            }
        });
    });

    // Handle card clicks
    document.querySelectorAll('.rule-type-card').forEach(function(card) {
        card.addEventListener('click', function() {
            const ruleType = this.getAttribute('data-rule-type');
            const radio = document.getElementById(ruleType + '_type');
            if (radio) {
                radio.checked = true;
                radio.dispatchEvent(new Event('change'));
            }
        });
    });

    // Form validation
    document.getElementById('ruleForm').addEventListener('submit', function(e) {
        const ruleType = document.querySelector('input[name="rule_type"]:checked');
        const action = document.querySelector('input[name="action"]:checked');
        
        if (!ruleType) {
            e.preventDefault();
            alert('Please select a rule type.');
            return;
        }
        
        if (!action) {
            e.preventDefault();
            alert('Please select an action.');
            return;
        }
        
        // Validate rule-specific fields
        if (ruleType.value === 'keyword') {
            const keywords = document.getElementById('keywords').value.trim();
            if (!keywords) {
                e.preventDefault();
                alert('Please enter at least one keyword.');
                return;
            }
        } else if (ruleType.value === 'regex') {
            const pattern = document.getElementById('regex_pattern').value.trim();
            if (!pattern) {
                e.preventDefault();
                alert('Please enter a regex pattern.');
                return;
            }
            
            // Test regex validity
            try {
                new RegExp(pattern);
            } catch (error) {
                e.preventDefault();
                alert('Invalid regex pattern: ' + error.message);
                return;
            }
        } else if (ruleType.value === 'ai_prompt') {
            const prompt = document.getElementById('ai_prompt').value.trim();
            if (!prompt) {
                e.preventDefault();
                alert('Please enter an AI prompt.');
                return;
            }
        }
    });

    // Add hover effects to rule type cards
    document.querySelectorAll('.rule-type-card').forEach(function(card) {
        card.style.cursor = 'pointer';
        card.addEventListener('mouseenter', function() {
            if (!this.classList.contains('border-primary')) {
                this.classList.add('border-secondary');
            }
        });
        card.addEventListener('mouseleave', function() {
            this.classList.remove('border-secondary');
        });
    });
}); 