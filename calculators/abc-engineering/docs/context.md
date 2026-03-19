# Sign Engineering Calculator — Technical Context

## What It Is

A self-contained single-file HTML/CSS/JavaScript application for structural engineering calculations on freestanding signs. No server, no dependencies, no build step — just open the HTML file in any browser.

Built as a modern replacement for a legacy Windows desktop application that performed the same calculations using VBScript macros and Excel spreadsheets.

---

## The Engineering Problem It Solves

When a sign company installs a freestanding sign, they must verify that the structure will survive wind loads. This requires calculating:

1. **How hard will wind push on this sign?** (Wind Load)
2. **What size steel column is strong enough?** (Section Modulus)
3. **What size anchor bolts hold the column to the base plate?** (Anchor Bolt)
4. **How deep and wide must the concrete foundation be?** (Foundation)
5. **What gusset plates reinforce the column-to-base-plate connection?** (Gusset)

These five questions map to the five tabs in the calculator.

---

## Architecture Overview

### Single-File Design
Everything lives in `sign-engineering-calculator.html`:
- Lines 1–255: CSS (dark theme, layout, component styles)
- Lines 257–543: HTML (header, tabs, sidebar inputs, results panel)
- Lines 545–589: Engineering data arrays (pipe sizes, bolt sizes, soil values)
- Lines 590–1267: JavaScript (calculations, renderers, UI logic)

### Data Flow
```
User types input
    ↓
calc() called (triggered by oninput on every field)
    ↓
calcShared() → computes ALL shared values → stores in lastCalc{}
    ↓
renderers[activeTab]() → generates HTML for results panel
    ↓
updatePrompt() → generates copy-paste text summary
```

### Shared State (`lastCalc` object)
All five tabs read from a single `lastCalc` object. When any input changes, the entire object is recomputed and all tabs reflect the new values. This means:
- Switch from Section Modulus tab to Foundation tab → same wind load, same moment, just different output
- The summary strip in the header always shows the current values across all tabs

---

## The Five Calculation Tabs

### Tab 1: Section Modulus
**Question:** What size steel column is needed?

**Inputs:** Sign width, height, clearance above ground, number of columns, steel condition (new/used)

**Calculation chain:**
1. Wind load (from sidebar) → PSF (pounds per square foot)
2. Wind force = PSF × sign area
3. Force per column = total force ÷ number of columns
4. Moment at base = force × (clearance + half sign height)
5. Required section modulus (S_req) = moment ÷ allowable stress
6. Scan PIPE[] array → first pipe where S ≥ S_req = recommendation

**Output:** Recommended pipe size (nominal inches, Schedule 40), with section modulus comparison

**Auto-feasibility grid:** Shows quick estimates for bolt, foundation, and gusset based on the recommended pipe

### Tab 2: Anchor Bolt
**Question:** What size bolts anchor the column base plate to the concrete?

**Inputs:** Bolt pattern (bolts per row, rows), bolt spacing, base plate dimensions

**Calculation chain:**
1. Total bolt count = bolts per row × rows
2. Bolt group moment arm from geometry
3. Maximum bolt tension = overturning moment ÷ bolt group resistance
4. Required tensile area = tension ÷ allowable bolt stress (20 ksi for A307)
5. Scan BOLT[] array → smallest bolt where At ≥ required = recommendation

**Output:** Recommended bolt diameter (A307 steel), with tensile area comparison and minimum base plate size

### Tab 3: Foundation
**Question:** How big does the concrete pier need to be?

**Foundation types:** Circular caisson, square caisson, or rectangular spread footing

**Inputs:** Foundation dimensions (diameter or width/length, depth), soil type

**Three checks (all must pass):**
1. **Overturning:** SF = resisting moment ÷ overturning moment ≥ 1.5
2. **Sliding:** SF = lateral soil resistance ÷ horizontal force ≥ 1.5
3. **Bearing:** Maximum soil pressure ≤ soil bearing capacity

**Auto-sizing:** Iterates candidate dimensions (1' to 20') to find smallest passing foundation

**Output:** Pass/fail for each check with safety factors, diagram showing forces, auto-minimum size

### Tab 4: Gusset Table
**Question:** What gusset plates should be used for each pipe size?

**No user inputs on this tab** — it's a reference table derived from the sign inputs.

Shows all 21 Schedule 40 pipe sizes with:
- Gusset leg length
- Gusset plate thickness
- Fillet weld size
- Minimum base plate size

Highlights the recommended pipe row (from Section Modulus tab).

**Key rules:**
- 4 gussets at 90° around the pipe
- Gusset thickness ≥ 2× column wall thickness
- Base plate thickness ≥ 2× column wall thickness
- Without gussets ≈ 70% of column section modulus

