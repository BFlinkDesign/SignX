# APEX Disaster Recovery Runbook

**Document Version:** 1.0.0
**Last Updated:** 2026-01-22
**Owner:** DevOps Engineering
**Classification:** CONFIDENTIAL - Internal Use Only

---

## Executive Summary

This runbook provides step-by-step procedures for recovering the APEX platform from various disaster scenarios. All team members should be familiar with these procedures before an incident occurs.

---

## 1. Recovery Objectives

### 1.1 RTO/RPO Targets by Scenario

| Scenario | RTO | RPO | Priority |
|----------|-----|-----|----------|
| Single pod/container failure | 30 seconds | 0 | P4 |
| Single node failure | 5 minutes | 0 | P3 |
| Database primary failure | 5 minutes | 0 | P2 |
| Single AZ failure | 15 minutes | 0 | P2 |
| Complete region failure | 4 hours | 15 minutes | P1 |
| Data corruption (detected quickly) | 1 hour | 15 minutes | P1 |
| Ransomware/security breach | 4 hours | 24 hours | P0 |

### 1.2 Critical Services Priority

1. **Database** - All operations depend on data availability
2. **API Service** - Core business functionality
3. **SignCalc Engine** - Calculation processing
4. **Worker Service** - Background job processing
5. **Frontend** - User interface
6. **Monitoring** - Observability

---

## 2. Pre-Incident Preparation

### 2.1 DR Environment Checklist

Verify monthly:

- [ ] DR region infrastructure is provisioned and up-to-date
- [ ] Database read replica in DR region is syncing (<1 min lag)
- [ ] Container images are replicated to DR registry
- [ ] DNS failover is configured and tested
- [ ] SSL certificates are valid in DR region
- [ ] Secrets are available in DR Vault instance
- [ ] Monitoring is configured for DR environment
- [ ] Team has access to DR environment

### 2.2 Access Requirements

Ensure these credentials are available offline:

- AWS IAM credentials with DR access
- Kubernetes admin kubeconfig for DR cluster
- Database master credentials
- Vault unseal keys
- DNS management access
- Communication channels (backup Slack, phone tree)

---

## 3. Incident Response Procedures

### 3.1 Initial Assessment

**Time limit: 5 minutes**

```bash
# 1. Check primary region status
kubectl get nodes -o wide
kubectl get pods -n apex-prod -o wide

# 2. Check database status
kubectl exec -it apex-db-0 -n apex-prod -- pg_isready

# 3. Check external connectivity
curl -fsS https://api.apex.example.com/health

# 4. Check monitoring
# Grafana: https://grafana.apex.example.com
# PagerDuty: Check incident timeline
```

**Decision Matrix:**

| Symptom | Action |
|---------|--------|
| Single pod unhealthy | Let Kubernetes auto-heal, monitor |
| Multiple pods unhealthy | Investigate node/network issue |
| Node unhealthy | Cordon and drain, replace node |
| Database unreachable | Check DB pod, initiate failover if needed |
| Entire region unreachable | Initiate DR failover |

---

## 4. Scenario: Database Primary Failure

**Estimated Recovery Time: 5-10 minutes**

### 4.1 Automatic Failover (Preferred)

If using managed database (RDS/Cloud SQL), automatic failover should occur.

```bash
# Monitor failover progress
watch -n 5 'aws rds describe-db-instances --db-instance-identifier apex-prod \
  --query "DBInstances[0].{Status:DBInstanceStatus,Endpoint:Endpoint.Address}"'

# Verify application reconnection
kubectl logs -f deployment/apex-api -n apex-prod | grep -i database
```

### 4.2 Manual Failover

If automatic failover fails:

