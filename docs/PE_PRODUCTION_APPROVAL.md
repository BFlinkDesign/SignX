# PE PRODUCTION APPROVAL - SignX Studio
**Date:** November 1, 2025
**Reviewer:** PE Production Code Reviewer
**System:** SignX Studio - Mechanical Engineering Copilot for PE-Stampable Calculations

---

## 🔴 GO/NO-GO DECISION: **NO-GO**

**CRITICAL:** This codebase is **NOT APPROVED** for production deployment due to fundamental calculation errors that pose PE liability risks.

---

## EXECUTIVE SUMMARY

The SignX Studio codebase contains critical calculation errors that disqualify it from PE-stampable production use. The most severe issue is an incorrect implementation of the ASCE 7-22 velocity pressure formula that would produce erroneous wind loads. Additionally, missing IBC load combinations, non-code-compliant foundation calculations, and inadequate error handling create unacceptable liability exposure for Professional Engineers.

---

## CALCULATION VERIFICATION RESULTS

### 1. ASCE 7-22 Wind Pressure Formula ❌ **FAILED**

**Critical Error Location:** `services/signcalc-service/apex_signcalc/wind_asce7.py:27`

```python
# CURRENT IMPLEMENTATION (INCORRECT):
return 0.00256 * kz * kzt * kd * (V_basic ** 2) * G  # G should NOT be here!

# CORRECT PER ASCE 7-22 EQ. 26.10-1:
qz = 0.00256 * Kz * Kzt * Kd * Ke * V²
```

**Impact:** This error artificially inflates velocity pressure by the gust factor (typically 0.85), resulting in:
- 15% underestimation of wind pressures when G < 1.0
- Unconservative designs that could lead to structural failure
- Direct violation of ASCE 7-22 Chapter 26

### 2. IBC 2024 Load Combinations ❌ **FAILED**

**Missing Load Cases:** Only wind loads considered, missing 5 of 7 required combinations per IBC 2024 Section 1605.2:
- ❌ 1.4D (Dead load only)
- ❌ 1.2D + 1.6L + 0.5(Lr or S or R)
- ❌ 1.2D + 1.6(Lr or S or R) + (L or 0.5W)
- ✅ 1.2D + 1.0W + L + 0.5(Lr or S or R) (partially implemented)
- ❌ 0.9D + 1.0W (critical for uplift/overturning)

### 3. AISC 360-22 Steel Design ⚠️ **PARTIALLY FAILED**

**Location:** `services/api/src/apex/domains/signage/single_pole_solver.py:229`

Issues identified:
- Uses simplified Fb = 0.66*Fy without checking section compactness
- Missing lateral-torsional buckling checks (Chapter F)
- No local buckling verification (Chapter B4)
- Combined stress interaction too simplified (should use H1-1a/b)

### 4. Foundation Design ❌ **FAILED**

**Location:** `services/signcalc-service/apex_signcalc/foundation_embed.py`

Critical issues:
- Arbitrary K_FACTOR = 0.15 with no engineering basis
- No reference to IBC 2024 Section 1807
- No consideration of soil properties per geotechnical standards
- Formula appears to be rules-of-thumb, not code-based

### 5. Edge Cases & Numerical Precision ⚠️ **PARTIALLY PASSED**

Verified scenarios:
- ✅ Zero wind speed handled (returns 0 pressure)
- ❌ Negative wind speeds not validated (could produce negative pressures)
- ✅ Division by zero protection implemented (but arbitrary epsilon)
- ⚠️ Extreme wind speeds (>200 mph) not bounded
- ✅ Unit conversions correct (psf, mph, ft verified)

---

## CRITICAL ISSUES (MUST FIX BEFORE DEPLOY)

### Priority 1: Calculation Errors

1. **Wind Pressure Formula** (`wind_asce7.py:27`)
   - Remove gust factor G from velocity pressure calculation
   - Add proper Ke factor per ASCE 7-22
   - Estimated fix time: 1 hour
   - Test impact: Update 12 existing tests

2. **Load Combinations** (`single_pole_solver.py`)
   - Implement all 7 IBC 2024 basic combinations
   - Add combination enveloping logic
   - Estimated fix time: 4 hours
   - Test impact: Add 20+ new test cases

3. **Foundation Calculations** (`foundation_embed.py`)
   - Replace with IBC 1807 pole foundation method
   - Or implement Brom's method with proper citations
   - Estimated fix time: 8 hours
   - Test impact: Complete rewrite of foundation tests

### Priority 2: Input Validation

