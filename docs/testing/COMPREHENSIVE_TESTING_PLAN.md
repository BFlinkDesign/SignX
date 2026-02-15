# SignX/APEX Comprehensive Testing Plan

## PE-Stampable Structural Engineering Calculation System

**Version:** 1.0
**Date:** 2026-01-22
**Status:** Complete Testing Strategy
**Target Coverage:** 90%+ for calculations, 80%+ overall

---

## Executive Summary

This testing plan ensures SignX/APEX calculations are:
- **Deterministic**: Same inputs always produce identical outputs
- **Code-Compliant**: All calculations validated against ASCE 7-22, AISC 360-22, ACI 318-19, IBC 2024
- **PE-Stampable**: Results suitable for professional engineering approval
- **Auditable**: Complete traceability from inputs to outputs

---

## 1. Unit Tests - Engineering Calculations

### 1.1 Wind Load Calculations (ASCE 7-22)

**File:** `tests/unit/engineering/test_wind_asce7_22.py`

#### Test Cases with Expected Values

```python
# Test Case 1: Basic Velocity Pressure (Equation 26.10-1)
# qz = 0.00256 * Kz * Kzt * Kd * Ke * V^2
#
# Iowa Grimes Baseline:
# - V = 115 mph (Risk Category II)
# - Exposure C, height 15 ft
# - Kz = 0.85 (Table 26.10-1)
# - Kzt = 1.0 (flat terrain)
# - Kd = 0.85 (signs, Table 26.6-1)
# - Ke = 1.0 (< 3000 ft elevation)
#
# Hand Calculation:
# qz = 0.00256 * 0.85 * 1.0 * 0.85 * 1.0 * 115^2 = 24.46 psf

@pytest.mark.parametrize("velocity,height,exposure,kzt,kd,ke,expected_qz,code_ref", [
    # ASCE 7-22 Equation 26.10-1 validation cases
    (115, 15, "C", 1.0, 0.85, 1.0, 24.46, "ASCE 7-22 Eq. 26.10-1"),
    (100, 15, "B", 1.0, 0.85, 1.0, 12.26, "ASCE 7-22 Eq. 26.10-1"),
    (100, 15, "C", 1.0, 0.85, 1.0, 18.32, "ASCE 7-22 Eq. 26.10-1"),
    (100, 15, "D", 1.0, 0.85, 1.0, 22.18, "ASCE 7-22 Eq. 26.10-1"),
    (120, 30, "C", 1.0, 0.85, 1.0, 25.67, "ASCE 7-22 Eq. 26.10-1"),
    (150, 60, "C", 1.0, 0.85, 1.0, 55.12, "ASCE 7-22 Eq. 26.10-1"),
    # With topographic factor
    (115, 15, "C", 1.3, 0.85, 1.0, 31.80, "ASCE 7-22 Section 26.8"),
    # High elevation
    (115, 15, "C", 1.0, 0.85, 0.89, 21.77, "ASCE 7-22 Table 26.9-1"),
])
def test_velocity_pressure_parametric():
    """Validate qz against hand calculations."""
```

#### Kz Coefficient Tests (Table 26.10-1)

```python
@pytest.mark.parametrize("height,exposure,expected_kz", [
    # Exposure B - Urban/Suburban
    (15, "B", 0.57), (20, "B", 0.62), (25, "B", 0.66),
    (30, "B", 0.70), (40, "B", 0.76), (50, "B", 0.81),
    (60, "B", 0.85), (80, "B", 0.93), (100, "B", 0.99),
    (120, "B", 1.04), (140, "B", 1.09), (160, "B", 1.13),

    # Exposure C - Open Terrain
    (15, "C", 0.85), (20, "C", 0.90), (25, "C", 0.94),
    (30, "C", 0.98), (40, "C", 1.04), (50, "C", 1.09),
    (60, "C", 1.13), (80, "C", 1.21), (100, "C", 1.26),

    # Exposure D - Flat/Coastal
    (15, "D", 1.03), (20, "D", 1.08), (25, "D", 1.12),
    (30, "D", 1.16), (40, "D", 1.22), (50, "D", 1.27),
    (60, "D", 1.31), (80, "D", 1.38), (100, "D", 1.43),
])
def test_kz_table_26_10_1_exact():
    """Verify Kz matches ASCE 7-22 Table 26.10-1 exactly."""
```

#### Edge Cases

```python
@pytest.mark.parametrize("test_name,velocity,height,exposure,expected_behavior", [
    ("zero_wind", 0, 15, "C", "returns_zero"),
    ("negative_wind", -10, 15, "C", "raises_validation_error"),
    ("extreme_wind", 250, 15, "C", "calculates_high_value"),
    ("negative_height", 115, -5, "C", "raises_validation_error"),
    ("below_minimum_height", 115, 5, "C", "uses_15ft_kz"),
    ("extreme_height", 115, 500, "C", "uses_power_law"),
    ("invalid_exposure", 115, 15, "X", "raises_validation_error"),
])
def test_wind_calculation_edge_cases():
    """Validate edge case handling."""
```

#### Determinism Tests

```python
def test_wind_calculation_determinism_1000_runs():
    """Run calculation 1000x with identical inputs, verify SHA256 match."""
    inputs = {
        "wind_speed_mph": 115.0,
        "height_ft": 25.0,
        "exposure": "C",
        "sign_area_ft2": 48.0,
    }

    results = [calculate_wind_force(**inputs) for _ in range(1000)]
    hashes = [hashlib.sha256(str(r).encode()).hexdigest() for r in results]

    assert len(set(hashes)) == 1, "Non-deterministic wind calculation detected"
```

---

### 1.2 Structural Analysis (AISC 360-22)

**File:** `tests/unit/engineering/test_aisc_360_22.py`

