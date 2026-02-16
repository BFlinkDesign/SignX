# SignX Warehouse - Session Handoff

**Date**: 2026-02-15
**Status**: CSV Export Pipeline COMPLETE, Enrichment COMPLETE
**GitHub**: https://github.com/EAGLE605/signx-warehouse + https://github.com/EAGLE605/SignX
**Agent**: Claude Opus 4.6

---

## Session 3 Summary (2026-02-15)

### Completed This Session

1. **CSV Export Extraction - Crash Recovery & Completion**
   - Script `extract_mvi_csv_exports.py` had crashed at job 110/154 on ReadTimeout (EXPORT.WIP.SUMMARY 2005 WIP_TYPE=O)
   - Added retry with exponential backoff (30s/60s/120s) on ReadTimeout/ConnectionError
   - Increased read timeout 60s -> 180s
   - Added crash resilience (try/except per job, log failure, continue)
   - Added `--resume` flag that scans existing files to rebuild checkpoint skip-list
   - Completed all 44 remaining jobs (0 failures)

2. **Merged Yearly CSVs**
   - Concatenated yearly extracts into 7 `_ALL.csv` files with single header row
   - Total: 1,563,495 lines across all merged files

3. **Reference Table Scraper (Playwright)**
   - Requests-based scraper couldn't reach data inside nested MVI framesets
   - Built `scrape_ref_tables_playwright.py` using Playwright with system Chrome
   - Navigates APPLOAD -> APP frame -> extracts second table
   - Added SHOW_ALL_CODES checkbox detection (includes inactive/historical records)
   - Handles two HTML patterns: itemLabel-based and oddTableRow-based headers
   - Result: 31/33 tables scraped successfully, 2 genuinely empty, 0 failures

4. **Enrichment Engine**
   - Built `enrich_csv_exports.py` - joins reference codes to human-readable names
   - Handles report-format CSVs (repeated year headers, subtotals, blank lines)
   - 5 files enriched with 98-100% match rates across all joins
   - Special chained lookup: work_code -> dept_code -> dept_name (EMP.HOURS)
   - 6 orphan salesperson codes (BOBR, TOMW, JMC, JENNYF, JENP, LUIS) - hard-deleted from KeyedIn

---

## Data Inventory

### Merged Reports (7 files, 89.6MB total)

| File | Lines | Size | Enriched |
|------|-------|------|----------|
| EMP.HOURS.BY.DATE_ALL.csv | 1,108,565 | 39MB | Yes (41MB) |
| CUST.PROD.EXPORT_ALL.csv | 134,869 | 7.4MB | Yes (6.5MB) |
| GM.BY.INV.EXPORT_ALL.csv | 129,165 | 8.4MB | Yes (7.0MB) |
| EXPORT.WIP.SUMMARY_C_ALL.csv | 67,997 | 9.1MB | No (no joinable codes) |
| SLSPER.PROD.EXPORT_ALL.csv | 63,421 | 4.5MB | Yes (4.1MB) |
| EXPORT.WO.LABOR.ANALYSIS_ALL.csv | 54,349 | 21MB | Yes (13MB) |
| EXPORT.WIP.SUMMARY_O_ALL.csv | 5,129 | 688KB | No (no joinable codes) |

### Reference Tables (33 files, 968 data rows)

Scraped from MVI reference code listings via Playwright. Key tables:
- SALESPERSONS_LIST (15 entries, including inactive)
- SIGN_TYPE_CODES_LISTING (34 entries)
- SIGN_TEMPLATE_LISTING, WORK_CODE_LIST, WORK_DEPT_LIST
- SALES_CODES_LIST, STATES_LIST, EST_QUOTE_STATUS_CODE_LIST
- Plus 25 more (see `ref_*.csv` files)

### Enrichment Join Results

