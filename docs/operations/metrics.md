# Metrics & KPIs Documentation

Complete guide to business and technical metrics for SIGN X Studio Clone.

## Overview

Metrics are categorized into:
- **Business Metrics**: User behavior, conversion, completion
- **Technical Metrics**: Performance, reliability, resource usage
- **Cost Metrics**: Infrastructure spending

## Business Metrics

### Daily Active Users

**Query:**
```sql
SELECT 
    DATE(created_at) as date,
    COUNT(DISTINCT created_by) as daily_active_users
FROM project_events
WHERE event_type = 'project.created'
  AND created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

**PromQL:**
```promql
# If tracking via metrics
increase(apex_users_active[1d])
```

**Target**: Track growth week-over-week

### Project Conversion Rate

**Query:**
```sql
WITH project_lifecycle AS (
    SELECT 
        project_id,
        MAX(CASE WHEN event_type = 'project.created' THEN 1 ELSE 0 END) as created,
        MAX(CASE WHEN event_type = 'project.submitted' THEN 1 ELSE 0 END) as submitted,
        MAX(CASE WHEN event_type = 'project.accepted' THEN 1 ELSE 0 END) as accepted
    FROM project_events
    WHERE created_at > NOW() - INTERVAL '30 days'
    GROUP BY project_id
)
SELECT 
    COUNT(*) as total_created,
    SUM(submitted) as total_submitted,
    SUM(accepted) as total_accepted,
    ROUND(100.0 * SUM(submitted) / COUNT(*), 2) as submission_rate,
    ROUND(100.0 * SUM(accepted) / SUM(submitted), 2) as acceptance_rate
FROM project_lifecycle;
```

**Target**: 
- Submission rate: >60%
- Acceptance rate: >80%

### Average Completion Time

**Query:**
```sql
SELECT 
    AVG(EXTRACT(EPOCH FROM (submitted_at - created_at))/3600) as avg_hours_to_submit,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (submitted_at - created_at))/3600) as median_hours
FROM (
    SELECT 
        project_id,
        MIN(CASE WHEN event_type = 'project.created' THEN timestamp END) as created_at,
        MIN(CASE WHEN event_type = 'project.submitted' THEN timestamp END) as submitted_at
    FROM project_events
    WHERE timestamp > NOW() - INTERVAL '30 days'
    GROUP BY project_id
    HAVING MIN(CASE WHEN event_type = 'project.submitted' THEN timestamp END) IS NOT NULL
) lifecycle;
```

**Target**: <24 hours average

### Stage Drop-Off Rates

**Query:**
```sql
WITH stage_reached AS (
    SELECT 
        project_id,
        MAX(CASE WHEN event_type = 'project.created' THEN 1 ELSE 0 END) as stage_0,
        MAX(CASE WHEN event_type = 'payload.saved' AND data->>'module' = 'signage.single_pole' THEN 1 ELSE 0 END) as stage_1,
        MAX(CASE WHEN event_type = 'project.submitted' THEN 1 ELSE 0 END) as stage_2
    FROM project_events
    WHERE created_at > NOW() - INTERVAL '30 days'
    GROUP BY project_id
)
SELECT 
    COUNT(*) as total,
    SUM(stage_0) as created,
    SUM(stage_1) as design_complete,
    SUM(stage_2) as submitted,
    ROUND(100.0 * SUM(stage_1) / SUM(stage_0), 2) as design_completion_rate,
    ROUND(100.0 * SUM(stage_2) / SUM(stage_1), 2) as submission_rate
FROM stage_reached;
```

### Most Common Selections

**Query:**
```sql
-- Most common pole selections
SELECT 
    payload->'config'->'selected'->'support'->>'designation' as pole,
    COUNT(*) as usage_count
FROM project_payloads
WHERE payload->'config'->'selected'->'support'->>'designation' IS NOT NULL
GROUP BY pole
ORDER BY usage_count DESC
LIMIT 10;

-- Most common footing types
SELECT 
    CASE 
        WHEN payload->'config'->'selected'->'foundation'->>'type' = 'direct_burial' THEN 'Direct Burial'
        WHEN payload->'config'->'selected'->'foundation'->>'type' = 'baseplate' THEN 'Baseplate'
    END as footing_type,
    COUNT(*) as usage_count
FROM project_payloads
GROUP BY footing_type
ORDER BY usage_count DESC;
```

## Technical Metrics

### API Request Distribution

**PromQL:**
```promql
# Requests by endpoint
sum(rate(http_requests_total[5m])) by (endpoint)

# Top 10 endpoints
topk(10, sum(rate(http_requests_total[5m])) by (endpoint))
```

**Grafana Query:**
```promql
sum(rate(http_requests_total{job="apex-api"}[5m])) by (endpoint)
```

### Solver Performance

**Metrics:**
```promql
# Derive loads latency
histogram_quantile(0.95,
  rate(apex_solver_duration_seconds_bucket{solver="derive_loads"}[5m])
)