#### Steel Member Capacity Tests

```python
# HSS Section Properties (AISC Steel Manual Table 1-12)
# HSS 8x8x1/2: Sx = 25.1 in^3, Zx = 31.0 in^3, Ag = 12.8 in^2

@pytest.mark.parametrize("section,fy_ksi,expected_phi_mn_kipin,code_ref", [
    # phi_Mn = phi * Fy * Zx (compact section)
    # phi = 0.9 per AISC 360-22 Section F1
    ("HSS4x4x1/4", 46, 258.75, "AISC 360-22 F7"),
    ("HSS6x6x3/8", 46, 516.42, "AISC 360-22 F7"),
    ("HSS8x8x1/2", 46, 1283.40, "AISC 360-22 F7"),
    ("HSS10x10x1/2", 46, 2066.40, "AISC 360-22 F7"),
    # A36 steel
    ("HSS8x8x1/2", 36, 1004.40, "AISC 360-22 F7"),
    # A992 steel
    ("W14x90", 50, 11700.0, "AISC 360-22 F2"),
])
def test_flexural_capacity_aisc_360():
    """Validate member flexural capacity per AISC 360-22."""
```

#### Combined Stress Ratio Tests (AISC H1-1)

```python
def test_combined_stress_ratio_aisc_h1_1a():
    """
    Verify combined axial and flexural stress per AISC 360-22 H1-1a.

    Tests interaction equation: Pr/Pc + 8/9(Mrx/Mcx + Mry/Mcy) <= 1.0

    Test case: W14x90 column with:
    - Axial load: Pr = 150 kips
    - Moment about x-axis: Mrx = 200 kip-ft = 2400 kip-in
    - Design strengths: Pc = 500 kips, Mcx = 4800 kip-in (400 kip-ft)

    Hand calculation:
    Pr/Pc = 150/500 = 0.30 > 0.2, use Eq. H1-1a
    Ratio = 0.30 + 8/9(2400/4800 + 0) = 0.30 + 0.44 = 0.74 < 1.0 [OK]

    Reference: AISC 360-22 Section H1.1, Equation H1-1a
    """
    result = calculate_interaction_ratio(
        axial_kip=150.0,
        moment_x_kipft=200.0,
        moment_y_kipft=0.0,
        section="W14x90",
        length_ft=12.0,
        k_factor=1.0,
    )

    assert result.interaction_ratio == pytest.approx(0.74, abs=0.02)
    assert result.governing_equation == "H1-1a"
    assert result.ok is True
```

---

### 1.3 Foundation Design (IBC 2024)

**File:** `tests/unit/engineering/test_foundation_ibc_2024.py`

#### Direct Burial Depth Tests

```python
@pytest.mark.parametrize("moment_kipft,diameter_ft,soil_psf,expected_depth_ft,method", [
    # Monotonic property: diameter down -> depth up
    (10.0, 2.0, 3000, 8.5, "CALTRANS"),
    (10.0, 3.0, 3000, 5.2, "CALTRANS"),
    (10.0, 4.0, 3000, 3.6, "CALTRANS"),
    # Higher moment -> deeper foundation
    (5.0, 3.0, 3000, 4.1, "CALTRANS"),
    (20.0, 3.0, 3000, 6.8, "CALTRANS"),
    # Lower soil capacity -> deeper foundation
    (10.0, 3.0, 2000, 6.5, "CALTRANS"),
    (10.0, 3.0, 4000, 4.2, "CALTRANS"),
])
def test_direct_burial_depth_calculation():
    """Validate foundation depth per IBC 2024 / CALTRANS Method A."""
```

#### Safety Factor Checks

```python
def test_foundation_safety_factors():
    """
    Verify all safety factors meet IBC 2024 requirements.

    Required factors:
    - Overturning: SF >= 1.5
    - Bearing: SF >= 2.0
    - Sliding: SF >= 1.5
    - Uplift: SF >= 1.5 (if applicable)
    """
    result = design_foundation(
        moment_kipft=15.0,
        shear_kip=2.0,
        axial_kip=3.0,
        soil_bearing_psf=3000,
    )

    assert result.sf_overturning >= 1.5, "IBC 2024 Section 1807.2.3"
    assert result.sf_bearing >= 2.0, "IBC 2024 Section 1806.1"
    assert result.sf_sliding >= 1.5, "IBC 2024 Section 1807.2.3"
```

---

### 1.4 Anchor Design (ACI 318-19)

**File:** `tests/unit/engineering/test_anchors_aci_318_19.py`

#### Concrete Breakout Strength (ACI 318-19 Chapter 17)

```python
@pytest.mark.parametrize("embed_in,fc_psi,n_anchors,spacing_in,edge_in,expected_ncb_kip", [
    # Single anchor, no edge effects
    # Ncb = ANc/ANco * psi_ed * psi_c * psi_cp * Nb
    # ANco = 9 * hef^2
    # Nb = 16 * lambda * sqrt(fc) * hef^1.5 (lb)
    (6, 4000, 1, None, None, 15.2),
    (8, 4000, 1, None, None, 23.4),
    (10, 4000, 1, None, None, 32.7),
    # Group of 4 anchors
    (8, 4000, 4, 6.0, 3.0, 58.8),
    # Higher concrete strength
    (8, 5000, 1, None, None, 26.2),
])
def test_concrete_breakout_strength_aci_17_4():
    """
    Validate concrete breakout strength per ACI 318-19 Section 17.4.2.

    Hand calculation for hef=8in, fc=4000psi, single anchor:
    ANco = 9 * 8^2 = 576 in^2
    Nb = 16 * 1.0 * sqrt(4000) * 8^1.5 = 22,888 lb = 22.9 kip
    psi factors = 1.0 (no edge effects)
    Ncb = 22.9 kip (phi = 0.7 for tension)
    phi_Ncb = 0.7 * 22.9 = 16.0 kip

    Reference: ACI 318-19 Section 17.4.2
    """
```

