# CalcuSign Worker Test Suite

**Agent 5 Deliverable**: Comprehensive pytest suite for Celery worker tasks

## Test Coverage: 80%+ Target

### Test Files

1. **`test_report_generation.py`** - PDF report generation with monotonicity tests
2. **`test_pm_dispatch.py`** - PM dispatch with idempotency validation
3. **`test_email_send.py`** - Email notifications with retry logic
4. **`test_rbac.py`** - Authorization and RBAC tests
5. **`test_integration.py`** - End-to-end workflow tests

## Test Categories

### ✅ Monotonicity Tests
- Identical payloads produce identical SHA256 hashes
- Deterministic report generation
- Cache validation

### ✅ Idempotency Tests
- Same idempotency key → same result
- Duplicate submission prevention
- Redis-backed idempotency

### ✅ RBAC Tests
- Project access validation
- Submit permission checks
- Recipient authorization

### ✅ Performance Tests (SLO <200ms)
- PM dispatch timing validation
- Email send performance checks
- Retry backoff timing

### ✅ Retry Logic Tests
- Max retries enforcement
- Exponential backoff
- Failure propagation

### ✅ Integration Tests
- Full submission workflow (report → dispatch → email)
- Concurrent task execution
- Error handling

## Running Tests

```bash
# All worker tests
pytest tests/worker/

# With coverage report
pytest tests/worker/ --cov=services/worker/src --cov-report=html

# Specific category
pytest tests/worker/test_rbac.py -m rbac

# Performance tests only
pytest tests/worker/ -m performance

# Skip slow tests
pytest tests/worker/ -m "not slow"
```

## Fixtures

**`conftest.py`** provides:
- `mock_celery_app` - Eager Celery app for synchronous testing
- `artifacts_dir` - Temporary directory for test artifacts
- `sample_payload` - Valid project payload for tests
- `sample_project_data` - Valid project metadata
- `mock_redis` - Redis mock for idempotency testing
- `mock_report_generation` - Mocked report generation
- `env_vars` - Test environment variables
- `tasks_module` - Imported tasks module

## Mock Strategy

### Report Generation
- Uses async mock for `generate_report_from_payload`
- Validates SHA256 determinism
- Tests caching behavior

### PM Dispatch
- UUID-based project numbers (placeholder)
- Idempotency key validation
- Connection error simulation

### Email Send
- UUID-based message IDs (placeholder)
- Template variant testing
- Retry logic validation

## Key Validations

1. **Determinism**: Same inputs → same outputs
2. **Idempotency**: Duplicate requests are safe
3. **Authorization**: Access control enforced
4. **Performance**: SLO <200ms maintained
5. **Resilience**: Retry logic works correctly
6. **Integration**: End-to-end workflows succeed

## Coverage Targets

- **Worker tasks**: 85%+
- **Celery client**: 80%+
- **BaseTask**: 90%+
- **Overall**: 80%+ (pytest --cov-fail-under=80)

## Known Limitations

1. **External API Mocks**: PM/Email use placeholders
2. **Redis**: In-memory mock (not production Redis)
3. **Async**: Converted to sync for Celery eager mode
4. **Time**: Mock time for deterministic test results

## Agent 5 Responsibilities

- ✅ CoT test planning
- ✅ Comprehensive coverage
- ✅ Monotonicity validation
- ✅ Idempotency checks
- ✅ RBAC verification
- ✅ Performance SLOs
- ✅ Zero flakes
- ✅ REPL for task mocks