### Tab 5: Soil Reference
**No calculations** — reference table showing UBC Table 18-I-A soil bearing values for Clay, Sand, Gravel, and Rock.

---

## Wind Load Calculation

The sidebar inputs drive everything. Two methods are supported:

### ASCE 7 Method (default, ASCE 7-10/16/22)
```
qz = 0.00256 × Kz × Kzt × Kd × Ke × V²
F  = qz × G × Cf × As
```
- V = wind speed (mph) — default 115 mph for Iowa
- Kz = exposure factor (height-dependent, from ASCE 7 Table 26.10-1)
- Kzt = topographic factor (usually 1.0 for flat terrain)
- Kd = wind directionality factor (0.85 for buildings/signs)
- Ke = ground elevation factor (1.0 at sea level)
- G = gust factor (0.85 for rigid structures)
- Cf = force coefficient (1.3 for flat signs by default)
- As = sign face area (ft²)

### UBC 1997 Method (legacy)
```
P = Ce × Cq × qs × Iw
```
User enters PSF directly. Used for validating old projects or permit submissions that require legacy code.

---

## Data Tables Embedded in Code

### PIPE[] — 21 Schedule 40 Pipe Sizes (2" to 36")
Each entry: `{ nom, od, wall, sm, gLeg, gThk, weld }`
- Section modulus values match the legacy gusset table exactly
- Gusset dimensions come from the original engineering reference

### BOLT[] — 11 A307 Bolt Sizes (1/2" to 3")
Each entry: `{ dia, At, lbl }`
- At = tensile stress area (in²) per AISC/ASTM tables
- A307 allowable tensile stress = 20 ksi

### SOIL{} — 4 Soil Types
```
clay:   vertical 1000 psf, lateral 100 psf/ft
sand:   vertical 1500 psf, lateral 150 psf/ft
gravel: vertical 2000 psf, lateral 200 psf/ft
rock:   vertical 2000 psf, lateral 400 psf/ft
```
Values from UBC Table 18-I-A (also used in IBC Table 1806.2).

---

## Building Code Context

| Code | Standard | When |
|------|----------|------|
| UBC 1997 | Legacy PSF direct | Pre-2000 projects, some older jurisdictions |
| ASCE 7-10 / IBC 2015 | V₃s speed maps | Projects designed 2012–2016 |
| ASCE 7-16 / IBC 2018 | Adds Ke factor | Projects designed 2016–2021 |
| ASCE 7-22 / IBC 2024 | Current | **Default — Iowa adoption** |

Iowa uses IBC 2024 which references ASCE 7-22. Default wind speed is 115 mph (Risk Category II).

---

## Relationship to Legacy Software

The legacy desktop application (Windows MFC/C++) performed the same calculations via:
- **VBScript modules:** BoltBase.vbs, CSRFound.vbs, SprFound.vbs
- **Excel templates:** BoltBase.xls, CSRFound.xls, Gusset.xls, SprFound.xls
- **Engineering basis:** UBC 1997 (the legacy app only supported UBC 1997)

The web calculator adds:
- ASCE 7-10/16/22 support (current codes)
- Real-time recalculation (legacy had a "Calculate" button)
- Auto-sizing for foundation and bolt (legacy required manual iteration)
- Auto-feasibility summary grid
- SVG diagrams

The web calculator is missing (from the legacy app):
- Pipe sizes 38"–60"
- Schedule 80 pipe data
- Pipe weight per foot
- Average centroid height calculator for multi-cabinet signs
- Spread footing foundation type
- Washer sizing for mechanical anchorage

---

## Known Engineering Gaps (Not Yet Implemented)

These are valid code-compliant checks that are not yet in the calculator:

| Feature | Standard | Status |
|---------|----------|--------|
| IBC 1807.3 Eq 18-1 | Nonconstrained embedded post | Not yet |
| IBC 1807.3 Eq 18-2 | Constrained embedded post | Not yet |
| ACI 318-19 §17.6.2 | Concrete breakout in tension | Not yet |
| ACI 318-19 §17.6.3 | Pullout in tension | Not yet |
| ACI 318-19 §17.6.4 | Side-face blowout | Not yet |
| ASTM F1554 bolt grades | Gr36/55/105 (vs A307 only) | Not yet |
| AISC 360-22 J8-2 | Baseplate concrete bearing | Not yet |
| AISC DG1 | Base plate thickness | Not yet |
| Cf auto-calc | ASCE 7 Fig 29.3-1 | Not yet |
| PDF reports | PE-stampable output | Not yet |