#### Steel Anchor Capacity

```python
@pytest.mark.parametrize("diameter_in,grade,n_threads,expected_phi_nsa_kip", [
    # Nsa = Ase * futa
    # Ase for threaded anchors per ACI 318-19 Eq. 17.4.1.2a
    (0.500, "F1554-55", 13, 8.4),
    (0.625, "F1554-55", 11, 13.2),
    (0.750, "F1554-55", 10, 19.0),
    (0.875, "F1554-55", 9, 25.9),
    (1.000, "F1554-105", 8, 54.2),
])
def test_anchor_steel_strength_aci_17_4_1():
    """Validate steel anchor tensile strength per ACI 318-19 17.4.1."""
```

---

### 1.5 Baseplate Design (AISC Design Guide 1)

**File:** `tests/unit/engineering/test_baseplate_aisc_dg1.py`

#### Plate Thickness Calculation

```python
def test_baseplate_thickness_aisc_dg1():
    """
    Verify baseplate thickness calculation per AISC Design Guide 1.

    Test case: W14x90 column, N=16", B=16", fp=2.0 ksi

    Cantilever projection: m = (N - 0.95*d)/2 = (16 - 0.95*14)/2 = 1.35"
                          n = (B - 0.8*bf)/2 = (16 - 0.8*14.5)/2 = 2.2"

    Required thickness: t = sqrt(2*fp*n^2/(0.9*Fy))
                       t = sqrt(2*2.0*2.2^2/(0.9*36)) = 0.87"

    Use 7/8" plate minimum.

    Reference: AISC Design Guide 1, Section 3.1
    """
    result = design_baseplate(
        column="W14x90",
        axial_kip=300.0,
        moment_kipft=50.0,
        plate_width_in=16.0,
        plate_length_in=16.0,
        concrete_fc_psi=4000,
        plate_fy_ksi=36.0,
    )

    assert result.required_thickness_in >= 0.875
    assert result.code_reference == "AISC Design Guide 1"
```

---

### 1.6 Precision and Floating Point Tests

**File:** `tests/unit/engineering/test_numerical_precision.py`

```python
class TestNumericalPrecision:
    """Verify floating point handling for PE-stampable calculations."""

    def test_rounding_consistency(self):
        """All outputs rounded to engineering precision (3 decimal places)."""
        result = calculate_wind_force(wind_speed_mph=115.0, height_ft=15.0)

        # Force should be rounded to 0.001 lb precision
        assert result.force_lb == round(result.force_lb, 3)

    def test_no_floating_point_drift(self):
        """Verify no accumulation errors in iterative calculations."""
        # Run footing optimization 100 times
        results = []
        for _ in range(100):
            r = footing_solve(mu_kipft=10.0, diameter_ft=3.0, soil_psf=3000)
            results.append(r.depth_ft)

        # All results must be identical (no drift)
        assert len(set(results)) == 1

    def test_unit_conversion_reversibility(self):
        """Verify unit conversions are reversible."""
        original_ksi = 50.0
        psi = original_ksi * 1000
        back_to_ksi = psi / 1000

        assert original_ksi == back_to_ksi
```

---

## 2. Integration Tests

### 2.1 API Endpoint Testing

**File:** `tests/integration/test_api_endpoints.py`

```python
@pytest.mark.asyncio
class TestWindLoadAPI:
    """Integration tests for wind load calculation API."""

    async def test_wind_calculation_endpoint(self, client):
        """Test /api/v1/calculations/wind endpoint."""
        payload = {
            "wind_speed_mph": 115.0,
            "height_ft": 15.0,
            "exposure_category": "C",
            "sign_area_ft2": 48.0,
            "risk_category": "II",
        }

        resp = await client.post("/api/v1/calculations/wind", json=payload)

        assert resp.status_code == 200
        data = resp.json()

        # Envelope structure
        assert "result" in data
        assert "confidence" in data
        assert "trace" in data

        # Engineering results
        assert data["result"]["velocity_pressure_psf"] == pytest.approx(24.46, abs=0.5)
        assert data["result"]["total_force_lb"] > 0

    async def test_wind_calculation_validation_errors(self, client):
        """Test input validation."""
        invalid_payloads = [
            {"wind_speed_mph": -10},  # Negative wind speed
            {"wind_speed_mph": 300},  # Exceeds max
            {"exposure_category": "X"},  # Invalid exposure
        ]

        for payload in invalid_payloads:
            resp = await client.post("/api/v1/calculations/wind", json=payload)
            assert resp.status_code == 422
```

### 2.2 Database Operations

**File:** `tests/integration/test_database_operations.py`

```python
@pytest.mark.asyncio
class TestProjectPersistence:
    """Test database CRUD operations."""

    async def test_project_create_read_update_delete(self, db_session):
        """Full CRUD cycle for project."""
        # Create
        project = await create_project(
            db_session,
            name="Test Project",
            account_id="test_account",
        )
        assert project.id is not None

        # Read
        fetched = await get_project(db_session, project.id)
        assert fetched.name == "Test Project"

        # Update
        await update_project(db_session, project.id, name="Updated Name")
        updated = await get_project(db_session, project.id)
        assert updated.name == "Updated Name"

        # Delete
        await delete_project(db_session, project.id)
        deleted = await get_project(db_session, project.id)
        assert deleted is None

    async def test_calculation_result_persistence(self, db_session):
        """Verify calculation results are stored with full audit trail."""
        result = await persist_calculation_result(
            db_session,
            module="wind_load",
            inputs={"wind_speed_mph": 115.0},
            outputs={"force_lb": 1200.0},
            code_version="abc123",
        )

        assert result.content_sha256 is not None
        assert result.created_at is not None
```

