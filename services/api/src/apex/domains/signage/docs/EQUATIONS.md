# APEX Signage Engineering - Equation Reference

## ASCE 7-22 Wind Loads

### Velocity Pressure (Chapter 26)

**Equation 26.10-1:**
```
qz = 0.00256 × Kz × Kzt × Kd × V² × G
```

**Variables:**
- `qz`: Velocity pressure (psf)
- `Kz`: Velocity pressure exposure coefficient (Table 26.10-1)
- `Kzt`: Topographic factor (Section 26.8)
- `Kd`: Wind directionality factor (Table 26.6-1) = 0.85
- `V`: Basic wind speed (mph)
- `G`: Gust effect factor = 0.85 (rigid structures)

**Code Reference:** `solvers.py:derive_loads()` → Line 133

### Service Moment

**Derived:**
```
M_service = qz × A × z_cg
```

**Variables:**
- `M_service`: Service moment (kip-ft)
- `A`: Projected area (ft²)
- `z_cg`: Centroid height (ft)

**Code Reference:** `solvers.py:derive_loads()` → Line 140

### Ultimate Moment (LRFD)

**ASCE 7-22 Load Combination:**
```
Mu = 1.6 × M_service
```

**Variables:**
- `Mu`: Ultimate moment (kip-ft)
- Load factor: 1.6 (wind)

**Code Reference:** `solvers.py:derive_loads()` → Line 144

## AISC 360-16 Steel Design

### Flexural Strength (Chapter F)

**Plastic Moment Capacity:**
```
Mn = Fy × Sx
```

**Design Strength:**
```
φMn = 0.9 × Mn >= Mu_required
```

**Variables:**
- `Mn`: Nominal moment capacity (kip-in)
- `Fy`: Yield strength (ksi)
- `Sx`: Section modulus (in³)
- `φ`: Resistance factor = 0.9 (bending)
- `Mu_required`: Required ultimate moment (kip-in)

**Code Reference:** `solvers.py:filter_poles()` → Line 206-210

### Plate Bending (Chapter J)

**Section Modulus:**
```
S = w × t² / 6
```

**Bending Stress:**
```
fb = M / S <= 0.6 × Fy
```

**Variables:**
- `S`: Section modulus (in³)
- `w`: Plate width (in)
- `t`: Plate thickness (in)
- `M`: Moment (kip-in)
- `fb`: Bending stress (ksi)
- `Fy`: Yield strength (ksi)

**Code Reference:** `solvers.py:baseplate_checks()` → Line 338

### Weld Strength (Table J2.5)

**Fillet Weld Capacity:**
```
Rn = 0.6 × Fexx × 0.707 × size × length
```

**Variables:**
- `Rn`: Nominal strength (kip)
- `Fexx`: Electrode strength (ksi) = 70.0 (E70XX)
- `size`: Weld size (in)
- `length`: Weld length (in)

**Code Reference:** `solvers.py:baseplate_checks()` → Line 361

## ACI 318 Anchor Design

### Steel Tension Capacity (D.5.1.2)

**Design Strength:**
```
φTn = φ × 0.75 × Ab × Fy
```

**Variables:**
- `φ`: Resistance factor = 0.75
- `Ab`: Bolt area (in²) = π × (dia/2)²
- `Fy`: Yield strength (ksi)

**Code Reference:** `solvers.py:baseplate_checks()` → Line 385

### Concrete Breakout (D.5.2)

**Simplified Breakout Capacity:**
```
Ncb = 25 × hef^1.5 × sqrt(fc') × spacing_factor
```

**Variables:**
- `Ncb`: Breakout capacity (kip)
- `hef`: Embedment depth (in)
- `fc'`: Concrete strength (psi)
- `spacing_factor`: Spacing reduction factor

**Code Reference:** `solvers.py:baseplate_checks()` → Line 394

### Shear Capacity (D.6.1.2)

**Design Strength:**
```
φVn = φ × 0.6 × Ab × Fy
```

**Variables:**
- `φ`: Resistance factor = 0.75
- `Ab`: Bolt area (in²)
- `Fy`: Yield strength (ksi)

**Code Reference:** `solvers.py:baseplate_checks()` → Line 416

## Foundation Design

### Direct Burial Depth (Broms Method)

**Lateral Capacity:**
```
h_min = K × Mu / (d³ × q_soil / conversion_factor)
```

**Variables:**
- `h_min`: Minimum depth (ft)
- `K`: Calibrated constant (versioned)
- `Mu`: Ultimate moment (kip-ft)
- `d`: Footing diameter (ft)
- `q_soil`: Soil bearing pressure (psf)
- `conversion_factor`: 12.0 (unit conversion)

**Code Reference:** `solvers.py:footing_solve()` → Line 287

**Monotonicity Property:**
- `diameter↓ → depth↑` (validated in tests)
- `moment↑ → depth↑` (validated in tests)

## Structural Analysis

### Dynamic Amplification (ASCE 7-22)

**Simplified Response Spectrum:**
```
amplification = f(fn_hz, damping_ratio, site_class)
```

For typical sign structures (fn ~ 2-5 Hz): amplification ~ 1.1-1.2

**Code Reference:** `structural_analysis.py:dynamic_load_analysis()` → Line 30

### Fatigue Life (AISC 360-16 Appendix 3)

**Fatigue Strength:**
```
S = (C/N)^(1/3) for N > 5×10⁶
```

**Variables:**
- `S`: Stress range (ksi)
- `C`: Detail category constant
- `N`: Number of cycles

**Code Reference:** `structural_analysis.py:fatigue_analysis()` → Line 50

## Reliability Analysis

### Reliability Index (Hasofer-Lind)

**Reliability Index:**
```
β = (μ_R - μ_Q) / sqrt(σ_R² + σ_Q²)
```

**Variables:**
- `β`: Reliability index
- `μ_R`: Mean resistance
- `μ_Q`: Mean load
- `σ_R`: Std dev resistance
- `σ_Q`: Std dev load

**Target:** β = 3.5 per ASCE 7-22

**Code Reference:** `calibration.py:monte_carlo_reliability()` → Line 50

## Optimization

### NSGA-II (Deb et al. 2002)

**Objectives:**
1. Minimize cost
2. Minimize weight
3. Maximize safety_factor

**Selection:** Non-dominated sorting + crowding distance

**Code Reference:** `optimization.py:pareto_optimize_poles()` → Line 155

### Genetic Algorithm

**Operators:**
- Crossover: Blend (cxBlend)
- Mutation: Gaussian (mutGaussian)
- Selection: Tournament (selTournament)

**Code Reference:** `optimization.py:baseplate_optimize_ga()` → Line 347-350

## Limitations

- **Simplified**: Many equations are simplified for practical use
- **Assumptions**: Standard assumptions (e.g., flat terrain, no topography)
- **Scope**: Focused on typical sign structures, not extreme cases
- **Updates**: Based on AISC 360-16, ASCE 7-22, ACI 318 current versions

## References

- ASCE 7-22: Minimum Design Loads and Associated Criteria
- AISC 360-16: Specification for Structural Steel Buildings
- ACI 318: Building Code Requirements for Structural Concrete
- Broms (1964): Lateral earth pressure theory
- Deb et al. (2002): NSGA-II algorithm

