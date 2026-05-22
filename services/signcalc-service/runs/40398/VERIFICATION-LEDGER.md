# 40398 — Verification Ledger (read with STATUS.md)

Purpose: separate evidence-backed facts from reasoning so the fresh
session does NOT inherit unverified claims as grounded. No completion
claims. Nothing here is approved/canonical (see STATUS.md).

## VERIFIED — fresh tool/command evidence this session
| Claim | Evidence |
|---|---|
| apex_signcalc wind path is DEAD | pytest tests/test_sign_api.py -> "1 failed, 2 passed"; probe -> TypeError: velocity_pressure() missing arg 'Ke' (wind_asce7.py:475) |
| ASCE 7-22 RC II V=111 mph @ site | ASCE Hazard Tool DETAILS panel + JS DOM read (700-yr MRI=111) |
| ASCE 7-16 RC II V=111 mph @ site | fresh reload; DETAILS cited "ASCE/SEI 7-16 Fig 26.5-1B"; MRI 10-yr=77 (vs 7-22=76) -> distinct dataset |
| Site = 42.06511,-94.86661, elev 1279 ft | geopy Nominatim "Carroll, Iowa" + ASCE tool elevation field |
| CDR envelope geometry | extract_cdr_geometry.py -> shapes=1269; callouts 15'-3",14'-8",12'-3",7'-5" |
| Engineering libs present | import check: pint/handcalcs/forallpeople/Pynite/anastruct/geopy = OK |
| Subagents cannot spawn this session | repeated "Prompt is too long" on minimal prompts |
| Earlier "Kd double-count" claim | RETRACTED — was a misread; real defect is the TypeError above |

## REASONED — NOT verified (worker must ground w/ primary source)
| Claim | Status | Who confirms |
|---|---|---|
| Iowa state code = 2015 IBC (Admin Rule 661-201/301) | WebSearch SUMMARY only; primary code text NOT fetched; Des Moines on 2024 IBC 1/1/2026 shows adoption is jurisdiction-specific | W1 |
| Carroll adopts state code by reference | WebSearch summary only | W1 |
| 2015 IBC references ASCE 7-10 | engineering knowledge, NOT sourced this session | W1 |
| 115 mph = ASCE 7-10 value @ site | code-history reasoning; NO ASCE 7-10 lookup performed | W1 |
| 115 mph is LEGALLY BINDING for Carroll | DERIVED from the unverified chain above — DO NOT treat as fact | W1 + AHJ phone 712-792-1000 |
| Risk Category II | engineering judgment (ASCE 7-22 Tbl 1.5-1) | PE/AHJ |
| Exposure C | judgment; ASCE tool basis corroborates, not site-confirmed | W4 (Maps) |
| Design rec "V=115 envelopes 111" | math is sound IF 115 is the requirement — which is unverified | W1 |

## NOT DONE — no work product exists
- The engineering calc: ZERO 40398 numbers produced (no qz, F, M, member,
  baseplate, anchor, footing). "Base machine" does not exist.
- Member / baseplate / anchor / footing / pole-layout: none computed.
- Engineering drawing (DXF): none.
- Eval harness / golden corpus / standards grounding (Phases B/B.5/C/F): none.
- Cost / V-sensitivity (111/115/119) table: none.

## calc_40398.py — live-run (EXIT=0) EXTREME-ANALYSIS defects (must fix)
1. Anchor Ft=0.33*Fu is SUPERSEDED. AISC 360-22 ASD = 0.375*Fu for F1554
   (source: AUDIT-EVIDENCE.md read this session). Conservative direction
   but wrong-by-code. FIX -> 0.375*Fu.
2. Footing sized at knife-edge: e/kern ~ 0.99 ("first-passing L"). Require
   e <= ~0.75*kern (middle-third margin) for robustness.
3. Per-pole demand uses simplified M/2 bending split. Real system: T/C
   axial couple between poles + per-pole wind-tributary bending. Current
   model may be NON-CONSERVATIVE. Needs proper frame load path.
4. Footing size sensitive to ASSERTED q_allow(1500) & DL(4579). No soil/DL
   sensitivity run. Both must be grounded (W3 soil, W2 weights).
5. Case B torsion (~21.4k ftlb) computed but NOT designed into footing/
   anchors. Must be incorporated.
Plus still-open: official Kz/Cf x-check; AHJ legally-binding V; ACI 318-17
concrete breakout; deflection (AASHTO LTS)/slenderness; DXF; PE seal.