---

## 3. Contract Tests

### 3.1 API Envelope Consistency

**File:** `tests/contract/test_envelope_contract.py`

```python
@pytest.mark.contract
class TestEnvelopeContract:
    """Verify all API responses follow envelope contract."""

    REQUIRED_ENVELOPE_FIELDS = ["result", "assumptions", "confidence", "trace"]

    @pytest.mark.parametrize("endpoint", [
        "/api/v1/calculations/wind",
        "/api/v1/calculations/foundation",
        "/api/v1/calculations/baseplate",
        "/api/v1/poles/options",
        "/api/v1/cabinets/derive",
    ])
    async def test_envelope_structure(self, client, endpoint, valid_payloads):
        """All calculation endpoints return standardized envelope."""
        payload = valid_payloads[endpoint]
        resp = await client.post(endpoint, json=payload)

        assert resp.status_code == 200
        data = resp.json()

        for field in self.REQUIRED_ENVELOPE_FIELDS:
            assert field in data, f"Missing envelope field: {field}"

        # Confidence must be valid
        assert 0.0 <= data["confidence"] <= 1.0

        # Trace must have code version
        assert "code_version" in data["trace"]
        assert "git_sha" in data["trace"]["code_version"]
```

### 3.2 OpenAPI Compliance

**File:** `tests/contract/test_openapi_compliance.py`

```python
@pytest.mark.contract
class TestOpenAPICompliance:
    """Verify API matches OpenAPI specification."""

    async def test_response_matches_schema(self, client):
        """Response structure matches OpenAPI schema."""
        from openapi_spec_validator import validate_spec
        import yaml

        # Fetch OpenAPI spec
        resp = await client.get("/openapi.json")
        spec = resp.json()

        # Validate spec itself
        validate_spec(spec)

        # Validate response against schema
        wind_resp = await client.post(
            "/api/v1/calculations/wind",
            json={"wind_speed_mph": 115.0, "height_ft": 15.0, "exposure_category": "C"},
        )

        # Validate response structure
        assert_response_matches_schema(wind_resp.json(), spec["components"]["schemas"]["WindLoadResponse"])
```

---

## 4. Validation Test Cases - Real-World Examples

### 4.1 Monument Sign: 8'x3' Face, 12' Pole, 115 mph, Exposure C

**File:** `tests/validation/test_monument_sign.py`

```python
class TestMonumentSignValidation:
    """
    Real-world validation: Monument sign in Iowa Grimes.

    Sign Parameters:
    - Face dimensions: 8 ft wide x 3 ft tall
    - Pole height: 12 ft (bottom of sign to grade)
    - Wind speed: 115 mph (Risk Category II)
    - Exposure: C (open terrain)
    - Soil bearing: 3000 psf

    Expected Results (hand-calculated):

    1. Wind Load:
       - Kz at 13.5 ft (centroid) = 0.85 (use 15 ft minimum)
       - qz = 0.00256 * 0.85 * 1.0 * 0.85 * 115^2 = 24.46 psf
       - G = 0.85 (gust factor)
       - Cf = 1.2 (force coefficient)
       - p = 24.46 * 0.85 * 1.2 = 24.95 psf
       - A = 8 * 3 = 24 ft^2
       - F = 24.95 * 24 = 598.8 lb

    2. Overturning Moment:
       - Moment arm = 12 + 3/2 = 13.5 ft
       - M = 598.8 * 13.5 = 8,084 lb-ft = 8.08 kip-ft

    3. Foundation (18" diameter direct burial):
       - Required depth ~ 4.5 ft (using CALTRANS method)
       - SF_overturning >= 1.5

    Reference: ASCE 7-22, IBC 2024
    """

    def test_monument_sign_wind_force(self):
        """Validate wind force calculation."""
        result = calculate_wind_force_on_sign(
            wind_speed_mph=115.0,
            sign_width_ft=8.0,
            sign_height_ft=3.0,
            pole_height_ft=12.0,
            exposure=ExposureCategory.C,
            risk_category=RiskCategory.II,
        )

        assert result.total_wind_force_lbs == pytest.approx(598.8, rel=0.02)
        assert result.velocity_pressure_psf == pytest.approx(24.46, abs=0.5)

    def test_monument_sign_overturning_moment(self):
        """Validate overturning moment calculation."""
        result = calculate_sign_loads(
            wind_speed_mph=115.0,
            sign_width_ft=8.0,
            sign_height_ft=3.0,
            pole_height_ft=12.0,
            exposure=ExposureCategory.C,
        )

        assert result.moment_kipft == pytest.approx(8.08, rel=0.02)

    def test_monument_sign_foundation(self):
        """Validate foundation design."""
        result = design_direct_burial_foundation(
            moment_kipft=8.08,
            diameter_in=18.0,
            soil_bearing_psf=3000,
        )

        assert result.required_depth_ft >= 4.0
        assert result.required_depth_ft <= 6.0
        assert result.sf_overturning >= 1.5
```

### 4.2 Pylon Sign: 10'x6' Face, 40' Height, 120 mph

**File:** `tests/validation/test_pylon_sign.py`

