// API Documentation page functionality
document.addEventListener('DOMContentLoaded', function() {
    // Smooth scrolling for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Highlight current section in navigation
    function updateActiveNavigation() {
        const sections = document.querySelectorAll('[id]');
        const navLinks = document.querySelectorAll('.nav-link[href^="#"]');

        let current = '';
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            if (window.pageYOffset >= sectionTop - 200) {
                current = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === '#' + current) {
                link.classList.add('active');
            }
        });
    }

    // Update navigation on scroll
    window.addEventListener('scroll', updateActiveNavigation);

    // Initial navigation update
    updateActiveNavigation();

    // Apply theme-appropriate code block styling
    updateCodeBlockTheme();

    // Add copy buttons to code blocks
    addCopyButtonsToCodeBlocks();

    // Initialize language switcher
    initializeLanguageSwitcher();

    // Watch for theme changes
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'data-bs-theme') {
                updateCodeBlockTheme();
            }
        });
    });

    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-bs-theme']
    });
});

// Update code block theme based on current mode
function updateCodeBlockTheme() {
    const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    const codeBlocks = document.querySelectorAll('pre.code-block');

    console.log('Updating code block theme. Dark mode:', isDark, 'Found blocks:', codeBlocks.length);

    codeBlocks.forEach(block => {
        // Remove existing theme classes
        block.classList.remove('code-block-light', 'code-block-dark');

        // Apply appropriate theme class
        if (isDark) {
            block.classList.add('code-block-dark');
        } else {
            block.classList.add('code-block-light');
        }

        console.log('Applied class to block:', isDark ? 'code-block-dark' : 'code-block-light');
    });
}

// Add copy buttons to all code blocks
function addCopyButtonsToCodeBlocks() {
    const codeContainers = document.querySelectorAll('.code-container');

    codeContainers.forEach(container => {
        const pre = container.querySelector('pre');
        if (!pre || pre.querySelector('.copy-btn')) return; // Skip if button already exists

        // Create copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-btn';
        copyBtn.textContent = 'Copy';
        copyBtn.onclick = function() { copyCode(this); };

        // Add button to container
        container.appendChild(copyBtn);
    });
}

// Copy code functionality
function copyCode(button) {
    const container = button.parentElement;
    const pre = container.querySelector('pre');
    const code = pre.querySelector('code');
    const text = code.textContent;

    navigator.clipboard.writeText(text).then(function() {
        // Success feedback
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.classList.add('copied');

        setTimeout(function() {
            button.textContent = originalText;
            button.classList.remove('copied');
        }, 2000);
    }).catch(function(err) {
        console.error('Failed to copy: ', err);
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);

        // Success feedback
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.classList.add('copied');

        setTimeout(function() {
            button.textContent = originalText;
            button.classList.remove('copied');
        }, 2000);
    });
}

// Initialize language switcher functionality
function initializeLanguageSwitcher() {
    const languageButtons = document.querySelectorAll('[data-lang]');
    const codeExamples = document.querySelectorAll('.code-example[data-lang]');

    languageButtons.forEach(button => {
        button.addEventListener('click', function() {
            const selectedLang = this.getAttribute('data-lang');

            // Update button states
            languageButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');

            // Show/hide appropriate code examples
            codeExamples.forEach(example => {
                const exampleLang = example.getAttribute('data-lang');
                if (exampleLang === selectedLang) {
                    example.style.display = 'block';
                } else {
                    example.style.display = 'none';
                }
            });
        });
    });
}
