# Session Handoff Document

## Project Identity
- **Project**: Sign Engineering Calculator (sign structural engineering calculator)
- **Primary File**: `sign-engineering-calculator.html` - single-file, self-contained HTML application

## What Has Been Built (Complete Feature List)

### Core Calculation Engine
1. **Wind load calculation** - ASCE 7 velocity pressure method with all factors (Kz, Kzt, Kd, Ke, G, Cf)
2. **UBC 1997 legacy mode** - direct PSF input for older projects
3. **Code selector** - switch between UBC 1997, ASCE 7-10, ASCE 7-16, ASCE 7-22
4. **Section modulus** - S_req from moment and allowable stress
5. **Column auto-selection** - from 21 Sch 40 pipes (2"-36") and 10 square tubes (2"-12")
6. **Anchor bolt sizing** - A307 tensile area check, auto-find smallest bolt
7. **Foundation design** - overturning, sliding, bearing checks for circular/square/rectangular
8. **Foundation auto-sizing** - iterates to find minimum passing dimensions
9. **Gusset table** - pre-engineered gusset/baseplate data for all 21 pipe sizes
10. **Auto-feasibility summary** - bolt + foundation + gusset + weight estimate on Section Modulus tab
11. **Summary strip** - header bar showing S_req, wind, moment, pipe, bolt, foundation at a glance
12. **SVG diagrams** - sign elevation and foundation cross-section
13. **Prompt generator** - copy-paste text summary of all calculations
14. **6 sign presets** - Small, Medium, Monument, Pole Sign, Highway, EMC
15. **4 foundation presets** - Sm Caisson, Med Caisson, Lg Square, Spread
16. **Soil reference tab** - UBC Table 18-I-A with classification info
17. **New vs Used steel** toggle - 0.66Fy vs 0.60Fy allowable stress

### UI/UX
- Dark theme with CSS custom properties
- Real-time recalculation on every input change
- Collapsible sidebar sections
- Tab-based navigation with tab-specific controls
- Color-coded pass/warn/fail indicators
- Monospace font for engineering values
- Responsive summary strip in header

## What Has NOT Been Built (Known Gaps)

### High Priority (Engineering Accuracy)
1. **IBC 1807.3 Eq 18-1** - nonconstrained foundation formula (code-compliant method)
2. **IBC 1807.3 Eq 18-2** - constrained foundation formula (slab-constrained)
3. **ACI 318-19 Ch.17** - concrete breakout in tension (most critical check)
4. **ACI 318-19 Ch.17** - pullout in tension
5. **ACI 318-19 Ch.17** - side-face blowout
6. **ACI 318-19 Ch.17** - concrete breakout/pryout in shear
7. **ACI 318-19 Ch.17** - tension + shear interaction equation
8. **ASTM F1554 bolt grades** - Grade 36/55/105 (currently only A307)
9. **Cf auto-calculation** - from ASCE 7 Figure 29.3-1 based on B/s and s/h ratios
10. **AISC 360-22 Eq J8-2** - baseplate concrete bearing check
11. **42" frost line enforcement** - Iowa minimum depth warning

### High Priority (Business Value)
12. **PDF report generation** - PE-stampable calculation sheets
13. **Materials list output** - bill of materials from calculations

### Medium Priority
14. **AISC Design Guide 1** - proper base plate thickness calculation
15. **Weld sizing** - per AISC 360-22
16. **Wind speed by zip code** - auto-lookup
17. **Multi-code comparison** - show results under all codes simultaneously
18. **Construction drawing generation** - basic structural drawings

### Future / Differentiators
19. **3D visualization** - Three.js sign structure preview
20. **AI PDF parsing** - extract dimensions from shop drawings
21. **Dynamic what-if analysis** - parameter sensitivity
22. **AR site previews** - augmented reality sign placement

## Research Completed

### Competitor Intelligence
- **Competitor A** (SaaS): Blazor app, generates construction drawings + materials lists + PE-stampable calc sheets, all 50 states
- **Competitor B** (WAaaS): Blazor app, on ASCE 7-10/IBC 2015 (outdated)
- Neither competitor's actual calculations or UI could be captured (Blazor blocks scraping)

### Code Standards Research
- Complete reference for IBC 2024, ASCE 7-22, AISC 360-22, ACI 318-19/25, AISC DG1
- All formulas documented in `docs/formulas.md`
- Iowa-specific requirements documented
- Code timeline from UBC 1997 through IBC 2024

### Technology Research
- Competing tools both use Blazor/WebAssembly (C#/.NET in browser)

## Failed Attempts (Don't Retry These)

1. **WebFetch on competitor SaaS sites** - Blazor returns empty shell + "unhandled error"
2. **PowerShell Chrome tab switching** - unreliable, doesn't capture competitor app UI

## Technical Environment
- **No build system** - single HTML file, open directly in browser
- **No dependencies** - everything is vanilla HTML/CSS/JS

## Key Decisions Made
1. **Single-file architecture** - intentional, not a limitation. Zero deployment complexity.
2. **ASCE 7-22 as default** - most current code, adopted in Iowa
3. **A307 bolts as baseline** - most common for sign work, F1554 grades to be added
4. **Simplified foundation method** - works but needs IBC 1807.3 upgrade
5. **Dark theme** - matches engineering software aesthetics
6. **No frameworks** - vanilla JS keeps file small and dependency-free
7. **PSF as common unit** - all wind methods convert to PSF for downstream calcs
8. **Safety factor 1.5** - standard for foundation overturning and sliding

## How to Continue Development
1. Read `CLAUDE.md` for project context
2. Read `sign-engineering-calculator.html` for current code
3. Read `docs/roadmap.md` for prioritized work items
4. Read `docs/formulas.md` for engineering reference
5. Read `docs/engineering-codes.md` for code standard details
6. Make changes to the HTML file
7. Test by opening in browser
8. All calculations should be validated against hand calculations or known references
