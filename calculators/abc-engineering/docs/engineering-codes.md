# Engineering Code References

## Gold Standard Codes (Current as of 2026)

### IBC 2024 (International Building Code)
- **Status**: Currently adopted in Iowa and most US jurisdictions
- References ASCE 7-22 for wind/snow/seismic loads
- References ACI 318-19 for concrete anchorage
- Section 1807.3: Embedded posts and poles (foundation design for signs)
- Section 1806.2: Presumptive load-bearing values of soils

### ASCE 7-22 (Minimum Design Loads and Associated Criteria)
- **Wind load formula**: F = qz * G * Cf * As
- **Velocity pressure**: qz = 0.00256 * Kz * Kzt * Kd * Ke * V^2
- **Exposure categories**:
  - B: Urban and suburban areas
  - C: Open terrain with scattered obstructions (default for most signs)
  - D: Flat, unobstructed areas and water surfaces
- **Risk categories**: I through IV (most signs are Risk Category II or III)
- **Figure 29.3-1**: Force coefficients (Cf) for solid freestanding walls and signs
  - Depends on B/s ratio (sign width / sign height)
  - Depends on s/h ratio (clearance ratio)
  - Current app uses Cf=1.2 default; should auto-calculate from these ratios
- **Table 26.10-1**: Kz values (velocity pressure exposure coefficient)
  - Currently implemented as power-law formula: Kz = 2.01 * (z/zg)^(2/alpha)
  - Alpha: B=7.0, C=9.5, D=11.5
  - zg: B=1200, C=900, D=700
- **Figure 26.5-1B**: Basic wind speeds for Risk Category II
  - Iowa: 115 mph

### AISC 360-22 (Specification for Structural Steel Buildings)
- **Eq. J8-2**: Column base plate bearing on concrete
  - Bearing strength: phi_c * Pp = phi_c * 0.85 * f'c * A1 * sqrt(A2/A1)
  - Upper limit: phi_c * 1.7 * f'c * A1
  - phi_c = 0.65
  - f'c = concrete compressive strength (typically 3000-4000 psi)
  - A1 = base plate area
  - A2 = concrete support area (foundation area)
- **Not yet implemented** in playground

### ACI 318-19 (Building Code Requirements for Structural Concrete)
- **Referenced by IBC 2024** for concrete anchorage design
- **Chapter 17**: Anchoring to Concrete
- **Key failure modes** (all must be checked):
  1. **Steel strength in tension** (17.6.1) - anchor rod capacity
  2. **Concrete breakout in tension** (17.6.2) - most critical for sign anchors
     - Breakout cone at 35-degree angle from anchor head
     - Affected by edge distance, spacing, concrete strength
  3. **Pullout in tension** (17.6.3) - bearing of anchor head on concrete
  4. **Side-face blowout** (17.6.4) - when anchor is near a free edge
  5. **Steel strength in shear** (17.7.1)
  6. **Concrete breakout in shear** (17.7.2)
  7. **Concrete pryout in shear** (17.7.3)
- **Interaction equation**: Combined tension + shear check
  - If V_ua/phi*V_n > 0.2 AND N_ua/phi*N_n > 0.2:
    - N_ua/(phi*N_n) + V_ua/(phi*V_n) <= 1.2
- **Not yet implemented** in playground

### ACI 318-25
- Latest edition (published 2025)
- Not yet adopted by IBC 2024
- Monitor for future code cycle adoption
- Same Chapter 17 anchoring provisions with updates

### AISC Design Guide 1 (3rd Edition, 2024)
- "Base Plate and Anchor Rod Design"
- Comprehensive guide for:
  - Base plate sizing (axial compression, tension, shear)
  - Anchor rod selection and layout
  - Concrete bearing and anchorage
- Updated for AISC 360-22 and ACI 318-19
- **Not yet implemented** in playground

## Code Standards Timeline

```
UBC 1997 (legacy)
  |
  v
IBC 2000 (ASCE 7-98) -- first IBC edition
  |
  v
IBC 2015 (ASCE 7-10) -- outdated (some competing tools still on this version)
  |
  v
IBC 2018 (ASCE 7-16) -- Ke factor introduced
  |
  v
IBC 2024 (ASCE 7-22) -- current gold standard, Iowa adopted
```

## Iowa-Specific Requirements

| Parameter | Value | Source |
|-----------|-------|--------|
| Frost line | 42 inches | Iowa Building Code |
| Basic wind speed (Risk Cat II) | 115 mph | ASCE 7-22 Fig 26.5-1B |
| Ground snow load | 33 psf | ASCE 7-22 Fig 7.2-1 |
| Building code | IBC 2024 | Iowa Admin Code |
| Seismic design category | A or B (low) | ASCE 7-22 |
| Default exposure | C (open terrain) | ASCE 7-22 |

## ASTM F1554 Anchor Bolt Specification

Used for cast-in-place anchor bolts in concrete foundations.

| Grade | Fy (ksi) | Fu (ksi) | Common Use |
|-------|----------|----------|------------|
| 36 | 36 | 58-80 | Most sign foundations |
| 55 | 55 | 75-95 | Medium-load signs |
| 105 | 105 | 125-150 | High-load / tall signs |

- Diameters: 1/2" to 4"
- Standard embedment: minimum 12 bolt diameters
- Head types: Headed, Hooked (J-bolt, L-bolt), or Nutted
- Currently playground only uses A307 specs; F1554 grades should be added

## What's Implemented vs. What's Needed

| Code Check | Status | Priority |
|------------|--------|----------|
| ASCE 7-22 wind load | Implemented | Done |
| Kz from Table 26.10-1 | Implemented (formula) | Done |
| Cf from Fig 29.3-1 | Manual input only | High |
| A307 bolt tensile check | Implemented | Done |
| ACI 318-19 Ch.17 breakout | Not implemented | High |
| ACI 318-19 Ch.17 pullout | Not implemented | High |
| ACI 318-19 Ch.17 interaction | Not implemented | High |
| AISC 360-22 Eq J8-2 bearing | Not implemented | Medium |
| IBC 1807.3 Eq 18-1 foundation | Not implemented | High |
| IBC 1807.3 Eq 18-2 foundation | Not implemented | Medium |
| F1554 bolt grades | Not implemented | Medium |
| AISC DG1 base plate design | Not implemented | Medium |
