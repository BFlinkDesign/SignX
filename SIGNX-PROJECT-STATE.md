# SIGNX PROJECT STATE

**Updated:** 2026-02-15
**Repo:** `EAGLE605/SignX` (main)
**Last Commit:** `b787707` — warehouse extraction pipeline + SignX-Takeoff validation

---

## Working

| Component | Status | Details |
|-----------|--------|---------|
| **Warehouse CSV Extraction** | COMPLETE | 1.56M rows, 7 merged CSVs, `extract_mvi_csv_exports.py` with --resume, retry, error-continue |
| **Warehouse Ref Tables** | COMPLETE | 33 MVI ref tables via `scrape_ref_tables_playwright.py` (968 rows total) |
| **Warehouse Enrichment** | COMPLETE | 5 enriched `_ALL_enriched.csv` files with work code names, sales code descriptions, sign type descriptions, salesperson names. 100% prod code match, 99.99% work codes. |
| **ESC File Index** | COMPLETE | 40,611 files indexed via `scan_esc_numbers.ps1` |
| **SignX-Takeoff Validated** | COMPLETE | 16/20 pass. PDF parser works (Gemini Art 11%, conceptuals 2-4% @ SF=2.75). Part numbers 8/8 verified. Warehouse benchmark confirmed (billing column, CHANNL filter, 2,443 jobs). |
| **PA Build Guide** | COMPLETE | `C:\Scripts\signx-intake\pa-flow-build-guide.md` + 3 HTTP body JSON files. Includes markdown fence cleanup step (Haiku wraps JSON in backticks). |
| **Monday Estimation Briefs** | COMPLETE | 3 context briefs (Mercy UC, St. Anthony EMC, Ankeny Parks) with customer history, file inventory, warehouse data, gaps identified. |
| **KeyedIn Intelligence** | COMPLETE | 262 CGI + 71 Informer = 333 endpoints mapped. See `PROJECT-STATE.md` for endpoint details. |

## Broken / TODO

| Item | Status | Details |
|------|--------|---------|
| **PA Flow 3** | READY TO BUILD | Build guide ready at `C:\Scripts\signx-intake\pa-flow-build-guide.md`. Brady builds manually in PA editor. Test with 2 emails. |
| **SignX-Takeoff part numbers** | DONE | 8/8 verified against `eagle-rates-fab-cheat-sheet.md` |
| **ESC Index false positives** | TODO | Year patterns in `quote_number` column (e.g. "2025") create false matches. Needs cleanup filter. |
| **SignX-Takeoff PDF auto-scale** | KNOWN LIMITATION | `known_letter_height` auto-detection unreliable on conceptuals (picks up borders, not letters). Manual SF=2.75 works. |
| **KeyedIn export endpoints** | BLOCKED | 14 endpoints need testing from VPN-connected PC. See `PROJECT-STATE.md`. |

## Next Actions

1. **[BRADY MANUAL]** Build PA CORRESPONDENCE-CLASSIFIER flow from build guide
2. **[BRADY MANUAL]** Test PA flow with 2 emails (Instruction + Variation)
3. **[NEXT SESSION]** Feed real conceptual PDF through SignX-Takeoff web UI, verify end-to-end
4. **[NEXT SESSION]** Clean ESC index false positives (year patterns in quote_number)
5. **[SPRINT 2]** SignX-Studio structural engineering — evaluate SkyCiv + ClearCalcs (DEC-003)
6. **[SPRINT 3]** SignX-Draw — ezdxf DXF generation

---

## Data Assets

| Asset | Size | Disk | Location |
|-------|------|------|----------|
| Merged CSVs (7) | ~1.56M rows | 542 MB | `C:\Scripts\signx-warehouse\warehouse\raw\csv_exports\*_ALL.csv` |
| Enriched CSVs (5) | ~571K data rows | 70.2 MB | `C:\Scripts\signx-warehouse\warehouse\raw\csv_exports\*_enriched.csv` |
| Ref Tables (33) | 968 rows | 1.2 MB | `C:\Scripts\signx-warehouse\warehouse\raw\ref_tables\*.json` |
| ESC File Index | 40,611 files | 4.8 MB | `C:\Scripts\signx-warehouse\esc_file_index.csv` |
| SO Contracts (parsed) | 25,400 rows | 18 MB | `C:\Scripts\signx-warehouse\warehouse\raw\so_contracts_parsed.csv` |
| ABC Labor Formulas | 342 formulas | — | `C:\Scripts\SignX\data\abc-estimating\LABOR_FORMULAS_COMPLETE.txt` |
| Fab Cheat Sheet | ~50 part numbers | — | `C:\Scripts\Modern Labor Standards\abc pricing guide\eagle-rates-fab-cheat-sheet.md` |