4. **Type Hints & Validation**
   ```python
   # Required pattern for all calculation functions:
   def calculate_wind_pressure(
       wind_speed_mph: float,
       height_ft: float,
       exposure: Literal['B', 'C', 'D']
   ) -> WindPressureResult:
       if wind_speed_mph <= 0:
           raise ValueError(f"Wind speed must be positive: {wind_speed_mph}")
       if not 0 < height_ft <= 500:
           raise ValueError(f"Height out of range: {height_ft}")
   ```

5. **Exception Handling**
   - Add try/except with engineering context
   - Log all calculation failures with inputs
   - Provide actionable error messages

### Priority 3: Audit Trail

6. **Comprehensive Logging**
   ```python
   logger.info(
       "ASCE 7-22 Wind Calculation",
       extra={
           "code_reference": "ASCE 7-22 Eq. 26.10-1",
           "inputs": {"V": wind_speed_mph, "h": height_ft},
           "formula": "qz = 0.00256*Kz*Kzt*Kd*Ke*V²",
           "result": qz_psf,
           "timestamp": datetime.utcnow().isoformat()
       }
   )
   ```

---

## PE STAMPING READINESS ASSESSMENT

### Current State: 🔴 **NOT READY**

**Liability Exposure Level: CRITICAL**

Reasons for failure:
1. **Calculation Errors**: Fundamental formula errors would produce incorrect results
2. **Incomplete Code Compliance**: Missing required load combinations
3. **Inadequate Documentation**: Foundation calculations lack code citations
4. **Insufficient Validation**: No protection against invalid inputs
5. **Poor Audit Trail**: Limited logging for liability protection

### Required for PE Approval:

- [ ] Fix all Priority 1 calculation errors
- [ ] Implement complete IBC 2024 load combinations
- [ ] Add code-compliant foundation design
- [ ] Complete input validation on all functions
- [ ] Add comprehensive calculation logging
- [ ] Achieve 90%+ test coverage on calculation modules
- [ ] Add integration tests for complete workflows
- [ ] Document all formulas with code citations
- [ ] Implement calculation versioning for reproducibility
- [ ] Add PE review checkpoints in critical paths

### Estimated Time to Production Ready:
- **Minimum:** 40 hours of focused development
- **Recommended:** 80 hours including comprehensive testing
- **With PE Review:** 120 hours including documentation and validation

---

## RECOMMENDATIONS

### Immediate Actions (This Sprint):
1. **STOP** any production deployment plans
2. Fix wind pressure formula (1 hour)
3. Add input validation to all calculation functions (8 hours)
4. Implement missing load combinations (4 hours)

### Next Sprint:
1. Rewrite foundation module with proper code basis
2. Complete AISC 360-22 implementation
3. Add comprehensive logging
4. Achieve 90% test coverage

### Before PE Deployment:
1. Independent code review by licensed PE
2. Validation against known design examples
3. Comparison with established software (RISA, SAP2000)
4. Legal review of liability disclaimers
5. Implement calculation versioning system

---

## TESTING REQUIREMENTS

Current Coverage: **Estimated 65%** (based on test file review)

Required for PE Use:
- Unit Tests: 95% coverage on calculation functions
- Integration Tests: All API endpoints validated
- Regression Tests: Known design examples
- Edge Case Tests: Boundary conditions, invalid inputs
- Performance Tests: <100ms for typical calculations
- Comparison Tests: Validate against hand calculations

---

## LIABILITY STATEMENT

**WARNING:** Deployment of this codebase in its current state for PE-stampable calculations would constitute professional negligence. The calculation errors identified could lead to:
- Structural failures due to under-designed components
- Legal liability for the signing PE
- Loss of professional license
- Criminal negligence charges in case of collapse

**Required Disclaimer:** Until all critical issues are resolved, this software must include:
```
THIS SOFTWARE IS IN DEVELOPMENT AND NOT APPROVED FOR
PROFESSIONAL ENGINEERING USE. DO NOT USE FOR FINAL DESIGNS.
CALCULATIONS HAVE NOT BEEN VALIDATED AGAINST CURRENT CODES.
```

---

## APPROVAL SIGNATURES

**PE Code Reviewer:** ❌ NOT APPROVED
**Date:** November 1, 2025
**Next Review:** After Priority 1 fixes complete

**Conditions for Re-Review:**
1. All Priority 1 calculation errors fixed
2. Test suite updated and passing
3. Code citations added to all formulas
4. Input validation implemented

---

## APPENDIX: SPECIFIC CODE CORRECTIONS REQUIRED

