# 🔴 Production Blockers Audit Report

**Generated**: December 10, 2025  
**Repository**: SignX/APEX  
**Auditor**: Automated Security & Code Quality Scan

---

## Executive Summary

| Severity | Count | Action Required |
|----------|-------|-----------------|
| 🔴 **HIGH** | 8 | Immediate fix before production |
| 🟡 **MEDIUM** | 15 | Fix before production launch |
| 🟢 **LOW** | 12 | Track for future improvement |

---

## 🔴 HIGH SEVERITY ISSUES

### 1. Hardcoded Production Credentials

**File**: `Keyedin/extract_with_credentials.py:10-11`  
**Type**: Hardcoded Secret  
**Risk**: Credential exposure in version control

```python
# CURRENT (VULNERABLE)
USERNAME = "BradyF"
PASSWORD = "[REDACTED]"
```

**Files Affected**:
- `Keyedin/extract_with_credentials.py:10-11`
- `Keyedin/test_api_with_cookies.py:13-14`
- `Keyedin/comprehensive_test.py:77,255`

**Suggested Fix**:
```python
# SECURE - Use environment variables
import os
USERNAME = os.getenv("KEYEDIN_USERNAME")
PASSWORD = os.getenv("KEYEDIN_PASSWORD")

if not USERNAME or not PASSWORD:
    raise ValueError("KEYEDIN_USERNAME and KEYEDIN_PASSWORD must be set")
```

<details>
<summary>📋 Diff Patch</summary>

```diff
--- a/Keyedin/extract_with_credentials.py
+++ b/Keyedin/extract_with_credentials.py
@@ -6,8 +6,13 @@
 
 from keyedin_cdp_extractor import KeyedInCDPExtractor, get_project_root
 
-# Credentials
-USERNAME = "BradyF"
-PASSWORD = "[REDACTED]"
+import os
+
+# Credentials from environment
+USERNAME = os.getenv("KEYEDIN_USERNAME")
+PASSWORD = os.getenv("KEYEDIN_PASSWORD")
+
+if not USERNAME or not PASSWORD:
+    raise ValueError("KEYEDIN_USERNAME and KEYEDIN_PASSWORD environment variables must be set")
 
 if __name__ == '__main__':
```

</details>

---

### 2. MFA Code Verification Bypass (DEV ONLY Code in Production Path)

**File**: `services/api/src/apex/api/routes/auth_mfa.py:243-246`  
**Type**: Security Bypass  
**Risk**: Any 6-digit code is accepted without validation

```python
# CURRENT (INSECURE)
# TODO: Retrieve stored code from Redis and validate
# For now, we'll accept any 6-digit code as valid (DEV ONLY)

is_valid = len(request.code) == 6 and request.code.isdigit()
```

**Suggested Fix**:
```python
# SECURE - Validate against stored code
from ..cache import redis_client

stored_code = await redis_client.get(f"mfa_code:{current_user.user_id}")
if not stored_code:
    raise HTTPException(status_code=401, detail="No pending MFA code. Request a new one.")

is_valid = secrets.compare_digest(stored_code, request.code)
await redis_client.delete(f"mfa_code:{current_user.user_id}")  # One-time use
```

<details>
<summary>📋 Diff Patch</summary>

```diff
--- a/services/api/src/apex/api/routes/auth_mfa.py
+++ b/services/api/src/apex/api/routes/auth_mfa.py
@@ -1,6 +1,7 @@
 """MFA routes for authentication API."""
 
 from __future__ import annotations
+import secrets
 
 from typing import Optional
 
@@ -240,10 +241,21 @@ async def verify_mfa_code(
     Returns:
         Success message and updated token with mfa_verified=True
     """
-    # TODO: Retrieve stored code from Redis and validate
-    # For now, we'll accept any 6-digit code as valid (DEV ONLY)
+    # Retrieve stored code from Redis
+    from ..deps import settings
+    import redis
     
-    is_valid = len(request.code) == 6 and request.code.isdigit()
+    redis_client = redis.from_url(settings.REDIS_URL)
+    stored_code_key = f"mfa_code:{current_user.user_id}"
+    stored_code = redis_client.get(stored_code_key)
+    
+    if not stored_code:
+        raise HTTPException(status_code=401, detail="No pending MFA code. Request a new one.")
+    
+    stored_code = stored_code.decode() if isinstance(stored_code, bytes) else stored_code
+    is_valid = secrets.compare_digest(stored_code, request.code)
+    redis_client.delete(stored_code_key)  # One-time use
     
     if not is_valid:
         logger.warning("mfa.code.verify_failed", user_id=current_user.user_id)
```

</details>

---