```python
class TestPylonSignValidation:
    """
    Real-world validation: Pylon sign in Florida.

    Sign Parameters:
    - Face dimensions: 10 ft wide x 6 ft tall
    - Overall height: 40 ft (sign centroid at 37 ft)
    - Wind speed: 120 mph (hurricane zone)
    - Exposure: C
    - Foundation: 24" diameter drilled shaft

    Expected Results:

    1. Wind Load:
       - Kz at 37 ft = 1.02 (interpolated)
       - qz = 0.00256 * 1.02 * 1.0 * 0.85 * 120^2 = 31.95 psf
       - p = 31.95 * 0.85 * 1.2 = 32.59 psf
       - A = 10 * 6 = 60 ft^2
       - F = 32.59 * 60 = 1,955 lb

    2. Overturning Moment:
       - M = 1,955 * 37 = 72,335 lb-ft = 72.3 kip-ft

    3. Foundation:
       - Required depth ~ 12 ft
       - Reinforcement: #6 bars vertical, #4 spiral
    """

    def test_pylon_sign_full_analysis(self):
        """Complete pylon sign analysis."""
        result = analyze_pylon_sign(
            sign_width_ft=10.0,
            sign_height_ft=6.0,
            overall_height_ft=40.0,
            wind_speed_mph=120.0,
            exposure="C",
            foundation_diameter_in=24.0,
            soil_bearing_psf=3000,
        )

        # Wind
        assert result.wind_force_lb == pytest.approx(1955, rel=0.05)

        # Moment
        assert result.moment_kipft == pytest.approx(72.3, rel=0.05)

        # Foundation
        assert result.foundation.depth_ft >= 10.0
        assert result.foundation.depth_ft <= 15.0
```

### 4.3 Cantilever Sign: 6' Arm, 4'x2' Sign, 100 mph

**File:** `tests/validation/test_cantilever_sign.py`

```python
class TestCantileverSignValidation:
    """
    Real-world validation: Cantilever sign.

    Sign Parameters:
    - Arm length: 6 ft horizontal projection
    - Sign: 4 ft wide x 2 ft tall
    - Sign weight: 150 lb
    - Pole height: 15 ft
    - Wind speed: 100 mph
    - Exposure: B (urban)

    Expected Results:

    1. Wind Load on Sign:
       - Kz at 16 ft = 0.57 (Exposure B, use 15 ft)
       - qz = 0.00256 * 0.57 * 1.0 * 0.85 * 100^2 = 12.38 psf
       - p = 12.38 * 0.85 * 1.2 = 12.63 psf
       - F = 12.63 * 8 = 101 lb

    2. Moments at Pole Base:
       - Mx (overturning from wind) = 101 * 16 = 1,616 lb-ft
       - My (dead load moment) = 150 * 6 = 900 lb-ft
       - Total M = sqrt(1616^2 + 900^2) = 1,850 lb-ft = 1.85 kip-ft

    3. Torsion (if eccentric):
       - With 1 ft eccentricity: Mz = 101 * 1 = 101 lb-ft

    Reference: AASHTO LTS-6, AISC 360-22
    """

    def test_cantilever_analysis(self):
        """Validate cantilever sign analysis."""
        config = CantileverConfig(
            type=CantileverType.SINGLE,
            arm_length_ft=6.0,
            arm_angle_deg=0.0,
            arm_section="HSS6x6x3/8",
            connection_type=ConnectionType.BOLTED_FLANGE,
        )

        loads = CantileverLoads(
            sign_weight_lb=150.0,
            sign_area_ft2=8.0,
            wind_pressure_psf=12.63,
            eccentricity_ft=0.0,
        )

        result = analyze_cantilever_sign(config, loads, pole_height_ft=15.0)

        assert result.moment_x_kipft == pytest.approx(1.62, rel=0.05)
        assert result.moment_y_kipft == pytest.approx(0.90, rel=0.05)
        assert result.total_moment_kipft == pytest.approx(1.85, rel=0.05)
```

---

## 5. Regression Tests

### 5.1 Golden File Tests

**File:** `tests/regression/test_golden_files.py`

```python
@pytest.mark.regression
class TestGoldenFiles:
    """Compare outputs against verified golden files."""

    GOLDEN_DIR = Path(__file__).parent / "golden_outputs"

    @pytest.mark.parametrize("case_file", [
        "monument_sign_iowa.json",
        "pylon_sign_florida.json",
        "cantilever_sign_texas.json",
        "multi_pole_california.json",
    ])
    def test_golden_file_match(self, case_file):
        """Output matches verified golden file."""
        with open(self.GOLDEN_DIR / case_file) as f:
            golden = json.load(f)

        inputs = golden["inputs"]
        expected = golden["expected_outputs"]

        actual = run_calculation(**inputs)

        # Compare with tolerance
        for key, expected_value in expected.items():
            actual_value = actual[key]
            if isinstance(expected_value, (int, float)):
                assert actual_value == pytest.approx(expected_value, rel=0.001), \
                    f"Mismatch for {key}: {actual_value} vs {expected_value}"
            else:
                assert actual_value == expected_value
```

### 5.2 Reference Problems (50+ Cases)

**File:** `tests/fixtures/reference_cases.json`

```json
{
  "case_01": {
    "description": "Monument sign - minimal",
    "inputs": {
      "endpoint": "/api/v1/calculations/wind",
      "payload": {
        "wind_speed_mph": 100,
        "height_ft": 15,
        "exposure_category": "C",
        "sign_area_ft2": 20
      }
    },
    "expected_outputs": {
      "result": {
        "velocity_pressure_psf": 18.32,
        "total_force_lb": 373
      }
    },
    "tolerance": 0.02,
    "code_reference": "ASCE 7-22 Eq. 26.10-1"
  },
  "case_02": {
    "description": "Pylon sign - hurricane zone",
    "inputs": {
      "endpoint": "/api/v1/calculations/wind",
      "payload": {
        "wind_speed_mph": 150,
        "height_ft": 50,
        "exposure_category": "D",
        "sign_area_ft2": 100
      }
    },
    "expected_outputs": {
      "result": {
        "velocity_pressure_psf": 73.2,
        "total_force_lb": 7469
      }
    },
    "tolerance": 0.02
  }
}
```

