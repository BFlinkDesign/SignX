# Configuration Reference

Complete configuration guide for SIGN X Studio Clone deployment.

## Environment Variables

### API Service

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENV` | No | `dev` | Environment name |
| `SERVICE_NAME` | Yes | `api` | Service identifier |
| `APP_VERSION` | No | `0.1.0` | Application version |
| `GIT_SHA` | No | `dev` | Git commit SHA |
| `GIT_DIRTY` | No | `false` | Git working tree status |
| `BUILD_ID` | No | `local` | Build identifier |
| `CORS_ALLOW_ORIGINS` | Yes | - | Comma-separated allowed origins |
| `REDIS_URL` | Yes | - | Redis connection URL |
| `DATABASE_URL` | Yes | - | PostgreSQL connection URL |
| `APEX_RATE_LIMIT_PER_MIN` | No | `60` | Rate limit per minute |
| `MINIO_URL` | Yes | - | MinIO API URL |
| `MINIO_ACCESS_KEY` | Yes | - | MinIO access key |
| `MINIO_SECRET_KEY` | Yes | - | MinIO secret key |
| `MINIO_BUCKET` | Yes | - | MinIO bucket name |
| `MODEL_PROVIDER` | No | `none` | LLM provider (if used) |
| `MODEL_NAME` | No | `none` | LLM model name |
| `MODEL_TEMPERATURE` | No | `0.0` | LLM temperature |
| `MODEL_MAX_TOKENS` | No | `1024` | LLM max tokens |

**Example**:
```yaml
environment:
  - ENV=production
  - DATABASE_URL=postgresql://apex:password@db:5432/apex
  - REDIS_URL=redis://cache:6379/0
  - MINIO_URL=http://object:9000
```

### Worker Service

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SERVICE_NAME` | Yes | `worker` | Service identifier |
| `REDIS_URL` | Yes | - | Redis connection URL |
| `CELERY_BROKER_URL` | Yes | - | Celery broker URL |
| `CELERY_RESULT_BACKEND` | Yes | - | Celery result backend URL |

**Example**:
```yaml
environment:
  - REDIS_URL=redis://cache:6379/0
  - CELERY_BROKER_URL=redis://cache:6379/0
  - CELERY_RESULT_BACKEND=redis://cache:6379/1
```

### Database Service

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_USER` | Yes | - | Database user |
| `POSTGRES_PASSWORD` | Yes | - | Database password |
| `POSTGRES_DB` | Yes | - | Database name |
| `POSTGRES_INITDB_ARGS` | No | - | Init database arguments |

**Example**:
```yaml
environment:
  - POSTGRES_USER=apex
  - POSTGRES_PASSWORD=apex
  - POSTGRES_DB=apex
```

### OpenSearch Service

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `discovery.type` | Yes | `single-node` | Discovery type |
| `plugins.security.disabled` | No | `true` | Security plugin |
| `OPENSEARCH_JAVA_OPTS` | No | `-Xms512m -Xmx512m` | JVM options |
| `OPENSEARCH_INITIAL_ADMIN_PASSWORD` | Yes | - | Admin password |

**⚠️ Production**: Use secrets for password

### Grafana Service

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GF_SECURITY_ADMIN_USER` | No | `admin` | Admin username |
| `GF_SECURITY_ADMIN_PASSWORD` | No | `admin` | Admin password |
| `GF_INSTALL_PLUGINS` | No | - | Comma-separated plugin list |

**⚠️ Production**: Change default admin password

---

## Port Mappings

| Service | Internal Port | External Port | Purpose |
|---------|--------------|---------------|---------|
| **api** | 8000 | 8000 | API endpoints |
| **frontend** | 3000 | 5173 | Web UI (dev server) |
| **signcalc** | 8002 | 8002 | Solver service |
| **db** | 5432 | 5432 | PostgreSQL (dev only) |
| **cache** | 6379 | 6379 | Redis (dev only) |
| **object** | 9000 | 9000 | MinIO API |
| **object** | 9001 | 9001 | MinIO Console |
| **search** | 9200 | 9200 | OpenSearch API |
| **dashboards** | 5601 | 5601 | OpenSearch Dashboards |
| **grafana** | 3000 | 3001 | Grafana UI |
| **postgres_exporter** | 9187 | 9187 | Prometheus metrics |

**Production**: Only expose necessary ports, use load balancer for API

---

## Volume Mounts

### Named Volumes

| Volume | Service | Purpose | Backup Strategy |
|--------|---------|--------|-----------------|
| `pg_data` | db | PostgreSQL data | Daily pg_dump |
| `minio_data` | object | MinIO object storage | S3 replication |
| `grafana_data` | grafana | Grafana dashboards/config | Config in Git |

**Backup Commands**:
```bash
# PostgreSQL backup
docker compose exec db pg_dump -U apex apex > backup.sql

# MinIO backup (if configured)
# Use MinIO replication or S3 sync
```

### Bind Mounts

| Host Path | Container Path | Service | Purpose |
|-----------|---------------|---------|---------|
| `./backups` | `/backups` | db | Backup storage |
| `./services/api/monitoring/postgres_exporter.yml` | `/etc/postgres_exporter.yml` | postgres_exporter | Config file |
| `./services/api/monitoring/grafana_dashboard.json` | `/etc/grafana/provisioning/dashboards/db.json` | grafana | Dashboard config |

