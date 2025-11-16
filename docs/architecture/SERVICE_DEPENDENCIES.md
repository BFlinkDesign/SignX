# Service Dependencies

Complete service dependency map and startup order for SIGN X Studio Clone.

## Service Overview

### Service Categories

1. **Infrastructure Layer**: Database, cache, storage, search
2. **Monitoring Layer**: Metrics, dashboards, exporters
3. **Application Layer**: API, workers, solvers
4. **Frontend Layer**: Web UI

---

## Service Dependency Graph

```
┌─────────────────────────────────────────────────┐
│           Infrastructure Layer                 │
│                                                 │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌───────┐ │
│  │   db   │  │ cache  │  │ object │  │search │ │
│  │(PostgreSQL)│(Redis)│ │(MinIO) │ │(OpenSearch)│
│  └────────┘  └────────┘  └────────┘  └───────┘ │
└─────────────────────────────────────────────────┘
         │        │        │        │
         │        │        │        │
         └────────┼────────┼────────┘
                  │        │
                  ▼        ▼
┌─────────────────────────────────────────────────┐
│          Monitoring Layer                       │
│                                                 │
│  ┌──────────────┐  ┌──────────┐  ┌──────────┐ │
│  │postgres_     │  │ grafana  │  │dashboards│ │
│  │  exporter    │  │          │  │          │ │
│  └──────────────┘  └──────────┘  └──────────┘ │
│         │              │              │        │
│         └──────────────┴──────────────┘        │
└─────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│          Application Layer                      │
│                                                 │
│  ┌──────┐  ┌────────┐  ┌──────────┐           │
│  │ api  │  │ worker │  │ signcalc│           │
│  └──────┘  └────────┘  └──────────┘           │
│     │         │            │                  │
│     └─────────┴────────────┘                  │
└─────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│          Frontend Layer                         │
│                                                 │
│  ┌─────────┐                                    │
│  │frontend │                                    │
│  │ (Next.js)│                                   │
│  └─────────┘                                    │
└─────────────────────────────────────────────────┘
```

---

## Service Startup Order

### Phase 1: Infrastructure Layer (Parallel)

**Order**: Can start in parallel (independent services)

1. **db** (PostgreSQL)
   - **Dependencies**: None
   - **Startup Time**: ~30 seconds
   - **Health Check**: `pg_isready -U apex`
   - **Must be healthy before**: api, postgres_exporter

2. **cache** (Redis)
   - **Dependencies**: None
   - **Startup Time**: ~5 seconds
   - **Health Check**: `redis-cli ping`
   - **Must be healthy before**: api, worker

3. **object** (MinIO)
   - **Dependencies**: None
   - **Startup Time**: ~10 seconds
   - **Health Check**: `curl http://localhost:9000/minio/health/live`
   - **Must be healthy before**: api

4. **search** (OpenSearch)
   - **Dependencies**: None
   - **Startup Time**: ~60 seconds
   - **Health Check**: `curl http://localhost:9200/_cluster/health`
   - **Must be healthy before**: api, dashboards

**Deployment Command**:
```bash
docker compose up -d db cache object search
```

**Wait For**:
```bash
docker compose ps db cache object search
# All should show: "healthy"
```

---

### Phase 2: Monitoring Layer (Parallel, depends on Infrastructure)

**Order**: Can start in parallel after Phase 1

5. **postgres_exporter**
   - **Dependencies**: db
   - **Startup Time**: ~5 seconds
   - **Health Check**: `curl http://localhost:9187/metrics`
   - **Must be healthy before**: grafana

6. **grafana**
   - **Dependencies**: postgres_exporter (optional, for metrics)
   - **Startup Time**: ~15 seconds
   - **Health Check**: `curl http://localhost:3001/api/health`
   - **Must be healthy before**: None

7. **dashboards** (OpenSearch Dashboards)
   - **Dependencies**: search
   - **Startup Time**: ~30 seconds
   - **Health Check**: Manual (browser check)
   - **Must be healthy before**: None

**Deployment Command**:
```bash
docker compose up -d postgres_exporter grafana dashboards
```

---

### Phase 3: Application Layer (Parallel, depends on Infrastructure)

**Order**: Can start in parallel after Phase 1

8. **api**
   - **Dependencies**: db, cache, object, search
   - **Startup Time**: ~10 seconds
   - **Health Check**: `curl http://localhost:8000/health`
   - **Must be healthy before**: frontend

9. **worker**
   - **Dependencies**: cache
   - **Startup Time**: ~10 seconds
   - **Health Check**: Internal Python check
   - **Must be healthy before**: None