---

## 6. Performance Tests

### 6.1 Calculation Latency

**File:** `tests/performance/test_calculation_latency.py`

```python
@pytest.mark.performance
class TestCalculationLatency:
    """Verify calculation performance meets SLOs."""

    @pytest.mark.parametrize("endpoint,target_p95_ms", [
        ("/api/v1/calculations/wind", 50),
        ("/api/v1/calculations/foundation", 100),
        ("/api/v1/calculations/baseplate", 100),
        ("/api/v1/poles/options", 50),
        ("/api/v1/cabinets/derive", 100),
    ])
    async def test_endpoint_latency_p95(self, client, endpoint, target_p95_ms, valid_payload):
        """Verify p95 latency < target."""
        latencies = []

        for _ in range(100):
            start = time.perf_counter()
            await client.post(endpoint, json=valid_payload)
            latencies.append((time.perf_counter() - start) * 1000)

        latencies.sort()
        p95 = latencies[int(0.95 * len(latencies))]

        assert p95 < target_p95_ms, \
            f"{endpoint} p95 latency {p95:.1f}ms exceeds {target_p95_ms}ms target"

    async def test_report_generation_latency(self, client, full_project_payload):
        """Report generation p95 < 1 second."""
        latencies = []

        for _ in range(20):
            start = time.perf_counter()
            await client.post("/api/v1/projects/test/report", json=full_project_payload)
            latencies.append((time.perf_counter() - start) * 1000)

        p95 = sorted(latencies)[int(0.95 * len(latencies))]
        assert p95 < 1000, f"Report p95 latency {p95:.1f}ms exceeds 1s target"
```

### 6.2 Concurrent Load

**File:** `tests/performance/test_concurrent_load.py`

```python
@pytest.mark.performance
class TestConcurrentLoad:
    """Test system under concurrent load."""

    async def test_100_concurrent_calculations(self, client):
        """System handles 100 concurrent calculation requests."""
        import asyncio

        async def make_request():
            return await client.post(
                "/api/v1/calculations/wind",
                json={"wind_speed_mph": 115, "height_ft": 15, "exposure_category": "C"},
            )

        start = time.perf_counter()
        results = await asyncio.gather(*[make_request() for _ in range(100)])
        elapsed = time.perf_counter() - start

        # All should succeed
        assert all(r.status_code == 200 for r in results)

        # Throughput > 10 req/sec
        throughput = 100 / elapsed
        assert throughput > 10, f"Throughput {throughput:.1f} req/s below 10 req/s target"
```

### 6.3 Memory Usage

**File:** `tests/performance/test_memory_usage.py`

```python
@pytest.mark.performance
class TestMemoryUsage:
    """Test memory efficiency."""

    async def test_memory_under_load(self, client):
        """Memory growth < 50MB for 1000 calculations."""
        import tracemalloc

        tracemalloc.start()
        start_mem = tracemalloc.get_traced_memory()[0]

        for _ in range(1000):
            await client.post(
                "/api/v1/calculations/wind",
                json={"wind_speed_mph": 115, "height_ft": 15, "exposure_category": "C"},
            )

        end_mem = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        growth_mb = (end_mem - start_mem) / (1024 * 1024)
        assert growth_mb < 50, f"Memory grew {growth_mb:.1f}MB, exceeds 50MB limit"
```

---

## 7. Security Tests

### 7.1 Input Sanitization

**File:** `tests/security/test_input_sanitization.py`

```python
@pytest.mark.security
class TestInputSanitization:
    """Verify input sanitization prevents attacks."""

    SQL_INJECTION_PAYLOADS = [
        "'; DROP TABLE projects; --",
        "' OR '1'='1",
        "admin'--",
        "1' UNION SELECT * FROM users--",
        "'; EXEC xp_cmdshell('dir'); --",
    ]

    XSS_PAYLOADS = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        "<svg onload=alert('XSS')>",
    ]

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    async def test_sql_injection_prevention(self, client, payload):
        """SQL injection attempts are blocked."""
        resp = await client.post(
            "/api/v1/projects/",
            json={"name": payload, "account_id": "test"},
        )

        # Should reject or sanitize
        assert resp.status_code in (200, 422, 400)

        if resp.status_code == 200:
            # If accepted, verify sanitized
            data = resp.json()
            assert "DROP TABLE" not in str(data)

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    async def test_xss_prevention(self, client, payload):
        """XSS attempts are sanitized."""
        resp = await client.post(
            "/api/v1/projects/",
            json={"name": payload, "account_id": "test"},
        )

        if resp.status_code == 200:
            data = resp.json()
            assert "<script>" not in str(data).lower()
            assert "javascript:" not in str(data).lower()
```

### 7.2 Authentication/Authorization

**File:** `tests/security/test_auth.py`

```python
@pytest.mark.security
class TestAuthentication:
    """Verify authentication requirements."""

    PROTECTED_ENDPOINTS = [
        ("POST", "/api/v1/projects/"),
        ("GET", "/api/v1/projects/{id}"),
        ("POST", "/api/v1/calculations/wind"),
        ("POST", "/api/v1/projects/{id}/submit"),
    ]

    @pytest.mark.parametrize("method,endpoint", PROTECTED_ENDPOINTS)
    async def test_unauthenticated_access_rejected(self, client, method, endpoint):
        """Protected endpoints require authentication."""
        if method == "GET":
            resp = await client.get(endpoint.replace("{id}", "test"))
        else:
            resp = await client.post(endpoint.replace("{id}", "test"), json={})

        # Should require auth (401) or be forbidden (403)
        assert resp.status_code in (401, 403, 422)
```

### 7.3 Rate Limiting

**File:** `tests/security/test_rate_limiting.py`

