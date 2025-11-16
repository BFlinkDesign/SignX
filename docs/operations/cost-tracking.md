# Cost Tracking & Optimization

Complete guide to tracking and optimizing infrastructure costs.

## Cost Breakdown

### AWS Cost Components

| Component | Cost Factor | Monthly Estimate |
|-----------|-------------|------------------|
| **Compute (EC2)** | $0.0832/hour (t3.xlarge) | $60 (2 instances) |
| **Database (RDS)** | $0.179/hour (db.r5.large) | $129 |
| **Cache (ElastiCache)** | $0.052/hour (cache.r6g.large) | $37 |
| **Storage (S3)** | $0.023/GB-month | $23 (1TB) |
| **Data Transfer** | $0.09/GB egress | $45 (500GB) |
| **Total** | | **$294/month** |

### GCP Cost Components

| Component | Cost Factor | Monthly Estimate |
|-----------|-------------|------------------|
| **Compute (GKE)** | $0.010995/hour | $80 |
| **Database (Cloud SQL)** | $0.00746/hour | $54 |
| **Cache (Memorystore)** | $0.054/hour | $39 |
| **Storage (Cloud Storage)** | $0.020/GB-month | $20 |
| **Data Transfer** | $0.12/GB egress | $60 |
| **Total** | | **$253/month** |

## Per-Project Cost Estimation

### Formula

```python
def estimate_project_cost(project: Project) -> dict:
    """
    Estimate infrastructure cost per project.
    
    Assumptions:
    - Average project: 10 API calls
    - Average compute time: 5 seconds
    - Average storage: 5 MB (PDF report)
    - Average data transfer: 2 MB
    """
    compute_cost = (
        project.total_compute_seconds * 0.000016667  # $/second
    )
    storage_cost = (
        project.storage_bytes / 1024**3 * 0.023 *  # $/GB-month
        (project.age_days / 30)  # Prorated for storage duration
    )
    api_cost = (
        project.api_call_count * 0.0001  # $/call
    )
    transfer_cost = (
        project.data_transfer_gb * 0.09  # $/GB
    )
    
    return {
        "compute": round(compute_cost, 4),
        "storage": round(storage_cost, 4),
        "api_calls": round(api_cost, 4),
        "data_transfer": round(transfer_cost, 4),
        "total": round(compute_cost + storage_cost + api_cost + transfer_cost, 4),
    }
```

### Tracking

```sql
-- Add cost tracking to projects table
ALTER TABLE projects ADD COLUMN cost_breakdown JSONB;

-- Update on project completion
UPDATE projects
SET cost_breakdown = jsonb_build_object(
    'compute', compute_cost,
    'storage', storage_cost,
    'api_calls', api_cost,
    'data_transfer', transfer_cost,
    'total', total_cost
)
WHERE project_id = 'proj_123';
```

## Cost Optimization

### Spot Instances (60% Savings)

```yaml
# Kubernetes node pool with spot
apiVersion: v1
kind: NodePool
metadata:
  name: spot-workers
spec:
  machineType: n1-standard-4
  spot: true
  autoscaling:
    minNodes: 0
    maxNodes: 10
  labels:
    workload: batch
    spot: "true"
```

**Use Cases:**
- Celery workers (fault-tolerant)
- Batch report generation
- Not for: API service (needs reliability)

### S3 Intelligent-Tiering

```python
# Automatically move old files to IA tier
lifecycle_config = {
    "Rules": [
        {
            "Id": "MoveOldPDFs",
            "Status": "Enabled",
            "Filter": {"Prefix": "blobs/"},
            "Transitions": [
                {
                    "Days": 30,
                    "StorageClass": "STANDARD_IA"  # 50% cheaper
                },
                {
                    "Days": 90,
                    "StorageClass": "GLACIER"  # 80% cheaper
                }
            ]
        }
    ]
}
```

**Savings**: ~50% on storage costs

### CloudFront Caching

```json
{
  "CacheBehaviors": [
    {
      "PathPattern": "/artifacts/*.pdf",
      "TargetOriginId": "apex-api",
      "CachePolicyId": "managed-caching-optimized",
      "Compress": true,
      "MinTTL": 86400
    }
  ]
}
```

**Savings**: ~80% reduction in origin requests

### Database Optimization

**Read Replicas**:
- Primary: Write operations
- Replicas: Read operations (reporting, dashboards)
- Cost: +50% for 1 replica
- Benefit: Offload read queries

**Connection Pooling**:
- Reduce connection count
- Lower database instance size
- Savings: 20-30%

### Cost Alerts

```yaml
# AWS Cost Anomaly Detection
- name: "Unexpected Cost Increase"
  threshold: 20%  # Alert if >20% increase
  dimensions:
    - Service
    - UsageType
```

## Monthly Cost Report

### Generate Report

```python
@router.get("/admin/cost-report")
async def generate_cost_report(
    month: int,
    year: int,
    db: AsyncSession = Depends(get_db),
    admin_token: str = Header(..., alias="X-Admin-Token"),
):
    await verify_admin(admin_token)
    
    # Aggregate costs
    report = {
        "period": f"{year}-{month:02d}",
        "total_cost": 0,
        "by_component": {},
        "by_project": {},
        "optimization_opportunities": [],
    }
    
    # Component costs (from AWS/GCP billing API)
    # Project costs (from database)
    
    return make_envelope(data=report, confidence=1.0)
```

---

**Next Steps:**
- [**Performance Tuning**](performance-tuning.md) - Reduce compute costs
- [**Monitoring**](monitoring-observability.md) - Track resource usage

