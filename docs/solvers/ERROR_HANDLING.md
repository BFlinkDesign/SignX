# Solver Error Handling Validation

**Last Updated**: 2024-11-01  
**Status**: ✅ Framework Documented, Testing Pending

## Overview

Comprehensive validation of error handling across all solver endpoints to ensure graceful degradation and helpful error messages.

## Error Categories

### 1. Input Validation Errors

Test invalid inputs return proper errors with clear guidance.

#### Test Cases

| Endpoint | Invalid Input | Expected Status | Expected Error | Verified |
|----------|---------------|-----------------|----------------|----------|
| Cabinet Derive | Negative dimensions | 400/422 | "width_ft must be positive" | ⚠️ PENDING |
| Cabinet Derive | Zero wind speed | 200 (uses default) | Warning in assumptions | ⚠️ PENDING |
| Pole Options | Negative moment | 400/422 | "mu_required_kipin must be positive" | ⚠️ PENDING |
| Footing Solve | Zero soil bearing | 400/422 | "soil_psf must be positive" | ⚠️ PENDING |
| Footing Solve | Negative diameter | 400/422 | "diameter_ft must be positive" | ⚠️ PENDING |
| Baseplate Checks | Missing required fields | 422 | "Field 'plate' is required" | ⚠️ PENDING |
| Site Resolve | Empty address | 400/422 | "address is required" | ⚠️ PENDING |

#### Test Commands

```bash
# Test: Invalid dimensions
curl -X POST http://localhost:8000/signage/common/cabinets/derive \
  -H "Content-Type: application/json" \
  -d '{"cabinets": [{"width_ft": -5, "height_ft": 0}]}' \
  | jq '.error'

# Expected: Clear error message with guidance
```

**Test Script:**
```python
# tests/integration/test_error_handling.py
def test_negative_dimensions():
    """Test negative dimensions return proper error."""
    resp = client.post("/signage/common/cabinets/derive", json={
        "cabinets": [{"width_ft": -5.0, "height_ft": 8.0}],
        "height_ft": 25.0
    })
    assert resp.status_code == 400 or resp.status_code == 422
    assert "positive" in resp.json()["detail"].lower()
```

**Status**: ⚠️ Needs execution

### 2. Calculation Failures

Test solvers handle unsolvable conditions gracefully.

#### Test Cases

| Scenario | Expected Behavior | Verified |
|----------|-------------------|----------|
| Impossible structural requirements | Return error with explanation, suggest alternatives | ⚠️ PENDING |
| No feasible poles found | Return empty list with warning | ⚠️ PENDING |
| Unsolvable footing depth | Return request_engineering flag | ⚠️ PENDING |
| Contradictory constraints | Return constraint error | ⚠️ PENDING |

**Test Script:**
```python
def test_no_feasible_poles():
    """Test no feasible poles returns graceful response."""
    resp = client.post("/signage/poles/options", json={
        "mu_required_kipin": 10000.0,  # Impossible
        "prefs": {"family": "HSS"}
    })
    assert resp.status_code == 200  # Returns empty list, not error
    assert len(resp.json()["result"]["options"]) == 0
    assert any("no feasible" in a.lower() for a in resp.json()["assumptions"])
```

**Status**: ⚠️ Needs execution

### 3. Service Failures

Test graceful degradation when dependencies fail.

#### Test Cases

| Scenario | Expected Behavior | Verified |
|----------|-------------------|----------|
| Database unavailable | Return cached results or graceful error | ⚠️ PENDING |
| External service timeout | Return partial results with warning | ⚠️ PENDING |
| Signcalc service down | Return error with fallback suggestion | ⚠️ PENDING |
| Redis unavailable | Continue without caching | ⚠️ PENDING |

**Test Script:**
```python
def test_database_unavailable():
    """Test graceful handling of database failure."""
    # Mock database failure
    with patch('apex.api.db.get_db', side_effect=Exception("DB unavailable")):
        resp = client.post("/projects/12345/payload", json={...})
        assert resp.status_code in [503, 500]
        assert "database" in resp.json()["error"]["message"].lower()
```

**Status**: ⚠️ Needs execution

## Error Response Format

All errors should return standardized format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Clear user-facing message",
    "details": "Technical details for debugging",
    "suggestions": ["Actionable fix 1", "Actionable fix 2"]
  },
  "trace": {
    "request_id": "uuid",
    "timestamp": "ISO8601",
    "service": "signcalc"
  }
}
```

**Current Status**: ⚠️ Needs validation

### HTTP Status Codes

| Error Type | Status Code | Usage |
|------------|-------------|-------|
| Validation Error | 422 | Invalid input format/values |
| Bad Request | 400 | Malformed request |
| Not Found | 404 | Resource not found |
| Internal Error | 500 | Unexpected server error |
| Service Unavailable | 503 | External service failure |
| Timeout | 504 | Request timeout |

**Current Status**: ⚠️ Needs validation

## Abstain Path Validation

Test that solvers properly abstain when uncertainty is high.

### Test Cases

| Scenario | Expected Behavior | Verified |
|----------|-------------------|----------|
| Extreme edge case | Return confidence=0.0 with recommendation | ⚠️ PENDING |
| Missing required data | Return abstain with data requirements | ⚠️ PENDING |
| Out of scope | Return abstain with scope explanation | ⚠️ PENDING |

**Test Script:**
```python
def test_abstain_on_edge_case():
    """Test abstain with recommendation."""
    resp = client.post("/signage/common/cabinets/derive", json={
        "cabinets": [{"width_ft": 200.0, "height_ft": 200.0}],  # Extreme
        "height_ft": 100.0
    })
    data = resp.json()
    if data["confidence"] == 0.0:
        assert "recommendation" in data or "requires_review" in data
        assert len(data["assumptions"]) > 0
```

**Status**: ⚠️ Needs execution

## Error Logging

Validate that errors are properly logged with context.

### Required Log Fields

- Request ID
- User ID (if authenticated)
- Endpoint
- Input parameters (sanitized)
- Error type
- Stack trace (for 5xx errors)
- Timestamp

**Status**: ⚠️ Needs validation

## Validation Checklist

- [ ] All error responses follow standard format
- [ ] Error messages are clear and actionable
- [ ] No stack traces exposed to users (production)
- [ ] Proper HTTP status codes used (400, 422, 500, 503)
- [ ] Errors logged with full context
- [ ] Retry-able errors identified
- [ ] Timeout handling implemented
- [ ] Graceful degradation tested
- [ ] Abstain paths validated
- [ ] Error rate monitoring configured

## Test Execution Plan

1. **Unit Tests**: Test error handling in individual solvers
2. **Integration Tests**: Test error propagation through API
3. **Load Tests**: Test error handling under load
4. **Chaos Tests**: Test service failure scenarios

## Known Error Handling Issues

| Issue | Status | Fix Plan |
|-------|--------|----------|
| Some errors don't include suggestions | ⚠️ PENDING | Add suggestion generation |
| Stack traces in dev mode | ✅ EXPECTED | Only in dev, not production |
| Timeout errors not retry-able | ⚠️ PENDING | Add retry logic |

## Action Items

- [ ] Create comprehensive error handling test suite
- [ ] Test all error paths
- [ ] Validate error response format
- [ ] Test graceful degradation
- [ ] Validate error logging
- [ ] Fix any error handling issues
- [ ] Document error codes and meanings

## Next Steps

1. **Create Test Suite**: Build comprehensive error handling tests
2. **Execute Tests**: Run all error path tests
3. **Fix Issues**: Address any error handling problems
4. **Document**: Update error codes and meanings
5. **Monitor**: Set up error rate alerts

