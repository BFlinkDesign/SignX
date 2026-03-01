# Unprotected Code Report — CNC-1

**Audited:** 2026-03-01
**Scope:** All PRODUCTION and DEVELOPMENT code NOT in GitHub, sorted by risk level

---

## CRITICAL RISK — Data loss = project dead in the water

### 1. SignX Warehouse DuckDB Database

| Attribute | Value |
|-----------|-------|
| **Path** | `C:\Scripts\signx-warehouse\warehouse\signx.duckdb` |
| **Est. Size** | ~200 MB |
| **Last Known Good** | 2026-01-30 (built from HTML parse) |
| **What It Does** | Consolidated analytical database of all Eagle Sign work orders, labor, materials. Used by `abc_engine.py` calibration, `calibrate.py`, `t1_query.py`, analysis scripts. |
| **Who Depends On It** | `abc_engine.py:1554` (auto-calibration), `calibrate.py:38` (P50 calibration), `bid_scoring.py`, `bid_model.py`, `customer_intel.py`, `warehouse.py` |
| **Rebuild Time** | 4-8 hours (re-run parse + build pipeline) |
| **OneDrive Backup?** | YES — `~\OneDrive - Eagle Sign Co\signx-warehouse\` (742 MB mirror) |
| **Risk Level** | **CRITICAL** — without this, calibration returns defaults, benchmarks return None, bid model can't train |

### 2. Warehouse Parser Script

| Attribute | Value |
|-----------|-------|
| **Path** | `C:\Scripts\signx-warehouse\scripts\parse_full_cost_detail.py` |
| **Est. LOC** | 907 |
| **What It Does** | Parses 168 HTML batch files (559 MB, 33,428 work orders) into structured CSVs: `wo_headers.csv`, `labor_detail.csv`, `labor_summary.csv`, `material_detail.csv`, `outplant_detail.csv` |
| **Who Depends On It** | Entire warehouse build pipeline. Without it, can't rebuild DuckDB from raw captures. |
| **Rebuild Time** | 8-16 hours (reverse-engineer HTML structure, regex patterns, cross-validation logic) |
| **In Any Repo?** | **NO** — exists only on CNC-1 and OneDrive mirror |
| **Risk Level** | **CRITICAL** — if lost AND the HTML files are lost, warehouse is permanently gone |

### 3. Production SQLite Warehouse

| Attribute | Value |
|-----------|-------|
| **Path** | `C:\Scripts\signx-warehouse\warehouse\production\eagle_warehouse.db` |
| **Est. Size** | 211 MB |
| **What It Does** | SQLite version of warehouse data for direct queries |
| **Rebuild Time** | 2 hours (re-run build pipeline from CSVs) |
| **Risk Level** | **CRITICAL** — but rebuildable from CSVs if those survive |

### 4. Raw Warehouse CSVs

| Attribute | Value |
|-----------|-------|
| **Path** | `C:\Scripts\signx-warehouse\warehouse\raw\` |
| **Key Files** | `so_contracts_parsed.csv`, `quote_status_report.csv`, plus 11 extraction runs |
| **Est. Size** | ~200 MB total |
| **What It Does** | Source of truth for all warehouse data. `so_contracts_parsed.csv` is loaded by 4 signx-takeoff modules at runtime. |
| **Referenced By** | `warehouse.py:20`, `bid_scoring.py:29,34`, `customer_intel.py:24`, `bid_model.py:42,47` |
| **Rebuild Time** | 4-8 hours (re-parse HTML captures) |
| **Risk Level** | **CRITICAL** — production takeoff features degrade to `None` without these |

---

## HIGH RISK — Loss would set back development weeks

### 5. KeyedIn Capture Scripts

| Attribute | Value |
|-----------|-------|
| **Path** | `C:\Scripts\keyedin-capture\` |
| **Files** | 9+ Python scripts |
| **Key Scripts** | `extract_wo_batches.py`, `cost_summary_automation.py`, `fast_extract.py`, `setup_credentials.py` |
| **What It Does** | CDP-based automated extraction from KeyedIn ERP. Logs into web ERP, navigates to reports, captures HTML batch files. |
| **Rebuild Time** | 16-24 hours (CDP browser automation is fragile, requires live KeyedIn access + VPN) |
| **Risk Level** | **HIGH** — only way to refresh warehouse data from ERP |

### 6. KeyedIn HTML Captures

| Attribute | Value |
|-----------|-------|
| **Path** | `C:\Scripts\keyedin-capture\reports\cost_detail\` |
| **Files** | 168 HTML files |
| **Size** | 559 MB |
| **Content** | 33,428 work orders with complete cost detail (labor hours, materials, outplant) |
| **Captured** | 2026-01-29 to 2026-01-30 |
| **Rebuild Time** | 4-8 hours (re-run capture scripts with VPN + ERP access) |
| **Risk Level** | **HIGH** — raw source for everything in the warehouse |

### 7. KeyedIn Automation / MCP Server

| Attribute | Value |
|-----------|-------|
| **Path** | `C:\Scripts\keyedin-automation\` |
| **Key Files** | `keyedin.py` (MCP server), `scripts/init_database.py`, `scripts/init_chromadb.py`, `scripts/discover_filesystem.py`, `scripts/ingest.py` |
| **What It Does** | FastMCP 2.14.3 server with ChromaDB vector store. 1,141 indexed documents. 8 tools for searching KeyedIn knowledge. |
| **Dependencies** | `fastmcp`, `chromadb`, `sentence-transformers` |
| **Rebuild Time** | 8-16 hours (recreate vector embeddings, re-map 288 functions) |
| **Risk Level** | **HIGH** — institutional knowledge about KeyedIn ERP navigation |

### 8. KeyedIn Site Map

| Attribute | Value |
|-----------|-------|
| **Path** | `C:\Scripts\keyedin-automation\discovery\keyedin\keyedin_site_map.json` |
| **Content** | 288 KeyedIn ERP functions mapped via Puppeteer (2025-05-22) |
| **Sections** | FAVORITES, CRM, PROJECT_MANAGEMENT, SALES_AND_AR, PURCHASING_AND_AP, INVENTORY, WORK_ORDERS, MISC, UTILITIES, GL, ADMIN |
| **Rebuild Time** | 2-4 hours (re-run Puppeteer scraper) |
| **Risk Level** | **HIGH** — only complete map of KeyedIn's GWT interface |

---

## MEDIUM RISK — Inconvenient to lose, rebuildable

### 9. CSV Export Scripts

| Attribute | Value |
|-----------|-------|
| **Path** | `C:\Scripts\signx-warehouse\warehouse\raw\csv_exports\` |
| **What It Does** | Export/enrichment pipeline for MVI/Informer BI data |
| **Scripts In Repo** | `scripts/extract_mvi_csv_exports.py`, `scripts/enrich_csv_exports.py` (but OUTPUT_DIR points to CNC-1) |
| **Rebuild Time** | 2-4 hours |
| **Risk Level** | **MEDIUM** |

### 10. 13 Analysis Scripts (keyedin-capture/reports/)

| Attribute | Value |
|-----------|-------|
| **Path** | `C:\Scripts\keyedin-capture\reports\` |
| **Scripts** | `generate_benchmarks.py`, `audit_script.py`, `build_abc_update.py`, `labor_query.py`, `parse_descriptions.py`, etc. |
| **Status** | All marked "EXISTS — untested" in KEYEDIN-PIPELINE-STATUS.md |
| **Rebuild Time** | 4-8 hours total |
| **Risk Level** | **MEDIUM** — untested, unknown utility |

---

## Summary: What Must Be Protected IMMEDIATELY

| Priority | Item | Path | Action |
|----------|------|------|--------|
| 1 | Warehouse DuckDB + CSVs | `C:\Scripts\signx-warehouse\warehouse\` | Git LFS or copy to private repo |
| 2 | Parser script | `C:\Scripts\signx-warehouse\scripts\parse_full_cost_detail.py` | Add to SignX repo |
| 3 | Capture scripts | `C:\Scripts\keyedin-capture\*.py` | Add to SignX repo under `keyedin-capture/` |
| 4 | HTML captures | `C:\Scripts\keyedin-capture\reports\cost_detail\` | OneDrive sync (559 MB too big for git) |
| 5 | MCP server | `C:\Scripts\keyedin-automation\keyedin.py` + scripts | Add to SignX repo under `keyedin-automation/` |
| 6 | Site map JSON | `C:\Scripts\keyedin-automation\discovery\` | Add to SignX repo |

**Total unprotected critical code: ~2,000 LOC**
**Total unprotected data: ~2.2 GB**
**OneDrive partially protects warehouse data (742 MB mirror) — but scripts are NOT mirrored**
