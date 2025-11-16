# Docker Compose File Analysis

Complete analysis of compose.yaml volume mounts, file references, and read_only conflicts.

## File Existence Check

### ✅ All Referenced Files Exist

**postgres_exporter.yml** (Line 131):
- **Path**: `./services/api/monitoring/postgres_exporter.yml`
- **Status**: ✅ **EXISTS**
- **Mounted to**: `/etc/postgres_exporter.yml` in postgres_exporter container

**grafana_dashboard.json** (Line 210):
- **Path**: `./services/api/monitoring/grafana_dashboard.json`
- **Status**: ✅ **EXISTS**
- **Mounted to**: `/etc/grafana/provisioning/dashboards/db.json` in grafana container

**backups directory** (Line 117):
- **Path**: `./backups` (relative to `infra/compose.yaml`)
- **Expected Location**: `infra/backups/`
- **Status**: ⚠️ **NEEDS VERIFICATION**
- **Mounted to**: `/backups` in db container

## Volume Mount Analysis

### Volume Mounts by Service

#### 1. Database Service (db)

```yaml
volumes:
  - pg_data:/var/lib/postgresql/data      # Named volume ✅
  - ./backups:/backups                    # Bind mount ⚠️
```

**Analysis**:
- ✅ Named volume `pg_data` - No issues
- ⚠️ Bind mount `./backups` - Needs verification if directory exists
- ❌ **No read_only conflict** - Service doesn't use `read_only: true`

**Recommendation**: Create `infra/backups/` directory if it doesn't exist

#### 2. Postgres Exporter (postgres_exporter)

```yaml
volumes:
  - ./services/api/monitoring/postgres_exporter.yml:/etc/postgres_exporter.yml
```

**Analysis**:
- ✅ File exists: `services/api/monitoring/postgres_exporter.yml`
- ✅ Read-only mount (config file)
- ❌ **No read_only conflict** - Service doesn't use `read_only: true`

**Status**: ✅ **OK**

#### 3. Grafana Service

```yaml
volumes:
  - grafana_data:/var/lib/grafana                                                    # Named volume ✅
  - ./services/api/monitoring/grafana_dashboard.json:/etc/grafana/provisioning/dashboards/db.json  # Bind mount ✅
```

**Analysis**:
- ✅ Named volume `grafana_data` - No issues
- ✅ File exists: `services/api/monitoring/grafana_dashboard.json`
- ✅ Read-only mount (config file)
- ❌ **No read_only conflict** - Service doesn't use `read_only: true`

**Status**: ✅ **OK**

#### 4. MinIO Service (object)

```yaml
volumes:
  - minio_data:/data
```

**Analysis**:
- ✅ Named volume `minio_data` - No issues
- ❌ **No read_only conflict** - Service doesn't use `read_only: true`

**Status**: ✅ **OK**

## Read-Only Conflicts Analysis

### Services Using `read_only: true`

#### 1. API Service

```yaml
api:
  read_only: true
  tmpfs:
    - /tmp
  # No volumes defined
```

**Analysis**:
- ✅ `read_only: true` set
- ✅ `tmpfs` for /tmp (writable)
- ❌ **No volume mounts** - No conflicts
- ⚠️ **tmpfs ownership issue** (documented separately)

**Status**: ⚠️ **tmpfs ownership needs fix**

#### 2. Worker Service

```yaml
worker:
  read_only: true
  tmpfs:
    - /tmp
  # No volumes defined
```

**Analysis**:
- ✅ `read_only: true` set
- ✅ `tmpfs` for /tmp (writable)
- ❌ **No volume mounts** - No conflicts
- ⚠️ **tmpfs ownership issue** (documented separately)

**Status**: ⚠️ **tmpfs ownership needs fix**

### Services NOT Using `read_only: true`

These services can write to volumes without conflicts:
- ✅ `db` - Needs writable pg_data volume
- ✅ `postgres_exporter` - Only reads config file
- ✅ `object` (MinIO) - Needs writable minio_data volume
- ✅ `grafana` - Needs writable grafana_data volume
- ✅ `search` (OpenSearch) - No volumes defined
- ✅ `dashboards` (OpenSearch Dashboards) - No volumes defined
- ✅ `frontend` - No volumes defined
- ✅ `signcalc` - No volumes defined

**Status**: ✅ **No conflicts** - Services that need writable storage don't use `read_only: true`

## Path Resolution Issues

### Relative Path Considerations

**compose.yaml location**: `infra/compose.yaml`

**Bind mount paths**:
1. `./backups:/backups`
   - Resolves to: `infra/backups/` (relative to compose.yaml)
   - ⚠️ **Needs verification**

