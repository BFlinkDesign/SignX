# SignX/APEX Infrastructure Plan

**Version:** 1.0.0
**Date:** 2026-01-22
**Author:** DevOps Engineering Team

## Executive Summary

This document outlines the complete infrastructure architecture for SignX/APEX, a structural engineering calculation system requiring high availability, data security, compliance (audit trails, PE requirements), and performance (<100ms calculation latency).

---

## 1. Container Architecture

### 1.1 Service Overview

| Service | Image | Purpose | Port | Resources |
|---------|-------|---------|------|-----------|
| api | apex-api | FastAPI REST API | 8000 | 2 CPU, 1GB |
| worker | apex-worker | Celery async workers | - | 1 CPU, 512MB |
| signcalc | apex-signcalc | Calculation engine | 8002 | 2 CPU, 2GB |
| frontend | apex-frontend | React UI | 3000 | 0.5 CPU, 256MB |
| nginx | nginx:alpine | Reverse proxy/TLS | 80/443 | 0.5 CPU, 128MB |
| db | pgvector/pgvector:pg16 | PostgreSQL + pgvector | 5432 | 2 CPU, 2GB |
| cache | redis:7-alpine | Redis cache/queue | 6379 | 0.5 CPU, 512MB |
| object | minio | S3-compatible storage | 9000 | 1 CPU, 512MB |
| search | opensearch:2.12 | Search engine | 9200 | 2 CPU, 2GB |

### 1.2 Resource Limits Strategy

```yaml
# Development: Minimal resources for local work
# Staging: 50% of production for realistic testing
# Production: Full resource allocation with headroom

# Critical Path Services (api, signcalc):
#   - Guaranteed QoS (requests = limits for k8s)
#   - Vertical autoscaling based on calculation load
#   - <100ms P95 latency target

# Background Services (worker):
#   - Burstable QoS
#   - Horizontal autoscaling based on queue depth
#   - Spot/preemptible instances acceptable
```

### 1.3 Health Check Strategy

| Service | Liveness | Readiness | Startup Grace |
|---------|----------|-----------|---------------|
| api | /health | /ready | 60s |
| signcalc | /healthz | /healthz | 30s |
| worker | Celery ping | Queue connectivity | 30s |
| db | pg_isready | pg_isready | 30s |
| cache | redis-cli ping | redis-cli ping | 10s |

---

## 2. Kubernetes Deployment

### 2.1 Helm Chart Structure

```
infra/helm/apex/
├── Chart.yaml                 # Chart metadata
├── values.yaml               # Default values
├── values-dev.yaml           # Development overrides
├── values-staging.yaml       # Staging overrides
├── values-prod.yaml          # Production overrides
├── templates/
│   ├── _helpers.tpl          # Template helpers
│   ├── namespace.yaml        # Namespace with labels
│   ├── configmap.yaml        # Non-sensitive configuration
│   ├── secret.yaml           # Secret references (external)
│   ├── api/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── hpa.yaml
│   │   └── pdb.yaml
│   ├── worker/
│   │   ├── deployment.yaml
│   │   └── hpa.yaml
│   ├── signcalc/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── hpa.yaml
│   ├── frontend/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── ingress.yaml          # Ingress configuration
│   ├── networkpolicy.yaml    # Network isolation
│   ├── serviceaccount.yaml   # RBAC
│   └── servicemonitor.yaml   # Prometheus scraping
└── tests/
    └── test-connection.yaml  # Helm test
```

### 2.2 Namespace Strategy

| Namespace | Purpose |
|-----------|---------|
| apex-dev | Development environment |
| apex-staging | Staging/QA environment |
| apex-prod | Production environment |
| apex-monitoring | Observability stack |
| apex-backup | Backup jobs and storage |

### 2.3 Horizontal Pod Autoscaling

```yaml
# API Service
- minReplicas: 2 (prod), 1 (staging/dev)
- maxReplicas: 10 (prod), 3 (staging/dev)
- targetCPUUtilization: 70%
- targetMemoryUtilization: 80%
- scaleDown.stabilizationWindowSeconds: 300

# Signcalc Service
- minReplicas: 2 (prod), 1 (staging/dev)
- maxReplicas: 20 (prod), 5 (staging)
- custom metric: calculation_queue_depth > 10

# Worker Service
- minReplicas: 2 (prod), 1 (staging/dev)
- maxReplicas: 50 (prod), 10 (staging)
- custom metric: celery_queue_depth > 100
```

