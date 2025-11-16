# Production Fixes Required

Complete list of fixes that must be applied before production deployment.

## Section 1: Critical Fixes (MUST Apply Before Launch)

### Critical Fix #1: tmpfs Ownership

**Issue**: tmpfs mounts owned by root, processes run as USER 1000:1000

**Impact**: 
- Services crash with "Permission denied" errors when writing to /tmp
- Application logs may fail to write
- Temporary file operations fail
- **BLOCKS DEPLOYMENT** ⚠️

**Location**: `infra/compose.yaml`

**Fix**: Update compose.yaml lines 51-52 (api service) and 74-75 (worker service)

**Before**:
```yaml
api:
  read_only: true
  tmpfs:
    - /tmp

worker:
  read_only: true
  tmpfs:
    - /tmp
```

**After**:
```yaml
api:
  read_only: true
  tmpfs:
    - /tmp:uid=1000,gid=1000,mode=1777
    - /var/tmp:uid=1000,gid=1000,mode=1777

worker:
  read_only: true
  tmpfs:
    - /tmp:uid=1000,gid=1000,mode=1777
    - /var/tmp:uid=1000,gid=1000,mode=1777
```

**Rationale**:
- `uid=1000,gid=1000`: Matches USER directive in Dockerfiles
- `mode=1777`: Allows all writes, sticky bit prevents deletion
- `/var/tmp`: Additional writable space for applications

**Verification Commands**:
```bash
# Check tmpfs ownership after deployment
docker compose exec api ls -ld /tmp
# Expected: drwxrwxrwt ... 1000 1000 ... /tmp

docker compose exec api touch /tmp/test.txt && echo "Success"
# Expected: Success (no permission errors)

docker compose exec worker ls -ld /tmp
# Expected: drwxrwxrwt ... 1000 1000 ... /tmp
```

**Priority**: 🔴 **CRITICAL** - Blocks deployment

---

### Critical Fix #2: Dockerfile File Ownership

**Issue**: Files copied as root, then USER switched to 1000:1000

**Impact**:
- Files may not be readable by USER 1000:1000
- Potential runtime permission errors
- **BLOCKS DEPLOYMENT** ⚠️

**Location**: `services/api/Dockerfile` and `services/worker/Dockerfile`

**Fix**: Add `--chown` flag to COPY commands

**Before**:
```dockerfile
COPY src /app/src
USER 1000:1000
```

**After**:
```dockerfile
# Create user explicitly
RUN groupadd -r appuser -g 1000 && \
    useradd -r -u 1000 -g appuser -d /app -s /bin/bash appuser

# Set ownership before copying
RUN mkdir -p /app && chown -R appuser:appuser /app

WORKDIR /app

# Copy with correct ownership
COPY --chown=appuser:appuser pyproject.toml /app/pyproject.toml
COPY --chown=appuser:appuser src /app/src

USER appuser
```

**Verification Commands**:
```bash
# Check file ownership in container
docker compose exec api ls -la /app/src
# Expected: Files owned by 1000:1000 (appuser)

docker compose exec api ps aux
# Expected: Processes running as user 1000 (appuser)
```

**Priority**: 🔴 **CRITICAL** - Blocks deployment

---

## Section 2: Recommended Fixes (Should Apply)

### Recommended Fix #1: Create Backups Directory

**Issue**: Backups volume mount may fail if directory doesn't exist

**Impact**: 
- Database backup operations may fail silently
- No functional impact if not using backups yet
- Best practice to create directory

**Location**: `infra/backups/` (relative to compose.yaml)

**Fix**:
```bash
# From project root
mkdir -p infra/backups
chmod 755 infra/backups
```

**Verification**:
```bash
test -d infra/backups && echo "Directory exists" || echo "Missing"
```

**Priority**: 🟡 **RECOMMENDED** - Best practice

---

### Recommended Fix #2: Fix Relative Paths (Optional)

**Issue**: Paths in compose.yaml use `./services/...` which assumes compose.yaml at root

**Impact**: 
- Currently works because files exist in both locations
- May break if file structure changes
- Better to use explicit paths

**Location**: `infra/compose.yaml` lines 131, 210

**Current**:
```yaml
- ./services/api/monitoring/postgres_exporter.yml:/etc/postgres_exporter.yml
- ./services/api/monitoring/grafana_dashboard.json:/etc/grafana/...
```