### 3. Mock Authentication Available in Production

**File**: `services/api/src/apex/api/auth.py:256-280`  
**Type**: Security Bypass  
**Risk**: Mock users with admin roles can be created without authentication

```python
# CURRENT (DANGEROUS)
class MockAuth:
    """Mock auth for local development without JWT."""
    
    @staticmethod
    def get_mock_user() -> TokenData:
        """Return a mock user for local dev."""
        return TokenData(
            user_id="dev-user",
            account_id="dev-account",
            email="dev@example.com",
            roles=["admin", "user"],  # ADMIN ROLE!
        )
```

**Suggested Fix**:
```python
# SECURE - Only available in dev environment with explicit flag
class MockAuth:
    """Mock auth for local development without JWT."""
    
    @staticmethod
    def get_mock_user() -> TokenData:
        """Return a mock user for local dev."""
        if settings.ENV == "prod":
            raise RuntimeError("MockAuth cannot be used in production")
        if not os.getenv("APEX_ALLOW_MOCK_AUTH", "").lower() == "true":
            raise RuntimeError("MockAuth requires APEX_ALLOW_MOCK_AUTH=true")
        
        logger.warning("auth.mock_user_created", msg="Using mock authentication - NOT FOR PRODUCTION")
        return TokenData(
            user_id="dev-user",
            account_id="dev-account", 
            email="dev@example.com",
            roles=["user"],  # No admin by default
        )
```

<details>
<summary>📋 Diff Patch</summary>

```diff
--- a/services/api/src/apex/api/auth.py
+++ b/services/api/src/apex/api/auth.py
@@ -253,18 +253,27 @@ def require_role(allowed_roles: list[str]):
     return _role_check
 
 
-# Placeholder auth for development
+# Placeholder auth for development ONLY
 class MockAuth:
     """Mock auth for local development without JWT."""
     
     @staticmethod
     def get_mock_user() -> TokenData:
         """Return a mock user for local dev."""
+        import os
+        
+        if settings.ENV == "prod":
+            raise RuntimeError("MockAuth cannot be used in production")
+        if not os.getenv("APEX_ALLOW_MOCK_AUTH", "").lower() == "true":
+            raise RuntimeError("MockAuth requires APEX_ALLOW_MOCK_AUTH=true environment variable")
+        
+        logger.warning("auth.mock_user_created", msg="Using mock authentication - NOT FOR PRODUCTION")
         return TokenData(
             user_id="dev-user",
             account_id="dev-account",
             email="dev@example.com",
-            roles=["admin", "user"],
+            roles=["user"],  # No admin privileges in mock auth
         )
```

</details>

---

### 4. MFA Codes Not Persisted to Redis

**File**: `services/api/src/apex/api/routes/auth_mfa.py:163,208`  
**Type**: Incomplete Implementation  
**Risk**: MFA codes stored in memory, lost on restart, no expiration

```python
# CURRENT (INCOMPLETE)
# TODO: Store code in Redis with expiration (10 minutes)
```

**Files Affected**:
- `services/api/src/apex/api/routes/auth_mfa.py:163` (SMS)
- `services/api/src/apex/api/routes/auth_mfa.py:208` (Email)

**Suggested Fix**:
```python
# After generating code, store in Redis
import redis
from ..deps import settings

redis_client = redis.from_url(settings.REDIS_URL)
redis_client.setex(
    f"mfa_code:{current_user.user_id}",
    600,  # 10 minutes TTL
    code
)
```

---

### 5. TOTP Secret Not Persisted to Database

**File**: `services/api/src/apex/api/routes/auth_mfa.py:105`  
**Type**: Incomplete Implementation  
**Risk**: TOTP secrets lost on restart, users cannot use 2FA

```python
# CURRENT (INCOMPLETE)
# TODO: Store secret in database associated with user
# For now, we'll create a new token with mfa_verified=True
```

**Suggested Fix**: Implement database storage for TOTP secrets with encryption at rest.

---

### 6. Hardcoded API Tokens in PowerShell Scripts

**File**: `Keyedin/GWT Google Web Toolkit/*.ps1`  
**Type**: Hardcoded Secret  
**Risk**: API tokens exposed in version control

```powershell
# CURRENT (VULNERABLE)
$catalogToken = "600437df-77ae-4aca-8f93-45b022255489"
$authToken = "af8f4d09-7cd7-4569-bdd1-d820d9dbc36b"
```

