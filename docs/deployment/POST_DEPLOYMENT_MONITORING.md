# Post-Deployment Monitoring

Comprehensive monitoring plan for the first hours, days, and week after deployment.

## First Hour Checklist

**Critical Monitoring**: Check every 15 minutes

### Service Health (Every 15 minutes)

```bash
# Check all services running
docker compose ps

# Expected: All services show "running" or "healthy"
# Action if not: Check logs, restart service
```

### Log Monitoring

```bash
# Watch logs in real-time
docker compose logs -f

# Check for errors
docker compose logs --tail=100 | grep -i error

# Check for warnings
docker compose logs --tail=100 | grep -i warning
```

**Action Thresholds**:
- >10 errors/minute: Investigate immediately
- >5 warnings/minute: Monitor closely
- <5 errors/hour: Normal operation

### Endpoint Health Checks (Every 15 minutes)

```bash
# API health
curl -s http://localhost:8000/health | jq '.status'
# Expected: "ok"

# API readiness
curl -s http://localhost:8000/ready | jq '.status'
# Expected: "ready"

# Signcalc health
curl -s http://localhost:8002/healthz | jq '.status'
# Expected: "ok"

# Frontend (if health endpoint)
curl -s http://localhost:5173/health
# Expected: 200 OK
```

### Metrics Dashboard (Every 15 minutes)

**Grafana**: http://localhost:3001

**Key Metrics to Watch**:
- [ ] API latency (P95) <200ms
- [ ] Error rate <1%
- [ ] Request rate normal
- [ ] Database connection pool <80%
- [ ] Redis cache hit rate >80%
- [ ] Worker queue depth <100

**Action if metrics abnormal**: Investigate immediately

### Resource Usage (Every 15 minutes)

```bash
# Check container resource usage
docker stats --no-stream

# Watch for:
# - CPU >90%
# - Memory >90%
# - Memory leaks (gradual increase)
```

**Action Thresholds**:
- CPU >90% sustained: Scale or optimize
- Memory >90%: Check for leaks, restart if needed
- Memory leak: Investigate application code

---

## First 24 Hours

**Monitoring Frequency**: Every 4 hours

### Metrics Review (Every 4 hours)

**Dashboard Review**:
- [ ] System uptime: >99.9%
- [ ] API latency: P95 <200ms, P99 <500ms
- [ ] Error rate: <1%
- [ ] Database query performance: <50ms average
- [ ] Cache hit rate: >80%
- [ ] Worker task completion rate: >95%

**Metrics to Track**:
```bash
# Query Prometheus metrics
curl -s http://localhost:9090/api/v1/query?query=rate\(http_requests_total\[5m\]\) | jq

# Database metrics
curl -s http://localhost:9187/metrics | grep postgres

# Redis metrics
docker compose exec cache redis-cli INFO stats | grep hit_rate
```

### Disk Space Growth (Every 4 hours)

```bash
# Check disk usage
docker system df

# Check volume sizes
docker volume ls
docker volume inspect apex_pg_data | jq '.[0].Mountpoint'
du -sh <mountpoint>

# Check log file sizes
docker compose logs --tail=1000 | wc -l
```

**Action Thresholds**:
- Disk >80%: Clean up logs, old images
- Volume growth >1GB/day: Investigate
- Logs >100MB: Rotate or archive

### Memory Usage (Every 4 hours)

```bash
# Check memory usage per service
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Check for memory leaks
# Compare memory usage over time
```

**Action if memory increasing**: Investigate potential leaks

### Error Rate Tracking (Every 4 hours)

```bash
# Count errors in last 4 hours
docker compose logs --since 4h | grep -i error | wc -l

# Categorize errors
docker compose logs --since 4h | grep -i error | sort | uniq -c | sort -rn

# Track error trends
# Should decrease over time
```

**Action if error rate increasing**: Investigate immediately

### Backup Verification (Once per day)

```bash
# Check backup job ran
ls -lh infra/backups/

# Verify backup integrity
docker compose exec db psql -U apex -d apex -c "SELECT COUNT(*) FROM projects;"
# Compare with backup file if needed
```

---

## First Week

**Monitoring Frequency**: Daily reviews

### Daily Metrics Summary

**Generate Daily Report**:

```bash
# Create metrics summary script
cat > daily_metrics.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y-%m-%d)
echo "=== Daily Metrics Report: $DATE ==="
echo ""
echo "Uptime:"
docker compose ps | grep -v "NAME" | awk '{print $1, $7}'
echo ""
echo "Error Count (last 24h):"
docker compose logs --since 24h | grep -i error | wc -l
echo ""
echo "Request Count:"
curl -s http://localhost:8000/metrics | grep http_requests_total | tail -5
echo ""
echo "Disk Usage:"
docker system df
EOF

chmod +x daily_metrics.sh
./daily_metrics.sh
```

### Performance Trends

**Track Week-over-Week**:
- [ ] API latency trends (should be stable)
- [ ] Error rate trends (should decrease)
- [ ] User adoption (should increase)
- [ ] Resource usage (should stabilize)

### Database Health

```bash
# Check slow queries
docker compose exec db psql -U apex -d apex -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"

# Check index hit rate
docker compose exec db psql -U apex -d apex -c "
SELECT schemaname, tablename,
  CASE WHEN idx_scan + seq_scan = 0 THEN 0
  ELSE (idx_scan::float / (idx_scan + seq_scan)) * 100
  END as index_hit_rate_pct
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY index_hit_rate_pct ASC;
"
```

**Target**: Index hit rate >95% for all tables

### User Activity Monitoring

```bash
# Track project creation
docker compose exec db psql -U apex -d apex -c "
SELECT DATE(created_at) as date, COUNT(*) as projects
FROM projects
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
"

# Track API usage
docker compose logs --since 7d | grep "POST\|GET" | wc -l
```

---

## Ongoing Monitoring Tasks

### Weekly Reviews

**Metrics Analysis**:
- [ ] Review weekly metrics summary
- [ ] Compare with previous week
- [ ] Identify trends
- [ ] Plan optimizations

**Capacity Planning**:
- [ ] Disk usage trends
- [ ] Memory usage trends
- [ ] CPU usage trends
- [ ] Growth projections

### Monthly Reviews

**Performance Optimization**:
- [ ] Database query optimization
- [ ] Cache tuning
- [ ] Resource allocation review
- [ ] Cost optimization

**Security Review**:
- [ ] Vulnerability scans
- [ ] Access log review
- [ ] Security patch review
- [ ] Compliance check

---

## Alert Thresholds

### Critical Alerts (Immediate Action)

| Metric | Threshold | Action |
|--------|-----------|--------|
| **Uptime** | <99% | Investigate immediately |
| **Error Rate** | >5% | Rollback or hotfix |
| **P95 Latency** | >1000ms | Scale or optimize |
| **Memory Usage** | >95% | Restart or scale |
| **Disk Usage** | >90% | Clean up immediately |

### Warning Alerts (Monitor Closely)

| Metric | Threshold | Action |
|--------|-----------|--------|
| **Error Rate** | 1-5% | Monitor, investigate |
| **P95 Latency** | 200-500ms | Review queries |
| **Memory Usage** | 80-95% | Monitor for leaks |
| **Disk Usage** | 75-90% | Plan cleanup |
| **Cache Hit Rate** | <70% | Review caching strategy |

### Info Alerts (Normal Operation)

| Metric | Threshold | Action |
|--------|-----------|--------|
| **Error Rate** | <1% | Normal |
| **P95 Latency** | <200ms | Normal |
| **Memory Usage** | <80% | Normal |
| **Cache Hit Rate** | >80% | Normal |

---

## Monitoring Tools

### Grafana Dashboards

**Access**: http://localhost:3001

**Key Dashboards**:
- Executive Dashboard: High-level metrics
- Operations Dashboard: System health
- Engineering Dashboard: Detailed metrics
- Database Dashboard: Query performance

### Prometheus

**Access**: http://localhost:9090

**Key Queries**:
```promql
# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Request rate
rate(http_requests_total[5m])
```

### Log Aggregation

**View Logs**:
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api

# Filtered logs
docker compose logs api | grep ERROR
```

---

## Escalation Procedures

### If Issues Detected

1. **Immediate (P0)**:
   - Page on-call engineer
   - Start incident response
   - Consider rollback

2. **High Priority (P1)**:
   - Notify team
   - Investigate root cause
   - Deploy hotfix if needed

3. **Medium Priority (P2)**:
   - Log issue
   - Monitor closely
   - Fix in next release

---

**Last Updated**: 2025-01-27  
**Review Frequency**: Update monthly

