# Development Roadmap

## Phase 1: Foundation Accuracy (High Priority)

### 1.1 IBC 1807.3 Eq 18-1 (Nonconstrained)
**What**: Replace simplified overturning check with the actual IBC code formula for embedded posts.
**Why**: This is what a PE reviewer checks against. Our current simplified method may give different results.
**Formula**: d = 0.5*A*{1+[1+(4.36*h/A)]^0.5}, A = 2.34*P/(S1*b)
**Implementation**:
- Add toggle: "Simplified" vs "IBC 1807.3" method
- Keep simplified as option for quick estimates
- Show both results side-by-side initially for validation
- S1 values from IBC Table 1806.2

### 1.2 IBC 1807.3 Eq 18-2 (Constrained)
**What**: Add constrained foundation option for slab-on-grade installations.
**Formula**: d^2 = 4.25*(P*h)/(S3*b)
**When**: Monument signs on concrete pads, signs through parking lot slabs

### 1.3 Iowa Frost Line Enforcement
**What**: Hard minimum 42" depth for Iowa installations.
**Implementation**: Warning/override when depth < 42", option for other states

### 1.4 Soil Bearing per IBC Table 1806.2
**What**: Update soil table to match IBC 2024 Table 1806.2 (may differ slightly from current UBC values).

---

## Phase 2: Anchor Bolt Accuracy (High Priority)

### 2.1 ASTM F1554 Bolt Grades
**What**: Add Grade 36, 55, 105 alongside current A307.
**Implementation**:
- Dropdown or radio: A307 / F1554 Gr36 / F1554 Gr55 / F1554 Gr105
- Update allowable stress values per grade
- Update BOLT[] array with grade-specific data

### 2.2 ACI 318-19 Ch.17 Concrete Breakout
**What**: Check concrete breakout strength in tension (17.6.2).
**Why**: This is often the governing failure mode for sign anchor bolts.
**Inputs needed**: f'c (concrete strength), h_ef (embedment depth), edge distances
**Formula**: N_cbg = (A_Nc/A_Nco) * psi factors * N_b

### 2.3 ACI 318-19 Pullout
**What**: Check pullout strength in tension (17.6.3).
**Formula**: N_pn = psi_c,P * N_p, where N_p = 8 * A_brg * f'c (for headed bolts)

### 2.4 ACI 318-19 Tension + Shear Interaction
**What**: Combined check when both tension and shear are significant.
**Formula**: N_ua/(phi*N_n) + V_ua/(phi*V_n) <= 1.2

### 2.5 Side-Face Blowout
**What**: Check when anchors are near pier edges (17.6.4).
**When**: Small diameter foundations where bolt is close to edge of concrete

---

## Phase 3: Baseplate Design (Medium Priority)

### 3.1 AISC 360-22 Eq J8-2 Bearing
**What**: Check concrete bearing stress under base plate.
**Formula**: phi_c * Pp = phi_c * 0.85 * f'c * A1 * sqrt(A2/A1)
**Inputs needed**: f'c, base plate dimensions, foundation dimensions

### 3.2 AISC Design Guide 1 Base Plate Sizing
**What**: Proper base plate thickness calculation.
**Method**: Based on cantilever bending of plate beyond column face

### 3.3 Weld Sizing
**What**: Size fillet welds connecting column to base plate per AISC 360-22.

---

## Phase 4: Output & Reports (High Business Value)

### 4.1 PDF Report Generation
**What**: Generate downloadable PDF calculation summary.
**Content**: All inputs, calculation steps, results, pass/fail checks
**Technology options**: jsPDF (client-side), html2canvas + jsPDF
**Why critical**: This is CalcuSign's #1 selling point

### 4.2 Materials List
**What**: Generate bill of materials from calculation results.
**Content**: Pipe size/length, bolt count/size, base plate dimensions, concrete volume, gusset specs

### 4.3 PE-Stampable Format
**What**: Format output to match what PEs expect for stamping.
**Content**: Cover sheet, calculation pages with equation references, sketches, summary

---

## Phase 5: Advanced Features (Future / Differentiators)

### 5.1 Cf Auto-Calculation
**What**: Auto-calculate force coefficient from ASCE 7 Figure 29.3-1.
**Implementation**: Lookup table based on B/s ratio and s/h ratio.
**Impact**: Removes a manual input that most users get wrong.

### 5.2 Wind Speed by Zip Code
**What**: Enter zip or address, auto-populate wind speed.
**Data source**: ASCE 7-22 wind speed maps (need digitized data or API)
**Iowa default**: 115 mph already set

### 5.3 Multi-Code Comparison
**What**: Show calculation results under all 4 codes simultaneously.
**Why**: Helps users understand code differences, useful for existing sign evaluation

### 5.4 3D Visualization
**What**: Three.js or similar 3D preview of sign structure.
**Shows**: Column(s), sign face, base plate, foundation, bolts

### 5.5 Dynamic What-If Analysis
**What**: Slider-based parameter exploration with live chart updates.
**Example**: Drag wind speed slider, watch foundation depth requirement change in real-time

### 5.6 Construction Drawing Generation
**What**: Auto-generate basic structural drawings (plan view, elevation, foundation detail).
**Technology**: SVG export or Canvas-based drawing

---

## Implementation Notes

### Keep Single-File Architecture
The single HTML file approach is a major advantage:
- Zero deployment complexity
- Works offline
- No build system to maintain
- Easy to share (just email the file)
- No server costs

For PDF generation, use client-side libraries (jsPDF) that can be embedded or loaded from CDN.

### Testing Strategy
Since this is engineering software where wrong answers have safety implications:
- Validate every formula against hand calculations
- Cross-check against known-good engineering references
- Test edge cases (very tall signs, very small foundations, max bolt sizes)
- Compare results with Accutrack for same inputs (when possible)
- Document all validation in a test log
