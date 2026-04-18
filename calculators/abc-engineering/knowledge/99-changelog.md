---
id: SC-99
title: Engineering Change Log
category: changelog
version: 1.0
last_updated: 2026-04-17
---

# Engineering Change Log

Entries are in reverse chronological order. Each entry must include: code section, date, what changed, what was wrong before, why it matters.

---

## v4.1.0 — 2026-04-17 (Phase 1 Trust Foundation)

### UI: Disclaimers — All Three Placements
- **Code:** HTML header, `generatePDF()` SCOPE box, `generatePDF()` footer
- **Change:** Added three disclaimer placements: (A) italic gray text in HTML header, (B) gray SCOPE & LIMITATIONS box on PDF page 1, (C) 6pt italic footer line on every PDF page.
- **Before:** No disclaimer anywhere. Tool output could be mistaken for a licensed PE calculation.
- **Why:** Permit liability. Eagle Sign is not a licensed engineering firm. Output must clearly state it is an internal estimate-prep tool only.

### UI: CALC_VERSION constant
- **Code:** Line 879, all `'v4.0'` references
- **Change:** Added `var CALC_VERSION = '4.1.0'`. Replaced all hardcoded `'v4.0'` strings in HTML badge and PDF output.
- **Before:** Version was a hardcoded string in three places. Version drift between places was possible.
- **Why:** Permit audit trail. Every calc sheet must trace to an exact version. Semver convention documented in `03-workflows.md`.

### ARCH: calc/render separation — calcBoltData/calcFoundData
- **Code:** `calc()` lines ~3469-3470, `renderAllResults()` lines ~2332-2333
- **Change:** Moved `calcBoltData()` and `calcFoundData()` calls from inside `renderAllResults()` into `calc()`. Results stored in `lastBoltCalc` and `lastFoundCalc`.
- **Before:** Bolt and foundation data was computed during rendering. In `projGenPDF()`, a 80ms gap between input restore and `generatePDF()` meant stale `lastBoltCalc`/`lastFoundCalc` could be read.
- **Why:** Data must be computed during calculation phase, not rendering phase. Eliminates stale-read race condition.

### ARCH: Null-initialize lastCalc globals
- **Code:** Lines ~1015-1021
- **Change:** Changed `var lastCalc = {}` (and five others) to `var lastCalc = null`. Added null guards in `renderAllResults()`, `updateDrawing()`, `calcBoltData()`, `calcFoundData()`, `lastACI &&`.
- **Before:** Globals initialized to `{}`. Stale reads (accessing `lastCalc.someField` before first `calc()`) returned `undefined` silently instead of failing fast.
- **Why:** Fail-fast on uninitialized state. `null` guard early-returns rather than silently using empty object.

### FIX: localStorage key migration v3 → v4
- **Code:** `saveToStorage()`, `loadFromStorage()`
- **Change:** Writes to `signcalc_v4`. Reads `signcalc_v4` first, falls back to `signcalc_v3` for migration.
- **Before:** Both save and load used `signcalc_v3`. File is v4 — key mismatch since initial v4 deployment.
- **Why:** Version key should match file version. v3 fallback retained until v4.2.0 to preserve existing user data.

### FIX: PDF MIME branch — PDF drawing uploads
- **Code:** `_callClaudeVision()`
- **Change:** Added `isPdf` flag. PDFs get `type: 'document'` (not `'image'`) and `anthropic-beta: 'pdfs-2024-09-25'` header.
- **Before:** All uploads sent as `type: 'image'`. PDFs would fail at the Anthropic API (wrong media type handling).
- **Why:** Anthropic API requires distinct document type and beta header for PDF inputs. Image type is incorrect for PDFs.

---

## v4.0 — 2026-04-15 (Session Engineering Fixes — retroactive)

### IBC-1806: Passive Resistance — Triangular Pressure (CRITICAL)
- **Code:** `calcFoundData()` passive force and moment calculations
- **Change:** Changed passive resistance from rectangular (Sl×fw×fd) to triangular (0.5×Sl×fw×fd²). Changed moment arm from fd/2 to fd/3.
- **Before:** Overstated lateral resistance by 2× for force and 3× for moment. Foundations were undersized.
- **Why:** IBC 2021 §1806.3.2 specifies triangular lateral bearing pressure (zero at surface, Sl×z at depth z). Rectangular was non-conservative.

### AISC-F2: W-Shape LTB — Inelastic Range (CRITICAL)
- **Code:** `calcFb_W_ltb()` function
- **Change:** Implemented full AISC 360-22 §F2 tri-linear LTB curve. Computed Lp, Lr, and interpolated Fcr in inelastic range.
- **Before:** Used flat 0.66Fy for all unbraced lengths regardless of Lb. Overstated capacity for Lb > Lp.
- **Why:** AISC §F2 requires reduction for Lb > Lp. Flat 0.66Fy is only valid in the plastic range (Lb ≤ Lp). Reference: W8×18, Lb=144 in → Fb=22,542 psi (inelastic range), not 33,000 psi (flat 0.66Fy).

### ACI-17: Concrete Breakout — kc=17 Cracked (CRITICAL)
- **Code:** `_aci_conc_breakout_T()`
- **Change:** Changed kc from 24 to 17 in Eq. 17.6.2.2b.
- **Before:** Used kc=24 (uncracked concrete assumption). Sign foundations are always in the cracked condition.
- **Why:** ACI 318-19 §17.6.2.2 Table 17.6.2.2b: kc=17 for cracked concrete, kc=24 for uncracked. Using kc=24 overstated Nb by 41% — non-conservative anchor design.

### AISC-J8: Base Plate Bearing — Vertical Demand (CRITICAL)
- **Code:** `calcBasePlateBearing()` and bearing demand in `renderAllResults()`
- **Change:** Changed bearing demand from horizontal wind shear to vertical compression (uplift + DL).
- **Before:** Compared phi×Pp (vertical bearing capacity) against horizontal wind force. Wrong demand quantity.
- **Why:** AISC 360-22 §J8-2 base plate bearing is a vertical bearing check. Demand = axial compression on plate (uplift load + dead load reaction). Using wind shear is a category error.
