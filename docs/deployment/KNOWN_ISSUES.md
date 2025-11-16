# Known Issues Registry

Registry of known non-critical issues and their status.

## Issue Classification

**Critical**: Blocks deployment or core functionality  
**High**: Major feature impact, workaround available  
**Medium**: Minor feature impact, workaround available  
**Low**: Cosmetic or non-functional  
**Non-Critical**: Monitoring or auxiliary service only

---

## Known Non-Critical Issues

### Issue #1: postgres_exporter May Show Unhealthy

**Status**: ✅ Known, Non-Critical  
**Priority**: 🟢 Low  
**Impact**: Monitoring metrics unavailable  
**Affected Services**: postgres_exporter

**Description**:
The postgres_exporter service may show as "unhealthy" in Docker Compose health checks. This does not affect application functionality.

**Symptoms**:
```bash
docker compose ps postgres_exporter
# Shows: unhealthy (1) or restarting
```

**Root Cause**:
- Configuration file compatibility
- Exporter version mismatch
- Health check endpoint timing

**Impact Assessment**:
- **Application**: ✅ No impact (monitoring only)
- **Database**: ✅ No impact
- **API**: ✅ No impact
- **Monitoring**: ⚠️ Metrics unavailable in Grafana

**Workaround**:
```bash
# Use direct database queries for monitoring
docker compose exec db psql -U apex -d apex -c "
SELECT * FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
"
```

**Fix Status**: 🔄 Pending investigation  
**Fix Priority**: Low (can be fixed post-launch)  
**Target Fix Date**: Week 2 post-launch

---

### Issue #2: Path Resolution Works Despite Incorrect Syntax

**Status**: ✅ Working as-is, Non-Issue  
**Priority**: 🟢 None  
**Impact**: None (works correctly)  
**Affected Files**: `infra/compose.yaml` lines 131, 210

**Description**:
Paths in compose.yaml use `./services/...` which technically should be `../services/...` from `infra/compose.yaml` location. However, it works because files exist in both locations.

**Current State**:
- ✅ Files accessible: `services/api/monitoring/postgres_exporter.yml`
- ✅ Also exists: `infra/services/api/monitoring/postgres_exporter.yml`
- ✅ Docker Compose resolves correctly

**Why It Works**:
- Files exist in both locations (original + infra/)
- Docker Compose context resolves paths correctly
- No functional impact

**Recommendation**:
- 🟡 Optional: Fix paths to `../services/...` for clarity
- ✅ No action required (works correctly)

---

### Issue #3: OpenSearch Password Hardcoded (Development Only)

**Status**: ⚠️ Acceptable for Dev, Must Fix for Production  
**Priority**: 🟡 Production Only  
**Impact**: Security risk in production  
**Affected Services**: search (OpenSearch)

**Description**:
Hardcoded password `StrongDevPassword123!@#` in compose.yaml line 179.

**Current State**:
```yaml
environment:
  - OPENSEARCH_INITIAL_ADMIN_PASSWORD=StrongDevPassword123!@#
```

**Impact Assessment**:
- **Development**: ✅ Acceptable
- **Staging**: ⚠️ Should use secrets
- **Production**: ❌ Must use secrets management

**Production Fix**:
```yaml
environment:
  - OPENSEARCH_INITIAL_ADMIN_PASSWORD=${OPENSEARCH_PASSWORD}
```

**Fix Status**: 📋 Planned for production  
**Fix Priority**: High (production only)  
**Target Fix Date**: Before production deployment

---

### Issue #4: Worker Service Missing Resource Limits

**Status**: ⚠️ Best Practice Issue  
**Priority**: 🟡 Recommended  
**Impact**: Worker could consume excessive resources  
**Affected Services**: worker

**Description**:
Worker service has no resource limits defined in compose.yaml, unlike API service which has limits.

**Current State**:
```yaml
worker:
  # No deploy.resources section
```

**Impact Assessment**:
- **Functionality**: ✅ No impact (works correctly)
- **Resource Usage**: ⚠️ Could consume excessive resources
- **Other Services**: ⚠️ May affect other services under load

**Recommended Fix**:
```yaml
worker:
  deploy:
    resources:
      limits:
        cpus: "1.0"
        memory: "1G"
      reservations:
        cpus: "0.5"
        memory: "512M"
```

**Fix Status**: 📋 Recommended  
**Fix Priority**: Medium (best practice)  
**Target Fix Date**: Week 1 post-launch

---

## Resolved Issues

### Resolved #1: Python Base Image SHA Conflicts

**Status**: ✅ Resolved  
**Resolution Date**: 2025-01-27  
**Fix Applied**: Removed pinned SHA, using `python:3.11-slim` tag

**Before**:
```dockerfile
FROM python:3.11-slim@sha256:9a0d733f8f4f5d2b5b8a5d5a5f4a9b2e6b86f1a9b6a7e9e4c4913a2f8f3c2e8a
```

**After**:
```dockerfile
FROM python:3.11-slim
```

---

### Resolved #2: PostgreSQL Exporter Image Version

**Status**: ✅ Resolved  
**Resolution Date**: 2025-01-27  
**Fix Applied**: Changed to available image version

**Before**:
```yaml
image: quay.io/prometheuscommunity/postgres-exporter:v0.15.1
```

**After**:
```yaml
image: prometheuscommunity/postgres-exporter:v0.15.0
```

---

## Monitoring Issues

### Monitoring Issue #1: Grafana Dashboard Configuration

**Status**: ✅ Working  
**Description**: Dashboard may need adjustment for production metrics

**Action**: Monitor post-deployment, adjust queries if needed

---

## Documentation Issues

### Doc Issue #1: Some Relative Paths Could Be Clearer

**Status**: 🟡 Minor  
**Impact**: Clarity only, no functional impact

**Action**: Optional cleanup (see Issue #2)

---

## Issue Tracking

### How to Report New Issues

1. **Check if already documented** in this file
2. **Classify issue** (Critical/High/Medium/Low)
3. **Document**:
   - Description
   - Symptoms
   - Impact
   - Workaround (if any)
   - Fix status
4. **Update** this document
5. **Notify team** if Critical or High priority

### Issue Lifecycle

1. **Discovered**: Issue found and documented
2. **Triaged**: Priority assigned, impact assessed
3. **Workaround**: Temporary solution implemented
4. **Fixing**: Root cause investigation
5. **Fixed**: Solution implemented and verified
6. **Resolved**: Moved to resolved section

---

## Summary Table

| Issue | Priority | Status | Impact | Fix Date |
|-------|----------|--------|--------|----------|
| postgres_exporter unhealthy | 🟢 Low | Known | Monitoring only | Week 2 |
| Path syntax | 🟢 None | Working | None | N/A |
| OpenSearch password | 🟡 Prod | Planned | Production only | Pre-prod |
| Worker resource limits | 🟡 Recommended | Planned | Best practice | Week 1 |

---

## Go/No-Go Assessment

**For Deployment Decision**:
- ✅ All Critical issues resolved
- ✅ All High issues have workarounds
- ⚠️ Known non-critical issues documented
- ✅ No blocking issues

**Decision**: ✅ **GO** (with documented known issues)

---

**Last Updated**: 2025-01-27  
**Review Frequency**: Weekly post-launch, before each deployment

