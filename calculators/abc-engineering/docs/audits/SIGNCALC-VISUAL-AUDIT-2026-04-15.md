# SignCalc v4 — Visual & UI Audit Report
**Date:** 2026-04-15  **Auditor:** Claude Opus designer agent
**Scope:** SVG drawing, title block, base plate inset, result cards, PDF report, input form

## CRITICAL (18 total)
- C-1: Foundation width uses above-grade scale; depth uses compressed scale → distorted caisson proportions
- C-2: Below-grade column hidden lines + foundation use mismatched scales — silent proportion error
- C-3: Foundation depth dim label shows only number — no "FND DEPTH" or "EMBED" qualifier
- C-4: Wind arrow terminates 3px short of sign face — should touch surface (ASME Y14.36)
- C-5: No moment arm annotation h= from resultant to grade
- C-6: SHEET / 1 OF 1 centering — mix of anchor styles (middle vs start) in same title block row
- C-7: Missing APPROVED BY / CHECKED BY cells (ANSI Y14.1 requirement for PE review)
- C-8: Base plate inset silently omitted for embedded connection — needs alternate detail
- C-9: Bolt pattern is rectangular grid but label says "B.C." (Bolt Circle) — wrong label
- C-10: ACI 318-19 result card shows only Ncbg — 6 of 7 limit states missing from display
- C-11: PDF has no drawing (SVG never embedded) — PE calc without pictorial is incomplete
- C-12: PDF missing pullout, side-face, bearing in ACI anchor section
- C-13: PDF footer typo: "Generated2026-04-15" (missing space)
- C-14: Default V=115 mph is correct for Iowa RC-II (ASCE 7-22 Fig 26.5-1B) — NOT a defect ✓
- C-16: Entire file uses var (ES5), no scoping — global state race conditions possible
- C-17: No unit tests for a safety-critical calculator
- C-18: SVG arrow marker `ldrA` declared inside updateDrawing() on every redraw — should be in getSVGDefs()

## MAJOR HIGHLIGHTS (43 total — see full report)
- M-1: Circular foundation width dim missing ⌀ prefix (ASME Y14.5)
- M-2: Frost line phantom dash pattern nonstandard (ASME Y14.2)
- M-3: Frost label mask punches opaque hole in soil hatch
- M-5: Column callout leader collides with right-side dim lines
- M-11: DRAWN BY field hardcoded "SignCalc" — should be engineer name
- M-12: DWG NO hardcoded "SC-YYYY-001" — no uniqueness per project
- M-16: Base plate inset never labels plate size (PL W×L×t)
- M-17: Column OD not shown inside base plate plan inset
- M-20: "0.66Fy §F2 conservative" label — remove "conservative"; it IS the code allowable
- M-21: Frost depth hardcoded 48" Iowa — should be configurable for other states
- M-22: Case B wind not shown in Wind Results card
- M-23: Base plate bearing uses LRFD φ=0.65 mixed with ASD everywhere else — must label
- m-12 MISLABELED (actually Major): edgeMin calculation wrong for bolt grids >2 bolts

## POLISH HIGHLIGHTS
- p-6: Font size stack has F_TITLE=9 < F_VALUE=9.5 — title should be largest
- p-8: No card border-left color stripe for at-a-glance status
- p-9: Decimal places inconsistent across result rows (0dp vs 2dp vs 3dp)

## TOP 10 ACTIONABLE QUICK FIXES
1. Foundation uniform scale (C-1/C-2) — use scale_below for both fd_px AND fw_px
2. All 7 ACI limit states in result cards (C-10)
3. Embed SVG in PDF (C-11) — XMLSerializer → canvas → doc.addImage
4. Foundation depth dim: add "EMBED" label (C-3)
5. Foundation width dim: add ⌀ prefix for circular (M-1)
6. Wire title block DRAWN BY/DWG NO/REV to project meta (M-11/M-12/M-13)
7. Label base plate inset with PL dimensions (M-16)
8. Fix "B.C." → "O.C." on rectangular bolt pattern (C-9)
9. PDF footer space typo (C-13) — 1 character fix
10. Frost depth configurable for non-Iowa (M-21)
