# Permission Issue Pattern Documentation

Complete analysis of the permission conflict pattern between Dockerfile USER settings and compose.yaml security configurations.

## Pattern Overview

**Issue**: Filesystem permission conflicts when combining:
- `USER 1000:1000` in Dockerfile
- `read_only: true` in compose.yaml
- `tmpfs` mounts without explicit ownership
- `COPY` commands without `--chown` flag

## Current Configuration Analysis

### compose.yaml Settings

```yaml
api:
  security_opt:
    - no-new-privileges:true
  read_only: true
  tmpfs:
    - /tmp

worker:
  security_opt:
    - no-new-privileges:true
  read_only: true
  tmpfs:
    - /tmp
```

**Issues Identified**:
1. ✅ `read_only: true` - Good (security)
2. ✅ `tmpfs: - /tmp` - Good (provides writable space)
3. ❌ **tmpfs lacks ownership specification** - Problem!
4. ❌ Files copied as root, then USER switched - Problem!

### Dockerfile Settings

**API Dockerfile**:
```dockerfile
WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY src /app/src
USER 1000:1000
```

**Worker Dockerfile**:
```dockerfile
WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY src /app/src
USER 1000:1000
```

**Issues Identified**:
1. ✅ `USER 1000:1000` - Good (non-root)
2. ❌ **COPY without --chown** - Files owned by root
3. ❌ **No explicit user creation** - Relies on numeric UID

## Permission Conflict Pattern

### Conflict 1: tmpfs Ownership Mismatch

**Problem**:
```yaml
tmpfs:
  - /tmp
```

Creates tmpfs with **default ownership** (typically root:root or host user), but:
- Process runs as USER 1000:1000
- Cannot write to root-owned /tmp
- Results in: `Permission denied: /tmp/file.txt`

**Symptoms**:
```bash
docker compose exec api touch /tmp/test.txt
# touch: cannot touch '/tmp/test.txt': Permission denied
```

**Root Cause**: tmpfs mount doesn't specify `uid=1000,gid=1000`

### Conflict 2: File Ownership Mismatch

**Problem**:
```dockerfile
COPY src /app/src
USER 1000:1000
```

Sequence:
1. Files copied by **root** (default)
2. Files owned by **root:root**
3. USER switched to **1000:1000**
4. `read_only: true` prevents ownership changes
5. Process cannot read/write root-owned files

**Symptoms**:
```bash
docker compose exec api ls -la /app/src
# drwxr-xr-x root root ... /app/src
# -rw-r--r-- root root ... /app/src/main.py

docker compose exec api python /app/src/main.py
# Permission denied (if file has restrictive permissions)
```

**Root Cause**: COPY doesn't set ownership before USER switch

### Conflict 3: Working Directory Permissions

**Problem**:
```dockerfile
WORKDIR /app
# Created by root, owned by root
COPY src /app/src
USER 1000:1000
# Cannot write to /app if needed (logs, cache, etc.)
```

**Symptoms**:
- Cannot create log files in /app/logs
- Cannot write cache files
- Runtime permission errors

## Solution Pattern

### Fix 1: Explicit tmpfs Ownership

**Before**:
```yaml
tmpfs:
  - /tmp
```

**After**:
```yaml
tmpfs:
  - /tmp:uid=1000,gid=1000,mode=1777
  - /var/tmp:uid=1000,gid=1000,mode=1777
```

**Why**:
- `uid=1000,gid=1000`: Matches USER directive
- `mode=1777`: Allows all writes (sticky bit prevents deletion)

### Fix 2: COPY with Ownership

**Before**:
```dockerfile
COPY src /app/src
USER 1000:1000
```

**After**:
```dockerfile
COPY --chown=1000:1000 src /app/src
USER 1000:1000
```

**Or create user explicitly**:
```dockerfile
RUN groupadd -r appuser -g 1000 && \
    useradd -r -u 1000 -g appuser -d /app -s /bin/bash appuser

COPY --chown=appuser:appuser src /app/src
USER appuser
```

### Fix 3: Directory Ownership

**Before**:
```dockerfile
WORKDIR /app
COPY src /app/src
```

**After**:
```dockerfile
RUN mkdir -p /app && chown -R 1000:1000 /app
WORKDIR /app
COPY --chown=1000:1000 src /app/src
```

## Recommended Complete Fix

### Updated compose.yaml

```yaml
api:
  security_opt:
    - no-new-privileges:true
  read_only: true
  tmpfs:
    - /tmp:uid=1000,gid=1000,mode=1777
    - /var/tmp:uid=1000,gid=1000,mode=1777

worker:
  security_opt:
    - no-new-privileges:true
  read_only: true
  tmpfs:
    - /tmp:uid=1000,gid=1000,mode=1777
    - /var/tmp:uid=1000,gid=1000,mode=1777
```

### Updated Dockerfile Pattern

```dockerfile
FROM python:3.11-slim

# Create app user
RUN groupadd -r appuser -g 1000 && \
    useradd -r -u 1000 -g appuser -d /app -s /bin/bash appuser

# Create and set ownership of app directory
RUN mkdir -p /app && chown -R appuser:appuser /app

WORKDIR /app

# Copy with correct ownership
COPY --chown=appuser:appuser pyproject.toml /app/pyproject.toml
COPY --chown=appuser:appuser src /app/src

# Switch to non-root user
USER appuser

CMD ["uvicorn", "apex.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Verification Commands

### Check tmpfs Ownership

```bash
docker compose exec api ls -ld /tmp
# Expected: drwxrwxrwt ... 1000 1000 ... /tmp
```

### Check File Ownership

```bash
docker compose exec api ls -la /app/src
# Expected: -rw-r--r-- ... 1000 1000 ... files
```

### Check Process User

```bash
docker compose exec api ps aux
# Expected: Processes running as user 1000 (appuser)
```

### Test Write Permissions

```bash
docker compose exec api touch /tmp/test.txt && echo "Success"
# Expected: Success
```

## Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `Permission denied: /tmp/file.txt` | tmpfs wrong ownership | Add `uid=1000,gid=1000` to tmpfs |
| `Permission denied: /app/script.py` | Files owned by root | Use `COPY --chown=1000:1000` |
| `Cannot write to /app/logs` | Directory not writable | Create with ownership or use tmpfs |
| `Operation not permitted` | read_only filesystem | Use tmpfs for writable directories |

## Security Best Practices

1. **Always use non-root user** (`USER 1000:1000` or named user)
2. **Set file ownership during COPY** (`COPY --chown`)
3. **Match tmpfs ownership** to USER directive
4. **Create user explicitly** in Dockerfile (not just numeric UID)
5. **Use named volumes** for persistent writable data
6. **Document writable directory requirements**

## Pattern Summary

**The Permission Issue Pattern**:
- **Compose** sets `read_only: true` and `tmpfs` without ownership
- **Dockerfile** sets `USER 1000:1000` but copies files as root
- **Result**: Permission conflicts at runtime

**The Solution Pattern**:
- **Compose** sets `tmpfs: - /tmp:uid=1000,gid=1000,mode=1777`
- **Dockerfile** uses `COPY --chown=1000:1000` and creates user explicitly
- **Result**: Consistent ownership throughout

---

**See Also**:
- [Permission Analysis](permission-analysis.md) - Detailed analysis
- [Dockerfile Best Practices](../deployment/dockerfile-best-practices.md) - Security guidelines

