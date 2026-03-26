# SignCalc v3.0 — Project State
**Status:** Active development | **Last updated:** 2026-03-25

## Completed (this session + prior)

### Engineering Code Corrections (2026-03-25)
- [x] F1554 bolt Ft values: 0.33×Fu → **0.375×Fu** per AISC 360-22 ASD (all grades verified)
- [x] ACI 318-19 §17.6.2.2: Added **λ=1.0** factor to Nb formula (was missing)
- [x] Hatch labeling: ANSI37 removed (metals), **AR-CONC** labeled correctly as concrete aggregate
- [x] Company name: "Eagle Sign & Design Inc." → **"Eagle Sign Co."** throughout UI, drawing, PDF

### Drawing / SVG (2026-03-25)
- [x] AR-CONC concrete hatch: 24×24 tile, 10 diagonal lines + 6 irregular aggregate ellipses
- [x] ANSI Earth soil hatch: horizontal lines + diagonal downward ticks (ANSI standard)
- [x] ANSI32 steel hatch: proper 45°+135° cross-hatch
- [x] Column width: `Math.max(8, signW_px * 0.06, 20)` — was `max(5, signW*0.045, 14)` (too thin)
- [x] Base plate width: `colW_px * 2.8` — was 3.5× (too wide)
- [x] Column hidden line: full `fd_px` depth — was `fd_px * 0.7` (column appeared to float)

### UI / Theme (2026-03-25)
- [x] Courier New monospace throughout — instrument-panel aesthetic
- [x] Zero border-radius everywhere — square/technical corners
- [x] 16px graph-paper grid overlay on input panel
- [x] LED dot spans (`.chip-led`) on all 4 status chips
- [x] `.header-sep` and `.footer-sep` dividers added
- [x] Footer: pipe-separated standard citations, Eagle Sign Co. right-aligned

### Documentation (2026-03-25)
- [x] CLAUDE.md rewritten to reflect v3.0 state (commit 9679c47)
- [x] behavioral-rules.md: SignCalc Engineering Code Scar Tissue section added (5 rules)

---

## Open / Next-Level Features (Brady's request 2026-03-25)

### Engineering Checks
- [ ] **Column deflection check** — AASHTO LTS-6 §10.4.2.1, δ ≤ L/40 (2.5% of height). Do NOT cite AISC DG1.
- [ ] **autoCf rigorous** — Add `s` (clearance) input; implement B/s AND s/h ratios per ASCE 7-22 §29.3 Fig. 29.3-1
- [ ] **Case B torsion** — ASCE 7-22 §29.3, eccentricity Dx=0.2B
- [ ] **LRFD load combos** — 1.2D+1.6W / 0.9D+1.0W for ACI 318-19 §17 anchor design
- [ ] **ACI λ select** — Add lightweight concrete toggle (λ=0.75)
- [ ] **Weld size check** — fillet weld at base plate / column
- [ ] **Dead load estimator** — auto-estimate from cabinet type (channel letters, faces, LED, etc.)

### UX / Features
- [ ] **DCR gauges** — demand/capacity ratio visual gauges on each result card
- [ ] **Share via URL** — #hash-encode all inputs for shareable links
- [ ] **ZIP → wind speed** — auto-populate V from ZIP code lookup
- [ ] **PDF stamp block** — PE signature/seal placeholder in PDF report

---

## Known Limitations (documented in code)
- `autoCf()` uses W/H approximation only — comment in code flags this
- ACI λ hardcoded to 1.0 (normal-weight only)
- No LRFD path (ASD only)
- No column deflection check
- Case B wind eccentricity not implemented