# Filter poles latency
histogram_quantile(0.95,
  rate(apex_solver_duration_seconds_bucket{solver="filter_poles"}[5m])
)

# Footing solve latency
histogram_quantile(0.95,
  rate(apex_solver_duration_seconds_bucket{solver="footing_solve"}[5m])
)
```

**Targets:**
- Derive loads: P95 <200ms
- Filter poles: P95 <100ms
- Footing solve: P95 <150ms

### Database Query Performance

**Query:**
```sql
-- Top 10 slowest queries
SELECT 
    query,
    calls,
    mean_exec_time,
    total_exec_time,
    (total_exec_time / calls) as avg_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

**PromQL:**
```promql
# Via postgres_exporter
pg_stat_statements_mean_exec_time{datname="apex"}
```

**Target**: All queries <50ms (p95)

### Cache Hit Rates

**PromQL:**
```promql
# Overall cache hit rate
rate(redis_hits_total[5m]) / (rate(redis_hits_total[5m]) + rate(redis_misses_total[5m]))

# By cache type
rate(redis_hits_total{cache_type="wind_data"}[5m]) / 
  (rate(redis_hits_total{cache_type="wind_data"}[5m]) + 
   rate(redis_misses_total{cache_type="wind_data"}[5m]))
```

**Target**: >80% overall hit rate

### Error Rate

**PromQL:**
```promql
# Error rate by endpoint
rate(http_requests_total{status=~"5.."}[5m]) / 
  rate(http_requests_total[5m]) by (endpoint)

# Overall error rate
sum(rate(http_requests_total{status=~"5.."}[5m])) / 
  sum(rate(http_requests_total[5m]))
```

**Target**: <1% error rate

## Storage Growth

### MinIO Usage Trends

**Query:**
```bash
# Check bucket size
mc du s3/apex-uploads

# Growth over time
mc du --recursive s3/apex-uploads | awk '{total+=$1} END {print total}'
```

**Monitoring:**
```promql
# If MinIO exposes metrics
minio_bucket_size_bytes{bucket="apex-uploads"}
```

### Cleanup Recommendations

```python
# Script: scripts/storage_cleanup.py
async def recommend_cleanup():
    # Find old files (>90 days, not referenced)
    old_files = await db.execute(
        select(ProjectFile).where(
            ProjectFile.created_at < datetime.now(timezone.utc) - timedelta(days=90),
            ~exists(
                select(1).where(
                    ProjectPayload.files.contains([ProjectFile.blob_key])
                )
            )
        )
    )
    
    total_size = sum(f.size_bytes for f in old_files.scalars())
    
    return {
        "files_to_delete": len(old_files.scalars()),
        "size_bytes": total_size,
        "size_gb": total_size / 1024**3,
    }
```

## Cost Tracking

### AWS Cost Breakdown

```python
# Cost estimation per project
def estimate_project_cost(project: Project) -> dict:
    compute_time = project.total_compute_seconds
    storage_size = project.storage_bytes
    api_calls = project.api_call_count
    
    return {
        "compute": compute_time * 0.000016667,  # $0.000016667/second
        "storage": storage_size / 1024**3 * 0.023,  # $0.023/GB-month
        "api_calls": api_calls * 0.0001,  # $0.0001/call
        "data_transfer": project.data_transfer_gb * 0.09,  # $0.09/GB
        "total": ...,
    }
```

### GCP Cost Breakdown

Similar structure with GCP pricing:
- Compute Engine: $0.010995/hour
- Cloud Storage: $0.020/GB-month
- Cloud SQL: $0.00746/hour

### Cost Optimization Recommendations

1. **Use Spot Instances** (60% savings)
   ```yaml
   # Kubernetes node pool with spot
   nodePool:
     machineType: n1-standard-4
     spot: true
   ```

2. **S3 Intelligent-Tiering** (50% savings for old files)
   ```python
   # Move old PDFs to IA tier
   lifecycle_config = {
       "Rules": [{
           "Status": "Enabled",
           "Transitions": [{
               "Days": 30,
               "StorageClass": "STANDARD_IA"
           }]
       }]
   }
   ```

3. **CloudFront Caching** (Reduce egress costs)
   - Cache PDF reports at edge
   - Reduce origin requests by 80%+

## Grafana Dashboard Queries

### Business Dashboard

```promql
# Projects created today
increase(apex_projects_created_total[1d])

# Submission success rate
rate(apex_projects_submitted_total{status="success"}[5m]) / 
  rate(apex_projects_submitted_total[5m])

# Average confidence
avg_over_time(apex_project_confidence[1h])
```

### System Health Dashboard

```promql
# Request rate
sum(rate(http_requests_total[5m])) by (method, status)

# Latency heatmap
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

---

**Next Steps:**
- [**Monitoring & Observability**](monitoring-observability.md) - Full monitoring setup
- [**Performance Tuning**](performance-tuning.md) - Optimization guides

