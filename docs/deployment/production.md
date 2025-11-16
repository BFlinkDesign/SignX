# Production Deployment Guide

Complete guide for deploying SIGN X Studio Clone in production.

## Prerequisites

- Docker & Docker Compose (or Kubernetes)
- PostgreSQL 15+ database
- Redis 7+ cache
- MinIO or S3-compatible storage
- Domain name and SSL certificates
- Monitoring infrastructure (Prometheus, Grafana)

## Pre-Deployment Checklist

### 1. Environment Configuration

Create `.env.prod`:

```bash
# Core
APEX_ENV=prod
APEX_SERVICE_NAME=api
APEX_APP_VERSION=0.1.0
GIT_SHA=<actual-git-sha>
GIT_DIRTY=false
BUILD_ID=<ci-build-id>

# Database
APEX_DATABASE_URL=postgresql://user:password@prod-db:5432/apex

# Cache
APEX_REDIS_URL=redis://prod-redis:6379/0

# Storage
APEX_MINIO_URL=https://s3.example.com
APEX_MINIO_ACCESS_KEY=<production-key>
APEX_MINIO_SECRET_KEY=<production-secret>
APEX_MINIO_BUCKET=apex-prod

# Search
APEX_OPENSEARCH_URL=http://prod-search:9200

# CORS
APEX_CORS_ALLOW_ORIGINS=https://app.example.com,https://admin.example.com

# Rate Limiting
APEX_RATE_LIMIT_PER_MIN=100

# Tracing
APEX_OTEL_EXPORTER=otlp
APEX_OTEL_ENDPOINT=http://jaeger:4318
```

### 2. Database Setup

```bash
# Create production database
psql -h prod-db -U postgres -c "CREATE DATABASE apex;"

# Run migrations
cd services/api
DATABASE_URL=$APEX_DATABASE_URL alembic upgrade head

# Seed initial data (if needed)
python scripts/seed_defaults.py
```

### 3. Security Configuration

#### SSL/TLS

Use reverse proxy (Nginx/Traefik) for SSL:

```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;
    
    ssl_certificate /etc/ssl/certs/api.example.com.crt;
    ssl_certificate_key /etc/ssl/private/api.example.com.key;
    
    location / {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### Secrets Management

**Option 1: Environment Variables**
```bash
# Use secrets management (AWS Secrets Manager, HashiCorp Vault, etc.)
export APEX_MINIO_SECRET_KEY=$(aws secretsmanager get-secret-value --secret-id apex/minio/key)
```

**Option 2: Docker Secrets**
```yaml
services:
  api:
    secrets:
      - minio_secret_key
secrets:
  minio_secret_key:
    external: true
```

### 4. Monitoring Setup

#### Prometheus Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'apex-api'
    scrape_interval: 15s
    static_configs:
      - targets: ['api:8000']
```

#### Grafana Dashboards

Import dashboards:
- API Performance
- Database Metrics
- Celery Queue
- System Health

### 5. Backup Configuration

#### Database Backups

```bash
# Automated daily backup
0 2 * * * pg_dump -h prod-db -U apex apex | gzip > /backups/apex-$(date +%Y%m%d).sql.gz
```

#### MinIO Backups

```bash
# Sync to backup bucket
mc mirror object/apex-prod object/apex-prod-backup
```

## Docker Compose Deployment

### Production Compose File

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  api:
    image: apex-api:${GIT_SHA}
    env_file:
      - .env.prod
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/ready"]
      interval: 10s
      timeout: 3s
      retries: 3
    networks:
      - apex-network

  worker:
    image: apex-worker:${GIT_SHA}
    env_file:
      - .env.prod
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
    depends_on:
      - cache
    networks:
      - apex-network

networks:
  apex-network:
    driver: overlay
```

### Deploy

```bash
# Build images
docker compose -f docker-compose.prod.yml build

# Tag with git SHA
docker tag apex-api:latest apex-api:${GIT_SHA}

# Push to registry
docker push registry.example.com/apex-api:${GIT_SHA}

# Deploy
docker compose -f docker-compose.prod.yml up -d
```

## Kubernetes Deployment

### Namespace Setup

```bash
kubectl create namespace apex
kubectl create secret generic apex-secrets \
  --from-env-file=.env.prod \
  -n apex
```

### Deployment Manifests

**Location**: `infra/k8s/`

#### API Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apex-api
  namespace: apex
spec:
  replicas: 2
  selector:
    matchLabels:
      app: apex-api
  template:
    metadata:
      labels:
        app: apex-api
    spec:
      containers:
      - name: api
        image: registry.example.com/apex-api:${GIT_SHA}
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: apex-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "500m"
          limits:
            memory: "512Mi"
            cpu: "1000m"
```

#### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: apex-api
  namespace: apex
spec:
  selector:
    app: apex-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Health Checks

### Liveness Probe

```bash
# Kubernetes liveness
httpGet:
  path: /health
  port: 8000
initialDelaySeconds: 30
periodSeconds: 10
```

### Readiness Probe

```bash
# Kubernetes readiness
httpGet:
  path: /ready
  port: 8000
initialDelaySeconds: 10
periodSeconds: 5
```

### Startup Probe

```bash
# Kubernetes startup (for slow-starting services)
httpGet:
  path: /health
  port: 8000
initialDelaySeconds: 0
periodSeconds: 5
failureThreshold: 12  # 60 seconds total
```

## Scaling

### Horizontal Scaling

```bash
# Docker Compose
docker compose scale api=3

# Kubernetes
kubectl scale deployment apex-api --replicas=3 -n apex
```

### Vertical Scaling

Adjust resource limits:

```yaml
resources:
  limits:
    memory: "1Gi"
    cpu: "2000m"
```

## Monitoring in Production

### Metrics Endpoint

```bash
# Prometheus scraping
curl http://api:8000/metrics
```

### Log Aggregation

**Option 1: Stdout (JSON)**
```bash
# Structured JSON logs
{"event":"request","method":"POST","path":"/projects","status":200}
```

**Option 2: OpenTelemetry**
```bash
# OTLP export
APEX_OTEL_EXPORTER=otlp
APEX_OTEL_ENDPOINT=http://jaeger:4318
```

### Alerting

Configure alerts in Prometheus:
- High error rate
- High latency
- Service down
- Database issues

## Rollback Procedure

### Docker Compose

```bash
# Rollback to previous version
docker compose -f docker-compose.prod.yml down
GIT_SHA=previous-sha docker compose -f docker-compose.prod.yml up -d
```

### Kubernetes

```bash
# Rollback deployment
kubectl rollout undo deployment/apex-api -n apex

# Check rollout status
kubectl rollout status deployment/apex-api -n apex
```

## Disaster Recovery

### Database Recovery

```bash
# Restore from backup
gunzip < /backups/apex-20250101.sql.gz | psql -h prod-db -U apex apex
```

### Service Recovery

```bash
# Restart services
docker compose restart

# Or in Kubernetes
kubectl rollout restart deployment/apex-api -n apex
```

## Performance Tuning

### Database Connection Pool

```python
# In db.py
_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)
```

### Redis Connection Pool

```python
# Configure Redis pool
Redis.from_url(
    settings.REDIS_URL,
    max_connections=50,
    decode_responses=True,
)
```

## Security Hardening

### 1. Non-Root User

```dockerfile
# In Dockerfile
RUN useradd -m -u 1000 apex
USER apex
```

### 2. Read-Only Filesystem

```yaml
# In docker-compose.yml
security_opt:
  - no-new-privileges:true
read_only: true
tmpfs:
  - /tmp
```

### 3. Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
```

### 4. Network Policies

```yaml
# Kubernetes NetworkPolicy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: apex-api-policy
spec:
  podSelector:
    matchLabels:
      app: apex-api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx
    ports:
    - protocol: TCP
      port: 8000
```

## Validation

### Post-Deployment Checks

```bash
# Health check
curl https://api.example.com/health

# Metrics endpoint
curl https://api.example.com/metrics

# API docs
open https://api.example.com/docs

# Test endpoint
curl -X POST https://api.example.com/projects \
  -H "Content-Type: application/json" \
  -d '{"account_id":"test","name":"Test","created_by":"test@example.com"}'
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose logs api
kubectl logs deployment/apex-api -n apex

# Check environment
docker compose exec api env | grep APEX_
```

### Database Connection Issues

```bash
# Test connection
docker compose exec api python -c "from apex.api.db import get_db; import asyncio; asyncio.run(get_db().__anext__())"

# Check database
psql $APEX_DATABASE_URL -c "SELECT 1;"
```

### High Memory Usage

```bash
# Check memory
docker stats
kubectl top pods -n apex

# Adjust limits
# Edit docker-compose.yml or deployment.yaml
```

## Next Steps

- [**Docker Compose Setup**](docker-compose.md) - Detailed Compose guide
- [**Kubernetes Deployment**](kubernetes.md) - K8s manifests
- [**Monitoring Guide**](../operations/monitoring.md) - Metrics and alerts

