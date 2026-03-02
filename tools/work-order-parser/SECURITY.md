# Security Policy

## Supported Versions

We currently support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within Work Order Parser, please send an email to security@eaglesignco.com. All security vulnerabilities will be promptly addressed.

Please include the following information in your report:
- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

## Security Best Practices

1. **Data Handling**
   - All sensitive data is encrypted at rest
   - No sensitive data is stored in plain text
   - Regular security audits are performed

2. **Access Control**
   - Role-based access control implemented
   - Regular password rotation enforced
   - Multi-factor authentication available

3. **Updates**
   - Regular security updates
   - Automatic update notifications
   - Critical security patches released immediately

## Security Updates

Security updates will be released as soon as possible after a vulnerability is confirmed. We will:
1. Acknowledge receipt of the vulnerability report
2. Confirm the problem and determine affected versions
3. Audit code to find any similar problems
4. Prepare fixes for all supported versions
5. Release updates with security patches 