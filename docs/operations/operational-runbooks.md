# Operational Runbooks

Complete incident response and operational procedures for SIGN X Studio Clone.

## Table of Contents

1. [Incident Response Framework](#incident-response-framework)
2. [Incident Scenarios](#incident-scenarios)
3. [Backup & Restore Procedures](#backup--restore-procedures)
4. [Scaling Guide](#scaling-guide)
5. [Maintenance Windows](#maintenance-windows)

## Incident Response Framework

### Severity Levels

| Severity | Description | Response Time | Escalation |
|----------|-------------|---------------|------------|
| **P0 - Critical** | Service down, data loss | 15 minutes | Immediate |
| **P1 - High** | Degraded performance, partial outage | 1 hour | On-call |
| **P2 - Medium** | Non-critical issues, warnings | 4 hours | Business hours |
| **P3 - Low** | Minor issues, improvements | Next day | Backlog |

### On-Call Rotation

- **Primary**: 24/7 coverage
- **Secondary**: Backup for critical incidents
- **Escalation**: Engineering lead for P0/P1

### Communication Channels

- **Slack**: #apex-oncall
- **PagerDuty**: Critical alerts
- **Status Page**: https://status.example.com
- **Email**: ops@example.com

## Incident Scenarios

### Scenario 1: API Service Down

**Symptoms:**
- Health endpoint returns 503
- All API requests failing
- Error rate 100%

**Diagnosis Steps:**

1. **Check Service Status**
   ```bash
   # Kubernetes
   kubectl get pods -n apex | grep api
   kubectl describe pod <pod-name> -n apex
   
   # Docker Compose
   docker compose ps api
   docker compose logs api --tail=100
   ```

2. **Check Health Endpoints**
   ```bash
   curl -v http://api.example.com/health
   curl -v http://api.example.com/ready
   ```

3. **Review Logs**
   ```bash
   # Kubernetes
   kubectl logs -n apex deployment/apex-api --tail=500 | grep ERROR
   
   # Docker Compose
   docker compose logs api --tail=500 | grep ERROR
   ```

**Resolution Steps:**

1. **Restart Service**
   ```bash
   # Kubernetes
   kubectl rollout restart deployment/apex-api -n apex
   kubectl rollout status deployment/apex-api -n apex
   
   # Docker Compose
   docker compose restart api
   ```

2. **Scale Up (if needed)**
   ```bash
   kubectl scale deployment apex-api -n apex --replicas=5
   ```

3. **Check Dependencies**
   ```bash
   # Database
   kubectl exec -n apex deployment/apex-api -- curl -v $APEX_DATABASE_URL
   
   # Redis
   kubectl exec -n apex deployment/apex-api -- redis-cli -u $APEX_REDIS_URL ping
   ```

4. **Verify Recovery**
   ```bash
   for i in {1..10}; do
     curl -f http://api.example.com/health && echo "OK" || echo "FAIL"
     sleep 2
   done
   ```

**Post-Incident:**
- Review logs for root cause
- Update runbook if new issue
- Document incident in post-mortem

---

### Scenario 2: Database Connection Pool Exhausted

**Symptoms:**
- `apex_pg_pool_used` metric at limit
- Database connection errors in logs
- Slow API responses

**Diagnosis Steps:**

1. **Check Pool Metrics**
   ```bash
   curl http://api.example.com/metrics | grep pg_pool
   ```

2. **Check Database Connections**
   ```sql
   SELECT count(*) as connections, state
   FROM pg_stat_activity
   WHERE datname = 'apex'
   GROUP BY state;
   ```

3. **Identify Long-Running Queries**
   ```sql
   SELECT pid, now() - pg_stat_activity.query_start AS duration, query
   FROM pg_stat_activity
   WHERE datname = 'apex' AND state = 'active'
   ORDER BY duration DESC
   LIMIT 10;
   ```

**Resolution Steps:**

1. **Scale Workers**
   ```bash
   kubectl scale deployment apex-worker -n apex --replicas=5
   ```

2. **Kill Long-Running Queries**
   ```sql
   -- Identify and kill (be careful!)
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE datname = 'apex'
   AND state = 'active'
   AND now() - query_start > interval '5 minutes';
   ```

3. **Increase Pool Size**
   ```python
   # In db.py - temporary fix
   _engine = create_async_engine(
       settings.DATABASE_URL,
       pool_size=30,  # Increase from 20
       max_overflow=15,  # Increase from 10
   )
   ```

4. **Add Database Indexes**
   ```sql
   -- Review slow queries and add indexes
   CREATE INDEX CONCURRENTLY idx_projects_status ON projects(status);
   CREATE INDEX CONCURRENTLY idx_payloads_project_id ON project_payloads(project_id);
   ```

**Prevention:**
- Monitor pool usage continuously
- Set alert at 80% capacity
- Review query patterns regularly

---

### Scenario 3: Derive Solver Timeout

**Symptoms:**
- `/signage/common/cabinets/derive` endpoint timing out
- 504 Gateway Timeout errors
- Worker logs show timeout errors

**Diagnosis Steps:**

1. **Check Endpoint Performance**
   ```bash
   # Time the request
   time curl -X POST http://api.example.com/signage/common/cabinets/derive \
     -H "Content-Type: application/json" \
     -d '{"overall_height_ft": 30.0, "cabinets": [...]}'
   ```

2. **Review Solver Logs**
   ```bash
   kubectl logs -n apex deployment/apex-api --tail=500 | grep derive
   ```

3. **Check Worker Queue**
   ```bash
   redis-cli -h prod-redis LLEN celery
   redis-cli -h prod-redis LRANGE celery 0 10
   ```

**Resolution Steps:**

1. **Increase Timeout**
   ```yaml
   # k8s/base/ingress.yaml
   annotations:
     nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
     nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
   ```

2. **Optimize Solver**
   ```python
   # Review solver performance
   # Check for inefficient loops or calculations
   # Add caching for repeated calculations
   ```

3. **Move to Async Processing**
   ```bash
   # For long-running derives, use Celery
   celery_task_id = enqueue_cabinet_derive(payload)
   # Return task ID, poll for result
   ```

4. **Add Circuit Breaker**
   ```python
   # In solver code
   if not breaker_allow("derive"):
       return make_envelope(
           result=None,
           assumptions=["Solver overloaded, please retry"],
           confidence=0.3
       )
   ```

**Prevention:**
- Set reasonable timeout limits
- Monitor solver performance
- Add performance benchmarks

---

### Scenario 4: MinIO Storage Full

**Symptoms:**
- File uploads failing
- `503 Service Unavailable` from MinIO
- Storage metrics showing 100% usage

**Diagnosis Steps:**

1. **Check Storage Usage**
   ```bash
   # MinIO client
   mc du s3/apex-uploads
   
   # Or via API
   curl http://minio:9000/minio/admin/v3/info
   ```

2. **Identify Large Files**
   ```bash
   mc ls --recursive s3/apex-uploads | sort -k5 -n | tail -20
   ```

3. **Check Lifecycle Policies**
   ```bash
   mc ilm ls s3/apex-uploads
   ```

**Resolution Steps:**

1. **Cleanup Old Files**
   ```bash
   # Delete files older than 90 days
   mc find s3/apex-uploads --older-than 90d --exec "mc rm {}"
   
   # Delete old report versions
   mc find s3/apex-uploads/blobs --older-than 30d --exec "mc rm {}"
   ```

2. **Archive to Glacier**
   ```bash
   # Move old files to archive tier
   mc ilm add s3/apex-uploads --transition-days 30 --storage-class GLACIER
   ```

3. **Expand Storage**
   ```bash
   # If using MinIO in K8s, scale PVC
   kubectl patch pvc minio-data -n apex -p '{"spec":{"resources":{"requests":{"storage":"500Gi"}}}}'
   ```

4. **Verify Recovery**
   ```bash
   # Test upload
   curl -X POST http://api.example.com/files/presign \
     -H "Content-Type: application/json" \
     -d '{"filename": "test.pdf"}'
   ```

**Prevention:**
- Set up lifecycle policies
- Monitor storage usage (alert at 80%)
- Regular cleanup jobs

---

### Scenario 5: High Error Rate

**Symptoms:**
- Error rate >5% (P0 threshold)
- Multiple endpoints failing
- Alerting triggered

**Diagnosis Steps:**

1. **Check Error Metrics**
   ```bash
   curl http://api.example.com/metrics | grep http_requests_total | grep "status=\"5"
   ```

2. **Identify Failing Endpoints**
   ```bash
   kubectl logs -n apex deployment/apex-api --tail=1000 | \
     grep ERROR | awk '{print $NF}' | sort | uniq -c | sort -rn
   ```

3. **Review Error Patterns**
   ```bash
   kubectl logs -n apex deployment/apex-api --tail=5000 | \
     grep -E "ERROR|Exception" | head -50
   ```

**Resolution Steps:**

1. **Check Dependencies**
   ```bash
   # Database
   kubectl exec -n apex deployment/apex-api -- \
     psql $APEX_DATABASE_URL -c "SELECT 1"
   
   # Redis
   kubectl exec -n apex deployment/apex-api -- \
     redis-cli -u $APEX_REDIS_URL ping
   ```

2. **Scale Services**
   ```bash
   kubectl scale deployment apex-api -n apex --replicas=5
   kubectl scale deployment apex-worker -n apex --replicas=3
   ```

3. **Enable Circuit Breakers**
   ```python
   # Temporarily enable circuit breakers for external services
   # Reduce load on failing dependencies
   ```

4. **Rollback Deployment**
   ```bash
   # If recent deployment, rollback
   kubectl rollout undo deployment/apex-api -n apex
   ```

**Post-Incident:**
- Root cause analysis
- Fix identified issues
- Update monitoring alerts

---

### Scenario 6: Redis Connection Failures

**Symptoms:**
- Cache misses increasing
- Celery tasks not processing
- Redis connection errors

**Diagnosis Steps:**

1. **Check Redis Status**
   ```bash
   kubectl get pods -n apex | grep redis
   redis-cli -h prod-redis ping
   ```

2. **Check Connection Count**
   ```bash
   redis-cli -h prod-redis INFO clients
   ```

3. **Review Redis Logs**
   ```bash
   kubectl logs -n apex deployment/redis --tail=100
   ```

**Resolution Steps:**

1. **Restart Redis**
   ```bash
   kubectl rollout restart statefulset/redis -n apex
   ```

2. **Clear Connection Pool**
   ```bash
   # Kill idle connections
   redis-cli -h prod-redis CLIENT LIST | grep idle | awk '{print $2}' | \
     xargs -I {} redis-cli -h prod-redis CLIENT KILL {}
   ```

3. **Scale Redis**
   ```bash
   # If using ElastiCache, scale up
   aws elasticache modify-replication-group \
     --replication-group-id prod-redis \
     --cache-node-type cache.r6g.large
   ```

---

### Scenario 7: OpenSearch Outage

**Symptoms:**
- Search queries failing
- `search_fallback: true` in responses
- High fallback rate

**Diagnosis Steps:**

1. **Check OpenSearch Health**
   ```bash
   curl http://search:9200/_cluster/health
   ```

2. **Check Fallback Metrics**
   ```bash
   curl http://api.example.com/metrics | grep search_fallback
   ```

3. **Review Search Logs**
   ```bash
   kubectl logs -n apex deployment/opensearch --tail=100
   ```

**Resolution Steps:**

1. **OpenSearch Should Auto-Fallback**
   ```python
   # System automatically falls back to DB
   # No immediate action needed
   ```

2. **Restart OpenSearch**
   ```bash
   kubectl rollout restart statefulset/opensearch -n apex
   ```

3. **Re-index Data**
   ```bash
   # Once OpenSearch recovers
   kubectl exec -n apex deployment/apex-api -- \
     python scripts/reindex_projects.py
   ```

**Prevention:**
- OpenSearch is optional (DB fallback works)
- Monitor fallback rate (alert if >20%)
- Regular health checks

---

### Scenario 8: Certificate Expiration

**Symptoms:**
- SSL/TLS errors
- Certificate warnings in browser
- cert-manager alerts

**Diagnosis Steps:**

1. **Check Certificate Status**
   ```bash
   kubectl get certificate -n apex
   kubectl describe certificate apex-api-tls -n apex
   ```

2. **Check Expiry**
   ```bash
   echo | openssl s_client -servername api.example.com -connect api.example.com:443 2>/dev/null | \
     openssl x509 -noout -dates
   ```

**Resolution Steps:**

1. **Force Certificate Renewal**
   ```bash
   kubectl delete certificate apex-api-tls -n apex
   kubectl apply -f k8s/base/certificate.yaml
   ```

2. **Verify Renewal**
   ```bash
   kubectl wait --for=condition=Ready certificate apex-api-tls -n apex --timeout=5m
   ```

3. **Test HTTPS**
   ```bash
   curl -v https://api.example.com/health
   ```

**Prevention:**
- Automated certificate rotation (see scripts/rotate-certificates.sh)
- Monitor certificate expiry (alert at 30 days)
- Use Let's Encrypt auto-renewal

---

## Backup & Restore Procedures

### Daily Automated Backups

#### Database Backup

```bash
#!/bin/bash
# scripts/backup-database.sh

set -e

BACKUP_DIR="/backups/database"
DATE=$(date +%Y%m%d)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Full backup
pg_dump -h prod-db -U apex_admin apex | \
  gzip > "$BACKUP_DIR/apex_full_${TIMESTAMP}.sql.gz"

# Keep only last 30 days
find "$BACKUP_DIR" -name "apex_full_*.sql.gz" -mtime +30 -delete

echo "Backup completed: apex_full_${TIMESTAMP}.sql.gz"
```

#### Automated Backup Cron

```yaml
# k8s/base/backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
  namespace: apex
spec:
  schedule: "0 2 * * *"  # 2 AM daily
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:15-alpine
              command:
                - /bin/sh
                - -c
                - |
                  pg_dump -h $DB_HOST -U $DB_USER $DB_NAME | \
                    gzip > /backups/apex_$(date +%Y%m%d_%H%M%S).sql.gz
                  # Upload to S3
                  aws s3 cp /backups/*.sql.gz s3://apex-backups/database/
              env:
                - name: DB_HOST
                  valueFrom:
                    secretKeyRef:
                      name: apex-secrets
                      key: APEX_DATABASE_URL
              volumeMounts:
                - name: backup-storage
                  mountPath: /backups
          volumes:
            - name: backup-storage
              persistentVolumeClaim:
                claimName: backup-storage
          restartPolicy: OnFailure
```

### Point-in-Time Recovery

#### Enable WAL Archiving

```yaml
# PostgreSQL configuration
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://apex-backups/wal/%f'
```

#### Restore to Point in Time

```bash
#!/bin/bash
# scripts/restore-pitr.sh

RECOVERY_TIME=$1  # Format: 2025-01-27 14:30:00

if [ -z "$RECOVERY_TIME" ]; then
  echo "Usage: $0 'YYYY-MM-DD HH:MM:SS'"
  exit 1
fi

# Restore base backup
gunzip < /backups/apex_full_20250127.sql.gz | psql -h prod-db -U apex_admin apex

# Configure recovery
cat > /tmp/recovery.conf <<EOF
restore_command = 'aws s3 cp s3://apex-backups/wal/%f %p'
recovery_target_time = '$RECOVERY_TIME'
EOF

# Restore WAL files
pg_basebackup -D /restore -Ft -z -P
# Apply WAL files until recovery target time
```

### Test Restore Procedure

#### Quarterly DR Drill

```bash
#!/bin/bash
# scripts/dr-drill.sh

set -e

echo "=== Disaster Recovery Drill ==="
echo "Date: $(date)"
echo ""

# 1. Restore to staging
echo "1. Restoring database to staging..."
STAGING_DB="staging-db"
BACKUP_FILE=$(ls -t /backups/apex_full_*.sql.gz | head -1)
gunzip < "$BACKUP_FILE" | psql -h $STAGING_DB -U apex_admin apex

# 2. Verify data integrity
echo "2. Verifying data integrity..."
psql -h $STAGING_DB -U apex_admin apex -c "SELECT COUNT(*) FROM projects;"
psql -h $STAGING_DB -U apex_admin apex -c "SELECT COUNT(*) FROM project_payloads;"

# 3. Test application
echo "3. Testing application..."
curl -f http://staging.example.com/health || exit 1

# 4. Run smoke tests
echo "4. Running smoke tests..."
pytest tests/e2e/ -v

echo ""
echo "=== DR Drill Complete ==="
echo "RTO: <4 hours"
echo "RPO: <15 minutes"
```

## Scaling Guide

### Horizontal Scaling

#### Add API Replicas

```bash
# Kubernetes
kubectl scale deployment apex-api -n apex --replicas=5

# Verify
kubectl get pods -n apex | grep api
```

#### Load Balancer Configuration

```yaml
# k8s/base/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: apex-api
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
spec:
  type: LoadBalancer
  ports:
    - port: 80
      targetPort: 8000
  selector:
    app: apex-api
```

### Vertical Scaling

#### Database Sizing

```bash
# RDS instance type upgrade
aws rds modify-db-instance \
  --db-instance-identifier prod-db \
  --db-instance-class db.r5.xlarge \
  --apply-immediately
```

#### Worker Memory Limits

```yaml
# k8s/base/worker-deployment.yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"  # Increase from 1Gi
    cpu: "2000m"
```

### Auto-Scaling

#### HPA Configuration

```yaml
# k8s/base/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: apex-api-hpa
  namespace: apex
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: apex-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 50
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 30
        - type: Pods
          value: 2
          periodSeconds: 30
      selectPolicy: Max
```

#### Queue-Based Scaling

```yaml
# k8s/base/keda-scaler.yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: apex-worker-scaler
  namespace: apex
spec:
  scaleTargetRef:
    name: apex-worker
  minReplicaCount: 2
  maxReplicaCount: 10
  triggers:
    - type: redis
      metadata:
        address: prod-redis:6379
        listName: celery
        listLength: "100"  # Scale when queue > 100
```

## Maintenance Windows

### Zero-Downtime Migration Strategy

#### Pre-Migration Checklist

- [ ] Notify users of maintenance window
- [ ] Verify backup is current
- [ ] Test migration on staging
- [ ] Prepare rollback plan
- [ ] Monitor setup ready

#### Migration Steps

1. **Enable Maintenance Mode (Read-Only)**
   ```bash
   kubectl set env deployment/apex-api -n apex MAINTENANCE_MODE=readonly
   ```

2. **Perform Migration**
   ```bash
   # Database migration
   kubectl exec -n apex deployment/apex-api -- \
     alembic upgrade head
   ```

3. **Verify Migration**
   ```bash
   # Check migration status
   kubectl exec -n apex deployment/apex-api -- \
     alembic current
   
   # Run smoke tests
   pytest tests/smoke/ -v
   ```

4. **Disable Maintenance Mode**
   ```bash
   kubectl set env deployment/apex-api -n apex MAINTENANCE_MODE-
   ```

5. **Monitor**
   ```bash
   # Watch metrics for 30 minutes
   watch -n 5 'curl -s http://api.example.com/metrics | grep http_requests_total'
   ```

#### Rollback Procedure

```bash
# If issues detected
kubectl exec -n apex deployment/apex-api -- \
  alembic downgrade -1

# Verify rollback
kubectl exec -n apex deployment/apex-api -- \
  alembic current
```

---

**Next Steps:**
- [**Monitoring & Observability**](monitoring-observability.md) - Advanced monitoring setup
- [**Security Hardening**](../security/security-hardening.md) - Security procedures
- [**Disaster Recovery**](disaster-recovery.md) - DR plan

