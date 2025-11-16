# COMPREHENSIVE CODEBASE REFACTORING PLAN

**Project:** SignX Studio - Structural Engineering Calculation Engine
**Scope:** Rigorous full-codebase refactoring
**Date:** 2025-11-02
**Standards:** Clean Code, SOLID, DDD, Python Best Practices

---

## EXECUTIVE SUMMARY

**Codebase Stats:**
- Total Files: 25+ Python modules
- Total Lines: ~7,200 LOC
- Largest Module: `solvers.py` (978 lines, 12 functions)
- Domain: Structural engineering calculations (ASCE 7-22, IBC 2024, AISC 360-22)

**Refactoring Objectives:**
1. ✅ Improve code quality and maintainability
2. ✅ Enhance type safety and validation
3. ✅ Increase testability and modularity
4. ✅ Optimize performance
5. ✅ Ensure PE-stamp compliance (determinism, audit trails)

---

## PHASE 1: ARCHITECTURAL IMPROVEMENTS (Priority: CRITICAL)

### 1.1 Domain-Driven Design (DDD) Restructuring

**Current Issue:**
- Flat module structure mixing concerns
- `solvers.py` contains multiple responsibilities (wind, poles, footings, base plates)
- No clear bounded contexts

**Refactoring:**
```
services/api/src/apex/domains/signage/
├── __init__.py
├── models/                    # Domain models (Pydantic)
│   ├── __init__.py
│   ├── site.py               # SiteLoads, Location
│   ├── sign.py               # Cabinet, SignGeometry
│   ├── loads.py              # LoadDerivation, WindLoads
│   ├── materials.py          # PoleSection, MaterialProperties
│   ├── foundation.py         # FootingConfig, BasePlateInput
│   └── results.py            # All *Result classes
│
├── services/                  # Domain services (business logic)
│   ├── __init__.py
│   ├── wind_loads.py         # ASCE 7-22 wind calculations
│   ├── load_combinations.py  # IBC 2024 load combinations
│   ├── pole_selection.py     # AISC pole filtering
│   ├── foundation_design.py  # IBC 2024 foundation calcs
│   └── base_plate_design.py  # AISC base plate checks
│
├── solvers/                   # Complete structural solvers
│   ├── __init__.py
│   ├── single_pole.py        # SinglePoleSolver class
│   ├── double_pole.py        # DoublePoleSolver class
│   ├── monument.py           # MonumentSolver class
│   └── cantilever.py         # CantileverSolver class
│
├── validators/                # Input validation
│   ├── __init__.py
│   ├── geometric.py          # Dimension validation
│   ├── engineering.py        # Engineering constraints
│   └── code_compliance.py    # Building code checks
│
├── calculators/               # Pure calculation functions
│   ├── __init__.py
│   ├── moments.py            # Moment calculations
│   ├── stresses.py           # Stress analysis
│   ├── deflections.py        # Deflection calculations
│   └── soil_mechanics.py     # Soil bearing, passive pressure
│
└── utils/                     # Shared utilities
    ├── __init__.py
    ├── units.py              # Unit conversion helpers
    ├── caching.py            # LRU cache decorators
    └── code_refs.py          # Engineering code references
```

**Benefits:**
- Clear separation of concerns
- Each module has single responsibility
- Easier to test in isolation
- Better code discoverability

**Effort:** 3-5 days
**Risk:** Medium (requires comprehensive testing)

---

### 1.2 Service Layer Pattern

**Current Issue:**
- Functions directly called by API routes
- No service layer for transaction management
- Mixed validation and business logic

**Refactoring:**
Create service classes with dependency injection:

```python
# services/wind_loads.py
from typing import Protocol

class WindLoadService:
    """ASCE 7-22 wind load calculations."""

    def __init__(self, code_version: str = "ASCE7-22"):
        self.code_version = code_version

    def calculate_velocity_pressure(
        self,
        wind_speed_mph: float,
        height_ft: float,
        exposure: Exposure,
        **kwargs
    ) -> VelocityPressureResult:
        """Calculate qz per ASCE 7-22 Equation 26.10-1."""
        # Validation
        self._validate_inputs(wind_speed_mph, height_ft)

        # Calculation
        kz = self._calculate_kz(height_ft, exposure)
        qz = self._apply_equation_26_10_1(wind_speed_mph, kz, **kwargs)

        # Return structured result
        return VelocityPressureResult(
            qz_psf=qz,
            kz=kz,
            code_ref=f"{self.code_version} Eq 26.10-1"
        )

    def _validate_inputs(self, wind_speed: float, height: float) -> None:
        """Validate inputs per ASCE 7-22 requirements."""
        if wind_speed < 85 or wind_speed > 200:
            raise ValueError(f"Wind speed {wind_speed} mph outside ASCE 7-22 range (85-200 mph)")
        if height < 0:
            raise ValueError(f"Height cannot be negative: {height} ft")

    # ... more methods
```

**Benefits:**
- Testable services with mocked dependencies
- Clear contract definitions (Protocols)
- Transaction boundaries
- Audit logging integration points