**Recommended**:
```yaml
- ../services/api/monitoring/postgres_exporter.yml:/etc/postgres_exporter.yml
- ../services/api/monitoring/grafana_dashboard.json:/etc/grafana/...
```

**Priority**: 🟡 **OPTIONAL** - Currently working, fix for clarity

---

### Recommended Fix #3: Add Resource Limits to Worker

**Issue**: Worker service has no resource limits defined

**Impact**: 
- Worker could consume excessive resources
- May affect other services
- Best practice to define limits

**Location**: `infra/compose.yaml` worker service (around line 54)

**Fix**:
```yaml
worker:
  # ... existing config ...
  deploy:
    resources:
      limits:
        cpus: "1.0"
        memory: "1G"
      reservations:
        cpus: "0.5"
        memory: "512M"
```

**Priority**: 🟡 **RECOMMENDED** - Best practice

---

## Section 3: Known Non-Issues

### Non-Issue #1: postgres_exporter May Show Unhealthy

**Status**: Known, Non-Critical

**Description**: postgres_exporter may show as unhealthy in health checks

**Impact**: 
- **Monitoring only** - Does not affect application functionality
- Database metrics unavailable in Prometheus/Grafana
- Application services unaffected

**Root Cause**: 
- Config file may need adjustment
- Or exporter version compatibility

**Workaround**: 
- Use direct database queries for monitoring
- Fix postgres_exporter config post-deployment

**Priority**: 🟢 **LOW** - Non-critical, monitoring only

**Action**: Monitor post-deployment, fix in first week if needed

---

### Non-Issue #2: Path Resolution Works Despite Incorrect Syntax

**Status**: Working as-is

**Description**: Paths use `./services/...` which technically should be `../services/...` from `infra/compose.yaml`

**Impact**: 
- **None** - Files exist in both locations
- Works correctly
- No functional issues

**Why It Works**: 
- Files exist at: `services/api/monitoring/`
- Also exist at: `infra/services/api/monitoring/`
- Docker Compose resolves correctly

**Priority**: 🟢 **NONE** - No action required

**Action**: Optional cleanup for clarity (Recommended Fix #2)

---

### Non-Issue #3: OpenSearch Password in Compose File

**Status**: Acceptable for Development, Fix for Production

**Description**: Hardcoded password `StrongDevPassword123!@#` in compose.yaml

**Impact**: 
- **Security risk** in production
- Acceptable for development/staging
- Must use secrets management in production

**Production Fix**:
```yaml
search:
  environment:
    - OPENSEARCH_INITIAL_ADMIN_PASSWORD=${OPENSEARCH_PASSWORD}
    # Remove hardcoded password
```

**Priority**: 🟡 **PRODUCTION ONLY** - Fix before production deployment

---

## Fix Priority Summary

| Fix | Priority | Blocks Deployment | Time to Fix |
|-----|----------|-------------------|-------------|
| tmpfs Ownership | 🔴 Critical | Yes | 2 minutes |
| Dockerfile Ownership | 🔴 Critical | Yes | 5 minutes |
| Backups Directory | 🟡 Recommended | No | 1 minute |
| Resource Limits | 🟡 Recommended | No | 2 minutes |
| Path Corrections | 🟡 Optional | No | 2 minutes |
| OpenSearch Password | 🟡 Production | No | 5 minutes |

## Pre-Deployment Action Items

### Must Complete Before Launch:
- [ ] Apply Critical Fix #1: tmpfs ownership
- [ ] Apply Critical Fix #2: Dockerfile ownership
- [ ] Rebuild Docker images
- [ ] Test services start correctly
- [ ] Verify permissions with test commands

### Should Complete Before Launch:
- [ ] Create backups directory
- [ ] Add worker resource limits
- [ ] Document OpenSearch password in secrets

### Optional (Post-Launch):
- [ ] Fix relative paths for clarity
- [ ] Resolve postgres_exporter health check
- [ ] Review all configuration files

## Verification Checklist

After applying fixes:

```bash
# 1. Verify tmpfs ownership
docker compose exec api ls -ld /tmp
docker compose exec worker ls -ld /tmp

# 2. Verify file ownership
docker compose exec api ls -la /app/src | head -5

# 3. Test write permissions
docker compose exec api touch /tmp/test.txt && rm /tmp/test.txt

# 4. Verify process user
docker compose exec api ps aux | grep -E "PID|uvicorn"

# 5. Check all services healthy
docker compose ps
```

---

**Last Updated**: 2025-01-27  
**Next Review**: Before each deployment