```bash
# 1. Promote read replica
aws rds promote-read-replica --db-instance-identifier apex-prod-replica

# 2. Wait for promotion (2-5 minutes)
aws rds wait db-instance-available --db-instance-identifier apex-prod-replica

# 3. Update application configuration
kubectl set env deployment/apex-api \
  DATABASE_HOST=apex-prod-replica.xxxxx.rds.amazonaws.com \
  -n apex-prod

# 4. Restart deployments
kubectl rollout restart deployment -n apex-prod

# 5. Verify connectivity
kubectl exec -it deployment/apex-api -n apex-prod -- \
  python -c "from apex.api.deps import get_db; print('DB OK')"
```

### 4.3 Post-Failover Tasks

- [ ] Investigate root cause of primary failure
- [ ] Create new read replica for future failover
- [ ] Update DNS if endpoint changed
- [ ] Notify stakeholders
- [ ] Document incident timeline

---

## 5. Scenario: Complete Region Failure

**Estimated Recovery Time: 4 hours**

### 5.1 Decision to Failover

Make this decision if:
- Primary region is confirmed unavailable
- Cloud provider status page shows region outage
- No ETA for recovery OR ETA > 4 hours
- Business impact justifies failover

**Authorization required from:** Engineering Manager or CTO

### 5.2 Failover Procedure

#### Step 1: Verify DR Readiness (10 minutes)

```bash
# Switch to DR cluster context
export KUBECONFIG=~/.kube/config-dr
kubectl config use-context apex-dr

# Verify DR cluster health
kubectl get nodes
kubectl get pods -n apex-prod

# Check database replica status
aws rds describe-db-instances \
  --region us-west-2 \
  --db-instance-identifier apex-dr \
  --query "DBInstances[0].{Status:DBInstanceStatus,ReplicaLag:StatusInfos}"

# Verify recent backup availability
aws s3 ls s3://apex-backups-dr/postgres/wal/ --region us-west-2 | tail -5
```

#### Step 2: Promote DR Database (15 minutes)

```bash
# Promote DR replica to primary
aws rds promote-read-replica \
  --db-instance-identifier apex-dr \
  --region us-west-2

# Wait for promotion
aws rds wait db-instance-available \
  --db-instance-identifier apex-dr \
  --region us-west-2

# Verify database is writable
psql -h apex-dr.xxxxx.us-west-2.rds.amazonaws.com \
  -U apex -d apex \
  -c "INSERT INTO health_check (timestamp) VALUES (NOW());"
```

#### Step 3: Update Application Configuration (10 minutes)

```bash
# Update secrets with DR database endpoint
kubectl create secret generic apex-db-secret \
  --from-literal=host=apex-dr.xxxxx.us-west-2.rds.amazonaws.com \
  --from-literal=password=${DB_PASSWORD} \
  -n apex-prod \
  --dry-run=client -o yaml | kubectl apply -f -

# Update ConfigMap with DR endpoints
kubectl apply -f infra/k8s/dr/configmap-dr.yaml -n apex-prod
```

#### Step 4: Scale Up DR Services (15 minutes)

```bash
# Scale up application pods
kubectl scale deployment apex-api --replicas=3 -n apex-prod
kubectl scale deployment apex-worker --replicas=3 -n apex-prod
kubectl scale deployment apex-signcalc --replicas=3 -n apex-prod
kubectl scale deployment apex-frontend --replicas=2 -n apex-prod

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=apex -n apex-prod --timeout=300s

# Verify deployments
kubectl get deployments -n apex-prod
```

#### Step 5: Update DNS (5 minutes)

```bash
# Update Route53 to point to DR region
# Option A: Automatic (if health checks configured)
# Health checks should automatically fail over

# Option B: Manual DNS update
aws route53 change-resource-record-sets \
  --hosted-zone-id ${HOSTED_ZONE_ID} \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.apex.example.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z1H1FL5HABSF5",
          "DNSName": "apex-dr-alb.us-west-2.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'

# Verify DNS propagation
dig api.apex.example.com +short
```

#### Step 6: Verify Application Health (15 minutes)

