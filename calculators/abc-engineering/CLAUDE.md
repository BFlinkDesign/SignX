# SignCalc v3.0 — Sign Engineering Calculator

## Project Overview
Single-file HTML application for sign structural engineering calculations.
**Primary file:** `sign-engineering-calculator.html` (~1700 lines, fully self-contained, zero dependencies)
**Last major update:** 2026-03-25 — GD&T drawing overhaul, engineering code corrections

## Architecture
- **Single HTML file** — embedded CSS + JS, no build system, no npm, no frameworks
- **3-panel layout**: Input panel (left 280px) | SVG drawing (center) | Results panel (right 320px)
- **Header**: SIGNCALC wordmark, live status chips (PASS/FAIL/WARN), code picker, PDF export
- **Shared state**: all inputs flow through `calcShared()` → `lastCalc` object → all result cards
- **LocalStorage** auto-saves and restores all inputs on reload

## Key Functions
| Function | Purpose |
|----------|---------|
| `calcShared()` | Master calculation — populates `lastCalc`, triggers all card renders |
| `calcWindPSF()` | ASCE 7-22 Eq. 26.10-1: qz×G×Cf; UBC 1997 direct PSF legacy path |
| `calcBoltData()` | Anchor bolt tension/shear per AISC 360 ASD |
| `calcFoundSized(w,d)` | Foundation check for given dimensions (OT, sliding, bearing) |
| `findMinFoundation()` | Brute-force w=1.5–10ft, d=3.5–20ft to find smallest passing caisson |
| `calcACI318Breakout()` | ACI 318-19 §17.6.2.2 concrete cone breakout — phi=0.70 Cond. B |
| `updateDrawing()` | Generates full SVG elevation with GD&T standards |
| `getSVGDefs()` | ANSI hatch patterns + GD&T arrowhead markers |
| `buildDimLine()` | ASME Y14.5 dimension lines (extension line gap/overshoot, paper mask) |
| `buildStatusBubble()` | Auto-width PASS/FAIL bubbles on drawing |
| `preset(name)` | Apply sign preset → calc() → findMinFoundation() (auto-sizes foundation) |
| `generatePDF()` | jsPDF calculation report (PE-stampable format) |

## Engineering Standards Implemented
| Check | Standard | Notes |
|-------|---------|-------|
| Wind load | ASCE 7-22 §29.3.1 | F = qz·G·Cf·Af |
| Cf auto | ASCE 7-22 §29.3 Fig 29.3-1 | **APPROXIMATION**: uses W/H ratio only; rigorous Cf requires both B/s AND s/h — see autoCf() comment |
| Column section modulus | AISC 360-22 | S_req = M/Fb |
| Base plate bearing | AISC 360-22 §J8-2 | φPp = 0.65·0.85·f'c·A1·√(A2/A1), cap 1.7f'c·A1 |
| Anchor bolt tension | AISC 360 ASD | Ft = **0.375·Fu** (current); 0.33·Fu is outdated pre-9th edition |
| Concrete breakout | ACI 318-19 §17.6.2.2 | Nb = 24·λ·√f'c·hef^1.5, λ=1.0 normal-weight |
| Foundation nonconstrained | IBC 2021 §1807.3 Eq. 18-1 | A = 2.34P/(S₁b), d = 0.5A[1+√(1+4.36h/A)] |
| Foundation constrained | IBC 2021 §1807.3 Eq. 18-2 | d² = 4.25Ph/(S₃b) |
| Frost line | IBC / local | Iowa default = 42" |

## BOLT_GRADES Constants (VERIFIED 2026-03-25)
```javascript
// Ft = 0.375 * Fu per AISC 360-22 ASD (current). 0.33*Fu = outdated pre-9th-edition.
BOLT_GRADES = {
  'A307':      { Fu: 60,  Ft: 19.8  },
  'F1554_36':  { Fu: 58,  Ft: 21.75 },  // 0.375 × 58
  'F1554_55':  { Fu: 75,  Ft: 28.13 },  // 0.375 × 75
  'F1554_105': { Fu: 125, Ft: 46.88 }   // 0.375 × 125
};
```

## Drawing Panel (GD&T / ASME Y14.5-2018)
- **Background**: vellum paper `#f5f0e6` with 20px blueprint grid
- **Line weights**: visible=1.4, hidden=0.7, thin=0.5, centerline=0.4 (ASME Y14.2)
- **Hatches**: soil=earth hatch, concrete=AR-CONC style (NOT ANSI37 — that's metals), steel=ANSI32 cross-hatch, general=ANSI31 45°
- **Dimension lines**: `buildDimLine()` — GAP=4, OVERSHOOT=5, OFFSET=26; paper mask behind text; closed filled arrowheads per ASME Y14.5
- **Title block**: ANSI Y14.1 format — company="Eagle Sign Co.", DWG NO, date, scale, revision, sheet

## Company Name Rule (MANDATORY)
- **Display name**: **"Eagle Sign Co."** — use in all UI labels, drawing title blocks, PDF reports
- **Legal entity**: "Eagle Sign & Design Inc." — for legal documents only, NOT in UI/drawings
- This is confirmed in `constants.py` and CLAUDE.md global rules

## Known Code Limitations / Future Work
1. **autoCf**: Currently uses W/H ratio approximation. ASCE 7-22 §29.3 Fig. 29.3-1 requires both B/s (sign width / clearance above grade) AND s/h (sign height / mounting height). Add `s` (clearance) input for rigorous Cf.
2. **Column deflection**: No check implemented. Correct source = AASHTO LTS-6 §10.4.2.1 (δ ≤ 2.5% of height = L/40). Do NOT cite AISC DG1 — that's base plates.
3. **ACI λ**: Currently hardcoded λ=1.0. Add lightweight concrete option (λ=0.75) if needed.
4. **Case B torsion**: ASCE 7-22 §29.3 Case B eccentricity (Dx=0.2B) not yet implemented.
5. **LRFD load combos**: Only ASD implemented. Add 1.2D+1.6W / 0.9D+1.0W for ACI 318-19 §17 anchor design.

## Next-Level Features (Brady's request 2026-03-25)
1. LRFD load combinations for ACI 318-19 anchor design
2. Column deflection check per AASHTO LTS-6
3. Case B torsion (ASCE 7-22 §29.3, Dx=0.2B)
4. DCR gauges on result cards
5. Share via URL (#hash encoded inputs)
6. ZIP → wind speed lookup
7. Weld size check
8. Dead load auto-estimator from cabinet type

## Code Style
- Compact functional JS — no frameworks, no build step
- CSS custom properties in `:root` (warm neutral dark theme — no blue/cyan)
- `val(id, fallback)` helper reads numeric inputs
- Result cards generated as innerHTML strings, not DOM manipulation
- `lastCalc`, `lastFoundCalc`, `lastACI` store results for cross-function access
- Presets call `calc()` then `findMinFoundation()` to auto-size foundation
