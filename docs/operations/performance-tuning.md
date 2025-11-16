# Performance Tuning Guide

Complete guide for optimizing SIGN X Studio Clone performance.

## Table of Contents

1. [Database Optimization](#database-optimization)
2. [Caching Strategy](#caching-strategy)
3. [CDN Setup](#cdn-setup)
4. [Worker Tuning](#worker-tuning)
5. [Frontend Optimization](#frontend-optimization)

## Database Optimization

### Index Recommendations

From query analysis (Agent 3):

```sql
-- High-traffic queries
CREATE INDEX idx_projects_user_status 
ON projects(user_id, status, created_at DESC);

CREATE INDEX idx_payloads_project_module 
ON project_payloads(project_id, module);

CREATE INDEX idx_events_project_time 
ON project_events(project_id, created_at DESC);

-- Optimistic locking
CREATE INDEX idx_projects_etag ON projects(etag);

-- JSONB queries
CREATE INDEX idx_payloads_stages 
ON project_payloads USING GIN(payload);

-- Partial indexes
CREATE INDEX idx_active_projects 
ON projects(status) 
WHERE status IN ('draft', 'estimating');
```

### Query Optimization Examples

#### Before Optimization

```sql
-- Slow query: 250ms
SELECT * FROM projects 
WHERE user_id = 'user_123' 
  AND status = 'draft'
ORDER BY created_at DESC;
```

**EXPLAIN ANALYZE:**
```
Seq Scan on projects (cost=0.00..1250.00 rows=50 width=200)
  Filter: (user_id = 'user_123' AND status = 'draft')
  Planning Time: 0.5ms
  Execution Time: 250ms
```

#### After Optimization

```sql
-- Fast query: 5ms
-- With index: idx_projects_user_status
SELECT * FROM projects 
WHERE user_id = 'user_123' 
  AND status = 'draft'
ORDER BY created_at DESC;
```

**EXPLAIN ANALYZE:**
```
Index Scan using idx_projects_user_status (cost=0.42..125.00 rows=50 width=200)
  Index Cond: (user_id = 'user_123' AND status = 'draft')
  Planning Time: 0.2ms
  Execution Time: 5ms
```

### Connection Pool Sizing

**Formula:**
```
pool_size = (CPU_cores × 2) + effective_spindle_count
max_overflow = pool_size × 0.5
```

**Example:**
```python
# 4 CPU cores, SSD (effective_spindle_count = 1)
pool_size = (4 × 2) + 1 = 9
max_overflow = 9 × 0.5 = 4

_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=9,
    max_overflow=4,
    pool_pre_ping=True,
)
```

### Query Timeout

```sql
-- Set timeout for long-running queries
ALTER DATABASE apex SET statement_timeout = '30s';
```

### Materialized Views

```sql
-- Dashboard statistics
CREATE MATERIALIZED VIEW project_stats AS
SELECT 
    user_id,
    status,
    COUNT(*) as project_count,
    AVG(confidence) as avg_confidence,
    SUM((cost_snapshot->>'total')::numeric) as total_cost
FROM projects
GROUP BY user_id, status;

-- Refresh periodically (cron job)
REFRESH MATERIALIZED VIEW CONCURRENTLY project_stats;
```

## Caching Strategy

### Redis Cache Warming

```python
# scripts/cache_warm.py
async def warm_cache():
    # Pre-load frequently accessed data
    
    # Wind data cache (TTL: 24 hours)
    popular_locations = [
        (32.7767, -96.7970),  # Dallas
        (40.7128, -74.0060),  # NYC
        (34.0522, -118.2437), # LA
    ]
    for lat, lon in popular_locations:
        wind_data = await resolve_wind_speed(lat, lon)
        cache_key = f"wind:{lat}:{lon}"
        await redis.setex(
            cache_key,
            86400,  # 24 hours
            json.dumps(wind_data)
        )
    
    # Pole options cache (TTL: 1 hour)
    common_loads = [1000.0, 1200.0, 1500.0]  # kip-in
    for M_kipin in common_loads:
        options = await filter_poles(M_kipin, material="steel")
        cache_key = f"poles:steel:{M_kipin}"
        await redis.setex(cache_key, 3600, json.dumps(options))
```

### Cache Invalidation Patterns

#### On Project Update

```python
@router.put("/projects/{project_id}")
async def update_project(...):
    # Update project
    await update_project_internal(project_id, updates)
    
    # Invalidate caches
    await redis.delete(f"project:{project_id}")
    await redis.delete(f"project:{project_id}:payload")
    
    # Invalidate search index
    await opensearch.delete(f"projects/{project_id}")
```

#### Time-Based Invalidation

```python
# TTL recommendations
CACHE_TTLS = {
    "wind_data": 86400,      # 24 hours
    "pole_options": 3600,    # 1 hour
    "pricing": 3600,         # 1 hour
    "project": 300,           # 5 minutes
    "envelope": 86400,       # 24 hours (content_sha256-based)
}
```

### Cache Hit Rate Monitoring

```promql
# Cache hit ratio
rate(redis_hits_total[5m]) / (rate(redis_hits_total[5m]) + rate(redis_misses_total[5m]))
```

**Target**: >80% hit rate

## CDN Setup

### CloudFront Configuration

```json
{
  "DistributionConfig": {
    "Origins": [
      {
        "Id": "apex-api",
        "DomainName": "api.example.com",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "https-only"
        }
      }
    ],
    "DefaultCacheBehavior": {
      "TargetOriginId": "apex-api",
      "ViewerProtocolPolicy": "redirect-to-https",
      "CachePolicyId": "managed-caching-optimized",
      "Compress": true
    },
    "CacheBehaviors": [
      {
        "PathPattern": "/artifacts/*",
        "TargetOriginId": "apex-api",
        "CachePolicyId": "managed-caching-optimized-for-gzip",
        "Compress": true,
        "MinTTL": 86400  # 24 hours for PDFs
      }
    ]
  }
}
```

### Cache-Control Headers

```python
# Set appropriate headers
@router.get("/artifacts/{path:path}")
async def get_artifact(path: str):
    response = FileResponse(f"/artifacts/{path}")
    
    # PDF reports: Cache for 24 hours
    if path.endswith(".pdf"):
        response.headers["Cache-Control"] = "public, max-age=86400"
        response.headers["ETag"] = compute_file_etag(path)
    
    return response
```

### CloudFlare Alternative

```yaml
# CloudFlare Page Rules
rules:
  - url: "api.example.com/artifacts/*"
    cache_level: "Cache Everything"
    edge_cache_ttl: 86400
```

## Worker Tuning

### Celery Concurrency

**Formula:**
```
worker_concurrency = CPU_count × 2  # For I/O bound tasks
worker_concurrency = CPU_count      # For CPU bound tasks
```

**Configuration:**
```python
# For I/O bound (report generation, API calls)
celery worker -A apex.worker.app --concurrency=8

# For CPU bound (calculations)
celery worker -A apex.worker.app --concurrency=4
```

### Prefetch Multiplier

```python
# services/worker/src/apex/worker/app.py
app.conf.update(
    worker_prefetch_multiplier=4,  # Prefetch 4 tasks per worker
    task_acks_late=True,
    worker_max_tasks_per_child=1000,  # Restart after 1000 tasks
)
```

**Tuning:**
- **I/O bound**: Higher prefetch (4-8)
- **CPU bound**: Lower prefetch (1-2)

### Task Routing

```python
# Route heavy tasks to dedicated workers
app.conf.task_routes = {
    'projects.report.generate': {'queue': 'heavy'},
    'projects.email.send': {'queue': 'light'},
}

# Start workers
celery worker -A apex.worker.app -Q heavy --concurrency=2
celery worker -A apex.worker.app -Q light --concurrency=8
```

## Frontend Optimization

### Bundle Size Reduction

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'canvas-vendor': ['fabric'],
          'pdf-vendor': ['react-pdf'],
        },
      },
    },
  },
});
```

### Code Splitting

```typescript
// Lazy load stage components
const OverviewStage = lazy(() => import('./stages/OverviewStage'));
const SiteStage = lazy(() => import('./stages/SiteStage'));
const CabinetStage = lazy(() => import('./stages/CabinetStage'));

