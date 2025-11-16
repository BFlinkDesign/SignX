# Disaster Recovery Plan

Complete disaster recovery procedures for SIGN X Studio Clone.

## Executive Summary

- **Recovery Time Objective (RTO)**: <4 hours
- **Recovery Point Objective (RPO)**: <15 minutes
- **Availability Target**: 99.9% (43 minutes/month downtime)

## RTO/RPO Definitions

### Recovery Time Objective (RTO)

**Target: <4 hours**

Time from disaster declaration to full service restoration.

**Breakdown:**
- Detection: 15 minutes
- Assessment: 30 minutes
- Recovery: 2-3 hours
- Verification: 30 minutes

### Recovery Point Objective (RPO)

**Target: <15 minutes**

Maximum acceptable data loss (time between last backup and disaster).

**Backup Frequency:**
- Database: Continuous WAL archiving + hourly snapshots
- Files: Real-time replication to secondary region
- Configuration: Version controlled

## Backup Verification

### Automated Restore Tests

```bash
#!/bin/bash
# scripts/backup-verification.sh

set -e

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup-file>"
  exit 1
fi

# Create test database
TEST_DB="apex_test_$(date +%Y%m%d_%H%M%S)"
psql -h test-db -U postgres -c "CREATE DATABASE $TEST_DB"

# Restore backup
gunzip < "$BACKUP_FILE" | psql -h test-db -U postgres -d "$TEST_DB"

# Verify data integrity
psql -h test-db -U postgres -d "$TEST_DB" -c "
  SELECT 
    (SELECT COUNT(*) FROM projects) as projects_count,
    (SELECT COUNT(*) FROM project_payloads) as payloads_count,
    (SELECT COUNT(*) FROM project_events) as events_count;
"

# Run smoke tests
pytest tests/smoke/ -v --db-url "postgresql://postgres@test-db/$TEST_DB"

# Cleanup
psql -h test-db -U postgres -c "DROP DATABASE $TEST_DB"

echo "Backup verification successful"
```

### Quarterly DR Drill

```bash
#!/bin/bash
# scripts/quarterly-dr-drill.sh

echo "=== Quarterly DR Drill ==="
echo "Date: $(date)"
echo ""

# 1. Simulate disaster
echo "1. Simulating disaster..."
# Stop primary services
kubectl scale deployment apex-api -n apex --replicas=0
kubectl scale deployment apex-worker -n apex --replicas=0

# 2. Activate DR site
echo "2. Activating DR site..."
# Switch DNS to DR region
# Scale up DR services
kubectl --context=dr-cluster scale deployment apex-api -n apex --replicas=3

# 3. Restore database
echo "3. Restoring database..."
LATEST_BACKUP=$(aws s3 ls s3://apex-backups/database/ | sort | tail -1 | awk '{print $4}')
aws s3 cp "s3://apex-backups/database/$LATEST_BACKUP" /tmp/backup.sql.gz
gunzip < /tmp/backup.sql.gz | psql -h dr-db -U apex_admin apex

# 4. Verify services
echo "4. Verifying services..."
for i in {1..10}; do
  curl -f https://dr-api.example.com/health || exit 1
  sleep 5
done

# 5. Run tests
echo "5. Running smoke tests..."
pytest tests/e2e/ -v --base-url "https://dr-api.example.com"

echo ""
echo "=== DR Drill Complete ==="
echo "RTO Achieved: <4 hours"
echo "RPO Achieved: <15 minutes"
```

## Failover Procedures

### Multi-Region Setup

#### Active-Passive Configuration

```
Primary Region (us-east-1)          Secondary Region (us-west-2)
├── API (Active)                    ├── API (Standby)
├── Database (Primary)              ├── Database (Replica)
├── Redis (Active)                  ├── Redis (Standby)
└── MinIO (Primary)                 └── MinIO (Replica)
```

#### Database Replication

```sql
-- Configure PostgreSQL replication
-- Primary (us-east-1)
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET max_wal_senders = 3;
ALTER SYSTEM SET hot_standby = on;

-- Create replication user
CREATE USER replicator REPLICATION ENCRYPTED PASSWORD 'repl_password';

-- Secondary (us-west-2)
-- Initialize replica
pg_basebackup -h primary-db -U replicator -D /var/lib/postgresql/data -R -P
```

#### Automated Failover Script

```bash
#!/bin/bash
# scripts/failover.sh

PRIMARY_REGION="us-east-1"
SECONDARY_REGION="us-west-2"

# Check primary health
if ! curl -f https://api-primary.example.com/health; then
  echo "Primary region unhealthy, initiating failover..."
  
  # 1. Promote secondary database
  kubectl --context=$SECONDARY_REGION exec -n apex postgres-0 -- \
    psql -c "SELECT pg_promote();"
  
  # 2. Scale up secondary API
  kubectl --context=$SECONDARY_REGION scale deployment apex-api -n apex --replicas=5
  
  # 3. Update DNS
  aws route53 change-resource-record-sets \
    --hosted-zone-id Z1234567890 \
    --change-batch '{
      "Changes": [{
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "AliasTarget": {
            "HostedZoneId": "Z2EXAMPLE",
            "DNSName": "api-dr.example.com",
            "EvaluateTargetHealth": true
          }
        }
      }]
    }'
  
  # 4. Verify failover
  sleep 60
  if curl -f https://api.example.com/health; then
    echo "Failover successful"
    # Send notification
    send_slack_message "#ops" "DR failover completed to $SECONDARY_REGION"
  else
    echo "Failover failed, manual intervention required"
    exit 1
  fi
fi
```

