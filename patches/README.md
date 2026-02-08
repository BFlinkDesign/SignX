# Security Patches

This directory contains security patches identified during the production audit.

## Application Order

Apply patches in numerical order:

```bash
# Review each patch before applying
git apply --check patches/001-remove-hardcoded-credentials.patch
git apply patches/001-remove-hardcoded-credentials.patch

git apply --check patches/002-secure-mock-auth.patch
git apply patches/002-secure-mock-auth.patch

git apply --check patches/003-implement-mfa-redis-storage.patch
git apply patches/003-implement-mfa-redis-storage.patch

git apply --check patches/004-remove-jwt-fallback.patch
git apply patches/004-remove-jwt-fallback.patch
```

## Patch Descriptions

| Patch | Severity | Description |
|-------|----------|-------------|
| 001 | 🔴 HIGH | Remove hardcoded KeyedIn credentials |
| 002 | 🔴 HIGH | Add production guards to MockAuth |
| 003 | 🔴 HIGH | Implement Redis storage for MFA codes |
| 004 | 🟡 MEDIUM | Remove fallback JWT secret |

## Post-Application Checklist

After applying patches:

1. **Set environment variables**:
   ```bash
   # KeyedIn credentials (for Keyedin scripts)
   export KEYEDIN_USERNAME="your_username"
   export KEYEDIN_PASSWORD="your_password"
   
   # For development mock auth (optional)
   export APEX_ALLOW_MOCK_AUTH="true"
   ```

2. **Verify Redis is running** for MFA code storage:
   ```bash
   docker-compose ps cache
   redis-cli ping
   ```

3. **Run tests**:
   ```bash
   make test
   pytest services/api/tests -v
   ```

4. **Verify no secrets in code**:
   ```bash
   # Check for any remaining hardcoded secrets
   grep -r "Eagle@605" . --include="*.py" --include="*.ps1"
   grep -r "password\s*=\s*['\"]" . --include="*.py" | grep -v "getenv"
   ```

## Reverting Patches

If needed, revert patches in reverse order:

```bash
git apply -R patches/004-remove-jwt-fallback.patch
git apply -R patches/003-implement-mfa-redis-storage.patch
git apply -R patches/002-secure-mock-auth.patch
git apply -R patches/001-remove-hardcoded-credentials.patch
```

