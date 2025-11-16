# APEX Quick Launch Test

## Status

**Ready to test launch**

All critical files are in place, PYTHONPATH configured in Dockerfiles.

## Launch Command

```bash
cd "C:\Scripts\Leo Ai Clone"
docker compose -f infra/compose.yaml up -d --build
```

## Expected Behavior

1. **Services will build**:
   - API: FastAPI with 35+ endpoints
   - Signcalc: Sign calculation service  
   - Worker: Celery worker
   - DB: PostgreSQL with pgvector
   - Cache: Redis
   - Object: MinIO
   - Search: OpenSearch
   - Dashboards: OpenSearch Dashboards

2. **Health checks**:
   - DB: `pg_isready`
   - Redis: `redis-cli ping`
   - MinIO: curl health endpoint
   - OpenSearch: cluster health API
   - API: `/ready` endpoint checks all dependencies
   - Worker: Celery ping task
   - Signcalc: `/healthz` endpoint

3. **Startup sequence**:
   - All base services start and become healthy
   - Worker waits for Redis healthy
   - API waits for DB, Redis, MinIO, OpenSearch healthy
   - Signcalc starts independently
   - API runs production validation (will skip in dev mode since ENV=dev)

## Verification

```powershell
# Wait for services (2-3 minutes first build)
timeout 180; docker compose -f infra/compose.yaml ps

# Check API health
Invoke-RestMethod http://localhost:8000/health | ConvertTo-Json -Depth 6

# Check readiness (should show all deps OK)
Invoke-RestMethod http://localhost:8000/ready | ConvertTo-Json -Depth 6

# Check signcalc
Invoke-RestMethod http://localhost:8002/healthz | ConvertTo-Json

# Check metrics
Invoke-WebRequest http://localhost:8000/metrics | Select-Object -ExpandProperty Content | Select-String apex_

# Check OpenAPI docs
Start-Process http://localhost:8000/docs
```

## Troubleshooting

If services fail to start:

1. **Check logs**:
   ```powershell
   docker compose -f infra/compose.yaml logs api
   docker compose -f infra/compose.yaml logs signcalc
   docker compose -f infra/compose.yaml logs worker
   ```

2. **Common issues**:
   - Port conflicts (8000, 5432, 6379, 9000, 9200, 5601)
   - Insufficient Docker memory allocation
   - Missing system dependencies in build

3. **Rebuild from scratch**:
   ```powershell
   docker compose -f infra/compose.yaml down -v
   docker compose -f infra/compose.yaml up -d --build --force-recreate
   ```

## Known Good State

- Zero linter errors
- All imports resolve
- PYTHONPATH configured correctly
- Health checks configured
- Production validation exists (skips in dev)

**Recommendation**: Launch and verify services come up healthy.