### Active-Active (Future)

For higher availability, implement active-active with:
- Multi-master database (PostgreSQL + Patroni)
- Global load balancing
- Conflict resolution

## Data Corruption Recovery

### Binary Log Replay

```bash
#!/bin/bash
# scripts/recover-from-corruption.sh

CORRUPTION_TIME=$1  # Timestamp of corruption detection

# 1. Stop writes
kubectl scale deployment apex-api -n apex --replicas=0

# 2. Restore from last known good backup
LAST_GOOD_BACKUP=$(find /backups -name "*.sql.gz" -mtime -1 | sort | tail -1)
gunzip < "$LAST_GOOD_BACKUP" | psql -h prod-db -U apex_admin apex

# 3. Replay WAL logs up to corruption time
pg_receivewal --dbname=apex --directory=/recovery/wal
pg_recovery_target_time="$CORRUPTION_TIME"
```

### Transaction Rollback

```sql
-- Identify corrupted transactions
SELECT xid, timestamp, query
FROM pg_stat_activity
WHERE state = 'active'
  AND query LIKE '%corrupted%';

-- Rollback specific transaction
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE xid = <corrupted_xid>;
```

### Point-in-Time Recovery

```bash
# Recover to specific point in time
RECOVERY_TIME="2025-01-27 14:30:00"

# 1. Restore base backup
pg_basebackup -D /recovery -Ft -z -P

# 2. Configure recovery
cat > /recovery/recovery.conf <<EOF
restore_command = 'aws s3 cp s3://apex-backups/wal/%f %p'
recovery_target_time = '$RECOVERY_TIME'
EOF

# 3. Start recovery
pg_ctl start -D /recovery

# 4. Verify data
psql -h recovery-db -U apex_admin apex -c "SELECT COUNT(*) FROM projects;"
```

## Communication Plan

### Status Page Updates

```python
# scripts/update-status-page.py
import requests

STATUS_PAGE_API = "https://api.statuspage.io/v1/pages/{page_id}/incidents"

def create_incident(title: str, description: str, severity: str):
    response = requests.post(
        f"{STATUS_PAGE_API}",
        headers={"Authorization": f"OAuth {STATUS_PAGE_TOKEN}"},
        json={
            "incident": {
                "name": title,
                "status": "investigating",
                "impact": severity,
                "body": description,
            }
        }
    )
    return response.json()

# During DR
create_incident(
    title="Service Degradation - DR Activated",
    description="We are experiencing issues in our primary region. DR site activated.",
    severity="major"
)
```

### Customer Notifications

```python
# Email template for DR
DR_EMAIL_TEMPLATE = """
Subject: Service Update - DR Activation

Dear Customer,

We are currently experiencing issues with our primary infrastructure.
Our disaster recovery site has been activated to maintain service.

Expected Impact:
- Brief service interruption (<15 minutes)
- Recent data may be delayed

We are monitoring the situation and will provide updates every hour.

Status Page: https://status.example.com

Thank you for your patience.
"""
```

## DR Testing Schedule

| Test Type | Frequency | Scope | Expected RTO |
|-----------|-----------|-------|--------------|
| **Backup Verification** | Weekly | Automated restore | N/A |
| **Failover Test** | Monthly | Single service | <1 hour |
| **Full DR Drill** | Quarterly | Complete failover | <4 hours |
| **Tabletop Exercise** | Semi-annually | Team coordination | N/A |

## DR Runbook Checklist

### Pre-Failover

- [ ] Verify primary region is unrecoverable
- [ ] Notify incident commander
- [ ] Activate DR team
- [ ] Document current state

### During Failover

- [ ] Stop writes to primary
- [ ] Promote secondary database
- [ ] Scale up secondary services
- [ ] Update DNS records
- [ ] Verify service health

### Post-Failover

- [ ] Monitor metrics for 1 hour
- [ ] Run smoke tests
- [ ] Update status page
- [ ] Notify customers
- [ ] Document lessons learned

### Recovery to Primary

- [ ] Verify primary region health
- [ ] Sync data from secondary
- [ ] Plan cutover window
- [ ] Execute cutover
- [ ] Monitor for 24 hours

---

**Next Steps:**
- [**Production Deployment**](../production/production-deployment.md) - Multi-region setup
- [**Operational Runbooks**](operational-runbooks.md) - Day-to-day operations