---

## Session History — Completed

| Session | Work | Key Results |
|---------|------|-------------|
| **T1** | MVI CSV extraction | 7 merged CSVs, 1.56M rows, --resume flag, error-continue |
| **T1 (continued)** | CSV enrichment | 5 files, ref lookups joined. Commit to git. |
| **T2** | SignX-Takeoff validation | 16/20 pass. PDF parser fixed (quad handler, scale factor, UI). Part numbers verified. |
| **T3** | PA build guide | 7-step flow with copy-paste expressions, 3 HTTP body files, markdown fence cleanup. |
| **T4** | Monday estimation briefs | Mercy (21 monument files, no caisson cost data), St. Anthony (26 quotes, full EMC history, no Watchfire pricing), Ankeny Parks (WDM Parks $57K baseline, job 7880 missing). |

---

## Discovered

- Haiku consistently wraps JSON in markdown fences despite prompt instructions — must strip in PA flow
- Conceptual PDFs have annotation vectors, not letter outlines — use SF=2.75 or Gemini Art files
- Job 7880 (Ankeny Parks baseline) doesn't exist in any data source
- `billing` column is the correct revenue field (NOT `quoted_price`)
- Work codes 0640/0650 = CREW-hours (not man-hours) — critical for KeyedIn entry
- PyMuPDF `qu` items are Quad objects (ul/ur/lr/ll corners), not quadratic beziers
- Gemini Art PDFs have 1:1 scale pages (e.g. 94"x22"), conceptuals are on letter-size paper

## Assumptions

| Assumption | Status | Evidence |
|------------|--------|----------|
| SignX-Takeoff PDF parser handles Eagle Sign conceptual PDFs | PARTIALLY VERIFIED | Works with Gemini Art (11% variance) and conceptuals with SF=2.75 (2-4%). Auto-detection unreliable. |
| Part numbers 214-XXXX are current active inventory | VERIFIED | 8/8 against fab cheat sheet |
| ABC Section 4B rates are current Eagle standards | ASSUMED | Sourced from `abc-labor-rates-complete.md`, not validated against recent actual jobs |
| `labor_cost / $40` gives reasonable hour estimates | ASSUMED | Implied rate $40/hr. Variance 40-54% vs ABC estimates (Test 2). |
| Warehouse `billing` column = actual invoiced revenue | ASSUMED | Used for GM% calculation. `quoted_price` exists but is less reliable. |

---

## Key Files

### SignX-Takeoff (`signx-takeoff/`)
| File | Purpose |
|------|---------|
| `app.py` | FastAPI server (port 8765) |
| `abc_engine.py` | ABC formula engine (Sections 4B/4C/4A/10B) |
| `extract_pf_from_pdf.py` | PyMuPDF PDF parser |
| `warehouse.py` | Historical benchmark (2,443 channel letter jobs) |
| `static/index.html` | Web UI (dark theme, 3 PF modes, export) |
| `test_validation.py` | Validation suite (16/20 pass) |
| `test_gemini_art.py` | Gemini Art accuracy test |

### Warehouse Scripts (`scripts/`)
| File | Purpose |
|------|---------|
| `extract_mvi_csv_exports.py` | MVI CSV extraction (--resume, retry, error-continue) |
| `scrape_ref_tables_playwright.py` | 33 ref tables via Playwright |
| `enrich_csv_exports.py` | Join ref table lookups into CSVs |
| `lookup_job.py` | Quote-to-files + warehouse lookup |
| `scan_esc_numbers.ps1` | G: drive ESC file scanner |
