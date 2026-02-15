# APEX Backup Procedures

**Document Version:** 1.0.0
**Last Updated:** 2026-01-22
**Owner:** DevOps Engineering

## Overview

This document details backup procedures for the APEX platform, including automated backup schedules, manual backup procedures, and verification steps.

---

## 1. Backup Schedule Summary

| Data Type | Frequency | Retention | Storage Location | Encryption |
|-----------|-----------|-----------|------------------|------------|
| PostgreSQL Full | Daily 2 AM UTC | 30 days | S3 Glacier | AES-256 |
| PostgreSQL WAL | Continuous | 7 days | S3 Standard | AES-256 |
| PostgreSQL PITR | Every 15 min | 7 days | S3 Standard | AES-256 |
| Redis RDB | Every 6 hours | 7 days | S3 Standard | AES-256 |
| MinIO/S3 Objects | Cross-region sync | Indefinite | S3 Cross-Region | AES-256 |
| Configuration | Git + Daily S3 | 1 year | S3 Glacier | AES-256 |
| Secrets (Vault) | Continuous | 30 days | Vault HA | Vault Seal |

---

## 2. PostgreSQL Backup Procedures

### 2.1 Automated Daily Full Backup

The automated backup runs via Kubernetes CronJob at 2 AM UTC daily.

**Backup Script Location:** `/home/user/SignX/infra/scripts/backup-postgres.sh`

**Manual Trigger:**
```bash
# Kubernetes
kubectl create job --from=cronjob/apex-db-backup apex-db-backup-manual-$(date +%s) -n apex-prod

# Docker Compose
docker compose -f compose.production.yaml exec db pg_dump \
  -U ${POSTGRES_USER} \
  -d ${POSTGRES_DB} \
  -F custom \
  -Z 9 \
  -f /backups/apex_$(date +%Y%m%d_%H%M%S).dump
```

**Backup Verification:**
```bash
# List recent backups
aws s3 ls s3://apex-backups-prod/postgres/daily/ --recursive | tail -10

# Verify backup integrity
pg_restore --list /backups/apex_latest.dump | head -20

# Test restore to staging (do not run in production!)
pg_restore -U apex -d apex_restore_test -F custom /backups/apex_latest.dump
```

### 2.2 Continuous WAL Archiving

WAL archiving is configured in PostgreSQL for point-in-time recovery.

**Configuration (in postgres command):**
```
archive_mode = on
archive_command = '/usr/local/bin/wal-g wal-push %p'
```

**Verify WAL archiving:**
```bash
# Check archive status
SELECT * FROM pg_stat_archiver;

# List recent WAL files
aws s3 ls s3://apex-backups-prod/postgres/wal/ | tail -20
```

### 2.3 Point-in-Time Recovery (PITR)

PITR allows restoration to any point within the retention window.

**Restore to specific time:**
```bash
# 1. Stop the current database
kubectl scale deployment apex-db --replicas=0 -n apex-prod

# 2. Create restore pod
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: postgres-restore
  namespace: apex-prod
spec:
  containers:
  - name: postgres
    image: pgvector/pgvector:pg16
    command: ["sleep", "infinity"]
    volumeMounts:
    - name: restore-data
      mountPath: /var/lib/postgresql/data
  volumes:
  - name: restore-data
    emptyDir: {}
EOF

# 3. Restore to specific time
kubectl exec -it postgres-restore -n apex-prod -- bash -c '
  wal-g backup-fetch /var/lib/postgresql/data LATEST
  cat > /var/lib/postgresql/data/recovery.signal
  cat > /var/lib/postgresql/data/postgresql.auto.conf << CONF
restore_command = "wal-g wal-fetch %f %p"
recovery_target_time = "2026-01-22 10:30:00 UTC"
recovery_target_action = "promote"
CONF
'

# 4. Start PostgreSQL and verify
kubectl exec -it postgres-restore -n apex-prod -- pg_ctl start -D /var/lib/postgresql/data

# 5. Verify data integrity
kubectl exec -it postgres-restore -n apex-prod -- psql -U apex -d apex -c "SELECT COUNT(*) FROM projects;"
```

---

## 3. Redis Backup Procedures