### 2.4 Pod Disruption Budgets

```yaml
# Critical services: Always maintain at least 1 replica
api: minAvailable: 1
signcalc: minAvailable: 1
worker: maxUnavailable: 50%
```

---

## 3. CI/CD Pipeline

### 3.1 Pipeline Stages

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Lint     │───▶│    Test     │───▶│   Build     │───▶│   Scan      │
│   (2 min)   │    │  (10 min)   │    │   (5 min)   │    │   (3 min)   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐           │
│  Production │◀───│   Staging   │◀───│    Dev      │◀──────────┘
│  (approval) │    │  (10 min)   │    │   (5 min)   │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 3.2 Test Matrix

| Stage | Tests | Duration | Failure Action |
|-------|-------|----------|----------------|
| Lint | ruff, mypy, eslint | 2 min | Block merge |
| Unit | pytest unit/ | 3 min | Block merge |
| Integration | pytest service/ | 5 min | Block merge |
| Contract | OpenAPI, envelope | 2 min | Block merge |
| E2E | pytest e2e/ | 10 min | Block merge |
| Performance | k6 smoke | 5 min | Warning only |
| Security | Semgrep, Trivy, Gitleaks | 5 min | Block on critical |

### 3.3 Deployment Strategy

| Environment | Trigger | Strategy | Rollback |
|-------------|---------|----------|----------|
| Dev | Push to feature/* | Recreate | Automatic |
| Staging | Merge to main | Blue-Green | Automatic |
| Production | Manual approval | Canary (10%→25%→50%→100%) | Manual |

### 3.4 Rollback Procedures

```bash
# Automatic rollback triggers:
# - Health check failures for 3 consecutive minutes
# - Error rate > 5% for 2 minutes
# - P95 latency > 2s for 5 minutes

# Manual rollback commands:
helm rollback apex [REVISION] --namespace apex-prod
kubectl rollout undo deployment/api --namespace apex-prod
```

---

## 4. Environment Strategy

### 4.1 Environment Matrix

| Aspect | Development | Staging | Production |
|--------|-------------|---------|------------|
| Replicas | 1 | 2 | 3-10 (auto) |
| Database | Shared container | Dedicated RDS | Multi-AZ RDS |
| Redis | Shared container | ElastiCache | ElastiCache cluster |
| Storage | MinIO container | S3 Standard | S3 IA + Glacier |
| TLS | Self-signed | Let's Encrypt | ACM wildcard |
| Logging | stdout | CloudWatch | CloudWatch + S3 |
| Monitoring | Basic | Full stack | Full + PagerDuty |
| Backups | None | Daily | Hourly + PITR |

### 4.2 Configuration Management

```yaml
# Configuration hierarchy (highest priority first):
# 1. Environment variables (runtime)
# 2. Kubernetes ConfigMaps (deployment)
# 3. Helm values-{env}.yaml (release)
# 4. Helm values.yaml (defaults)

# Secret management:
# - Development: .env files (gitignored)
# - Staging: AWS Secrets Manager
# - Production: HashiCorp Vault
```

---

## 5. Monitoring and Observability

### 5.1 Metrics (Prometheus)

**Application Metrics:**
```
# Request metrics
http_requests_total{method, endpoint, status}
http_request_duration_seconds{method, endpoint}
http_request_size_bytes{method, endpoint}

# Calculation metrics
apex_calculation_duration_seconds{calc_type}
apex_calculation_total{calc_type, status}
apex_calculation_queue_depth

# Business metrics
apex_projects_created_total
apex_calculations_per_project
apex_active_users_gauge
```

**Infrastructure Metrics:**
```
# Database
pg_connections_active
pg_replication_lag_seconds
pg_deadlocks_total

# Cache
redis_memory_used_bytes
redis_commands_processed_total
redis_connected_clients

# Queue
celery_tasks_total{task, state}
celery_task_duration_seconds{task}
```

### 5.2 Logging (Structured JSON)

```json
{
  "timestamp": "2026-01-22T10:30:00.000Z",
  "level": "INFO",
  "service": "api",
  "trace_id": "abc123",
  "span_id": "def456",
  "user_id": "usr_789",
  "message": "Calculation completed",
  "calculation_id": "calc_001",
  "duration_ms": 45,
  "project_id": "proj_123"
}
```

**Log Retention:**
| Level | Dev | Staging | Production |
|-------|-----|---------|------------|
| DEBUG | 1 day | 3 days | N/A |
| INFO | 7 days | 14 days | 30 days |
| WARN | 14 days | 30 days | 90 days |
| ERROR | 30 days | 90 days | 1 year |

### 5.3 Tracing (OpenTelemetry)

```yaml
# Trace sampling rates:
development: 100%
staging: 50%
production: 10% (100% for errors)

# Required spans:
- HTTP request handling
- Database queries
- External API calls
- Calculation execution
- Cache operations
- Queue operations
```

### 5.4 Alerting Rules

| Alert | Severity | Condition | Action |
|-------|----------|-----------|--------|
| ServiceDown | Critical | up == 0 for 1m | PagerDuty |
| HighErrorRate | Critical | 5xx > 10% for 2m | PagerDuty |
| HighLatency | Warning | P95 > 2s for 5m | Slack |
| DatabasePoolExhausted | Critical | connections > 90% | PagerDuty |
| DiskSpaceLow | Warning | disk < 20% | Slack |
| CertificateExpiring | Warning | < 14 days | Email |

### 5.5 Grafana Dashboards

1. **Executive Overview** - SLO status, error budget, availability
2. **API Performance** - Request rate, latency, error rate
3. **Calculation Engine** - Queue depth, processing time, throughput
4. **Infrastructure** - CPU, memory, disk, network
5. **Business Metrics** - Users, projects, calculations

---

## 6. Security

### 6.1 Secrets Management

**Development:**
```bash
# .env file (gitignored)
DATABASE_URL=postgresql://apex:apex@localhost:5432/apex
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=dev-secret-key-not-for-production
```

**Staging/Production (Vault):**
```hcl
# Vault path structure
secret/apex/staging/database
secret/apex/staging/redis
secret/apex/prod/database
secret/apex/prod/redis
secret/apex/prod/encryption
```

**Kubernetes Integration:**
```yaml
# External Secrets Operator
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: apex-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: apex-secrets
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: secret/apex/prod/database
        property: url
```

### 6.2 Network Policies

```yaml
# Default deny all ingress
# Allow only:
# - Ingress controller -> API, Frontend
# - API -> Database, Redis, Search, Worker
# - Worker -> Database, Redis, API
# - Signcalc -> Database
# - Prometheus -> All (metrics only)
```

### 6.3 TLS Configuration

```yaml
# Minimum TLS 1.2
# Preferred cipher suites (in order):
# - TLS_AES_256_GCM_SHA384
# - TLS_CHACHA20_POLY1305_SHA256
# - TLS_AES_128_GCM_SHA256

# Certificate management:
# - Development: mkcert (local CA)
# - Staging: Let's Encrypt (cert-manager)
# - Production: AWS ACM or DigiCert
```

### 6.4 WAF Rules (AWS WAF / Cloudflare)

```yaml
# Rate limiting
- Rule: Global rate limit
  Threshold: 1000 requests/5min per IP

- Rule: Login rate limit
  Threshold: 10 requests/min per IP
  Path: /api/auth/*

# Common attack patterns
- Rule: SQL injection protection
- Rule: XSS protection
- Rule: Path traversal protection
- Rule: Known malicious IPs (managed list)

# Geographic restrictions (if required)
- Rule: Block non-approved countries
```

### 6.5 Container Security

```dockerfile
# Dockerfile security best practices
FROM python:3.11-slim  # Minimal base image

# Non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

# Read-only filesystem where possible
# No shell in production images
# Scan images with Trivy before deployment
```

---

## 7. Backup and Disaster Recovery

### 7.1 Backup Schedule

| Data Type | Frequency | Retention | Storage |
|-----------|-----------|-----------|---------|
| PostgreSQL Full | Daily 2 AM | 30 days | S3 Glacier |
| PostgreSQL WAL | Continuous | 7 days | S3 Standard |
| PostgreSQL PITR | Every 15 min | 7 days | S3 Standard |
| Redis RDB | Every 6 hours | 7 days | S3 Standard |
| MinIO objects | Cross-region sync | Indefinite | S3 IA |
| Configuration | Git + S3 | 1 year | S3 Glacier |

### 7.2 RTO/RPO Targets

| Scenario | RTO Target | RPO Target | Strategy |
|----------|------------|------------|----------|
| Single pod failure | 30 seconds | 0 | Auto-healing |
| Single node failure | 2 minutes | 0 | Pod rescheduling |
| Database failover | 5 minutes | 0 | Multi-AZ replica |
| AZ failure | 15 minutes | 0 | Multi-AZ deployment |
| Region failure | 4 hours | 15 minutes | Cross-region DR |
| Data corruption | 1 hour | 15 minutes | PITR restore |

### 7.3 Disaster Recovery Runbook

```bash
# DR Procedure: Complete Region Failure

# 1. Activate DR region (automated via Route53 health checks)
#    - DNS failover to DR region
#    - Estimated time: 60 seconds

# 2. Verify DR database is current
aws rds describe-db-instances --db-instance-identifier apex-dr
# Check LastReplicatedTime

# 3. Promote DR database to primary
aws rds promote-read-replica --db-instance-identifier apex-dr

# 4. Scale up DR services
kubectl scale deployment api --replicas=3 --namespace apex-prod

# 5. Verify application health
curl -f https://api.apex.example.com/health

# 6. Notify stakeholders
# Send to: #engineering, #support, engineering-leads@apex.com
```

### 7.4 Backup Encryption

```yaml
# All backups encrypted at rest
# Encryption: AES-256

# Key management:
# - KMS key for each environment
# - Key rotation: 90 days
# - Key access audit logging enabled

# Cross-account backup:
# - Backups replicated to separate AWS account
# - Different IAM roles for backup/restore
```

---

## 8. Cost Optimization

### 8.1 Resource Right-sizing

| Service | Initial | Optimized | Savings |
|---------|---------|-----------|---------|
| API | m5.large | t3.large | 30% |
| Worker | m5.xlarge | Spot c5.xlarge | 70% |
| Signcalc | c5.xlarge | c5.xlarge | 0% (compute-bound) |
| Database | db.r5.xlarge | db.r5.large + read replica | 20% |

### 8.2 Spot Instance Strategy

```yaml
# Worker nodes (non-critical, resumable):
# - 80% Spot, 20% On-Demand baseline
# - Diversified instance types (c5, c5a, c6i)
# - Capacity-optimized allocation strategy

# Mixed instance policy:
SpotAllocationStrategy: capacity-optimized
OnDemandBaseCapacity: 2
OnDemandPercentageAboveBaseCapacity: 20
```

### 8.3 Storage Tiering

```yaml
# S3 Lifecycle Rules:
calculation-results/:
  - Standard: 0-30 days
  - IA: 30-90 days
  - Glacier: 90+ days (audit requirement)

project-files/:
  - Standard: 0-90 days
  - IA: 90-365 days
  - Glacier Deep Archive: 365+ days

temporary-uploads/:
  - Standard: 0-7 days
  - Expiration: 7 days
```

### 8.4 Reserved Capacity

```yaml
# 1-year reserved instances (production baseline):
# - 2x m5.large (API)
# - 1x db.r5.large (Database primary)
# - Savings plan: Compute savings plan (flexible)
# - Estimated savings: 35-40%
```

---

## 9. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Finalize Dockerfiles with multi-stage builds
- [ ] Create Helm chart structure
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Configure development environment

### Phase 2: Staging (Week 3-4)
- [ ] Deploy to staging Kubernetes cluster
- [ ] Configure monitoring stack (Prometheus, Grafana)
- [ ] Implement backup automation
- [ ] Security hardening and scanning

### Phase 3: Production (Week 5-6)
- [ ] Deploy to production cluster
- [ ] Configure WAF and DDoS protection
- [ ] Set up cross-region DR
- [ ] Load testing and optimization

### Phase 4: Hardening (Week 7-8)
- [ ] Complete DR testing
- [ ] Chaos engineering tests
- [ ] Documentation and runbooks
- [ ] Team training

---

## 10. Contacts and Escalation

| Role | Contact | Escalation Time |
|------|---------|-----------------|
| On-call Engineer | PagerDuty rotation | Immediate |
| DevOps Lead | [TBD] | 15 minutes |
| Engineering Manager | [TBD] | 30 minutes |
| CTO | [TBD] | 1 hour (critical only) |

---

## Appendices

- A: Detailed Kubernetes Manifests
- B: CI/CD Pipeline Configuration
- C: Monitoring Dashboards JSON
- D: DR Runbook Details
- E: Security Compliance Checklist
