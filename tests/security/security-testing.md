# Security Testing Guide

**Agent 5**: Comprehensive security testing for CalcuSign.

## OWASP Top 10 Coverage

### 1. Injection (SQL, NoSQL, Command)
- ✅ SQL injection tests in `test_owasp.py`
- ✅ Input validation on all numeric fields
- ✅ Parameterized queries enforced

### 2. Broken Authentication
- ✅ JWT validation tests
- ✅ Expired token handling
- ✅ Authentication bypass attempts

### 3. Sensitive Data Exposure
- ✅ No passwords in responses
- ✅ No API keys exposed
- ✅ Data encryption at rest

### 4. XML External Entities (XXE)
- ✅ JSON-only API (no XML parsing)
- ✅ Safe JSON deserialization

### 5. Broken Access Control
- ✅ RBAC enforcement tests
- ✅ Authorization validation
- ✅ Path traversal protection

### 6. Security Misconfiguration
- ✅ Environment-based config
- ✅ No default credentials
- ✅ Secure headers (CORS, CSP)

### 7. XSS (Cross-Site Scripting)
- ✅ Input sanitization
- ✅ Response escaping
- ✅ No script execution

### 8. Insecure Deserialization
- ✅ JSON validation with Pydantic
- ✅ Safe object reconstruction

### 9. Using Components with Known Vulnerabilities
- ✅ Safety checks on dependencies
- ✅ Trivy image scanning
- ✅ SBOM generation

### 10. Insufficient Logging & Monitoring
- ✅ Structured logging
- ✅ Audit trails
- ✅ Event logging

## Security Scanning

### Static Analysis
```bash
# Bandit - Python security linter
bandit -r services/api/src -f json -o bandit-report.json

# Ruff security
ruff check --select S services/api/src
```

### Dependency Scanning
```bash
# Safety - Check for known vulnerabilities
safety check --json

# Trivy - Container scanning
trivy image apex-api:latest
```

### Dynamic Analysis
```bash
# OWASP ZAP
zap-cli quick-scan --self-contained http://localhost:8000
```

## Running Security Tests

```bash
# All security tests
pytest tests/security/ -v

# OWASP Top 10
pytest tests/security/test_owasp.py -v

# With Bandit
bandit -r services/api/src
```

## Success Criteria

✅ Zero critical vulnerabilities  
✅ All OWASP Top 10 covered  
✅ No sensitive data exposed  
✅ Proper input validation  
✅ Secure by default  

