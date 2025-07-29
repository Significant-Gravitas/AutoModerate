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

    // Add copy functionality to code blocks
    addCopyButtonsToCodeBlocks();
});

// Add copy buttons to code blocks
function addCopyButtonsToCodeBlocks() {
    const codeBlocks = document.querySelectorAll('pre code');
    
    codeBlocks.forEach((codeBlock, index) => {
        const pre = codeBlock.parentElement;
        
        // Skip if already has a copy button
        if (pre.querySelector('.copy-btn')) return;
        
        // Create copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'btn btn-sm btn-outline-light copy-btn';
        copyBtn.style.cssText = 'position: absolute; top: 0.5rem; right: 0.5rem; opacity: 0.7; transition: opacity 0.2s;';
        copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
        copyBtn.title = 'Copy code';
        
        // Style the pre element
        pre.style.position = 'relative';
        
        // Add hover effects
        pre.addEventListener('mouseenter', () => {
            copyBtn.style.opacity = '1';
        });
        
        pre.addEventListener('mouseleave', () => {
            copyBtn.style.opacity = '0.7';
        });
        
        // Add copy functionality
        copyBtn.addEventListener('click', function() {
            const text = codeBlock.textContent;
            
            navigator.clipboard.writeText(text).then(function() {
                // Success feedback
                const originalHTML = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i class="fas fa-check"></i>';
                copyBtn.classList.remove('btn-outline-light');
                copyBtn.classList.add('btn-success');
                
                setTimeout(function() {
                    copyBtn.innerHTML = originalHTML;
                    copyBtn.classList.remove('btn-success');
                    copyBtn.classList.add('btn-outline-light');
                }, 2000);
            }).catch(function(err) {
                console.error('Failed to copy: ', err);
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                
                // Success feedback
                const originalHTML = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i class="fas fa-check"></i>';
                copyBtn.classList.remove('btn-outline-light');
                copyBtn.classList.add('btn-success');
                
                setTimeout(function() {
                    copyBtn.innerHTML = originalHTML;
                    copyBtn.classList.remove('btn-success');
                    copyBtn.classList.add('btn-outline-light');
                }, 2000);
            });
        });
        
        pre.appendChild(copyBtn);
    });
}