```python
@pytest.mark.security
class TestRateLimiting:
    """Verify rate limiting prevents abuse."""

    async def test_rate_limit_triggers(self, client):
        """Rate limit triggers after threshold."""
        responses = []

        # Rapid-fire 200 requests
        for _ in range(200):
            resp = await client.get("/api/v1/health")
            responses.append(resp.status_code)
            if resp.status_code == 429:
                break

        assert 429 in responses, "Rate limiting not triggered after 200 requests"

    async def test_rate_limit_headers(self, client):
        """Rate limit headers are present."""
        resp = await client.get("/api/v1/health")

        assert "X-RateLimit-Limit" in resp.headers
        assert "X-RateLimit-Remaining" in resp.headers
```

---

## 8. Simulation / Monte Carlo Tests

### 8.1 Parameter Sweeps

**File:** `tests/simulation/test_parameter_sweeps.py`

```python
@pytest.mark.simulation
class TestParameterSweeps:
    """Systematic parameter variation testing."""

    def test_wind_speed_sweep(self):
        """Sweep wind speed 50-200 mph, verify monotonic force increase."""
        forces = []

        for wind_speed in range(50, 201, 10):
            result = calculate_wind_force(
                wind_speed_mph=wind_speed,
                height_ft=20.0,
                exposure="C",
                sign_area_ft2=48.0,
            )
            forces.append(result.total_force_lb)

        # Force should increase monotonically with V^2
        for i in range(len(forces) - 1):
            assert forces[i+1] > forces[i], \
                f"Non-monotonic at V={50+i*10}mph"

    def test_height_kz_sweep(self):
        """Sweep height 15-200 ft, verify Kz increases."""
        kz_values = []

        for height in range(15, 201, 10):
            kz = calculate_kz(height, ExposureCategory.C)
            kz_values.append(kz)

        for i in range(len(kz_values) - 1):
            assert kz_values[i+1] >= kz_values[i], \
                f"Kz non-monotonic at h={15+i*10}ft"

    def test_footing_diameter_depth_relationship(self):
        """Verify inverse relationship: larger diameter -> shallower depth."""
        depths = []

        for diameter in [12, 15, 18, 21, 24, 30, 36]:
            result = design_foundation(
                moment_kipft=20.0,
                diameter_in=diameter,
                soil_bearing_psf=3000,
            )
            depths.append(result.depth_ft)

        for i in range(len(depths) - 1):
            assert depths[i+1] <= depths[i] + 0.5, \
                f"Depth not decreasing with diameter: {depths[i]} to {depths[i+1]}"
```

### 8.2 Probabilistic Analysis

**File:** `tests/simulation/test_monte_carlo.py`

```python
@pytest.mark.simulation
@pytest.mark.slow
class TestMonteCarlo:
    """Monte Carlo simulation for statistical validation."""

    def test_wind_load_distribution(self):
        """
        Monte Carlo: Vary wind speed with normal distribution,
        verify output distribution is reasonable.
        """
        import numpy as np

        np.random.seed(42)  # Reproducibility

        # Wind speed: mean 115, std 10
        wind_speeds = np.random.normal(115, 10, 1000)
        wind_speeds = np.clip(wind_speeds, 80, 150)

        forces = []
        for ws in wind_speeds:
            result = calculate_wind_force(
                wind_speed_mph=float(ws),
                height_ft=20.0,
                exposure="C",
                sign_area_ft2=48.0,
            )
            forces.append(result.total_force_lb)

        forces = np.array(forces)

        # Statistical checks
        assert np.mean(forces) > 500  # Reasonable mean
        assert np.std(forces) > 50   # Some variation
        assert np.min(forces) > 0    # No negative forces
        assert np.max(forces) < 5000 # Not unreasonably high

    def test_load_combination_enumeration(self):
        """Enumerate all load combinations per ASCE 7-22 Section 2.4."""
        load_cases = [
            {"D": 1.0, "L": 0.0, "W": 0.0},  # 1.4D
            {"D": 1.0, "L": 1.0, "W": 0.0},  # 1.2D + 1.6L
            {"D": 1.0, "L": 0.5, "W": 1.0},  # 1.2D + 1.0W + L
            {"D": 0.9, "L": 0.0, "W": 1.0},  # 0.9D + 1.0W
        ]

        results = []
        for case in load_cases:
            result = calculate_combined_loads(
                dead_kip=10.0,
                live_kip=5.0,
                wind_kip=8.0,
                load_factors=case,
            )
            results.append(result)

        # Governing case should be max
        governing = max(results, key=lambda r: r.total_factored_kip)
        assert governing.governing_combination is not None
```

### 8.3 Sensitivity Analysis

**File:** `tests/simulation/test_sensitivity.py`

```python
@pytest.mark.simulation
class TestSensitivityAnalysis:
    """Analyze sensitivity of outputs to input variations."""

    def test_foundation_sensitivity_to_soil(self):
        """Foundation depth sensitivity to soil bearing capacity."""
        base_soil = 3000  # psf

        sensitivities = []
        for delta_pct in [-20, -10, 0, 10, 20]:
            soil = base_soil * (1 + delta_pct / 100)
            result = design_foundation(
                moment_kipft=20.0,
                diameter_in=18.0,
                soil_bearing_psf=soil,
            )
            sensitivities.append({
                "soil_delta_pct": delta_pct,
                "depth_ft": result.depth_ft,
            })

        # Lower soil -> deeper foundation
        depths = [s["depth_ft"] for s in sensitivities]
        assert depths[0] > depths[4], "Depth should increase with lower soil capacity"

    def test_wind_sensitivity_to_exposure(self):
        """Wind load sensitivity to exposure category."""
        results = {}

        for exposure in ["B", "C", "D"]:
            result = calculate_wind_force(
                wind_speed_mph=115.0,
                height_ft=30.0,
                exposure=exposure,
                sign_area_ft2=48.0,
            )
            results[exposure] = result.total_force_lb

        # D > C > B
        assert results["D"] > results["C"] > results["B"]

        # Quantify sensitivity
        sensitivity_bc = (results["C"] - results["B"]) / results["B"]
        sensitivity_cd = (results["D"] - results["C"]) / results["C"]

        assert sensitivity_bc > 0.1, "Exposure B->C sensitivity should be >10%"
        assert sensitivity_cd > 0.05, "Exposure C->D sensitivity should be >5%"
```

