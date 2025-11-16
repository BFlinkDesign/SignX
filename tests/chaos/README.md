# Chaos Engineering Tests

**Agent 5**: Chaos and resilience testing for CalcuSign production validation.

## Overview

Chaos tests verify that the system handles failures gracefully and maintains service availability under adverse conditions.

## Test Categories

### 1. Service Failures
- Redis down → graceful degradation
- Postgres connection loss → proper error handling
- OpenSearch unavailable → DB fallback
- MinIO timeout → graceful errors
- External API failures → circuit breakers

### 2. Network Issues
- Latency spikes → timeouts work
- Packet loss → retries work
- Connection drops → reconnection

### 3. Resource Exhaustion
- CPU saturation → health checks fail
- Memory pressure → OOM handling
- Disk full → file operations fail gracefully
- Connection pool exhausted → queuing

### 4. Dependency Failures
- External API failures → circuit breakers
- Partial data loss → recovery
- Concurrent request bursts → load handling

## Running Tests

```bash
# Run all chaos tests
pytest tests/chaos/ -v

# Run specific category
pytest tests/chaos/ -k "service_failure" -v

# Run with extended timeout
pytest tests/chaos/ -v --timeout=60
```

## Manual Chaos Tests

```bash
# Simulate Redis down
docker-compose stop cache
pytest tests/chaos/test_service_failures.py::test_redis_down -v
docker-compose start cache

# Simulate network partition
iptables -A INPUT -p tcp --dport 5432 -j DROP
pytest tests/chaos/ -v
iptables -D INPUT -p tcp --dport 5432 -j DROP
```

## Success Criteria

✅ All failures handled gracefully  
✅ No cascading failures  
✅ Circuit breakers activate  
✅ Fallbacks work correctly  
✅ No data corruption  
✅ Service maintains availability  

## Runbooks

See `tests/chaos/runbooks.md` for operational procedures.