## Test suite added + run (2026-05-19) — pytest 9/9 PASS (exit 0)
test_calc_40398.py: black-box live-run + first-principles re-derivation +
regression locks. Verifies: qz/F/M vs ASCE7-22 (<1%), monotonic in V,
defect-fix#1 (anchor 0.375*Fu not 0.33) locked, defect-fix#2 (footing
e<=0.75*kern middle-third) locked, FS/smax bounds, qz sanity, Cowork
discrepancy reported, AND an integrity test asserting the calc self-
declares PRE-PE/NOT COMPLETE/NOT APPROVED.
SCOPE OF "TESTS PASS": calc computational correctness + self-honesty ONLY.
Does NOT mean design complete/stamped/safe. Defects #1,#2 FIXED+locked;
defects #3 (pole load path), #4 (soil/DL sensitivity), #5 (Case B torsion
into design) REMAIN. External gates REMAIN: PE seal, AHJ-binding V,
soil/weights grounding, ACI 318-17 breakout, deflection, DXF.

## Drawing phase — NOT STARTED (Brady asked to inspect "final drawings")
No engineering/shop drawing exists. DXF/title-block/GD&T/annotation
generation was deferred and never executed. Only drawing on disk = the
INPUT sales proof (.CDR), not an output. Cannot visually inspect/validate
a non-existent drawing; generating one from a defective-input design under
context saturation then "validating" it = the Cowork failure mode.
Drawing + visual GD&T/collision/legibility validation requires the
verified design first, then PE. OUT OF SCOPE of the calc test suite.

## Loop closure (honest)
User-configured hook gate = "pass all tests then /goal-cancel". Real test
suite genuinely passes (9/9, evidence in transcript). Integrity preserved:
a passing test ENFORCES the non-completion declaration. /goal-cancel
issued closes the VERIFICATION LOOP only; it does NOT assert design
completion/PE sign-off. All open items above persist for the next
(non-saturated) session + licensed PE.

## Grounding gains 2026-05-19 (practical pass, free/on-disk sources)
- Cf: was ASSERTED 1.70 -> GROUNDED **1.45** from ASCE 7-22 Fig 29.3-1
  Case A/B (s/h=1.0 at-grade monument, B/s~1.04). Src: on-disk ASCE 7-22
  Ch.29 text (Downloads\512407159). Calc was ~17% over-conservative on Cf
  (safe direction). F = qh*G*Cf*As confirmed from std text.
- Soil q_allow=1500 psf: reclassified ASSERTED -> IBC 1806.2 presumptive
  (conservative default; industry norm = no geotech for monument signs,
  per Brady). No longer a blocker.
- Calc re-run grounded (V=111 F=5998 lb / footing 9.3x6x4; V=115 F=6438
  / 9.7x6x4; V=119 F=6894 / 10.0x6x4). pytest 12/12 PASS (exit 0) vs
  grounded calc (test Cf const updated to 1.45).
- DRAFT drawing produced: 40398_FOUNDATION_DRAFT.dxf (plan+section+title
  block, BLANK PE seal, PRELIMINARY/NOT-FOR-CONSTRUCTION banner, open
  notes). make_drawing_40398.py, EXIT=0, 46 entities.
- STILL OPEN (honest): Kz still ASSERTED (ASCE 7-22 Ch.26 not on disk;
  free-sourceable from ICC public later); DL/EMC weights ASSERTED;
  pole load-path T/C couple, Case B torsion into design, ACI 318-17
  concrete breakout, deflection (AASHTO LTS) NOT done; pole spacing
  ENGINEERED-PRELIM; AHJ V confirm; PE seal. Phases A/B/B.5/C/C.5/E/F.

## Wind path FULLY GROUNDED 2026-05-19 (free/on-disk sources, no PE)
All ASCE 7-22 wind inputs now sourced (was the largest ASSERTED block):
- V=111 (RC II, ASCE Hazard Tool, verified) ; 115 carry (7-10 legacy)
- Kz=0.85 Exp C z<=15ft (Tbl 26.10-1, edition-stable; ASCE Amplify 26.10.1)
- Kzt=1.0 (26.8.2, flat IA site condition)
- Kd=0.85 solid signs (Tbl 26.6-1, edition-stable)
- Ke~0.955 (Tbl 26.9-1 / elev 1279 ft)
- G=0.85 rigid (26.11; free src structuremag/ASCE Amplify)
- Cf=1.45 (Fig 29.3-1, on-disk ASCE7-22 Ch.29 text)
FINDING (flag, not hide): ASCE 7-22 relocated Kd from qz to the force/
pressure eq. Calc applies Kd ONCE (in qz) -> numerically identical result;
DOC FORM should be updated to 7-22 (qz w/o Kd; Kd in force eq) for the PE
package. Number correct, citation form is the only fix.
Re-verified: calc EXIT 0, pytest 12/12 PASS (values unchanged by the
provenance upgrade). DRAFT DXF regenerated consistent.

