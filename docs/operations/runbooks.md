# Operational Runbooks

Standard procedures for operating SIGN X Studio Clone.

## Runbook Index

1. [Service Restart](#service-restart)
2. [Database Migration](#database-migration)
3. [Backup & Restore](#backup--restore)
4. [Scaling Services](#scaling-services)
5. [Troubleshooting Production Issues](#troubleshooting-production-issues)

## Service Restart

### Restart API Service

```bash
# Docker Compose
docker compose restart api

# Kubernetes
kubectl rollout restart deployment/apex-api -n apex

# Verify
curl http://localhost:8000/health
```

### Restart All Services

```bash
# Docker Compose
docker compose restart

# Kubernetes
kubectl rollout restart deployment -n apex

# Verify all services
docker compose ps
```

### Graceful Shutdown

```bash
# Stop with timeout
docker compose stop -t 30

# Start
docker compose start
```

## Database Migration

### Apply Migrations

```bash
# Check current revision
alembic current

# Apply all pending
alembic upgrade head

# Apply specific revision
alembic upgrade <revision>

# Verify
alembic current
```

### Rollback Migration

```bash
# Rollback one revision
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision>

# Verify
alembic current
```

### Create New Migration

```bash
# Auto-generate
alembic revision --autogenerate -m "add column"

# Review generated file
# Edit if needed

# Test migration
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

## Backup & Restore

### Database Backup

```bash
# Full backup
pg_dump -h prod-db -U apex apex | gzip > backup-$(date +%Y%m%d).sql.gz

# Schema only
pg_dump -h prod-db -U apex apex --schema-only > schema.sql

# Data only
pg_dump -h prod-db -U apex apex --data-only > data.sql
```

### Database Restore

```bash
# Restore from backup
gunzip < backup-20250101.sql.gz | psql -h prod-db -U apex apex

# Verify
psql -h prod-db -U apex apex -c "SELECT COUNT(*) FROM projects;"
```

### MinIO Backup

```bash
# Sync to backup location
mc mirror object/apex-prod object/apex-prod-backup

# Verify
mc ls object/apex-prod-backup/
```

## Scaling Services

### Scale API

```bash
# Docker Compose
docker compose up -d --scale api=3

# Kubernetes
kubectl scale deployment apex-api --replicas=3 -n apex
```

### Scale Workers

```bash
# Docker Compose
docker compose up -d --scale worker=5

# Kubernetes
kubectl scale deployment apex-worker --replicas=5 -n apex
```

### Verify Scaling

```bash
# Check replicas
docker compose ps | grep api
kubectl get pods -n apex | grep api
```

## Troubleshooting Production Issues

### High Error Rate

1. **Check Metrics**
   ```bash
   curl http://localhost:8000/metrics | grep http_requests_total
   ```

2. **Check Logs**
   ```bash
   docker compose logs api | grep ERROR | tail -50
   ```

3. **Identify Pattern**
   - Specific endpoint?
   - Specific error type?
   - Time-based?

4. **Take Action**
   - Scale services
   - Rollback deployment
   - Fix root cause

### Database Connection Issues

1. **Check Pool Usage**
   ```bash
   curl http://localhost:8000/metrics | grep pg_pool
   ```

2. **Check Database**
   ```bash
   psql $APEX_DATABASE_URL -c "SELECT COUNT(*) FROM pg_stat_activity;"
   ```

3. **Restart API**
   ```bash
   docker compose restart api
   ```

### High Latency

1. **Check Duration Metrics**
   ```bash
   curl http://localhost:8000/metrics | grep duration
   ```

2. **Identify Slow Endpoints**
   - Review metrics by endpoint
   - Check database queries
   - Review external API calls

3. **Optimize**
   - Add caching
   - Optimize queries
   - Scale services

## Emergency Procedures

### Service Outage

1. **Assess Impact**
   - Check health endpoints
   - Review metrics
   - Check user reports

2. **Restart Services**
   ```bash
   docker compose restart
   ```

3. **Check Dependencies**
   - Database
   - Redis
   - External APIs

4. **Rollback if Needed**
   ```bash
   # Docker Compose
   GIT_SHA=previous-sha docker compose up -d
   
   # Kubernetes
   kubectl rollout undo deployment/apex-api -n apex
   ```

### Data Corruption

1. **Stop Services**
   ```bash
   docker compose stop
   ```

2. **Restore Backup**
   ```bash
   # Restore database
   gunzip < backup.sql.gz | psql ...
   ```

3. **Verify Data**
   ```bash
   psql -c "SELECT COUNT(*) FROM projects;"
   ```

4. **Restart Services**
   ```bash
   docker compose start
   ```

## Maintenance Windows

### Scheduled Maintenance

1. **Notify Users**
   - Maintenance window announced
   - Expected duration

2. **Backup Data**
   ```bash
   # Full backup
   pg_dump ... | gzip > pre-maintenance-$(date +%Y%m%d).sql.gz
   ```

3. **Perform Maintenance**
   - Apply updates
   - Run migrations
   - Restart services

4. **Verify**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/ready
   ```

5. **Monitor**
   - Check metrics
   - Review logs
   - Verify functionality

## Next Steps

- [**Troubleshooting Guide**](troubleshooting.md) - Common issues
- [**Monitoring Guide**](monitoring.md) - Health monitoring

