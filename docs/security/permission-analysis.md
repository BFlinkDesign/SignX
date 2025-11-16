# Permission & Security Settings Analysis

Analysis of Docker security settings, USER configurations, and permission conflicts.

## Current Configuration

### Dockerfile USER Settings

**API Service** (`services/api/Dockerfile`):
```dockerfile
USER 1000:1000
```

**Worker Service** (`services/worker/Dockerfile`):
```dockerfile
USER 1000:1000
```

**Both services run as non-root user**: ✅ Good security practice

### Compose.yaml Security Settings

**API Service** (`infra/compose.yaml`):
```yaml
security_opt:
  - no-new-privileges:true
read_only: true
tmpfs:
  - /tmp
```

**Worker Service** (`infra/compose.yaml`):
```yaml
security_opt:
  - no-new-privileges:true
read_only: true
tmpfs:
  - /tmp
```

## Security Analysis

### ✅ Good Security Practices

1. **Non-root User (USER 1000:1000)**
   - Reduces attack surface
   - Prevents privilege escalation
   - Complies with security best practices

2. **no-new-privileges**
   - Prevents processes from gaining additional privileges
   - Complements USER directive
   - Critical for container security

3. **Read-only Root Filesystem**
   - Prevents modification of application files
   - Reduces risk of malware persistence
   - Protects system files

4. **Temporary Filesystem (tmpfs)**
   - Provides writable /tmp directory
   - Essential for applications needing temporary storage
   - Isolated from host filesystem

## Potential Permission Issues

### Issue 1: tmpfs Ownership

**Problem**: tmpfs mounts may not respect USER 1000:1000 ownership

**Symptoms**:
- Permission denied errors when writing to /tmp
- Application crashes on file operations
- Log files cannot be created

**Analysis**:
```yaml
tmpfs:
  - /tmp
```

This creates tmpfs with default ownership (root:root or host user), not USER 1000:1000.

**Solution**:
```yaml
tmpfs:
  - /tmp:uid=1000,gid=1000,mode=1777
```

### Issue 2: File Copy Permissions

**Problem**: Files copied in Dockerfile as root may not be readable by USER 1000:1000

**Current Dockerfile Pattern**:
```dockerfile
COPY src /app/src
USER 1000:1000
```

**Analysis**:
- Files copied by root (default) are owned by root
- USER 1000:1000 cannot read root-owned files with restrictive permissions
- `read_only: true` prevents changing ownership

**Solution**:
```dockerfile
COPY --chown=1000:1000 src /app/src
USER 1000:1000
```

### Issue 3: Working Directory Permissions

**Problem**: /app directory created by root may not be writable by USER 1000:1000

**Current Pattern**:
```dockerfile
WORKDIR /app
COPY src /app/src
USER 1000:1000
```

**Analysis**:
- /app created by root
- USER 1000:1000 needs write access for logs, cache, etc.
- `read_only: true` prevents runtime changes

**Solution**:
```dockerfile
RUN mkdir -p /app && chown -R 1000:1000 /app
WORKDIR /app
COPY --chown=1000:1000 src /app/src
USER 1000:1000
```

## Recommended Fixes

### Fix 1: Update tmpfs Configuration

**File**: `infra/compose.yaml`

**Change**:
```yaml
# API service
api:
  tmpfs:
    - /tmp:uid=1000,gid=1000,mode=1777
    - /var/tmp:uid=1000,gid=1000,mode=1777

# Worker service
worker:
  tmpfs:
    - /tmp:uid=1000,gid=1000,mode=1777
    - /var/tmp:uid=1000,gid=1000,mode=1777
```

**Rationale**:
- `uid=1000,gid=1000`: Sets ownership to match USER directive
- `mode=1777`: Allows all users to write (sticky bit prevents deletion)

### Fix 2: Update Dockerfiles for Proper Ownership

**File**: `services/api/Dockerfile`

**Change**:
```dockerfile
FROM python:3.11-slim

# ... existing setup ...

# Create app user and directory
RUN groupadd -r appuser -g 1000 && \
    useradd -r -u 1000 -g appuser -d /app -s /bin/bash appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

WORKDIR /app

# Copy with correct ownership
COPY --chown=appuser:appuser pyproject.toml /app/pyproject.toml
COPY --chown=appuser:appuser src /app/src

USER appuser

CMD ["uvicorn", "apex.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**File**: `services/worker/Dockerfile`

**Similar changes**: Update to create appuser and set ownership.

### Fix 3: Add Writable Directories (if needed)

**For applications needing persistent writable directories**:

```yaml
# In compose.yaml
api:
  read_only: true
  tmpfs:
    - /tmp:uid=1000,gid=1000,mode=1777
    - /app/logs:uid=1000,gid=1000,mode=0755
    - /app/cache:uid=1000,gid=1000,mode=0755
```

Or use named volumes for persistent data:
```yaml
volumes:
  api_logs:
    driver: local
    driver_opts:
      type: tmpfs
      device: tmpfs
      o: uid=1000,gid=1000,mode=0755
```

## Verification Steps

### 1. Check tmpfs Ownership

```bash
docker compose exec api ls -ld /tmp
# Should show: drwxrwxrwt ... 1000 1000 ... /tmp
```

### 2. Check File Ownership

```bash
docker compose exec api ls -la /app
# Should show files owned by 1000:1000 (appuser)
```

### 3. Test Write Permissions

```bash
docker compose exec api touch /tmp/test.txt
# Should succeed without permission errors
```

### 4. Check Process User

```bash
docker compose exec api ps aux
# Should show processes running as user 1000
```

## Security Checklist

- [x] Non-root user (USER 1000:1000)
- [x] no-new-privileges enabled
- [x] Read-only root filesystem
- [ ] tmpfs ownership matches USER
- [ ] File ownership set correctly in Dockerfile
- [ ] Working directory writable by user
- [ ] Logs directory writable (if needed)
- [ ] Cache directory writable (if needed)

## Common Permission Errors

### Error: "Permission denied: /tmp/file.txt"

**Cause**: tmpfs created with wrong ownership  
**Fix**: Add `uid=1000,gid=1000` to tmpfs mount

### Error: "Permission denied: /app/script.py"

**Cause**: Files owned by root, not readable by USER 1000:1000  
**Fix**: Use `COPY --chown=1000:1000` in Dockerfile

### Error: "Cannot write to /app/logs"

**Cause**: Directory not writable or doesn't exist  
**Fix**: Create directory with correct ownership or use tmpfs volume

## Best Practices Summary

1. **Always use non-root user** in Dockerfile
2. **Set file ownership during COPY** (`--chown`)
3. **Match tmpfs ownership** to USER directive
4. **Use named volumes** for persistent writable data
5. **Test permissions** after deployment
6. **Document writable directories** required by application

---

**Next Steps**:
1. Update `infra/compose.yaml` with proper tmpfs ownership
2. Update Dockerfiles with `--chown` flags
3. Create appuser explicitly in Dockerfiles
4. Test permissions in staging environment
5. Document writable directory requirements

