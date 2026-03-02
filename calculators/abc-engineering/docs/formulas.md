# Engineering Formulas Reference

## Currently Implemented

### Wind Load (ASCE 7)
```
F = qz * G * Cf * As              (total wind force on sign, lbs)
qz = 0.00256 * Kz * Kzt * Kd * Ke * V^2   (velocity pressure, psf)
```

Where:
- V = basic wind speed (mph) - Iowa default: 115
- Kz = velocity pressure exposure coefficient (from height + exposure)
- Kzt = topographic factor (default 1.0)
- Kd = wind directionality factor (0.85 for signs)
- Ke = ground elevation factor (default 1.0, introduced in ASCE 7-16)
- G = gust-effect factor (0.85 for rigid structures)
- Cf = net force coefficient (default 1.2, should auto-calc from Fig 29.3-1)
- As = gross area of sign face (sf)

### Kz Calculation (ASCE 7 Table 26.10-1)
```
Kz = 2.01 * (z / zg)^(2/alpha)
z = max(15, min(h, zg))           (effective height, ft)
```

| Exposure | alpha | zg (ft) |
|----------|-------|---------|
| B | 7.0 | 1200 |
| C | 9.5 | 900 |
| D | 11.5 | 700 |

### Section Modulus
```
M_ft = F_per_col * centroid_height   (moment at base, ft-lbs)
M_in = M_ft * 12                     (moment in in-lbs)
S_req = M_in / F_allow               (required section modulus, in^3)
```

Where:
- F_per_col = total_wind_force / number_of_columns
- centroid_height = ground_clearance + sign_height/2
- F_allow = 0.66 * Fy (new steel) or 0.60 * Fy (used steel)
- Fy = 36,000 psi (A36 steel)

### Anchor Bolt (A307 Simple Check)
```
T_req = M_in / (n_per_row * spacing * Fb)   (required tensile area per bolt)
```

Where:
- n_per_row = bolts per row in wind direction (default 2)
- spacing = bolt spacing in wind direction (default 6")
- Fb = 20,000 psi (A307 allowable tensile stress)

Select smallest bolt from table where At >= T_req.

### Foundation Checks (Current Simplified Method)

**Bearing:**
```
q = (DL + W_concrete) / A_foundation
Pass if q <= allowable_vertical_soil_pressure
```

**Overturning (about base of pier):**
```
OT_moment = M_per_col + F_per_col * depth
R_gravity = total_vertical_load * (width / 2)
R_soil = S_lateral * width * depth^2 / 2
SF_ot = (R_gravity + R_soil) / OT_moment
Pass if SF >= 1.5
```

**Sliding:**
```
F_friction = total_vertical_load * 0.35
F_passive = S_lateral * width * depth
SF_slide = (F_friction + F_passive) / F_per_col
Pass if SF >= 1.5
```

### Pipe Weight
```
W_per_ft = 10.69 * (OD - wall) * wall   (lbs/ft, Sch 40 steel pipe)
```

### Base Plate Minimum Size
```
Min_BP = OD + 2 * (gusset_leg + fillet_weld)
```

### Perimeter-Based Force (PBF)
```
PBF = total_wind_force / sign_perimeter   (lbs/ft)
```

---

## Not Yet Implemented (Needed)

### IBC 1807.3 Eq 18-1: Nonconstrained Foundation
For posts/poles embedded in soil WITHOUT lateral constraint at ground surface:
```
d = 0.5 * A * {1 + [1 + (4.36 * h / A)]^0.5}
A = 2.34 * P / (S1 * b)
```

Where:
- d = required depth of embedment (ft)
- h = distance from ground surface to point of application of lateral force (ft)
- P = applied lateral force (lbs)
- S1 = allowable lateral soil-bearing pressure as set forth in IBC Section 1806.2, based on a depth of one-third the depth of embedment (psf/ft depth)
- b = diameter of round post or footing, or diagonal dimension of square post or footing (ft)

### IBC 1807.3 Eq 18-2: Constrained Foundation
For posts/poles with lateral constraint at ground surface (concrete slab, pavement):
```
d^2 = 4.25 * (P * h) / (S3 * b)
```

Where:
- S3 = allowable lateral soil-bearing pressure as set forth in IBC Section 1806.2, based on a depth equal to the depth of embedment (psf)

### ACI 318-19 Chapter 17: Concrete Breakout (Tension)
```
N_cbg = (A_Nc / A_Nco) * psi_ec,N * psi_ed,N * psi_c,N * psi_cp,N * N_b
N_b = k_c * lambda_a * sqrt(f'c) * h_ef^1.5
A_Nco = 9 * h_ef^2
```

Where:
- h_ef = effective anchor embedment depth
- f'c = concrete compressive strength (psi)
- k_c = 24 for cast-in anchors, 17 for post-installed
- lambda_a = 1.0 for normal weight concrete
- psi factors = modification factors for eccentricity, edge, cracking, splitting

### ACI 318-19: Concrete Breakout (Shear)
```
V_cbg = (A_Vc / A_Vco) * psi_ec,V * psi_ed,V * psi_c,V * psi_h,V * V_b
V_b = min(7 * (l_e/d_a)^0.2 * sqrt(d_a) * lambda_a * sqrt(f'c) * c_a1^1.5,
          9 * lambda_a * sqrt(f'c) * c_a1^1.5)
```

### ACI 318-19: Tension + Shear Interaction
```
If N_ua/(phi*N_n) <= 0.2: full shear capacity available
If V_ua/(phi*V_n) <= 0.2: full tension capacity available
Otherwise: N_ua/(phi*N_n) + V_ua/(phi*V_n) <= 1.2
```

### AISC 360-22 Eq J8-2: Base Plate Bearing
```
phi_c * Pp = phi_c * 0.85 * f'c * A1 * sqrt(A2/A1)
Upper limit: phi_c * 1.7 * f'c * A1
phi_c = 0.65
```

Where:
- f'c = concrete compressive strength (psi)
- A1 = area of base plate (in^2)
- A2 = maximum area of the portion of the supporting surface that is geometrically similar to and concentric with the loaded area (in^2)

### Cf Auto-Calculation (ASCE 7 Fig 29.3-1)
```
B/s = sign_width / sign_height
s/h = sign_height / (ground_clearance + sign_height)

Cf lookup table from Figure 29.3-1:
- For s/h <= 0.05 (near ground): Cf ranges 1.2 to 1.8 depending on B/s
- For s/h = 1.0 (ground-mounted): Cf ranges 1.0 to 1.3
- Interpolate for intermediate values
```

### ASTM F1554 Bolt Capacity
```
T_n = F_nt * A_bolt    (nominal tensile strength)

Grade 36: F_nt = 58 ksi (ultimate), F_y = 36 ksi
Grade 55: F_nt = 75 ksi (ultimate), F_y = 55 ksi
Grade 105: F_nt = 125 ksi (ultimate), F_y = 105 ksi

ASD allowable: T_a = 0.75 * F_nt / 2.0 * A_bolt
```