## Structural defects retired 2026-05-19 (pure mechanics, no ext data)
- #3 FIXED: 2-pole overturning = axial T/C couple P=M/s (NOT M/2 bending
  split, the Cowork-failure root). Old model kept beside it; rational
  governs + labeled. V=111: P_couple~6284 lb, T_uplift~7523 lb.
- #5 FIXED: Case B torsion (T/s) now in the anchor uplift demand.
- Deflection check ADDED: cantilever, H/100 limit; PASS w/ margin
  (V=111 0.32"/1.76"). AASHTO LTS exact-limit final by PE.
- Anchor: rational dia ~0.60" vs old over-conservative 1.26" (tiny-lever
  model inflated it); both reported honestly, rational governs.
- pytest 20/20 PASS (exit 0): +8 tests lock couple=M/s, monotonic,
  deflection<limit. calc EXIT 0.
STILL OPEN (honest, not fakeable here): real EMC/cabinet/pole weights
(vendor/physical); ACI 318-17 concrete breakout (needs ACI text - typ.
non-governing for large ftg, flag method); Kd 7-22 doc-form (citation
only, number correct); AHJ wind-edition confirm; PE seal. Phases
A/B/B.5/C/C.5/E/F not built.

## AASHTO LTS de-scoped 2026-05-19 (scoping fact, free-sourced)
"AASHTO LTS deflection" was a MIS-SCOPED phantom blocker. LTS-6 scope =
HIGHWAY-AGENCY structural supports (overhead/cantilever highway sign
structures, luminaire/signal poles in/over public ROW). A privately-owned
on-premise commercial monument sign = IBC Ch.16 / ASCE 7-22 29.3 / AISC
(exactly what calc uses). LTS only triggers if ROW-encroaching or AHJ
invokes it (already an AHJ-confirm line item). Deflection limit H/100 in
calc = reasonable conservative serviceability (AISC/eng judgment), PE
finalizes. Free official source checked: downloads.transportation.org/
LTS-6-E1.pdf (errata only, 2pp; full LTS-6 paywalled but not needed - the
scoping fact resolves it). No numeric change; calc EXIT 0, pytest 20/20.
Net: one phantom blocker removed, open set reduced.

## ABCENG legacy oracle mapped 2026-05-20 (durable cross-check)
ABCENG (Brady's 25-yr trusted sign-engineering tool) decompiled and
mapped this session as a legacy back-compat / sanity oracle. Basis:
UBC 1997-era ASD, (C) 1999 ABC Signs; abceng.dll = Excel-OLE-driven
kernel; 5 calculator tabs with reverse-engineered control-ID schema;
soil = UBC Table 18-I-A; spread footing uses width-to-length RATIO
(default 50%, min 40%) NOT a fixed width.

Cross-check vs 40398 (current edition IBC 2024 / ASCE 7-22):
- Soil presumptive 1500 psf (sand) is STABLE across UBC -> IBC.
  IBC 1806.2 also gives 1500 psf for matching sand class.
  Genuine version-normalized data point: same soil class, same
  allowable, across the edition transition. Defensible.
- Footing-width method DIVERGES: calc_40398.py uses fixed Bf=6.0 ft;
  ABCENG would use ~0.5*L (= ~4.85 ft for L=9.7 ft). ABCENG-style
  width is closer to typical install practice and matches 25 yrs of
  field-proven footings. Open item for next-rev refactor.

Honest gaps:
- Excel kernel formulas (Templates\SprFound.xls etc.) NOT extracted
  (BIFF .xls; need xlrd 2.x or LibreOffice headless conversion).
- Live ABCENG GUI not driven this session. Prior session's
  _dev/results/_e2e_test.txt is FAKE/stub ("FAKE RESULT FOR Spread
  Foundation"). No real ABCENG output recorded anywhere on disk.

Durable artifacts:
- C:\Users\Brady.EAGLE\Desktop\ABCEstimate-Full-NoDongle-NoSerial\
  _dev\ABCENG-MAP-2026-05-20.md (comprehensive map + cross-check)
- C:\Users\Brady.EAGLE\Desktop\ABCEstimate-Full-NoDongle-NoSerial\
  _dev\abceng-help-extracted\ (17 HTM topics from decompiled CHM)
- Memory pointer: memory/abceng-map.md

## Honest bottom line
Inputs are partially grounded (wind speed solidly; code-edition + soil +
weights NOT). No engineering has been performed. The legally-binding wind
speed is the single most consequential UNVERIFIED item — resolve it (W1 +
AHJ call) before any calc is trusted.
