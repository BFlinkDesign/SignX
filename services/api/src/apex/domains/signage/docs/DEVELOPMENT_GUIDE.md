# APEX Signage Engineering Solvers - Development Guide

## How to Add a New Solver Function

### 1. Define Function Signature

```python
from apex.domains.signage.solver_versioning import solver_version
from apex.domains.signage.models import YourInput, YourOutput

@solver_version("1.0.0")
@validate_call
def your_new_solver(
    input: YourInput,
    seed: int = 0,
    warnings_list: Optional[List[str]] = None,
) -> YourOutput:
    """
    Your solver description.
    
    Args:
        input: Input parameters
        seed: Random seed for determinism
        warnings_list: Optional warnings list
    
    Returns:
        Output result
    
    References:
        Code reference (e.g., AISC 360-16 Chapter X)
    """
    warnings_list = warnings_list or []
    
    # Input validation
    _validate_positive(input.value, "value")
    
    # Calculation
    result = your_calculation(input)
    
    # Sanity checks
    if result > threshold:
        warnings_list.append("Result exceeds threshold")
    
    return YourOutput(
        result=round(result, 2),  # Round to 2 decimals
    )
```

### 2. Maintain Determinism

- Use `seed` parameter for any random operations
- Round outputs to 2 decimals
- Use deterministic sorting (hash-based tie-breaking)
- Document any non-deterministic assumptions

### 3. Handle Edge Cases

```python
from apex.domains.signage.edge_cases_advanced import abstain_with_recommendation

# Detect edge case
if is_edge_case(input):
    return abstain_with_recommendation(
        edge_case_type="extreme_wind",
        reason="Wind speed exceeds design limits",
        recommendation="Requires engineering review",
        confidence=0.0,
    )
```

### 4. Write Tests

```python
def test_your_new_solver_basic():
    """Test basic functionality."""
    result = your_new_solver(YourInput(value=10.0), seed=42)
    assert result.result > 0

def test_your_new_solver_edge_case():
    """Test edge case handling."""
    with pytest.raises(ValueError):
        your_new_solver(YourInput(value=-5.0))

def test_your_new_solver_deterministic():
    """Test determinism."""
    result1 = your_new_solver(YourInput(value=10.0), seed=42)
    result2 = your_new_solver(YourInput(value=10.0), seed=42)
    assert result1.result == result2.result
```

### 5. Update Documentation

- Add to `EQUATIONS.md` with code reference
- Update `ARCHITECTURE.md` if algorithm choice is significant
- Add to solver version registry

## Maintaining Determinism

### Rules

1. **Same inputs + same seed → same outputs**
2. **Round all outputs to 2 decimals**
3. **Use seeded random number generators**
4. **Hash-based tie-breaking for sorts**

### Example

```python
import random
import numpy as np

random.seed(seed)
np.random.seed(seed)

# Deterministic sort
items.sort(key=lambda x: (x.value, hash(x.name + str(seed)) % 10000))
```

## Handling Edge Cases

### Abstain Pattern

```python
if edge_case_detected:
    return abstain_with_recommendation(
        edge_case_type="soil",
        reason="Layered soil profile requires geotechnical analysis",
        recommendation="Obtain geotechnical report",
        confidence=0.0,
    )
```

### Warning Pattern

```python
if unusual_but_acceptable:
    warnings_list.append("Unusual configuration detected")
    # Continue with lower confidence
    confidence = max(0.0, confidence - 0.1)
```

## Writing Tests

### Unit Tests

```python
def test_function_name_scenario():
    """Clear description of what's tested."""
    # Arrange
    input = YourInput(...)
    
    # Act
    result = your_function(input)
    
    # Assert
    assert result.property == expected_value
```

### Property-Based Tests

```python
def test_monotonicity():
    """Property: Output increases with input."""
    for x1, x2 in [(5.0, 10.0), (10.0, 20.0)]:
        r1 = your_function(YourInput(value=x1))
        r2 = your_function(YourInput(value=x2))
        assert r2.result >= r1.result
```

### Integration Tests

```python
async def test_solver_api_endpoint():
    """Test solver via API."""
    response = await client.post("/endpoint", json={...})
    assert response.status_code == 200
    assert "result" in response.json()
```

## Performance Considerations

1. **Target Latency**: <100ms p95 for real-time derives
2. **Caching**: Use LRU cache for repeated calculations
3. **Vectorization**: Use numpy arrays where possible
4. **Profiling**: Profile with cProfile if slow

## Code Style

- Type hints: All functions typed
- Docstrings: Include references to codes
- Validation: Use `@validate_call` and helper functions
- Rounding: All outputs rounded to 2 decimals
- Error messages: Clear and actionable

