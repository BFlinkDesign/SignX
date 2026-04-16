# SignCalc v4 — Engineering Audit Report
**Date:** 2026-04-15  **Auditor:** Claude Opus (multi-agent)  **File:** SignCalc-v4.html (3,334 lines)

---

## CRITICAL BUGS (unsafe — do not use for PE stamps in current state)

### C-1. Column shaft wind moment NEVER added to demand  
**Location:** Lines 1345-1360 (compute), 1276-1279 (lastCalc — MISSING)  
Column shaft wind (ASCE 7-22 §29.4) is computed and displayed but never folded into `momentFtLb`. All downstream checks — section sizing (Sreq), anchor design, base plate, foundation overturning — see only the sign-face moment.  
**Effect:** 5-25% undersize on column, foundation, and anchors depending on GC height.  
**Fix:** Add `M_col_wind` → `momentFtLb` and `F_col_wind` → `windForce` in lastCalc before all checks.

### C-2. W-shape bending: no lateral-torsional buckling (LTB) — AISC 360-22 §F2/F3 missing  
**Location:** Lines 1282-1288  
Flat `Fb = 0.66Fy` applied to W-shapes regardless of unbraced length. For cantilever `Lb = GC + H/2` of 20-30 ft, actual Fb from §F2/F3 can drop below `0.33Fy` — calculator reports PASS on sections that fail LTB by 50%.  
Also missing: D/t compactness check for pipe (§F8 assumes compact; fails for 14"+ Std Wt); b/t for HSS (§F7).  
**Fix:** Implement §F2 LTB with `Lb`, `Lp`, `Lr`, `Cb=1.67` (cantilever). Add D/t and b/t gates.

---

## MAJOR FINDINGS (would require PE supplement)

### M-1. No ASD load combinations (ASCE 7-22 §2.4.1)  
Uses `1.0W` throughout. Should use `D + 0.6W` for column demand; `0.6D + 0.6W` for overturning resistance. Net effect: overturning SF is optimistic (0.6D resistance vs 1.0D used).

### M-2. No deflection / drift check  
Industry standard: tip deflection ≤ H/60 (nominal wind). IBC 1604.3 requires serviceability. `Ix` is tabulated but never used for deflection.  
Formula: `δ_tip = w·L⁴/(8EI) + P·L³/(3EI)`

### M-3. Case B torsion computed but never checked  
`T_B` stored in lastCalc. No check against §H3 torsional capacity or §H1.3 interaction (flex + torsion + shear).

### M-4. Column shaft Kz: uses sign centroid height, not column centroid  
Back-solves `qz·G` from sign design pressure (at centroid `GC+H/2`), then applies to column. Column centroid is at `GC/2` — separate `qz` lookup required.

### M-5. No Risk Category / Importance Factor  
Iowa defaults should be: RC I=100 mph, RC II=110 mph, RC III=115 mph, RC IV=120 mph per ASCE 7-22 Fig 26.5-1.

### M-6. Simplified foundation: friction + passive summed (IBC 1806.3.4 requires max, not sum)  
**Non-conservative**: reported `latSF` can be 2× actual. Also passive should integrate triangularly: `0.5·Sl·b·d²` not `Sl·b·d`.  
**Fix:** Switch default to IBC 1807 Eq 18-1 (Eq 18-1 formula verified correct but cosmetic-only in current render).

---

## MINOR/REFINEMENT

| ID | Finding | Severity |
|----|---------|---------|
| m-1 | ACI anchor group area: `n·ANco` ignores bolt spacing overlap (non-conservative for tight patterns) | Minor-Major |
| m-2 | Shear breakout missing ψ_ec,V ψ_ed,V ψ_c,V ψ_h,V factors | Minor |
| m-4 | ACI Nb uses kc=24 (uncracked); default should be kc=17 (cracked) per §17.6.2.2b | Minor-Major |
| m-9 | Ke default 1.0; Grimes IA at 940 ft elevation → Ke=0.967 (conservative direction) | Minor |
| m-12 | Base plate bearing compare: `phiPp ≥ windForce` — dimensionally wrong. φPp is bearing compression vs Fy·A is shear | Major |
| m-13 | No base plate weld check (AISC §J2.4) or anchor edge distance (§J3.4) | Major |
| m-14 | No AASHTO LTS-6 disclaimer for highway signs | Minor |

---

## VERIFIED CORRECT ✓

- Kz table lookup (ASCE 7-22 Table 26.10-1, exact values, linear interp)
- Cf Fig 29.3-1: Cases A/B/C with B/s and s/h interpolation
- Case B eccentricity `0.2·B`; governing case selection
- GCpi correctly omitted (external force only for solid signs)
- Fb=0.76Fy pipe §F8; Fb=0.72Fy HSS §F7 (compact assumed — D/t check needed)
- KL/r slenderness with K=2.0; Fcr §E3 elastic/inelastic branches (displayed)
- Section modulus S (elastic, ASD) — correct; spot-checked NPS 6/8/10 vs AISC ✓
- ACI 318-19 steel tension §17.6.1; pullout §17.6.3; interaction §17.8 (5/3, 0.2 thresholds)
- ACI edge factor ψ_ed §17.6.2.4
- AISC DG1 base plate: N×B, m/n/λn cantilevers, plate thickness formula
- IBC 1807 Eq 18-1 and 18-2 formulas (correct, but used cosmetically not for pass/fail)
- Frost depth 48" gates foundAllPass correctly
- Material Fy: A53 Gr B=35, A500 Gr C=46, A992=50 ksi ✓
- F1554 grades 36/55/105, Fu values (58/75/125) ✓

---

## Upgrade Roadmap (Priority Order)

**Tier 1 — Required for any PE-stamped use:**
1. C-1: Fold column shaft wind into downstream moment/force demand
2. C-2: AISC §F2 LTB for W-shapes; D/t compactness for pipe; b/t for HSS
3. M-1: ASD load combos D+0.6W (demand), 0.6D+0.6W (overturning)
4. M-6: Fix foundation passive to triangular; IBC 1807 Eq 18-1 as default pass/fail
5. m-12: Fix base plate bearing comparison

**Tier 2 — Completeness:**
6. M-2: Tip deflection check H/60
7. M-3: §H3 torsion + §H1.3 interaction for Case B
8. M-4: Column shaft Kz at GC/2
9. M-5: Risk Category selector with IA mapped V defaults
10. m-1/m-4: ACI group ANc from plate geometry; kc=17 cracked default
11. m-13: Weld check + anchor edge distance

**Tier 3 — Refinement:**
12. m-7: Open-frame Cf (Fig 29.4-1) for solidity <70%
13. m-9: Auto-Ke from site elevation (Grimes 940 ft default)
14. m-14: AASHTO LTS-6 disclaimer