**Files Affected**:
- `Keyedin/GWT Google Web Toolkit/test_with_cookie.ps1:18`
- `Keyedin/GWT Google Web Toolkit/test_getdata_arrays.ps1:17`
- `Keyedin/GWT Google Web Toolkit/test_exact_working_payload.ps1:18`
- `Keyedin/GWT Google Web Toolkit/test_both_signatures.ps1:18,34`
- `Keyedin/GWT Google Web Toolkit/test_api_methods.ps1:18`
- `Keyedin/GWT Google Web Toolkit/session_keepalive.ps1:15`

**Suggested Fix**:
```powershell
# SECURE - Use environment variables
$catalogToken = $env:KEYEDIN_CATALOG_TOKEN
if (-not $catalogToken) {
    Write-Error "KEYEDIN_CATALOG_TOKEN environment variable not set"
    exit 1
}
```

---

### 7. Default JWT Secret in Dev Falls Through to Production

**File**: `services/api/src/apex/api/routes/auth.py:36`  
**Type**: Weak Default  
**Risk**: Predictable secret if ENV check fails

```python
# CURRENT (RISKY)
JWT_SECRET_KEY = getattr(settings, "JWT_SECRET_KEY", "dev-secret-key-change-in-production")
```

**Note**: The main `auth.py` correctly raises an error in production, but this route file has a fallback.

**Suggested Fix**: Remove the fallback, rely on centralized JWT_SECRET_KEY from `auth.py`.

---

### 8. Database Password in Backup Script

**File**: `services/api/backups/dump.sh:14`  
**Type**: Hardcoded Default  
**Risk**: Default password exposed

```bash
# CURRENT (RISKY)
export PGPASSWORD="${POSTGRES_PASSWORD:-apex}"
```

**Suggested Fix**: Remove default, require explicit password.

---

## 🟡 MEDIUM SEVERITY ISSUES

### 9. Placeholder MinIO Presigned URLs

**File**: `services/api/src/apex/api/routes/files.py:63`  
**Type**: Placeholder Implementation  
**Risk**: File uploads may not work in production

```python
add_assumption(assumptions, "MinIO presigned URL placeholder (client not configured)")
```

**Suggested Fix**: Ensure MinIO is properly configured with required environment variables.

---

### 10. Placeholder Engineering Calculations

**File**: `services/api/src/apex/domains/signage/edge_cases_advanced.py:53`  
**Type**: Placeholder Value  
**Risk**: Incorrect wind force estimates

```python
wind_force_estimate = 1000.0  # Placeholder
```

**Suggested Fix**: Implement proper wind force calculation based on ASCE 7 standards.

---

### 11. ML Model Placeholder Training

**File**: `services/api/src/apex/domains/signage/ml_models.py:87,120,147`  
**Type**: Stub Implementation  
**Risk**: ML predictions will be random/invalid

```python
# Load trained model (placeholder - would load pickle/joblib)
self.model.fit(X, np.random.rand(len(X)))  # Placeholder
# Placeholder prediction
```

**Suggested Fix**: Load actual trained models from artifact storage.

---

### 12. Missing Rate Limiting on MFA Attempts

**File**: `SESSION_SUMMARY.md:383-384`, `PROGRESS_REPORT.md:275`  
**Type**: Missing Security Feature  
**Risk**: Brute force attacks on MFA codes

**TODO Items**:
- `[ ] Rate limiting for MFA attempts (max 5/minute)`
- `[ ] Account lockout after failed attempts`

**Suggested Fix**: Implement rate limiting middleware for MFA endpoints.

---

### 13. LaTeX PDF Generation Not Implemented

**File**: `services/api/src/apex/domains/signage/engineering_docs.py:189-190`  
**Type**: Incomplete Implementation  
**Risk**: Engineering document generation fails

```python
# Placeholder - would execute: pdflatex -output-directory /tmp file.tex
raise NotImplementedError("LaTeX to PDF compilation requires pdflatex (not implemented)")
```

---

### 14. Search Fallback Returns Empty

**File**: `services/api/src/apex/api/utils/search.py:127,136`  
**Type**: Silent Failure  
**Risk**: Search functionality fails silently

```python
return [], True  # Returns empty results on error
```

---

### 15. CORS Allows Localhost Origins

**File**: `services/api/src/apex/api/deps.py:46`  
**Type**: Development Configuration  
**Risk**: Should be restricted in production

```python
CORS_ALLOW_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])
```

**Suggested Fix**: Use environment-specific CORS configuration.

---

### 16. Hardcoded localhost in SignX-Intel

**File**: `SignX-Intel/src/signx_intel/config.py:37`  
**Type**: Hardcoded Endpoint  
**Risk**: Service won't connect in production

```python
minio_endpoint: str = "localhost:9000"
```

---

### 17. CRM Webhook Missing Signature Validation

**File**: `services/api/src/apex/api/routes/crm.py:51`  
**Type**: Security TODO  
**Risk**: Webhook spoofing possible

