---
id: SC-BACKLOG
title: Engineering Debt and Roadmap Backlog
category: backlog
version: 1.0
last_updated: 2026-04-17
---

# SignCalc Backlog

## Phase 1 Remaining (Engineering Integrity)

### SQ Table — Ix Missing (ENGINEERING CRITICAL)
- **Problem:** `Ix_def` uses proxy `recSq.sm * recSq.side / 2` instead of true Ix from AISC Table 1-11. For 6x6 HSS, proxy gives ~32 in4 vs actual ~68.7 in4 — deflection check is 2x conservative (false failures).
- **Fix:** Add `Ix` field to every row of `_SQ_TABLE` from AISC 16th Ed. Table 1-11. Update deflection calc to use `recSq.Ix`.
- **Effort:** ~1 hour (data entry + one-line code fix)
- **Commit prefix:** `DATA: AISC-T1-11`

### WSEC Table — W16 through W21 Missing
- **Problem:** Table stops at W14x30 (Sx=42 in3). Large high-wind signs needing W16–W21 fall off the table. Calc shows FAIL and recommends W14x30, which is wrong.
- **Fix:** Add W16x26 through W21x68 (~14 shapes) from AISC 16th Ed. Table 3-2.
- **Effort:** ~2 hours (data entry)
- **Commit prefix:** `DATA: AISC-T3-2`

### Storage Key Migration — Cleanup at v4.2.0
- `signcalc_v3` fallback in `loadFromStorage()` retained until v4.2.0. Remove at that version bump.
- **Effort:** 5 minutes

### Frost Depth — Extract to Named Constant
- Hardcoded `4.0 ft` scattered in code and PDF. Extract to `var FROST_DEPTH_FT = 4.0;` with IBC citation.
- **Effort:** 20 minutes
- **Commit prefix:** `IBC-1809:`

### IBC Method UI Label
- UI says "IBC Eq.18-1" but section is §1806.3.2 in IBC 2021. Label fix for permit documentation accuracy.
- **Effort:** 5 minutes
- **Commit prefix:** `UI:`

### BOLT Table — Abrg Reconciliation
- Some bolt bearing areas (Abrg) in BOLT table may not match AISC 16th Ed. Table 7-18. Verify all entries.
- **Effort:** ~1 hour

### Input Validation
- No range validation on numeric inputs. `val()` silently returns the fallback. Visible error state needed for out-of-range values.
- **Effort:** ~2 hours

## Phase 2 — AbcENG Replacement UX

- Replace AbcENG Windows desktop software as the primary sign quote tool
- Add project database (localStorage or IndexedDB) replacing single-project save
- Material takeoff integration: connect to SignX warehouse DB via local API
- Dual-company support: Eagle Sign & Design (primary) + second company calibration
  - NOTE: Second company uses different soil bearing values and wind exposure defaults. Calibration required before enabling.
- Shareable project export (JSON or .signcalc format)
- Real-time drawing update tied to all calc inputs

## Phase 3 — PE-Ready Output

- Output format suitable for PE review (not PE-stamped, but PE-reviewable)
- Engineer-of-record block on PDF with project number, revision tracking
- Calculation narrative (show work, not just results)
- Load path diagram embedded in PDF
- ASCE 7-22 wind speed map lookup by GPS coordinates
- Bid-to-permit traceability: link SignCalc report to Notion Bid Pipeline entry

## Deferred / Can Wait

- GitHub remote + CI (valuable once team grows beyond 1 person)
- Branch protection, PRs (overhead-to-benefit inverted for single-person tool)
- project-guardian Layer 2 drawing evals (drawing analysis prompt lives in `_callClaudeVision()`)
- Held-out test set (defer until suite reaches 30+ cases)