**Effort:** 2-3 days
**Risk:** Low (additive, doesn't break existing code)

---

## PHASE 2: CODE QUALITY IMPROVEMENTS (Priority: HIGH)

### 2.1 Type Safety Enhancement

**Current Issue:**
- Many `float` types instead of specific domain types
- Missing type hints in some functions
- `Unit = float` alias doesn't provide type safety

**Refactoring:**
Use NewType for domain-specific types:

```python
from typing import NewType

# Domain-specific types
Feet = NewType('Feet', float)
Inches = NewType('Inches', float)
Psf = NewType('Psf', float)  # Pounds per square foot
Ksi = NewType('Ksi', float)  # Kips per square inch
KipFt = NewType('KipFt', float)  # Kip-feet (moment)
Mph = NewType('Mph', float)  # Miles per hour

# Example usage
def calculate_moment(force_kips: Kips, arm_ft: Feet) -> KipFt:
    """Calculate moment with type safety."""
    return KipFt(force_kips * arm_ft)
```

**Use Pydantic for runtime validation:**

```python
from pydantic import Field, field_validator

class WindLoadInput(BaseModel):
    """Type-safe wind load inputs with validation."""

    wind_speed_mph: float = Field(ge=85, le=200, description="ASCE 7-22 wind speed range")
    height_ft: float = Field(gt=0, description="Height above ground")
    exposure: Literal["B", "C", "D"]

    @field_validator('wind_speed_mph')
    @classmethod
    def validate_wind_speed(cls, v: float) -> float:
        """Validate wind speed per ASCE 7-22."""
        if v < 85:
            raise ValueError(f"Wind speed {v} mph below ASCE 7-22 minimum (85 mph)")
        if v > 200:
            warnings.warn(f"Wind speed {v} mph exceeds typical ASCE 7-22 range")
        return v
```

**Benefits:**
- Catch type errors at development time
- Self-documenting code
- Better IDE autocomplete
- Runtime validation

**Effort:** 2-3 days
**Risk:** Low (mostly additive)

---

### 2.2 Error Handling Standardization

**Current Issue:**
- Inconsistent error messages
- Mix of ValueError, RuntimeError, etc.
- No structured error responses

**Refactoring:**
Create domain-specific exceptions:

```python
# exceptions.py
class SignageEngineeringError(Exception):
    """Base exception for signage engineering calculations."""

    def __init__(self, message: str, code_ref: str | None = None, **context):
        self.message = message
        self.code_ref = code_ref
        self.context = context
        super().__init__(self.formatted_message)

    @property
    def formatted_message(self) -> str:
        msg = self.message
        if self.code_ref:
            msg += f" (per {self.code_ref})"
        if self.context:
            msg += f" Context: {self.context}"
        return msg


class ValidationError(SignageEngineeringError):
    """Input validation error."""
    pass


class CalculationError(SignageEngineeringError):
    """Calculation failed to converge or produced invalid results."""
    pass


class CodeComplianceError(SignageEngineeringError):
    """Building code compliance violation."""
    pass


# Usage example
def calculate_foundation_depth(...) -> float:
    if soil_psf <= 0:
        raise ValidationError(
            message=f"Soil bearing pressure must be positive: {soil_psf} psf",
            code_ref="IBC 2024 Table 1806.2",
            soil_psf=soil_psf,
            acceptable_range="(0, 10000) psf"
        )
```

**Benefits:**
- Consistent error handling
- Better debugging information
- Structured error responses for API
- Code compliance traceability

**Effort:** 1-2 days
**Risk:** Low

---

### 2.3 Function Decomposition

**Current Issue:**
- Some functions exceed 50-100 lines
- Mixed levels of abstraction
- Hard to test individual steps

**Refactoring Example:**

**Before:**
```python
def analyze_single_pole_sign(config: SinglePoleConfig) -> SinglePoleResults:
    """300+ line function doing everything"""
    # Wind loads
    wind_result = calculate_wind_force_on_sign(...)
    wind_moment = calculate_wind_moment_at_base(...)

    # Dead loads
    dead_load_sign = config.sign_area_sqft * config.sign_weight_psf
    dead_load_pole = config.pole_section.weight_plf * config.pole_height_ft

    # Load combinations
    for lc_name, factors in IBC_LOAD_COMBINATIONS.items():
        ...

    # Structural analysis
    bending_stress_fb = (max_bending_moment * 12.0) / config.pole_section.sx_in3
    ...

    # 200 more lines...
```

**After:**
```python
class SinglePoleSolver:
    """Single-pole sign structural analysis per IBC 2024/ASCE 7-22/AISC 360-22."""

    def __init__(self, wind_service: WindLoadService, foundation_service: FoundationService):
        self.wind_service = wind_service
        self.foundation_service = foundation_service

    def analyze(self, config: SinglePoleConfig) -> SinglePoleResults:
        """Complete structural analysis."""
        # Step 1: Load analysis
        loads = self._calculate_loads(config)

        # Step 2: Load combinations
        governing_lc = self._evaluate_load_combinations(loads)

        # Step 3: Structural checks
        structural_results = self._check_structural_capacity(config, governing_lc)

        # Step 4: Foundation design
        foundation_results = self._design_foundation(config, governing_lc)

        # Step 5: Assemble results
        return self._assemble_results(loads, structural_results, foundation_results)

    def _calculate_loads(self, config: SinglePoleConfig) -> LoadResults:
        """Calculate wind and dead loads."""
        wind = self.wind_service.calculate_wind_loads(
            wind_speed=config.basic_wind_speed_mph,
            height=config.pole_height_ft,
            ...
        )

        dead_load = DeadLoadCalculator.calculate(
            sign_area=config.sign_area_sqft,
            pole_weight=config.pole_section.weight_plf,
            ...
        )

        return LoadResults(wind=wind, dead=dead_load)

    def _evaluate_load_combinations(self, loads: LoadResults) -> LoadCombinationResult:
        """Evaluate all 7 IBC 2024 load combinations."""
        return LoadCombinationService.evaluate_ibc_2024(loads)

    # ... each method is 10-20 lines, focused, testable
```

**Benefits:**
- Each method < 30 lines
- Single level of abstraction
- Easy to unit test
- Clear execution flow

**Effort:** 3-4 days
**Risk:** Medium (requires comprehensive tests)

---

## PHASE 3: TESTING IMPROVEMENTS (Priority: HIGH)

### 3.1 Comprehensive Unit Test Suite

**Current Issue:**
- Limited test coverage
- Tests not colocated with code
- Missing edge case tests

**Refactoring:**
Create comprehensive pytest suite:

```
tests/
├── unit/
│   ├── services/
│   │   ├── test_wind_loads.py
│   │   ├── test_load_combinations.py
│   │   ├── test_foundation_design.py
│   │   └── test_pole_selection.py
│   ├── calculators/
│   │   ├── test_moments.py
│   │   ├── test_stresses.py
│   │   └── test_deflections.py
│   └── validators/
│       ├── test_geometric_validation.py
│       └── test_code_compliance.py
│
├── integration/
│   ├── test_single_pole_solver.py
│   ├── test_double_pole_solver.py
│   └── test_monument_solver.py
│
├── contract/
│   ├── test_api_schemas.py
│   └── test_envelope_pattern.py
│
└── property/
    ├── test_determinism.py        # Same inputs → same outputs
    ├── test_monotonicity.py        # Load ↑ → capacity requirement ↑
    └── test_code_compliance.py     # Results always meet building codes
```

**Example Test:**
```python
# tests/unit/services/test_wind_loads.py
import pytest
from hypothesis import given, strategies as st

from apex.domains.signage.services.wind_loads import WindLoadService
from apex.domains.signage.exceptions import ValidationError


class TestWindLoadService:
    """Test suite for ASCE 7-22 wind load calculations."""

    @pytest.fixture
    def service(self):
        return WindLoadService(code_version="ASCE7-22")

    def test_velocity_pressure_asce7_example(self, service):
        """Verify against ASCE 7-22 Commentary Example."""
        result = service.calculate_velocity_pressure(
            wind_speed_mph=115,
            height_ft=15,
            exposure="C",
        )

        assert abs(result.qz_psf - 24.46) < 0.1, "Should match ASCE 7-22 example"
        assert result.code_ref == "ASCE7-22 Eq 26.10-1"

    def test_validates_wind_speed_range(self, service):
        """Should reject wind speeds outside ASCE 7-22 range."""
        with pytest.raises(ValidationError, match="below ASCE 7-22 minimum"):
            service.calculate_velocity_pressure(
                wind_speed_mph=50,  # Too low
                height_ft=15,
                exposure="C",
            )

    @given(
        wind_speed=st.floats(min_value=85, max_value=200),
        height=st.floats(min_value=0.1, max_value=100),
    )
    def test_determinism_property(self, service, wind_speed, height):
        """Same inputs always produce same outputs (PE requirement)."""
        result1 = service.calculate_velocity_pressure(wind_speed, height, "C")
        result2 = service.calculate_velocity_pressure(wind_speed, height, "C")

        assert result1.qz_psf == result2.qz_psf, "Must be deterministic"

    def test_monotonicity_with_wind_speed(self, service):
        """Higher wind speed → higher velocity pressure."""
        results = [
            service.calculate_velocity_pressure(v, 15, "C")
            for v in [90, 100, 110, 120]
        ]

        pressures = [r.qz_psf for r in results]
        assert pressures == sorted(pressures), "qz must increase with wind speed"
```

**Benefits:**
- Comprehensive test coverage (target: >90%)
- Property-based testing for PE compliance
- Fast feedback loop
- Regression protection

**Effort:** 4-5 days
**Risk:** Low (additive)

---

## PHASE 4: PERFORMANCE OPTIMIZATION (Priority: MEDIUM)

### 4.1 Caching Strategy

**Current Issue:**
- LRU cache used but not comprehensive
- No cache invalidation strategy
- Cache keys could be better designed

**Refactoring:**
```python
# utils/caching.py
from functools import wraps
from typing import Callable, TypeVar, ParamSpec

P = ParamSpec('P')
T = TypeVar('T')


def engineering_cache(
    maxsize: int = 256,
    typed: bool = True,
    key_func: Callable | None = None
):
    """
    Cache decorator for engineering calculations.

    - Uses typed=True for type safety (15.0 != 15)
    - Custom key_func for rounding floating point inputs
    - Thread-safe LRU cache
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Round inputs for cache stability
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _default_key_func(*args, **kwargs)

            # Use functools.lru_cache internally
            return _cached_call(cache_key, func, *args, **kwargs)

        return wrapper
    return decorator


# Usage
@engineering_cache(maxsize=512, key_func=lambda mu, d, s, k, p, ft: (round(mu, 2), round(d, 2), int(s)))
def calculate_foundation_depth(...) -> float:
    """Expensive calculation with smart caching."""
    ...
```

**Benefits:**
- 10-100x speedup for repeated calculations
- Predictable cache behavior
- Memory-efficient

**Effort:** 1-2 days
**Risk:** Low

---

### 4.2 Vectorization with NumPy

**Current Issue:**
- Pole filtering uses Python loops
- Could be vectorized for 10x speedup

**Refactoring:**
```python
def filter_poles_vectorized(
    mu_required_kipin: float,
    sections: list[dict],
    prefs: dict
) -> list[PoleOption]:
    """Vectorized pole filtering (10x faster)."""
    import numpy as np

    # Convert to numpy arrays
    sx_array = np.array([s['sx_in3'] for s in sections])
    fy_array = np.array([s['fy_ksi'] for s in sections])
    types = np.array([s['type'] for s in sections])

    # Vectorized capacity calculation
    phi_mn_array = PHI_B * fy_array * sx_array

    # Vectorized filtering
    family_mask = types == prefs['family']
    strength_mask = phi_mn_array >= mu_required_kipin
    feasible_mask = family_mask & strength_mask

    # Extract results
    feasible_indices = np.where(feasible_mask)[0]

    return [
        PoleOption(
            shape=sections[i]['shape'],
            sx_in3=sx_array[i],
            ...
        )
        for i in feasible_indices
    ]
```

**Benefits:**
- 10-20x speedup for large datasets
- Leverages CPU vectorization (SIMD)
- More memory efficient

**Effort:** 1-2 days
**Risk:** Low

---

## PHASE 5: DOCUMENTATION & MAINTAINABILITY (Priority: MEDIUM)

### 5.1 Comprehensive Docstrings

**Current Issue:**
- Some functions lack detailed docstrings
- Missing parameter descriptions
- No return type documentation

**Refactoring:**
Use Google-style docstrings with examples:

```python
def calculate_velocity_pressure(
    wind_speed_mph: float,
    height_ft: float,
    exposure: Exposure,
    kzt: float = 1.0,
    kd: float = 0.85,
    ke: float = 1.0,
) -> VelocityPressureResult:
    """
    Calculate velocity pressure qz per ASCE 7-22 Equation 26.10-1.

    Implements the fundamental wind pressure equation from ASCE 7-22 Chapter 26.
    The velocity pressure represents the kinetic energy of the wind and is used
    to calculate design pressures on structures.

    Args:
        wind_speed_mph: Basic wind speed in miles per hour (3-second gust).
            Must be between 85-200 mph per ASCE 7-22 Figure 26.5-1.
        height_ft: Height above ground level in feet where pressure is calculated.
            Must be >= 0. For heights < 15 ft, code uses 15 ft value (conservative).
        exposure: Wind exposure category per ASCE 7-22 Section 26.7:
            - "B": Urban/suburban (many obstructions)
            - "C": Open terrain (default for most locations)
            - "D": Flat coastal areas
        kzt: Topographic factor per Section 26.8. Default 1.0 for flat terrain.
            Use > 1.0 for hills, ridges, escarpments per Figure 26.8-1.
        kd: Wind directionality factor per Table 26.6-1. Default 0.85 for signs.
        ke: Ground elevation factor per Section 26.9. Default 1.0 for elevation < 3000 ft.

    Returns:
        VelocityPressureResult containing:
            - qz_psf: Velocity pressure in pounds per square foot
            - kz: Calculated velocity pressure exposure coefficient
            - code_ref: ASCE 7-22 equation reference

    Raises:
        ValidationError: If wind speed outside 85-200 mph range or height < 0.

    Examples:
        >>> # Basic calculation for 115 mph wind at 15 ft, Exposure C
        >>> result = calculate_velocity_pressure(115, 15, "C")
        >>> print(f"qz = {result.qz_psf:.2f} psf")
        qz = 24.46 psf

        >>> # With topographic factor for hill
        >>> result = calculate_velocity_pressure(120, 20, "C", kzt=1.15)
        >>> print(f"qz = {result.qz_psf:.2f} psf")
        qz = 31.28 psf

    References:
        - ASCE 7-22 Section 26.10: Velocity Pressure
        - ASCE 7-22 Equation 26.10-1: qz = 0.00256 * Kz * Kzt * Kd * Ke * V²
        - ASCE 7-22 Table 26.10-1: Velocity Pressure Exposure Coefficients

    Notes:
        - This calculation does NOT include the gust effect factor G.
          G is applied separately in design pressure calculations per Chapter 29.
        - Results are deterministic (same inputs always give same outputs) per
          PE stamping requirements.
        - For sign structures, use this with Chapter 29 force coefficients.
    """
    # Implementation...
```

**Benefits:**
- Self-documenting code
- Better IDE support
- Easier onboarding
- PE review clarity

**Effort:** 2-3 days
**Risk:** None (additive)

---

### 5.2 Architectural Decision Records (ADRs)

**Refactoring:**
Create `/docs/adr/` directory with markdown files:

```markdown
# ADR-001: Use IBC 2024 Equation 18-1 for Foundation Depth

## Status
Accepted - Implemented 2025-11-02

## Context
Previous foundation depth calculations used an empirical Broms-style formula with
a calibration constant `k`. This did not comply with IBC 2024 requirements.

## Decision
Replace empirical formula with IBC 2024 Section 1807.3 Equation 18-1:
- d = (4.36 × h / b) × √(P / S)
- Implement iterative solver (depth appears on both sides)
- Converge to < 1% tolerance or 0.1 ft

## Consequences
### Positive
- Code-compliant per IBC 2024
- Eliminates calibration factor uncertainty
- Clear code reference for PE review

### Negative
- Results differ from previous calculations (50-522% in some cases)
- Requires user notification about changed results
- Slightly more computationally expensive (iterative)

## Alternatives Considered
1. Keep Broms formula - Rejected (not IBC compliant)
2. Use simplified IBC approximation - Rejected (less accurate)

## References
- IBC 2024 Section 1807.3
- PE_FIXES_APPLIED.md
```

**Benefits:**
- Historical context preserved
- Design decisions documented
- Easier maintenance

**Effort:** 1 day
**Risk:** None

---

## PHASE 6: CLEAN CODE PRINCIPLES (Priority: MEDIUM)

### 6.1 Remove Magic Numbers

**Current Issue:**
```python
qz = 0.00256 * kz * kzt * kd * (v_basic**2)  # What is 0.00256?
depth_ft = max(2.0, depth_ft)  # Why 2.0?
```

**Refactoring:**
```python
# constants.py
# ASCE 7-22 Constants
ASCE7_22_VELOCITY_PRESSURE_COEFFICIENT = 0.00256  # psf/(mph²) - Eq 26.10-1
ASCE7_22_WIND_DIRECTIONALITY_SIGNS = 0.85  # Table 26.6-1
ASCE7_22_GUST_EFFECT_RIGID = 0.85  # Section 26.11

# IBC 2024 Constants
IBC_2024_MIN_FOUNDATION_DEPTH_FT = 2.0  # Section 1807.1.6.2
IBC_2024_FOUNDATION_CONSTANT = 4.36  # Equation 18-1
IBC_2024_OVERTURNING_SAFETY_FACTOR = 1.5  # Section 1605.2.1

# Usage
qz = ASCE7_22_VELOCITY_PRESSURE_COEFFICIENT * kz * kzt * kd * (v_basic**2)
depth_ft = max(IBC_2024_MIN_FOUNDATION_DEPTH_FT, depth_ft)
```

**Benefits:**
- Self-documenting constants
- Single source of truth
- Easy to update when codes change

**Effort:** 0.5 days
**Risk:** None

---

### 6.2 Improve Variable Naming

**Before:**
```python
fb = (M * 12.0) / S
fv = V / A
```

**After:**
```python
bending_stress_ksi = (moment_kipft * 12.0) / section_modulus_in3
shear_stress_ksi = shear_force_kips / area_in2
```

**Effort:** 1 day
**Risk:** Low

---

## IMPLEMENTATION ROADMAP

### Week 1: Foundation (5 days)
- [x] Day 1: PE calculation fixes (COMPLETE)
- [ ] Day 2-3: DDD restructuring (Phase 1.1)
- [ ] Day 4-5: Service layer pattern (Phase 1.2)

### Week 2: Quality (5 days)
- [ ] Day 1-2: Type safety enhancement (Phase 2.1)
- [ ] Day 2-3: Error handling standardization (Phase 2.2)
- [ ] Day 4-5: Function decomposition (Phase 2.3)

### Week 3: Testing (5 days)
- [ ] Day 1-5: Comprehensive test suite (Phase 3.1)
- [ ] Achieve >90% code coverage
- [ ] Property-based tests for determinism

### Week 4: Polish (5 days)
- [ ] Day 1-2: Performance optimization (Phase 4)
- [ ] Day 3-4: Documentation (Phase 5)
- [ ] Day 5: Clean code principles (Phase 6)

**Total Effort:** 4 weeks (20 working days)

---

## RISK MITIGATION

### Risk 1: Breaking Changes
**Mitigation:**
- Feature flags for new code paths
- Parallel implementation (old + new)
- Comprehensive regression tests
- Gradual rollout

### Risk 2: PE Compliance
**Mitigation:**
- All refactoring preserves determinism
- Add property tests for PE requirements
- Maintain audit trail logging
- PE review after each phase

### Risk 3: Performance Regression
**Mitigation:**
- Benchmark before/after each change
- Performance tests in CI/CD
- Profiling to identify bottlenecks

---

## SUCCESS METRICS

| Metric | Current | Target | Method |
|--------|---------|--------|--------|
| Code Coverage | ~60% | >90% | pytest-cov |
| Avg Function Length | 81 lines | <30 lines | radon |
| Cyclomatic Complexity | Unknown | <10 per function | radon |
| Type Coverage | ~70% | >95% | mypy strict mode |
| Documentation Coverage | ~50% | 100% | interrogate |
| Performance (pole filter) | 100ms | <10ms | pytest-benchmark |

---

## TOOLS & TECHNOLOGIES

- **Testing:** pytest, pytest-cov, pytest-benchmark, hypothesis
- **Type Checking:** mypy (strict mode), pyright
- **Linting:** ruff (replacing flake8/black/isort)
- **Code Quality:** radon (complexity), interrogate (docstrings)
- **Performance:** py-spy, memory_profiler
- **Documentation:** mkdocs, mkdocstrings

---

## CONCLUSION

This rigorous refactoring plan transforms the SignX Studio codebase from a functional but monolithic structure into a clean, maintainable, highly-tested architecture that maintains PE compliance while improving developer experience and code quality.

**Expected Outcomes:**
- ✅ 50% reduction in bug rate
- ✅ 90%+ test coverage
- ✅ 3x faster developer onboarding
- ✅ 10x faster pole selection (vectorization)
- ✅ 100% type safety
- ✅ Comprehensive documentation

**Status:** Ready to begin implementation
**Owner:** Development Team
**Approver:** Technical Lead + PE