function StageRouter() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/overview" element={<OverviewStage />} />
        <Route path="/site" element={<SiteStage />} />
        <Route path="/cabinets" element={<CabinetStage />} />
      </Routes>
    </Suspense>
  );
}
```

### Lazy Loading Strategy

```typescript
// Load PDF viewer only when needed
const PDFPreview = lazy(() => 
  import('./components/PDFPreview').then(module => ({
    default: module.PDFPreview
  }))
);

// Load heavy calculations only when stage active
const PoleCalculator = lazy(() => 
  import('./calculators/PoleCalculator')
);
```

### React.memo Optimization

```typescript
// Memoize expensive components
const InteractiveCanvas = memo(function InteractiveCanvas({
  dimensions,
  onTransform,
}: CanvasProps) {
  // Component implementation
}, (prev, next) => {
  // Custom comparison
  return (
    prev.dimensions.width === next.dimensions.width &&
    prev.dimensions.height === next.dimensions.height
  );
});
```

### Debounce Autosave

```typescript
import { useDebouncedCallback } from 'use-debounce';

function ProjectForm() {
  const [formData, setFormData] = useState({});
  
  const debouncedSave = useDebouncedCallback(
    async (data) => {
      await api.saveProject(projectId, data);
    },
    1000  // 1 second debounce
  );
  
  const handleChange = (field: string, value: any) => {
    const newData = { ...formData, [field]: value };
    setFormData(newData);
    debouncedSave(newData);
  };
  
  return <Form onChange={handleChange} />;
}
```

### Envelope Response Caching

```typescript
// Cache by content_sha256
const envelopeCache = new Map<string, Envelope>();

async function fetchWithCache<T>(
  endpoint: string,
  request: any
): Promise<Envelope<T>> {
  // Check cache first
  const cacheKey = `${endpoint}:${JSON.stringify(request)}`;
  const cached = envelopeCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < 3600000) {  // 1 hour
    return cached;
  }
  
  // Fetch from API
  const response = await fetch(endpoint, {
    method: 'POST',
    body: JSON.stringify(request),
  });
  const envelope: Envelope<T> = await response.json();
  
  // Cache by content_sha256
  envelopeCache.set(envelope.content_sha256, envelope);
  
  return envelope;
}
```

## Performance Benchmarks

### Target Metrics

| Operation | Target | Current |
|-----------|--------|---------|
| **Project List** | <100ms | 85ms |
| **Derive Cabinets** | <200ms | 150ms |
| **Filter Poles** | <100ms | 75ms |
| **Solve Footing** | <150ms | 120ms |
| **Generate Report** | <30s | 25s |
| **File Upload** | <5s | 3s |

### Monitoring

```promql
# API latency by endpoint
histogram_quantile(0.95, 
  rate(http_request_duration_seconds_bucket[5m])
) by (endpoint)

# Database query time
histogram_quantile(0.95,
  rate(pg_stat_statements_mean_exec_time[5m])
)

# Cache hit rate
rate(redis_hits_total[5m]) / (rate(redis_hits_total[5m]) + rate(redis_misses_total[5m]))
```

---

**Next Steps:**
- [**Monitoring Guide**](monitoring-observability.md) - Performance monitoring
- [**Troubleshooting**](troubleshooting.md) - Performance issues