```bash
# Health checks
curl -fsS https://api.apex.example.com/health
curl -fsS https://api.apex.example.com/ready

# Functional verification
curl -fsS https://api.apex.example.com/api/v1/status

# Run smoke tests
cd tests && python -m pytest smoke/ -v --maxfail=3

# Check logs for errors
kubectl logs -f deployment/apex-api -n apex-prod --since=5m | grep -i error
```

#### Step 7: Communication (Throughout)

```bash
# Update status page
# URL: https://status.apex.example.com/admin

# Notify stakeholders
# - Engineering team: #engineering Slack
# - Support team: #support Slack
# - Executives: Direct message
# - Customers: Status page update + email for major accounts
```

### 5.3 Post-Failover Checklist

- [ ] All services healthy in DR region
- [ ] DNS fully propagated (check from multiple locations)
- [ ] Monitoring shows traffic in DR region
- [ ] No elevated error rates
- [ ] Customer-facing communication sent
- [ ] Incident ticket created with timeline
- [ ] Schedule post-mortem within 48 hours

---

## 6. Scenario: Data Corruption

**Estimated Recovery Time: 1-4 hours depending on scope**

### 6.1 Identify Corruption Scope

```bash
# Check for obvious corruption signs
psql -c "SELECT relname, n_dead_tup FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 10;"

# Identify affected time range from logs
kubectl logs deployment/apex-api -n apex-prod --since=24h | grep -i "integrity\|corrupt\|constraint"

# Identify affected tables
psql -c "SELECT schemaname, tablename, last_analyze, last_vacuum
         FROM pg_stat_user_tables
         WHERE last_analyze < NOW() - INTERVAL '1 day';"
```

### 6.2 Point-in-Time Recovery

```bash
# 1. Identify safe recovery point (before corruption)
RECOVERY_TIME="2026-01-22 09:00:00 UTC"

# 2. Create recovery instance
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier apex-prod \
  --target-db-instance-identifier apex-pitr-recovery \
  --restore-time "${RECOVERY_TIME}" \
  --db-instance-class db.r5.large

# 3. Wait for instance
aws rds wait db-instance-available --db-instance-identifier apex-pitr-recovery

# 4. Verify recovered data
psql -h apex-pitr-recovery.xxxxx.rds.amazonaws.com -U apex -d apex \
  -c "SELECT COUNT(*) FROM projects;"

# 5. Compare with corrupted data to assess impact
# ... custom verification queries based on affected tables ...

# 6. If recovery point is good, perform switchover
# Follow steps from Section 4.2 Manual Failover
```

### 6.3 Selective Table Recovery

For corruption limited to specific tables:

```bash
# 1. Export affected tables from PITR instance
pg_dump -h apex-pitr-recovery.xxxxx.rds.amazonaws.com \
  -U apex -d apex \
  -t affected_table \
  -F custom -f /tmp/affected_table.dump

# 2. On production, rename corrupted table
psql -c "ALTER TABLE affected_table RENAME TO affected_table_corrupted;"

# 3. Restore table
pg_restore -h apex-prod.xxxxx.rds.amazonaws.com \
  -U apex -d apex \
  -t affected_table \
  /tmp/affected_table.dump

# 4. Verify
psql -c "SELECT COUNT(*) FROM affected_table;"
psql -c "SELECT COUNT(*) FROM affected_table_corrupted;"

# 5. After verification, drop corrupted table
psql -c "DROP TABLE affected_table_corrupted;"
```

---

## 7. Scenario: Security Breach / Ransomware

**CRITICAL: Do not skip any steps**

### 7.1 Immediate Actions (First 15 minutes)

```bash
# 1. ISOLATE - Block all external access
# Update security groups to deny all traffic
aws ec2 authorize-security-group-ingress \
  --group-id sg-apex-prod \
  --protocol -1 \
  --cidr 0.0.0.0/0 \
  --rule-description "EMERGENCY: Block all traffic"

# 2. PRESERVE - Take snapshots of everything
aws rds create-db-snapshot \
  --db-instance-identifier apex-prod \
  --db-snapshot-identifier apex-incident-$(date +%s)

aws ec2 create-snapshot \
  --volume-id vol-xxx \
  --description "Incident snapshot $(date +%s)"

# 3. NOTIFY - Security team and management
# Call security hotline: [PHONE NUMBER]
# Page CTO if after hours
```