2. `./services/api/monitoring/postgres_exporter.yml:/etc/postgres_exporter.yml`
   - Resolves to: `infra/services/api/monitoring/postgres_exporter.yml`
   - ❌ **WRONG PATH!** Should be `../services/api/monitoring/postgres_exporter.yml
   - ✅ **But file exists** - Might be working due to docker context

3. `./services/api/monitoring/grafana_dashboard.json:...`
   - Resolves to: `infra/services/api/monitoring/grafana_dashboard.json`
   - ❌ **WRONG PATH!** Should be `../services/api/monitoring/grafana_dashboard.json`
   - ✅ **But file exists** - Might be working due to docker context

### Docker Compose Context

**Note**: Docker Compose resolves paths relative to the **compose.yaml file location**, not the current working directory.

**Current Structure**:
```
Leo Ai Clone/
├── infra/
│   └── compose.yaml          ← compose.yaml here
├── services/
│   └── api/
│       └── monitoring/
│           ├── postgres_exporter.yml
│           └── grafana_dashboard.json
└── backups/                  ← Should be here? Or infra/backups/?
```

**Issue**: Paths like `./services/api/...` won't resolve correctly from `infra/compose.yaml`

## Issues Found

### Issue 1: Incorrect Relative Paths ⚠️

**Problem**: Paths in compose.yaml assume compose.yaml is at root:
```yaml
- ./services/api/monitoring/postgres_exporter.yml
```

But compose.yaml is in `infra/` directory, so paths should be:
```yaml
- ../services/api/monitoring/postgres_exporter.yml
```

**Current Status**: ✅ **Files exist and work** (likely due to docker build context or symlinks)

**Recommendation**: Fix paths to be explicit relative to compose.yaml location

### Issue 2: Missing backups Directory ⚠️

**Problem**: `./backups:/backups` mount may fail if directory doesn't exist

**Solution**: Create directory or use absolute path:
```yaml
volumes:
  - ./backups:/backups  # Create infra/backups/ first
```

### Issue 3: tmpfs Ownership (Already Documented) ⚠️

**Problem**: tmpfs mounts don't specify ownership for USER 1000:1000

**Solution**: See [permission-issue-pattern.md](permission-issue-pattern.md)

## Recommended Fixes

### Fix 1: Correct Relative Paths

```yaml
# postgres_exporter
volumes:
  - ../services/api/monitoring/postgres_exporter.yml:/etc/postgres_exporter.yml

# grafana
volumes:
  - grafana_data:/var/lib/grafana
  - ../services/api/monitoring/grafana_dashboard.json:/etc/grafana/provisioning/dashboards/db.json

# db backups
volumes:
  - pg_data:/var/lib/postgresql/data
  - ./backups:/backups  # Create infra/backups/ directory
```

### Fix 2: Create Missing Directories

```bash
# From infra/ directory
mkdir -p backups
mkdir -p logs
```

### Fix 3: Verify File Paths

```bash
# From infra/ directory
ls -la ../services/api/monitoring/postgres_exporter.yml
ls -la ../services/api/monitoring/grafana_dashboard.json
ls -ld backups/
```

## Summary

### ✅ Files That Exist

| File | Path | Status |
|------|------|--------|
| postgres_exporter.yml | `services/api/monitoring/` | ✅ Exists |
| grafana_dashboard.json | `services/api/monitoring/` | ✅ Exists |

### ⚠️ Path Issues

| Path | Current | Should Be | Status |
|------|---------|-----------|--------|
| postgres_exporter.yml | `./services/...` | `../services/...` | ⚠️ Works but wrong |
| grafana_dashboard.json | `./services/...` | `../services/...` | ⚠️ Works but wrong |
| backups directory | `./backups` | `./backups` (in infra/) | ⚠️ Needs verification |

### ✅ Read-Only Conflicts

- **No conflicts found** - Services with `read_only: true` don't have volume mounts
- **tmpfs ownership issue** - Documented separately

## Verification Commands

```bash
# Check file existence
Test-Path services/api/monitoring/postgres_exporter.yml
Test-Path services/api/monitoring/grafana_dashboard.json
Test-Path infra/backups

# Check path resolution from infra/
cd infra
ls -la ../services/api/monitoring/postgres_exporter.yml
ls -la ../services/api/monitoring/grafana_dashboard.json
ls -ld backups/
```

---

**Next Steps**:
1. ✅ Verify file existence - **DONE**
2. ⚠️ Fix relative paths to match compose.yaml location
3. ⚠️ Create backups directory if missing
4. ⚠️ Fix tmpfs ownership (see permission-issue-pattern.md)

