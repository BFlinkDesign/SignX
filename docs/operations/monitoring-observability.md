# Advanced Monitoring & Observability

Complete guide to monitoring, observability, and alerting for SIGN X Studio Clone.

## Table of Contents

1. [Distributed Tracing](#distributed-tracing)
2. [Log Aggregation](#log-aggregation)
3. [Custom Dashboards](#custom-dashboards)
4. [Alerting Rules](#alerting-rules)
5. [SLO/SLA Definitions](#slosla-definitions)
6. [Error Tracking](#error-tracking)

## Distributed Tracing

### OpenTelemetry Integration

#### Configuration

```python
# services/api/src/apex/api/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

def setup_tracing():
    if settings.OTEL_EXPORTER != "otlp":
        return
    
    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.OTEL_ENDPOINT))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    
    # Auto-instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    # Auto-instrument SQLAlchemy
    SQLAlchemyInstrumentor().instrument(engine=_engine)
```

#### Manual Instrumentation

```python
# Example: Trace custom operations
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@router.post("/signage/common/cabinets/derive")
async def derive_cabinets(req: dict):
    with tracer.start_as_current_span("cabinet_derive") as span:
        span.set_attribute("cabinets.count", len(req.get("cabinets", [])))
        
        # Perform calculation
        result = calculate_cabinets(req)
        
        span.set_attribute("result.area_ft2", result["A_ft2"])
        span.set_attribute("result.weight_lb", result["weight_estimate_lb"])
        
        return result
```

#### Trace Context Propagation

```python
# Propagate trace context to external services
from opentelemetry.propagate import inject

async def call_external_api(url, data):
    headers = {}
    inject(headers)  # Add trace context to headers
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        return response
```

### Jaeger UI

Access Jaeger UI:
- **URL**: https://jaeger.example.com
- **Service**: `apex-api`
- **Tags**: `http.method`, `http.route`, `http.status_code`

## Log Aggregation

### ELK Stack Setup

#### Elasticsearch Configuration

```yaml
# k8s/base/elasticsearch.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: elasticsearch
  namespace: logging
spec:
  serviceName: elasticsearch
  replicas: 3
  template:
    spec:
      containers:
        - name: elasticsearch
          image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
          env:
            - name: discovery.type
              value: "single-node"  # Multi-node for prod
            - name: ES_JAVA_OPTS
              value: "-Xms2g -Xmx2g"
          volumeMounts:
            - name: data
              mountPath: /usr/share/elasticsearch/data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: elasticsearch-data
```

#### Logstash Configuration

```ruby
# infra/logging/logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [fields][service] == "apex-api" {
    json {
      source => "message"
    }
    
    # Parse structured logs
    if [event] {
      mutate {
        rename => { "event" => "log_event" }
      }
    }
    
    # Add geoip for IPs
    if [source_ip] {
      geoip {
        source => "source_ip"
      }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "apex-logs-%{+YYYY.MM.dd}"
  }
}
```

#### Filebeat Sidecar

```yaml
# k8s/base/filebeat-sidecar.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: filebeat
  namespace: logging
spec:
  template:
    spec:
      containers:
        - name: filebeat
          image: docker.elastic.co/beats/filebeat:8.11.0
          volumeMounts:
            - name: varlog
              mountPath: /var/log
            - name: varlibdockercontainers
              mountPath: /var/lib/docker/containers
          env:
            - name: ELASTICSEARCH_HOST
              value: "elasticsearch:9200"
      volumes:
        - name: varlog
          hostPath:
            path: /var/log
        - name: varlibdockercontainers
          hostPath:
            path: /var/lib/docker/containers
```

### Grafana Loki Alternative

```yaml
# k8s/base/loki.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: loki
  namespace: logging
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: loki
          image: grafana/loki:2.9.0
          args:
            - -config.file=/etc/loki/local-config.yaml
          volumeMounts:
            - name: config
              mountPath: /etc/loki
      volumes:
        - name: config
          configMap:
            name: loki-config
```

## Custom Dashboards

### Business Metrics Dashboard

#### Grafana Dashboard JSON

```json
{
  "dashboard": {
    "title": "APEX Business Metrics",
    "panels": [
      {
        "title": "Projects Created Today",
        "targets": [{
          "expr": "increase(apex_projects_created_total[24h])",
          "legendFormat": "Projects"
        }],
        "type": "stat",
        "gridPos": {"x": 0, "y": 0, "w": 6, "h": 4}
      },
      {
        "title": "Submission Success Rate",
        "targets": [{
          "expr": "rate(apex_projects_submitted_total{status=\"success\"}[5m]) / rate(apex_projects_submitted_total[5m]) * 100",
          "legendFormat": "Success Rate %"
        }],
        "type": "graph",
        "gridPos": {"x": 6, "y": 0, "w": 6, "h": 4}
      },
      {
        "title": "Average Calculation Time",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(apex_calc_duration_seconds_bucket[5m]))",
          "legendFormat": "P95 Latency"
        }],
        "type": "graph",
        "gridPos": {"x": 0, "y": 4, "w": 12, "h": 8}
      }
    ]
  }
}
```

### System Health Dashboard

#### Key Panels

1. **API Latency Heatmap**
   ```promql
   rate(http_request_duration_seconds_bucket[5m])
   ```

2. **Database Connection Pool**
   ```promql
   apex_pg_pool_used / apex_pg_pool_total * 100
   ```

3. **Cache Hit Rates**
   ```promql
   rate(apex_cache_hits_total[5m]) / rate(apex_cache_requests_total[5m]) * 100
   ```

## Alerting Rules

### Critical Alerts

#### API Error Rate >5%

```yaml
# infra/monitoring/alerts.yml
- alert: CriticalErrorRate
  expr: |
    rate(http_requests_total{status=~"5.."}[5m]) 
    / rate(http_requests_total[5m]) > 0.05
  for: 2m
  labels:
    severity: critical
    component: api
  annotations:
    summary: "Critical API error rate"
    description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"
    runbook_url: "https://docs.example.com/runbooks/api-errors"
```

#### Database Down

```yaml
- alert: DatabaseDown
  expr: up{job="postgres"} == 0
  for: 1m
  labels:
    severity: critical
    component: database
  annotations:
    summary: "Database is down"
    description: "PostgreSQL instance is not responding"
    runbook_url: "https://docs.example.com/runbooks/database-down"
```

#### Disk Usage >90%

```yaml
- alert: HighDiskUsage
  expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.1
  for: 5m
  labels:
    severity: critical
    component: infrastructure
  annotations:
    summary: "Disk usage critical"
    description: "Disk usage on {{ $labels.instance }} is {{ $value | humanizePercentage }}"
```

### Warning Alerts

#### P95 Latency >250ms

```yaml
- alert: HighLatency
  expr: |
    histogram_quantile(0.95, 
      rate(http_request_duration_seconds_bucket[5m])
    ) > 0.25
  for: 5m
  labels:
    severity: warning
    component: api
  annotations:
    summary: "High API latency"
    description: "P95 latency is {{ $value }}s"
```

#### Queue Lag >5min

```yaml
- alert: HighQueueLag
  expr: apex_celery_queue_age_seconds > 300
  for: 5m
  labels:
    severity: warning
    component: worker
  annotations:
    summary: "Celery queue lag"
    description: "Oldest task in queue is {{ $value }}s old"
```

#### Cache Miss Rate >50%

```yaml
- alert: HighCacheMissRate
  expr: |
    (1 - (rate(apex_cache_hits_total[5m]) / rate(apex_cache_requests_total[5m]))) > 0.5
  for: 10m
  labels:
    severity: warning
    component: cache
  annotations:
    summary: "High cache miss rate"
    description: "Cache miss rate is {{ $value | humanizePercentage }}"
```

### PagerDuty Integration

```yaml
# infra/monitoring/pagerduty-routes.yaml
route:
  receiver: 'pagerduty-critical'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty-critical'
    - match:
        severity: warning
      receiver: 'pagerduty-warning'

receivers:
  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_SERVICE_KEY}'
        description: '{{ .GroupLabels.alertname }}'
        
  - name: 'pagerduty-warning'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_SERVICE_KEY}'
        severity: 'warning'
```

## SLO/SLA Definitions

### API Availability: 99.9% Uptime

**Target**: 43 minutes/month downtime allowed

**Measurement**:
```promql
# Uptime percentage
(
  sum(rate(http_requests_total{status=~"2..|3.."}[5m])) 
  / sum(rate(http_requests_total[5m]))
) * 100
```

**Alerting**:
```yaml
- alert: SLIViolation
  expr: |
    (
      sum(rate(http_requests_total{status=~"2..|3.."}[30d])) 
      / sum(rate(http_requests_total[30d]))
    ) < 0.999
  for: 30d
  labels:
    severity: critical
    sli: "availability"
```

### Derive Response Time: P95 <200ms, P99 <500ms

**Measurement**:
```promql
# P95 latency
histogram_quantile(0.95, 
  rate(http_request_duration_seconds_bucket{endpoint="/signage/common/cabinets/derive"}[5m])
)

# P99 latency
histogram_quantile(0.99, 
  rate(http_request_duration_seconds_bucket{endpoint="/signage/common/cabinets/derive"}[5m])
)
```

**Alerting**:
```yaml
- alert: DeriveSLIViolation
  expr: |
    histogram_quantile(0.95,
      rate(http_request_duration_seconds_bucket{endpoint="/signage/common/cabinets/derive"}[5m])
    ) > 0.2
  for: 5m
  labels:
    severity: warning
    sli: "derive_latency"
```

### Report Generation: 95% Complete Within 30s

**Measurement**:
```promql
# Percentage of reports completed in <30s
histogram_quantile(0.05,
  rate(apex_report_generation_duration_seconds_bucket{le="30"}[5m])
) * 100
```

**Alerting**:
```yaml
- alert: ReportSLIViolation
  expr: |
    (
      sum(rate(apex_report_generation_duration_seconds_bucket{le="30"}[24h]))
      / sum(rate(apex_report_generation_duration_seconds_count[24h]))
    ) < 0.95
  for: 24h
  labels:
    severity: warning
    sli: "report_generation"
```

## Error Tracking

### Sentry Integration

#### Setup

```python
# services/api/src/apex/api/error_tracking.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

def setup_sentry():
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% of transactions
        environment=settings.ENV,
        release=settings.GIT_SHA,
    )
```

#### Release Tracking

```bash
# Create release in Sentry
sentry-cli releases new $GIT_SHA
sentry-cli releases set-commits $GIT_SHA --auto
sentry-cli releases finalize $GIT_SHA
```

#### Source Maps (if applicable)

```bash
# Upload source maps
sentry-cli releases files $GIT_SHA upload-sourcemaps \
  --url-prefix "https://api.example.com/static" \
  ./static/
```

### Error Aggregation

#### Error Rate by Endpoint

```promql
# Top 10 endpoints by error rate
topk(10,
  rate(http_requests_total{status=~"5.."}[5m]) 
  / rate(http_requests_total[5m])
)
```

#### Error Trends

```promql
# Error rate over time
sum(rate(http_requests_total{status=~"5.."}[5m])) by (endpoint)
```

---

**Next Steps:**
- [**Security Hardening**](../security/security-hardening.md) - Security procedures
- [**Disaster Recovery**](disaster-recovery.md) - DR plan
- [**Performance Tuning**](../performance/performance-tuning.md) - Optimization guides