### 7.2 Assessment Phase

**DO NOT attempt recovery until security team approves**

- Identify attack vector
- Determine scope of compromise
- Check for data exfiltration
- Review audit logs
- Engage incident response team if needed

### 7.3 Recovery (Only after security approval)

```bash
# Restore from KNOWN GOOD backup (pre-incident)
# Use offline/immutable backup if available

# 1. Create clean environment
# Deploy to new, isolated cluster

# 2. Restore from verified clean backup
# Verify backup integrity before restore

# 3. Apply security patches
# Rotate ALL credentials

# 4. Gradual re-enablement
# Start with internal access only
# Enable external access only after full verification
```

---

## 8. Communication Templates

### 8.1 Internal Escalation

```
SUBJECT: [P1/P2] APEX Production Incident - [Brief Description]

IMPACT: [Number] users affected, [Service] unavailable
STARTED: [Time UTC]
CURRENT STATUS: [Investigating/Mitigating/Resolved]

TIMELINE:
- HH:MM UTC: [Event]
- HH:MM UTC: [Event]

NEXT STEPS:
- [Action] - [Owner] - [ETA]

BRIDGE: [Conference call link]
```

### 8.2 Customer Communication (Major Incident)

```
SUBJECT: APEX Service Disruption - Update [N]

We are currently experiencing a service disruption affecting [describe impact].

IMPACT: [Specific functionality affected]
STATUS: [Current status]
ETA: [Expected resolution time or "investigating"]

We will provide updates every [30 minutes/1 hour].

For urgent assistance, contact support@apex.example.com

We apologize for any inconvenience.
```

---

## 9. Post-Incident Procedures

### 9.1 Immediate (Within 24 hours)

- [ ] Verify all services fully recovered
- [ ] Review and address any data inconsistencies
- [ ] Update monitoring/alerting based on incident
- [ ] Brief summary to stakeholders

### 9.2 Short-term (Within 1 week)

- [ ] Conduct blameless post-mortem
- [ ] Document root cause analysis
- [ ] Create action items for prevention
- [ ] Update runbooks based on lessons learned

### 9.3 Long-term (Within 1 month)

- [ ] Implement prevention measures
- [ ] Conduct DR drill if not done recently
- [ ] Review and update DR documentation
- [ ] Training for team on updated procedures

---

## 10. DR Testing Schedule

| Test Type | Frequency | Last Test | Next Test |
|-----------|-----------|-----------|-----------|
| Backup restore verification | Weekly | [Date] | [Date] |
| Database failover drill | Monthly | [Date] | [Date] |
| Full DR failover drill | Quarterly | [Date] | [Date] |
| Security incident simulation | Semi-annually | [Date] | [Date] |

---

## 11. Appendices

### A. Emergency Contacts

| Role | Name | Phone | Email |
|------|------|-------|-------|
| On-call Engineer | PagerDuty | N/A | via PagerDuty |
| Engineering Manager | [Name] | [Phone] | [Email] |
| CTO | [Name] | [Phone] | [Email] |
| AWS Support | N/A | N/A | [Support Case] |
| Security Team | [Name] | [Phone] | security@apex.example.com |

### B. External Dependencies

| Service | Support Contact | SLA |
|---------|-----------------|-----|
| AWS | Premium Support | 15 min P1 |
| Supabase | support@supabase.io | 4 hour |
| Sentry | support@sentry.io | 1 day |
| PagerDuty | support@pagerduty.com | 1 hour |

### C. Critical URLs

- AWS Console: https://console.aws.amazon.com
- Status Page Admin: https://status.apex.example.com/admin
- Grafana: https://grafana.apex.example.com
- PagerDuty: https://apex.pagerduty.com
