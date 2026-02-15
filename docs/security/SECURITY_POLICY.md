# SignX/APEX Security Policy

## Reporting Security Vulnerabilities

We take security seriously at SignX Studio. If you discover a security vulnerability, please report it responsibly.

### How to Report

**DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, please email security@signxstudio.com with:

1. **Description**: Clear description of the vulnerability
2. **Impact**: What an attacker could achieve
3. **Steps to Reproduce**: Detailed steps to reproduce the issue
4. **Affected Components**: Which services/components are affected
5. **Suggested Fix**: (Optional) Your recommendation for fixing

### What to Expect

- **Acknowledgment**: Within 24 hours
- **Initial Assessment**: Within 72 hours
- **Resolution Timeline**: Based on severity
  - Critical: 24-48 hours
  - High: 7 days
  - Medium: 30 days
  - Low: 90 days

### Scope

The following are in scope for security reports:

- SignX API (api.signxstudio.com)
- SignX Web Application (app.signxstudio.com)
- Authentication and authorization systems
- Data storage and encryption
- PE stamp integrity

The following are **out of scope**:

- Third-party services (Supabase, AWS, etc.) - report directly to them
- Social engineering attacks
- Physical security
- Denial of service attacks
- Spam or content injection

## Security Standards

### Data Classification

| Level | Description | Examples | Controls |
|-------|-------------|----------|----------|
| Critical | Data breach would cause severe harm | PE stamps, passwords, encryption keys | Encryption at rest, strict access, audit logging |
| High | Confidential business data | Calculations, project data, client info | Access control, encryption in transit |
| Medium | Internal business data | Logs, metrics, analytics | Role-based access |
| Low | Public information | Documentation, marketing | Standard protection |

### Authentication Requirements

- **Password Policy**: Minimum 12 characters, 3/4 complexity types
- **MFA**: Required for PE stamps and administrative actions
- **Session Duration**: 7 days maximum, 30 minutes idle timeout
- **Account Lockout**: 5 failed attempts, 15-minute lockout

### Access Control

- Principle of least privilege
- Role-based access control (RBAC)
- Organization/account isolation
- Resource-level permissions

### Encryption

- **In Transit**: TLS 1.3 required
- **At Rest**: AES-256 for sensitive fields, bcrypt for passwords
- **Key Management**: Secrets via environment variables, rotation policy

### Audit Logging

All security-relevant events are logged:
- Authentication events
- Authorization decisions
- Data access
- PE stamp operations
- Administrative actions

Retention: 7 years for engineering liability compliance.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x.x | Yes |
| < 1.0.0 | No |

## Security Updates

Security updates are released as:
- **Critical**: Immediate patch release
- **High**: Next patch release (within 7 days)
- **Medium**: Next minor release (within 30 days)
- **Low**: Next major release

## Compliance

SignX/APEX is designed to support:
- GDPR (data protection, right to erasure)
- CCPA (California consumer privacy)
- Professional engineering regulations (PE stamp requirements)

## Contact

- Security Team: security@signxstudio.com
- General Support: support@signxstudio.com