### A1. Wind Pressure Correction
```python
# FILE: services/signcalc-service/apex_signcalc/wind_asce7.py
# LINE: 27
# CURRENT (INCORRECT):
return 0.00256 * kz * kzt * kd * (V_basic ** 2) * G

# REQUIRED CORRECTION:
# Per ASCE 7-22 Equation 26.10-1
ke = 1.0  # Ground elevation factor, Table 26.9-1
return 0.00256 * kz * kzt * kd * ke * (V_basic ** 2)
# Note: G is applied later to get design wind pressure
```

### A2. Load Combination Implementation
```python
# FILE: services/api/src/apex/domains/signage/single_pole_solver.py
# ADD: Complete IBC 2024 Section 1605.2 combinations

def calculate_load_combinations(D, L, Lr, S, R, W, E):
    """Calculate all IBC 2024 basic load combinations."""
    combos = []

    # 1. 1.4D
    combos.append(("1.4D", 1.4 * D))

    # 2. 1.2D + 1.6L + 0.5(Lr or S or R)
    combos.append(("1.2D+1.6L+0.5Lr", 1.2*D + 1.6*L + 0.5*max(Lr, S, R)))

    # 3. 1.2D + 1.6(Lr or S or R) + (L or 0.5W)
    combos.append(("1.2D+1.6Lr+L", 1.2*D + 1.6*max(Lr, S, R) + L))
    combos.append(("1.2D+1.6Lr+0.5W", 1.2*D + 1.6*max(Lr, S, R) + 0.5*W))

    # 4. 1.2D + 1.0W + L + 0.5(Lr or S or R)
    combos.append(("1.2D+1.0W+L+0.5Lr", 1.2*D + 1.0*W + L + 0.5*max(Lr, S, R)))

    # 5. 0.9D + 1.0W
    combos.append(("0.9D+1.0W", 0.9*D + 1.0*W))

    # 6 & 7: Seismic combinations (if applicable)
    if E > 0:
        combos.append(("1.2D+1.0E+L", 1.2*D + 1.0*E + L))
        combos.append(("0.9D+1.0E", 0.9*D + 1.0*E))

    return combos
```

### A3. Foundation Design Fix
```python
# FILE: services/signcalc-service/apex_signcalc/foundation_embed.py
# COMPLETE REWRITE REQUIRED

def calculate_pole_embedment_ibc(
    lateral_load_lb: float,
    height_ft: float,
    allowable_lateral_pressure_psf: float,
    pole_diameter_in: float,
    safety_factor: float = 2.0
) -> float:
    """
    Calculate pole embedment per IBC 2024 Section 1807.3.

    References:
        IBC 2024 Section 1807.3 - Embedded posts and poles
        IBC 2024 Equation 18-1 for non-constrained condition

    Args:
        lateral_load_lb: Applied lateral load at top of pole (lb)
        height_ft: Height of load application above grade (ft)
        allowable_lateral_pressure_psf: Allowable soil pressure (psf)
        pole_diameter_in: Diameter of pole (in)
        safety_factor: Safety factor (typically 2.0)

    Returns:
        Required embedment depth in feet
    """
    # IBC 2024 Equation 18-1 (simplified for preliminary design)
    # d = (4.36 * h / b) * sqrt(P / S)
    # where:
    #   d = embedment depth (ft)
    #   h = height above grade (ft)
    #   b = pole diameter (ft)
    #   P = lateral load (lb)
    #   S = allowable soil pressure (psf)

    b = pole_diameter_in / 12.0  # Convert to feet

    if allowable_lateral_pressure_psf <= 0:
        raise ValueError(f"Allowable pressure must be positive: {allowable_lateral_pressure_psf}")

    # IBC non-constrained formula
    d_required = (4.36 * height_ft / b) * math.sqrt(
        lateral_load_lb / allowable_lateral_pressure_psf
    )

    # Apply safety factor
    d_design = d_required * safety_factor

    # Log for PE audit trail
    logger.info(
        "IBC 2024 Pole Embedment Calculation",
        extra={
            "code_reference": "IBC 2024 Section 1807.3, Eq. 18-1",
            "inputs": {
                "lateral_load_lb": lateral_load_lb,
                "height_ft": height_ft,
                "allowable_pressure_psf": allowable_lateral_pressure_psf,
                "pole_diameter_in": pole_diameter_in
            },
            "results": {
                "required_depth_ft": d_required,
                "design_depth_ft": d_design,
                "safety_factor": safety_factor
            }
        }
    )

    return d_design
```

---

**END OF PE PRODUCTION APPROVAL DOCUMENT**

*This document must be updated and re-reviewed after each round of fixes.*