```python
# TODO: Add webhook signature validation
```

---

### 18-23. Missing Database/Redis Integration TODOs

| File | Line | Issue |
|------|------|-------|
| `auth_mfa.py` | 105 | Store TOTP secret in database |
| `auth_mfa.py` | 163 | Store SMS code in Redis |
| `auth_mfa.py` | 208 | Store email code in Redis |
| `auth_mfa.py` | 295 | Query database for MFA config |
| `auth_mfa.py` | 299 | Check database for mfa_enabled |
| `auth_mfa.py` | 330 | Remove MFA config from database |

---

## 🟢 LOW SEVERITY ISSUES

### 24. Test User Patterns in Test Files (ACCEPTABLE)

These are in test files and are appropriate:

| File | Pattern |
|------|---------|
| `tests/test_file_uploads.py:21,67` | `"created_by": "test_user"` |
| `tests/integration/test_idempotency.py:19,32,40` | `"test_user"` |
| `tests/e2e/test_full_workflow.py:83,168,217` | `"test_user"` |
| `tests/compliance/test_gdpr_ccpa.py:17,19` | `"gdpr_test_user"` |

**Status**: ✅ Appropriate for test context

---

### 25. Sample Data in Analysis Tools (ACCEPTABLE)

| File | Pattern | Purpose |
|------|---------|---------|
| `eagle_analyzer_v1/sign_type_analyzer.py:122` | `sample_size >= 5` | Statistical threshold |
| `eagle_analyzer_v1/eagle_pricing_guide.py:201` | `sample_size` | Analytics |

**Status**: ✅ Appropriate naming for analytics

---

### 26. Documentation Placeholder Examples

| File | Issue |
|------|-------|
| `GEMINI.md:52` | `$env:GEMINI_API_KEY = "your_api_key_here"` |
| `README.md:97` | `$env:GEMINI_API_KEY = "your-key-from-aistudio"` |
| `START_HERE.md:103` | `$env:GEMINI_API_KEY = "your-key-here"` |

**Status**: ✅ Appropriate for documentation

---

### 27. Empty Exception Handlers

Multiple files contain `pass` in exception handlers. Review for appropriate error handling:

| File | Line |
|------|------|
| `services/api/src/apex/api/main.py` | 77, 149, 195 |
| `services/api/src/apex/api/auth.py` | 176, 180 |
| `services/api/src/apex/api/audit.py` | 105, 108 |

---

### 28. Stub Functions in External Libraries

Files in `WebScrapers/Scrapling-main/` contain stub implementations. These are third-party code.

**Status**: ⚠️ Review if library is modified

---

### 29-35. Future Enhancement TODOs

| File | Line | Enhancement |
|------|------|-------------|
| `routes/cabinets.py` | 132 | Update project payload with cabinet config |
| `routes/submission.py` | 136 | Extract manager email from project metadata |
| `PROGRESS_REPORT.md` | 62 | Add Redis integration |
| `QUICKSTART.md` | 378 | Production deployment guide |

---

## 📊 Summary by Category

| Category | High | Medium | Low |
|----------|------|--------|-----|
| Hardcoded Secrets | 3 | 0 | 0 |
| Security Bypass | 2 | 1 | 0 |
| Incomplete Implementation | 3 | 8 | 0 |
| Placeholder Values | 0 | 4 | 0 |
| Configuration Issues | 0 | 2 | 0 |
| Test/Doc Patterns | 0 | 0 | 12 |

---

## 🔧 Recommended Actions

### Immediate (Before Production)

1. **Remove hardcoded credentials** from `Keyedin/` directory
2. **Implement Redis storage** for MFA codes
3. **Add production guard** to MockAuth class
4. **Implement TOTP secret** database persistence
5. **Remove fallback JWT secret** from routes/auth.py

### Before Launch

1. Configure production CORS origins
2. Implement webhook signature validation
3. Set up proper MinIO configuration
4. Review and fix placeholder calculations
5. Add rate limiting to MFA endpoints

### Post-Launch

1. Load trained ML models
2. Implement LaTeX PDF generation
3. Complete all database integration TODOs

---

## 🛡️ Security Checklist

- [ ] All credentials removed from source code
- [ ] JWT_SECRET_KEY set via environment variable
- [ ] MFA codes stored in Redis with TTL
- [ ] MockAuth disabled in production
- [ ] CORS restricted to production domains
- [ ] Webhook signatures validated
- [ ] Rate limiting enabled on auth endpoints
- [ ] TOTP secrets encrypted at rest

---

*Report generated by automated codebase audit. Manual review recommended for all HIGH severity items.*