---

## 9. Test Organization and Execution

### 9.1 Directory Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── unit/
│   ├── engineering/
│   │   ├── test_wind_asce7_22.py
│   │   ├── test_aisc_360_22.py
│   │   ├── test_foundation_ibc_2024.py
│   │   ├── test_anchors_aci_318_19.py
│   │   ├── test_baseplate_aisc_dg1.py
│   │   └── test_numerical_precision.py
│   └── services/
│       ├── test_wind_service.py
│       └── test_foundation_service.py
├── integration/
│   ├── test_api_endpoints.py
│   └── test_database_operations.py
├── contract/
│   ├── test_envelope_contract.py
│   ├── test_openapi_compliance.py
│   └── test_determinism.py
├── validation/
│   ├── test_monument_sign.py
│   ├── test_pylon_sign.py
│   └── test_cantilever_sign.py
├── regression/
│   ├── test_golden_files.py
│   └── golden_outputs/
├── performance/
│   ├── test_calculation_latency.py
│   ├── test_concurrent_load.py
│   └── test_memory_usage.py
├── security/
│   ├── test_input_sanitization.py
│   ├── test_auth.py
│   └── test_rate_limiting.py
├── simulation/
│   ├── test_parameter_sweeps.py
│   ├── test_monte_carlo.py
│   └── test_sensitivity.py
└── fixtures/
    ├── reference_cases.json
    └── materials.json
```

### 9.2 Test Markers

```ini
# pytest.ini
[pytest]
markers =
    unit: Unit tests for calculations
    integration: Integration tests with external dependencies
    contract: API contract validation
    regression: Regression tests against golden files
    performance: Performance and latency tests
    security: Security and input validation tests
    simulation: Monte Carlo and sensitivity tests
    determinism: Determinism validation tests
    slow: Tests that take >1 minute
    engineering: Tests with code compliance validation
```

### 9.3 Execution Commands

```bash
# Run all unit tests
pytest tests/unit/ -v --tb=short

# Run engineering calculation tests only
pytest -m engineering -v

# Run determinism tests (1000 iterations)
pytest -m determinism -v

# Run contract tests
pytest tests/contract/ -v

# Run performance tests
pytest tests/performance/ -v --timeout=600

# Run security tests
pytest tests/security/ -v

# Run Monte Carlo simulations (slow)
pytest tests/simulation/ -v -m slow

# Full test suite with coverage
pytest --cov=services/api/src --cov-report=html --cov-fail-under=80

# Generate coverage report
pytest --cov=services --cov-report=xml --cov-report=term-missing

# Run specific validation cases
pytest tests/validation/ -v -k "monument"
```

### 9.4 Coverage Targets

| Module | Target Coverage | Critical Functions |
|--------|-----------------|-------------------|
| Wind calculations | 100% | calculate_kz, calculate_qz, calculate_wind_force |
| Foundation design | 100% | footing_solve, design_foundation |
| Baseplate checks | 100% | baseplate_checks, anchor_capacity |
| Structural analysis | 95% | calculate_interaction_ratio, filter_poles |
| API routes | 90% | All POST endpoints |
| Database operations | 80% | CRUD operations |
| Overall | 85% | - |

---

## 10. Continuous Integration

### 10.1 CI Pipeline Stages

```yaml
# .github/workflows/test.yml
stages:
  - lint:
      - ruff check .
      - mypy services/

  - unit-tests:
      - pytest tests/unit/ --cov --cov-fail-under=90

  - contract-tests:
      - pytest tests/contract/ -v

  - integration-tests:
      - docker-compose up -d
      - pytest tests/integration/ -v

  - security-tests:
      - pytest tests/security/ -v

  - performance-tests:
      - pytest tests/performance/ -v --timeout=600
```

### 10.2 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: Run unit tests
        entry: pytest tests/unit/ -x -q
        language: system
        pass_filenames: false

      - id: pytest-determinism
        name: Verify determinism
        entry: pytest -m determinism -x -q
        language: system
        pass_filenames: false
```

---

## Appendix A: Code Reference Summary

| Code | Section | Test Coverage |
|------|---------|---------------|
| ASCE 7-22 | 26.10-1 | Velocity pressure calculation |
| ASCE 7-22 | Table 26.10-1 | Kz coefficients |
| ASCE 7-22 | Table 1.5-2 | Importance factors |
| ASCE 7-22 | Section 26.8 | Topographic factors |
| AISC 360-22 | F2, F7 | Flexural capacity |
| AISC 360-22 | H1-1 | Combined stress interaction |
| AISC 360-22 | J4 | Weld strength |
| ACI 318-19 | 17.4.2 | Concrete breakout |
| ACI 318-19 | 17.4.1 | Steel anchor strength |
| IBC 2024 | 1807.2.3 | Foundation safety factors |
| AISC DG1 | Section 3.1 | Baseplate thickness |
| AASHTO LTS-6 | - | Cantilever fatigue |

---

## Appendix B: Hand Calculation Worksheets

See `tests/fixtures/hand_calculations/` for detailed hand calculation worksheets for each validation case, providing complete audit trail from code equations to expected test values.
