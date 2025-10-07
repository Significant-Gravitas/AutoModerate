# Security Policy

## Reporting Security Issues

We take the security of our project seriously. If you believe you have found a security vulnerability, please report it to us privately. **Please do not report security vulnerabilities through public GitHub issues, discussions, or pull requests.**

Instead, please report them via:

**[GitHub Security Advisory](https://github.com/Significant-Gravitas/AutoModerate/security/advisories/new)**

### Reporting Process

1. **Submit Report**: Use the GitHub Security Advisory link above to submit your report
2. **Response Time**: Our team will acknowledge receipt of your report within 14 business days
3. **Collaboration**: We will collaborate with you to understand and validate the issue
4. **Resolution**: We will work on a fix and coordinate the release process

### Disclosure Policy

- Please provide detailed reports with reproducible steps
- Include the version/commit hash where you discovered the vulnerability
- Allow us a 90-day security fix window before any public disclosure
- After patch is released, allow 30 days for users to update before public disclosure (for a total of 120 days max between update time and fix time)
- Share any potential mitigations or workarounds if known

## Supported Versions

Only the following versions are eligible for security updates:

| Version | Supported |
|---------|-----------|
| Latest release on `master` branch | ✅ |
| Development commits (pre-master) | ✅ |
| All other versions | ❌ |

## Security Best Practices

When using this project:

- Always use the latest stable version
- Review security advisories before updating
- Keep your dependencies up to date
- Never commit API keys or `.env` files to version control
- Use environment variables for sensitive configuration
- Deploy with HTTPS (TLS 1.2+) and a reverse proxy in production
- Implement rate limiting and strong authentication policies
- Validate all user input and be aware of potential prompt injection attacks

## Past Security Advisories

For a list of past security advisories, please visit our [Security Advisory Page](https://github.com/Significant-Gravitas/AutoModerate/security/advisories).

---

*Last updated: October 2025*