| File | Column | Match Rate | Orphans |
|------|--------|------------|---------|
| EMP.HOURS | Work Code | 100% | 0 |
| EMP.HOURS | Work Dept | 100% | 0 |
| CUST.PROD | Prod Code | 100% | 0 |
| CUST.PROD | Salesperson #1 | 98.3% | 6 codes |
| GM.BY.INV | Prod Code | 100% | 0 |
| GM.BY.INV | SalesPer #1 | 98.2% | 6 codes |
| SLSPER.PROD | Prod Code | 100% | 0 |
| SLSPER.PROD | Salesperson #1 | 98.0% | 6 codes |
| WO.LABOR | Sign Type | 99.8% | 1 code |
| WO.LABOR | Template | 99.0% | 3 codes |

---

## Pipeline Scripts

| Script | Purpose |
|--------|---------|
| `scripts/extract_mvi_csv_exports.py` | Bulk CSV export from MVI (6 endpoints x 22 years, resume/retry) |
| `scripts/scrape_ref_tables_playwright.py` | Playwright scraper for 33 MVI reference tables |
| `scripts/enrich_csv_exports.py` | Join reference codes onto merged CSVs |
| `scripts/merge_csv_exports.py` | Concatenate yearly CSVs into _ALL files |

---

## Technical Reference

### MVI Export Pattern
1. POST form params to `mvi.exe/ENDPOINT` (date range, WIP type, etc.)
2. GET `mvi.exe/ENDPOINT.RUN` to trigger report generation
3. Poll `mvi.exe/VIEW.LOG` until "CSV extract file created"
4. Download CSV from `/attachments/{filename}`

### MVI Frameset Structure (Reference Tables)
```
APPLOAD?APP=ENDPOINT
  -> frameset
     -> TITLE frame (page title)
     -> APP frame (data table)
        -> table[0] = title/nav
        -> table[1] = data (headers + rows)
        -> #SHOW_ALL_CODES checkbox (some pages)
```

### KeyedIn ERP Endpoints
- **Base**: `https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe`
- **Login**: `LOGIN.START` (form POST with USERNAME/PASSWORD)
- **Exports**: CUST.PROD.EXPORT, GM.BY.INV.EXPORT, EMP.HOURS.BY.DATE, SLSPER.PROD.EXPORT, EXPORT.WO.LABOR.ANALYSIS, EXPORT.WIP.SUMMARY
- **Reference Tables**: 33 endpoints (STATES.LIST, SALESPERSONS.LIST, etc.)

---

## Session History

| Session | Date | Work |
|---------|------|------|
| 1 | 2026-02-06 | Informer BI capture (30 reports), MVI ERP discovery |
| 2 | 2026-02-08 | G: drive discovery, ESC file index, quote lookup tool |
| 3 | 2026-02-15 | CSV export pipeline (extract, merge, ref tables, enrichment) |

---

## Commit History

```
84bc856 Add warehouse data extraction pipeline, parsed datasets, and skills
6086bbe Add CSV export pipeline: extract, reference tables, and enrichment
f7f12b5 Add G: drive discovery, ESC file index, and quote lookup tool
dbf6d00 Update session handoff with final status
ea086b1 Initial commit: SignX Warehouse - KeyedIn data extraction toolkit
```

---

## File Locations

```
C:\Scripts\signx-warehouse\
  scripts/
    extract_mvi_csv_exports.py     # Bulk CSV extractor (resume/retry)
    scrape_ref_tables_playwright.py # Playwright ref table scraper
    enrich_csv_exports.py           # Reference code enrichment
    merge_csv_exports.py            # Yearly -> _ALL merge
  warehouse/raw/csv_exports/
    *_ALL.csv                       # 7 merged report files
    *_ALL_enriched.csv              # 5 enriched files
    ref_*.csv                       # 33 reference tables
    extraction_progress.json        # Checkpoint file
  SESSION_HANDOFF.md                # This file
```

---

## Resume Instructions

```
Read C:\Scripts\signx-warehouse\SESSION_HANDOFF.md
```

**Data pipeline is complete.** Next steps would be:
- Load enriched CSVs into analytics (DuckDB, Pandas, Supabase)
- Build dashboards or reports
- Capture additional MVI modules (Quotes, Sales Orders, GL, etc.)

---

**Session End**: 2026-02-15
**User**: Brady Flink
**Agent**: Claude Opus 4.6