### 3.1 Automated RDB Snapshots

Redis creates RDB snapshots every 6 hours and on shutdown.

**Manual Snapshot:**
```bash
# Docker Compose
docker compose -f compose.production.yaml exec cache redis-cli -a ${REDIS_PASSWORD} BGSAVE

# Kubernetes
kubectl exec -it apex-cache-0 -n apex-prod -- redis-cli -a ${REDIS_PASSWORD} BGSAVE
```

**Verify Backup:**
```bash
# Check last save time
redis-cli -a ${REDIS_PASSWORD} LASTSAVE

# Copy RDB file
docker cp apex-cache:/data/dump.rdb ./backups/redis/dump_$(date +%Y%m%d_%H%M%S).rdb
```

### 3.2 Redis Restore

```bash
# 1. Stop Redis
kubectl scale statefulset apex-cache --replicas=0 -n apex-prod

# 2. Copy backup to PVC
kubectl cp ./backups/redis/dump.rdb apex-prod/apex-cache-restore:/data/dump.rdb

# 3. Start Redis
kubectl scale statefulset apex-cache --replicas=1 -n apex-prod

# 4. Verify
kubectl exec -it apex-cache-0 -n apex-prod -- redis-cli -a ${REDIS_PASSWORD} DBSIZE
```

---

## 4. Object Storage Backup

### 4.1 Cross-Region Replication

S3 cross-region replication is configured for all buckets.

**Verify Replication:**
```bash
# Check replication status
aws s3api head-object \
  --bucket apex-prod-uploads \
  --key path/to/object \
  --query 'ReplicationStatus'

# List objects in DR region
aws s3 ls s3://apex-dr-uploads/ --region us-west-2 | head -20
```

### 4.2 Manual Object Sync

```bash
# Sync to DR region
aws s3 sync s3://apex-prod-uploads s3://apex-dr-uploads --region us-west-2

# Verify sync
aws s3 ls s3://apex-prod-uploads --summarize | tail -2
aws s3 ls s3://apex-dr-uploads --region us-west-2 --summarize | tail -2
```

---

## 5. Configuration Backup

### 5.1 Automated Config Backup

All configurations are versioned in Git and backed up to S3 daily.

**Manual Config Backup:**
```bash
# Export Kubernetes configs
kubectl get configmap -n apex-prod -o yaml > configs/configmaps.yaml
kubectl get secret -n apex-prod -o yaml > configs/secrets.yaml  # Encrypted

# Export Helm values
helm get values apex -n apex-prod > configs/helm-values.yaml

# Upload to S3
aws s3 cp configs/ s3://apex-backups-prod/configs/$(date +%Y%m%d)/ --recursive
```

---

## 6. Backup Monitoring

### 6.1 Alerts

The following alerts are configured:

| Alert | Condition | Severity |
|-------|-----------|----------|
| BackupFailed | Backup job failed | Critical |
| BackupMissing | No backup in 36 hours | Warning |
| BackupSizeDrop | Backup size dropped >20% | Warning |
| WALArchivingFailed | WAL archive failed | Critical |

### 6.2 Verification Checklist

Run weekly:

- [ ] Verify daily backup exists for last 7 days
- [ ] Check backup file sizes are consistent
- [ ] Test restore to staging environment
- [ ] Verify cross-region replication lag
- [ ] Check backup encryption is working
- [ ] Review backup monitoring alerts

---

## 7. Backup Restoration Matrix

| Scenario | RTO | RPO | Procedure |
|----------|-----|-----|-----------|
| Accidental deletion | 30 min | 15 min | PITR restore |
| Database corruption | 1 hour | 15 min | PITR to before corruption |
| Full database loss | 2 hours | 24 hours | Full backup restore |
| Region failure | 4 hours | 15 min | DR region activation |
| Ransomware | 4 hours | 24 hours | Isolated restore from offsite |

---

## 8. Contacts

| Role | Contact | Availability |
|------|---------|--------------|
| Primary DBA | dba-oncall@apex.example.com | 24/7 via PagerDuty |
| Backup Owner | backup-team@apex.example.com | Business hours |
| Security (ransomware) | security@apex.example.com | 24/7 |