10. **signcalc**
    - **Dependencies**: None (independent)
    - **Startup Time**: ~5 seconds
    - **Health Check**: `curl http://localhost:8002/healthz`
    - **Must be healthy before**: api (for calculations)

**Deployment Command**:
```bash
docker compose up -d api worker signcalc
```

---

### Phase 4: Frontend Layer (depends on Application)

11. **frontend**
    - **Dependencies**: api
    - **Startup Time**: ~15 seconds
    - **Health Check**: `curl http://localhost:5173` (if configured)
    - **Must be healthy before**: None

**Deployment Command**:
```bash
docker compose up -d frontend
```

---

## Dependency Matrix

| Service | Depends On | Required By | Startup Order |
|---------|-----------|-------------|---------------|
| **db** | None | api, postgres_exporter | 1 |
| **cache** | None | api, worker | 1 |
| **object** | None | api | 1 |
| **search** | None | api, dashboards | 1 |
| **postgres_exporter** | db | grafana | 2 |
| **grafana** | postgres_exporter | None | 2 |
| **dashboards** | search | None | 2 |
| **api** | db, cache, object, search | frontend | 3 |
| **worker** | cache | None | 3 |
| **signcalc** | None | api | 3 |
| **frontend** | api | None | 4 |

---

## Health Check Dependencies

### Health Check Sequence

**Critical Path**:
1. Infrastructure healthy (db, cache, object, search)
2. API healthy (depends on infrastructure)
3. Frontend healthy (depends on API)

**Parallel Checks**:
- Monitoring services can start independently
- Worker can start independently (only needs cache)
- Signcalc can start independently

---

## Startup Script

### Automated Startup

```bash
#!/bin/bash
# deploy.sh - Automated deployment with dependency ordering

set -e

echo "Phase 1: Infrastructure Layer"
docker compose up -d db cache object search
echo "Waiting for infrastructure health checks..."
sleep 60
docker compose ps db cache object search | grep -v "healthy" && exit 1

echo "Phase 2: Monitoring Layer"
docker compose up -d postgres_exporter grafana dashboards
sleep 30

echo "Phase 3: Application Layer"
docker compose up -d api worker signcalc
sleep 30
docker compose ps api worker signcalc | grep -v "healthy\|running" && exit 1

echo "Phase 4: Frontend Layer"
docker compose up -d frontend
sleep 15

echo "Deployment complete!"
docker compose ps
```

---

## Dependency Verification

### Check Dependencies Met

```bash
# Check db is ready
docker compose exec db pg_isready -U apex
# Expected: accepting connections

# Check cache is ready
docker compose exec cache redis-cli ping
# Expected: PONG

# Check object is ready
curl -f http://localhost:9000/minio/health/live
# Expected: 200 OK

# Check search is ready
curl -f http://localhost:9200/_cluster/health?wait_for_status=yellow
# Expected: {"status":"yellow" or "green"}
```

### Verify Startup Order

```bash
# Check service start times
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.CreatedAt}}"

# Services should show start times in dependency order:
# 1. db, cache, object, search (Phase 1)
# 2. postgres_exporter, grafana, dashboards (Phase 2)
# 3. api, worker, signcalc (Phase 3)
# 4. frontend (Phase 4)
```

---

## Troubleshooting Dependencies

### Issue: Service Won't Start

**Check Dependencies**:
```bash
# Check if dependencies are healthy
docker compose ps <dependency-service>

# Check dependency logs
docker compose logs <dependency-service>

# Check health endpoint
curl http://localhost:<dependency-port>/health
```

### Issue: Circular Dependencies

**Current State**: ✅ No circular dependencies detected

**Verification**:
- All services have clear dependency tree
- No service depends on itself
- No circular dependency chains

---

## Service Communication

### Internal Communication

**Services communicate via**:
- **Service Names**: docker-compose network DNS
  - `db`, `cache`, `object`, `search`, `api`, `worker`
- **Default Network**: `apex_default`
- **Ports**: Only exposed ports need host access

**Example**:
```python
# API connects to database via service name
DATABASE_URL = "postgresql://apex:apex@db:5432/apex"
# Not: localhost:5432
```

### External Communication

**Exposed Ports**:
- API: `localhost:8000`
- Frontend: `localhost:5173`
- Signcalc: `localhost:8002`
- Database: `localhost:5432` (dev only)
- MinIO: `localhost:9000`, `9001`
- Grafana: `localhost:3001`

---

**Last Updated**: 2025-01-27  
**Review Frequency**: When adding new services