---

## Resource Limits

### API Service

```yaml
deploy:
  resources:
    limits:
      cpus: "1.0"
      memory: "512M"
```

**Rationale**:
- API is stateless, can scale horizontally
- Moderate CPU for request processing
- Memory for connection pooling and caching

### Worker Service

**Current**: No limits (⚠️ Should add)

**Recommended**:
```yaml
deploy:
  resources:
    limits:
      cpus: "1.0"
      memory: "1G"
    reservations:
      cpus: "0.5"
      memory: "512M"
```

**Rationale**:
- Workers process background tasks
- May need more memory for large calculations
- CPU for concurrent task processing

### Frontend Service

```yaml
deploy:
  resources:
    limits:
      cpus: "0.5"
      memory: "256M"
```

**Rationale**:
- Frontend is mostly static
- Low resource requirements
- Can scale if needed

### Database Service

**Current**: No explicit limits (uses Docker defaults)

**Recommended**:
```yaml
deploy:
  resources:
    limits:
      cpus: "2.0"
      memory: "2G"
    reservations:
      cpus: "1.0"
      memory: "1G"
```

**Rationale**:
- Database is critical resource
- Needs sufficient memory for buffer cache
- CPU for query processing

---

## Security Settings

### API and Worker Services

```yaml
security_opt:
  - no-new-privileges:true
read_only: true
tmpfs:
  - /tmp:uid=1000,gid=1000,mode=1777
  - /var/tmp:uid=1000,gid=1000,mode=1777
```

**Settings Explained**:
- `no-new-privileges:true`: Prevents privilege escalation
- `read_only: true`: Makes root filesystem read-only
- `tmpfs`: Provides writable temporary space with correct ownership

### Dockerfile Security

**User Configuration**:
```dockerfile
RUN groupadd -r appuser -g 1000 && \
    useradd -r -u 1000 -g appuser -d /app -s /bin/bash appuser

COPY --chown=appuser:appuser src /app/src
USER appuser
```

**Best Practices**:
- Non-root user (1000:1000)
- Files owned by application user
- No SUID binaries
- Minimal base image (slim)

---

## Network Configuration

### Default Network

**Name**: `apex_default` (auto-created by docker-compose)

**Type**: Bridge network

**DNS**: Service names resolve to container IPs

**Services** can communicate using service names:
- `db` → `db:5432`
- `cache` → `cache:6379`
- `api` → `api:8000`

### External Access

**Only exposed ports** accessible from host:
- API: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Database: `localhost:5432` (dev only, remove in production)

---

## Health Checks

### API Service

```yaml
healthcheck:
  test: ["CMD", "curl", "-fsS", "http://localhost:8000/ready"]
  interval: 10s
  timeout: 3s
  retries: 5
```

**Checks**: Database, Redis, MinIO, OpenSearch connectivity

### Worker Service

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "from apex.worker.app import ping; import sys; sys.exit(0 if ping().get('status')=='ok' else 1)"]
  interval: 30s
  timeout: 5s
  retries: 5
```

### Database Service

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER"]
  interval: 10s
  timeout: 5s
  retries: 10
```

**Checks**: PostgreSQL accepts connections

### Signcalc Service

```yaml
healthcheck:
  test: ["CMD", "curl", "-fsS", "http://localhost:8002/healthz"]
  interval: 10s
  timeout: 3s
  retries: 5
```

---

## Configuration Files

### postgres_exporter.yml

**Location**: `services/api/monitoring/postgres_exporter.yml`  
**Mounted to**: `/etc/postgres_exporter.yml`  
**Purpose**: Prometheus query configuration

### grafana_dashboard.json

**Location**: `services/api/monitoring/grafana_dashboard.json`  
**Mounted to**: `/etc/grafana/provisioning/dashboards/db.json`  
**Purpose**: Auto-provisioned dashboard

---

## Production Configuration Changes

### Required for Production

1. **Secrets Management**:
   ```yaml
   # Use environment variables from secrets
   environment:
     - DATABASE_URL=${DATABASE_URL}  # From Vault/AWS Secrets Manager
     - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
   ```

2. **Remove Dev Ports**:
   ```yaml
   # Remove external database port
   # db:
   #   ports:
   #     - "5432:5432"  # Remove in production
   ```

3. **Resource Limits**:
   - Add limits to all services
   - Scale based on load

4. **SSL/TLS**:
   - Use reverse proxy (nginx/traefik)
   - Configure SSL certificates
   - Enable HTTPS only

5. **Monitoring**:
   - Configure external Prometheus
   - Set up alerting (PagerDuty/Opsgenie)
   - Configure log aggregation

---

## Configuration Validation

### Validate Compose File

```bash
cd infra
docker compose config > /dev/null && echo "✅ Valid" || echo "❌ Invalid"
```

### Validate Environment Variables

```bash
# Check required variables are set
docker compose config | grep -E "DATABASE_URL|REDIS_URL|MINIO_URL"
```

### Validate Health Checks

```bash
# Check all health checks pass
docker compose ps | grep -v "healthy\|running" && echo "⚠️ Some services unhealthy"
```

---

**Last Updated**: 2025-01-27  
**Review Frequency**: Quarterly or when adding new services

