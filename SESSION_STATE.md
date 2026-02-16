# SignX Warehouse - Comprehensive Session State

**Generated:** 2026-02-15 23:30 CST
**Repository:** https://github.com/EAGLE605/signx-warehouse
**Branch:** master
**Latest Commit:** ea772ab (2026-02-15 22:59:23 -0600)
**Total Size:** 1.5 GB on disk (warehouse data + scripts)
**Agent:** Claude Opus 4.6
**Operator:** Brady Flink, Eagle Sign Co.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Session Timeline](#2-session-timeline)
3. [Git History](#3-git-history)
4. [Repository Structure](#4-repository-structure)
5. [Data Pipeline Architecture](#5-data-pipeline-architecture)
6. [Warehouse Database](#6-warehouse-database)
7. [Scripts Inventory](#7-scripts-inventory)
8. [G: Drive Integration](#8-g-drive-integration)
9. [Data Coverage & Gaps](#9-data-coverage--gaps)
10. [Numbering Systems](#10-numbering-systems)
11. [Technical Reference](#11-technical-reference)
12. [Decision Engine](#12-decision-engine)
13. [Known Issues](#13-known-issues)
14. [Deliverables](#14-deliverables)
15. [Next Steps](#15-next-steps)

---

## 1. Project Overview

SignX Warehouse is a data extraction, parsing, and analytics toolkit that pulls operational data from Eagle Sign's KeyedIn Manufacturing ERP (Sign Edition) and maps it to the company's G: drive file archive. The goal is to build an independent data warehouse for estimation, analytics, and business intelligence.

### What It Does

1. **Extracts data** from two systems:
   - **KeyedIn ERP** (CGI-based, `mvi.exe`) - Work orders, labor, materials, invoices, sales, purchasing
   - **Informer BI** (GWT-RPC v7) - 30 pre-built reports on port 8443
2. **Parses HTML spool files** - 168 batch HTML files containing 33,428 work order cost details
3. **Maps the G: drive** (`\\ES-FS02\customers2`) - 6,861 customer folders, 456,030 files scanned
4. **Cross-references** warehouse data with G: drive files via customer name + ESC quote numbers
5. **Produces analytics** via decision engine (estimating accuracy, profitability, capacity, efficiency)

### Why It Exists

- KeyedIn runs on a UniVerse/Pick database with **no direct ODBC access**
- Only 30 pre-built Informer reports available (Consumer role, not Designer)
- No data dictionary or schema documentation provided
- Eagle Sign needs independent data copies for IRS compliance (IRC 6001, 7-year retention)
- Internal analytics require data the 30 canned reports don't cover

---

## 2. Session Timeline

| Session | Date | Agent | Key Work |
|---------|------|-------|----------|
| **1** | 2026-02-06 | Opus 4.5 | Informer BI capture (30 GWT-RPC report payloads), MVI ERP discovery (240+ processes, 19 modules), initial repo setup |
| **2** | 2026-02-08 | Opus 4.5 | HTML Cost Detail parser (168 batches -> 5 CSVs), GWT parser/deserializer, build_warehouse.py (SQLite), decision engine, local file ingestion |
| **3** | 2026-02-15 (early) | Opus 4.6 | CSV export pipeline (6 endpoints x 22 years), reference table scraper (33 tables), enrichment engine, crash recovery/resume |
| **4** | 2026-02-15 (late) | Opus 4.6 | G: drive discovery (6,861 folders), ESC filename scanner (40,611 indexed files), quote lookup tool, estimation briefs (Mercy/St. Anthony/Ankeny), .gitignore security fix, full commit/push |

### Session 4 Detail (Current)

**Tasks completed this session:**

1. **G: Drive Folder Structure Mapping**
   - Remapped stale SMB drive `G:` -> `\\ES-FS02\customers2`
   - Scanned 50 top-level folders, cataloged 6,861 customer folders
   - Exported `g_drive_customer_map.csv` (Letter, Customer, SubfolderCount, SampleSubfolders, Path)
   - Found naming convention: 85.7% plain names, 14.3% year-based, 0% with WO numbers in folder names
   - Key discovery: WO/quote numbers appear in **filenames** not folder names, format `MMYY-NNNNN-RR`

2. **ESC Filename Scanner**
   - Built `scan_esc_numbers.ps1` (214 lines PowerShell, streaming CSV output)
   - Scanned 456,030 files in 4:08
   - Found 43,367 matches, 32,468 unique ESC numbers
   - Cleaned false positives -> `esc_file_index_clean.csv` (40,611 clean rows)
   - Preserved 4-digit jobs >= 8000 (legitimate pre-2012 quotes)

3. **Quote Lookup Tool**
   - Built `scripts/lookup_job.py` (203 lines Python)
   - Combines ESC file index + warehouse billing data
   - Batch support: `python lookup_job.py 40654 40655 40660`
   - Shows customer, WO, billing, GM%, files with sizes/dates, G: paths

4. **Customer Cross-Reference**
   - 85.6% match rate (2,775/3,241 warehouse customers found on G: drive)
   - Match breakdown: 37.3% exact, 45.9% first-word, 2.4% contains
   - 466 unmatched (mostly numeric-prefix names, abbreviations, defunct)
   - ESC quote_number to warehouse quote_nbr: 31.1% match rate (4,015 matches)

5. **Monday Estimation Briefs**
   - Gathered context for 3 pending jobs:
     - **Mercy UC Pleasant Hill** - caisson replacement (21 monument files, 8 quotes, no caisson cost history)
     - **St. Anthony Hospital EMC** - Watchfire monument (68 files, 26 quotes across 5 phases, need Watchfire pricing)
     - **Ankeny Parks** - 3 park signs (sparse data, WDM Parks $57K baseline, Job 7880 missing)
   - Saved to `C:\Users\Brady.EAGLE\Desktop\MONDAY-ESTIMATION-BRIEFS.md`

6. **Security & Repository Cleanup**
   - Caught `informer_session.json` containing session tokens (jsessionid, auth_token, client_id)
   - Removed from git tracking, added to `.gitignore`
   - Added large data directories to `.gitignore`: `so_contracts/`, `so_contract_raw/`, `csv_exports/`, `spooled_samples/`, `wo_batches/`, `2026-*/`
   - Staged 23 files, committed, pushed to origin/master

---

## 3. Git History

```
ea772ab 2026-02-15 22:59:23 Update session handoff with Session 3 status (pipeline complete)
84bc856 2026-02-15 22:56:57 Add warehouse data extraction pipeline, parsed datasets, and skills
6086bbe 2026-02-15 22:53:05 Add CSV export pipeline: extract, reference tables, and enrichment
f7f12b5 2026-02-15 22:52:42 Add G: drive discovery, ESC file index, and quote lookup tool
dbf6d00 2026-02-06 17:46:58 Update session handoff with final status
ea086b1 2026-02-06 00:47:43 Initial commit: SignX Warehouse - KeyedIn data extraction toolkit
```

**Total changes since initial commit:** 231 files changed, 4,209,733 insertions, 181 deletions

---

## 4. Repository Structure

```
C:\Scripts\signx-warehouse\ (1.5 GB)
├── .gitignore                         # Excludes secrets, large data, caches
├── AGENTS.md                          # Agent instructions (beads integration)
├── SESSION_HANDOFF.md                 # Session-by-session handoff notes
├── SESSION_STATE.md                   # THIS FILE - comprehensive state
├── SYSTEM_KNOWLEDGE_BASE.md           # Full technical reference (550 lines)
├── g_drive_discovery.md               # G: drive mapping report (293 lines)
├── g_drive_matched_customers.csv      # 2,775 warehouse->G: matches
├── g_drive_unmatched_customers.csv    # 466 unmatched customers
├── esc_file_index.csv                 # Raw ESC scan (43,367 rows, in .gitignore)
├── esc_file_index_clean.csv           # Clean ESC index (40,611 rows)
├── scan_esc_numbers.ps1               # PowerShell G: drive scanner (214 lines)
│
├── config/                            # (empty)
├── skills/
│   └── constructioniq-frameworks.md   # Skill reference
├── tests/                             # (empty)
│
├── scripts/ (924 KB, 13,968 lines across 27 files)
│   ├── _get_session.py                # Playwright SSO -> Informer session (254 lines)
│   ├── build_warehouse.py             # Merge all CSVs into SQLite (1,034 lines)
│   ├── capture_all_reports.py         # Playwright GWT-RPC capture (1,093 lines)
│   ├── capture_hook.js                # Browser JS injection hook
│   ├── decision_engine.py             # 8-module analytics engine (711 lines)
│   ├── enrich_csv_exports.py          # Reference code enrichment (413 lines)
│   ├── extract_all_so_contracts.py    # CDP batch extraction (724 lines)
│   ├── extract_mvi_csv_exports.py     # Bulk CSV export from MVI (967 lines)
│   ├── extract_quote_report.py        # Quote report extractor (301 lines)
│   ├── extract_spooled_reports.py     # Spooled report handler (281 lines)
│   ├── gwt_analyze.py                 # GWT serialization diagnostics (379 lines)
│   ├── gwt_deserialize.py             # Right-to-left GWT deser (613 lines)
│   ├── gwt_dump_rows.py               # Raw data dump (155 lines)
│   ├── gwt_parser.py                  # GWT RPC v7 parser (1,259 lines)
│   ├── ingest_local_files.py          # H:\ + OneDrive scanner (632 lines)
│   ├── lookup_job.py                  # Quote-to-files lookup (203 lines)
│   ├── parse_full_cost_detail.py      # HTML -> 5 CSVs (907 lines)
│   ├── scrape_informer.py             # HTTP GWT-RPC extraction (1,748 lines)
│   ├── scrape_ref_tables_playwright.py # Playwright ref table scraper (319 lines)
│   ├── split_captures.py              # Split capture files (170 lines)
│   ├── tracer_bullet.py               # POC CDP login (451 lines)
│   ├── validate_so_contract.py        # Data validation (408 lines)
│   ├── test_extract_5pages.py         # Extraction tests (118 lines)
│   ├── test_field_mapping.py          # Field mapping tests (137 lines)
│   ├── test_pipeline_fixes.py         # Pipeline fix tests (269 lines)
│   └── test_quote_pagination.py       # Quote pagination tests (292 lines)
│
├── warehouse/
│   ├── production/
│   │   ├── eagle_warehouse.db         # SQLite database (211 MB, 1,376,130 rows)
│   │   └── warehouse_manifest.json    # Build metadata + row counts
│   ├── staging/                       # (empty, used during builds)
│   ├── reports/
│   │   └── decision_report_*.md       # Decision engine output
│   └── raw/                           # (1.4 GB, mostly .gitignored)
│       ├── 2026-01-30T*/              # 11 timestamped ingestion runs
│       ├── 2026-02-15T*/              # 5 timestamped runs from session 4
│       ├── csv_exports/               # 7 merged + 5 enriched + 33 ref tables
│       ├── so_contracts/              # .gitignored
│       ├── so_contract_raw/           # .gitignored
│       ├── spooled_samples/           # .gitignored
│       ├── wo_batches/                # .gitignored
│       ├── recon/                     # Reconnaissance data
│       ├── all_wo_numbers.csv         # Full WO number list
│       ├── so_contracts_parsed.csv    # 27,063 parsed WO rows
│       ├── so_contract_wo_summary.csv # 13,752 WO summaries
│       ├── so_contract_labor.csv      # Labor detail
│       ├── so_contract_material.csv   # Material detail
│       ├── so_contract_outplant.csv   # Outplant detail (7,126 rows)
│       ├── wo_labor_all_DUE.csv       # 27,052 labor rows
│       └── quote_status_report.csv    # Quote status extract
```

---

## 5. Data Pipeline Architecture

```
                    +---------------------------+
                    |   UniVerse / Pick DB       |
                    |   (Rocket U2 Engine)       |
                    |   NO DIRECT ACCESS         |
                    +---------------------------+
                       |                    |
              +--------+--------+    +------+------+
              |  KeyedIn ERP    |    | Informer BI  |
              |  (CGI/mvi.exe)  |    | v4.7 (GWT)   |
              |  Port 80/443    |    | Port 8443     |
              |  240 processes  |    | 30 reports    |
              +--------+--------+    +------+------+
                       |                    |
    +------------------+----------+    +----+----+
    |                             |    |         |
+---+---+  +-----+-----+  +-----+--+ +----+---+
|fast_  |  |extract_mvi|  |scrape_ | |capture_|
|extract|  |_csv_      |  |ref_    | |all_    |
|.py    |  |exports.py |  |tables  | |reports |
|(CDP)  |  |(HTTP POST)|  |_playwt | |.py     |
+---+---+  +-----+-----+  +-----+--+ +---+----+
    |            |              |          |
    v            v              v          v
+---+---+  +----+-----+  +----+----+ +---+----+
|168 HTML|  |7 merged  |  |33 ref  | |30 GWT  |
|batches |  |CSVs      |  |tables  | |payloads|
+---+---+  +----+-----+  +----+----+ +---+----+
    |            |              |          |
    v            |              |          |
+---+--------+  |              |          |
|parse_full_ |  v              v          |
|cost_detail |  +----+---------+          |
|.py         |  |enrich_csv_exports.py|   |
+---+--------+  +----+----------------+  |
    |                 |                   |
    v                 v                   v
+---+-----+    +-----+-----+    +-------+------+
|5 parsed |    |5 enriched |    |scrape_       |
|CSVs     |    |CSVs       |    |informer.py   |
+---+-----+    +-----+-----+    +-------+------+
    |                 |                   |
    +---------+-------+---+------+--------+
              |           |      |
              v           v      v
         +----+----+ +---+---+ +-+--------+
         |ingest_  | |build_ | |decision_ |
         |local_   | |ware-  | |engine.py |
         |files.py | |house  | |(8 modules)|
         +----+----+ |.py    | +---+------+
              |      +---+---+     |
              +----------|--------+
                         v
                  +------+-------+
                  |eagle_warehouse|
                  |.db (211 MB)   |
                  |1,376,130 rows |
                  |17 tables      |
                  +--------------+
```

### Trust Hierarchy (source_tier)

| Tier | Source | Status | Description |
|------|--------|--------|-------------|
| 1 | erp_fresh_scrape | **BLOCKED** | Direct UniVerse ODBC - requires vendor access |
| 2 | informer_bi_export | **PARTIAL** | GWT RPC extraction - 1/30 reports automated |
| 3 | html_reparse | **COMPLETE** | 168 HTML batch files -> 5 CSVs (33,428 WOs) |
| 4 | local_excel_csv | **COMPLETE** | 13 local file sources ingested |

---

## 6. Warehouse Database

### eagle_warehouse.db (211 MB SQLite)

**Location:** `warehouse/production/eagle_warehouse.db`
**Built:** 2026-01-30T11:10:07
**Total rows:** 1,376,130

#### Core Tables (11)

| Table | Rows | Key Columns |
|-------|------|-------------|
| work_orders | 33,428 | wo_number, customer_name, location, sign_type, sales_code, estimator, quote_nbr, total_cost, quoted_price, sale_price, gross_margin, gm_pct |
| labor_detail | 254,012 | wo_number, labor_date, work_dept, work_code, employee_name, actual_hrs, job_cost |
| labor_summary | 161,377 | wo_number, work_dept, work_code, est_hrs, actual_hrs, est_cost, job_cost |
| material_transactions | 780,868 | wo_number, material_date, inventory_item, est_qty, actual_qty, est_cost, job_cost |
| outplant_transactions | 23,352 | wo_number, outplant_date, sub_contractor, est_qty, actual_qty, est_cost, job_cost |
| invoices | 26,643 | invoice_number, invoice_date, customer_name, gross_sales, total_cost, gross_margin |
| customers | 3,748 | customer_id, customer_name, gross_sales, total_cost, gross_margin |
| sales_orders | 27,707 | so_number, customer_name, order_date, ship_date, order_status |
| purchase_orders | 5,974 | po_number, vendor_name, wo_number, order_qty, unit_price |
| inventory | 1,062 | part_number, description, qty_on_hand, uom, acctg_cost |
| employees | 95 | employee_name, total_hours, primary_dept, is_active (18 active) |

#### Reference Tables (2)

| Table | Rows | Purpose |
|-------|------|---------|
| ref_work_codes | 62 | Work code -> description + department |
| ref_sign_types | 38 | Sign type code -> description |

#### Analytics Tables (4)

| Table | Rows | Purpose |
|-------|------|---------|
| shop_efficiency | 44 | Efficiency score per work code |
| labor_multipliers | 42 | Labor time stats (avg, min, max, std_dev) |
| gm_by_salesperson | 4,298 | GM detail by salesperson |
| labor_forensics | 53,380 | Deep labor analysis |

#### Indexes (19)

```
idx_labor_detail_wo, idx_labor_detail_emp, idx_labor_detail_dept, idx_labor_detail_date
idx_labor_summary_wo, idx_material_wo, idx_outplant_wo
idx_invoices_cust, idx_invoices_date, idx_wo_customer, idx_wo_sign_type
idx_wo_estimator, idx_wo_date, idx_po_vendor, idx_sales_orders_so
idx_forensics_wo, idx_forensics_emp, idx_gm_sp_cust
```

---

## 7. Scripts Inventory

### Data Extraction (6 scripts, 4,148 lines)

| Script | Lines | Method | Status |
|--------|-------|--------|--------|
| extract_all_so_contracts.py | 724 | Chrome CDP -> HTML spool | COMPLETE (168 batches) |
| extract_mvi_csv_exports.py | 967 | HTTP POST -> CSV download | COMPLETE (6 endpoints x 22 years) |
| scrape_ref_tables_playwright.py | 319 | Playwright -> ref table HTML | COMPLETE (31/33 tables) |
| capture_all_reports.py | 1,093 | Playwright -> GWT-RPC payloads | COMPLETE (30 reports) |
| scrape_informer.py | 1,748 | HTTP GWT-RPC replay | PARTIAL (1/30 automated) |
| _get_session.py | 254 | Playwright SSO -> session tokens | WORKING |

### Data Parsing & Transformation (5 scripts, 2,792 lines)

| Script | Lines | Input | Output |
|--------|-------|-------|--------|
| parse_full_cost_detail.py | 907 | 168 HTML batch files | 5 CSVs (WO headers, labor detail/summary, material, outplant) |
| gwt_parser.py | 1,259 | GWT-RPC responses | Parsed rows via extract_rows() |
| gwt_deserialize.py | 613 | GWT binary format | Right-to-left HashMap deserialization |
| enrich_csv_exports.py | 413 | Merged CSVs + ref tables | 5 enriched CSVs with human-readable names |
| split_captures.py | 170 | Captured payloads | Split into individual files |

### Data Loading (2 scripts, 1,666 lines)

| Script | Lines | Purpose |
|--------|-------|---------|
| build_warehouse.py | 1,034 | Merge all CSVs into SQLite with trust-based upsert |
| ingest_local_files.py | 632 | Scan H:\ and OneDrive for Excel/CSV -> local_*.csv |

### Analytics (1 script, 711 lines)

| Script | Lines | Purpose |
|--------|-------|---------|
| decision_engine.py | 711 | 8-module analytics (estimating, profitability, capacity, efficiency, materials, customers, vendors, cash flow) |

### Lookup & Query (1 script, 203 lines)

| Script | Lines | Purpose |
|--------|-------|---------|
| lookup_job.py | 203 | Quote-to-files lookup combining ESC index + warehouse data |

### Utilities & Debug (5 scripts, 1,632 lines)

| Script | Lines | Purpose |
|--------|-------|---------|
| tracer_bullet.py | 451 | POC: CDP login -> Informer export |
| validate_so_contract.py | 408 | Data validation checks |
| gwt_analyze.py | 379 | GWT serialization diagnostics |
| gwt_dump_rows.py | 155 | Raw data dump around Row positions |
| extract_quote_report.py | 301 | Quote report extraction |
| extract_spooled_reports.py | 281 | Spooled report handling |

### Tests (4 scripts, 816 lines)

| Script | Lines | Purpose |
|--------|-------|---------|
| test_pipeline_fixes.py | 269 | Pytest suite for extraction pipeline |
| test_quote_pagination.py | 292 | Quote pagination validation |
| test_field_mapping.py | 137 | Field mapping verification |
| test_extract_5pages.py | 118 | 5-page extraction test |

---

## 8. G: Drive Integration

### G: Drive = `\\ES-FS02\customers2` (mapped as G:)

| Metric | Value |
|--------|-------|
| Top-level folders | 50 (A-Z + numerics + special) |
| Customer folders | 6,861 |
| Total files scanned | 456,030 |
| ESC-numbered files | 40,611 (clean) |
| Unique ESC numbers | ~13,508 |

### Folder Hierarchy

```
G:\
  [Letter A-Z]/
    [Customer Name]/
      [Location or Project or Year]/
        [Files: CDR, PDF, AI, DXF, JPG, etc.]
```

### ESC Filename Format

**Pattern:** `[Description] MMYY-NNNNN-RR.ext`

| Component | Meaning | Example |
|-----------|---------|---------|
| MMYY | Month/Year created | `0126` = January 2026 |
| NNNNN | ESC quote/job number | `40654` |
| RR | Revision number | `00` = original |

### ESC Number Timeline

| Range | Era | Example |
|-------|-----|---------|
| ~8000s | 2010-2011 | `Bankers Trust 1st Flr 1110-8398-00.pdf` |
| ~15000s | 2014 | `H & R Block 0114-15454-00.ai` |
| ~21000s | 2016 | n/a |
| ~27000s | 2019 | `Mercy One Euclid Monument 0319-27135-00.pdf` |
| ~37000s | 2024 | Phase 1 St. Anthony letters |
| ~40000s | 2025-2026 | `Pancheros Waukee West Elev 0126-40654-00.pdf` |

### Cross-Reference Results

| Metric | Value |
|--------|-------|
| Warehouse customers matched to G: | 2,775 / 3,241 (85.6%) |
| Match: exact name | 1,208 (37.3%) |
| Match: first-word | 1,488 (45.9%) |
| Match: contains | 79 (2.4%) |
| Unmatched | 466 (14.4%) |
| ESC quote -> warehouse quote_nbr | 4,015 / 12,912 (31.1%) |

### Generated Files

| File | Rows | Purpose |
|------|------|---------|
| `g_drive_customer_map.csv` | 6,861 | Letter, Customer, SubfolderCount, Path |
| `esc_file_index_clean.csv` | 40,611 | esc_number, quote_number, full_path, customer_folder |
| `g_drive_matched_customers.csv` | 2,775 | Name, G: folder, match type |
| `g_drive_unmatched_customers.csv` | 466 | Name, reason |
| `g_drive_discovery.md` | 293 lines | Full discovery report |

---

## 9. Data Coverage & Gaps

### What's In The Warehouse (1,376,130 rows)

| Data | Rows | Source Tier | Completeness |
|------|------|------------|--------------|
| Work order costs & margins | 33,428 | Tier 3 (HTML parse) | HIGH - all historical WOs |
| Labor transactions | 254,012 | Tier 3 | HIGH - full detail |
| Labor est vs actual | 161,377 | Tier 3 | HIGH - summary rollup |
| Material transactions | 780,868 | Tier 3 | MEDIUM - contains dupes |
| Outplant transactions | 23,352 | Tier 3 | HIGH |
| Invoices | 26,643 | Tier 4 (local Excel) | MEDIUM - may be subset |
| Customers | 3,748 | Tier 4 | LOW - summary only |
| Sales orders | 27,707 | Tier 4 | MEDIUM |
| Purchase orders | 5,974 | Tier 4 | LOW - may be subset |
| Inventory | 1,062 | Tier 4 | MEDIUM - snapshot |
| Employees | 95 | Derived | HIGH (18 active) |

### What's NOT In The Warehouse

| Data | Where It Lives | How to Get It |
|------|---------------|---------------|
| Full customer master | UniVerse CUSTOMER | ODBC or Informer Customer Listing |
| Vendor master | UniVerse VENDOR | ODBC or Informer Vendor Listing |
| Quote details | UniVerse QUOTE | ODBC or Informer Quote Status |
| AR open invoices | UniVerse AR | ODBC or Informer AR Open |
| Inventory history | UniVerse INV.TRANS | ODBC or Informer Inv Trans History |
| Purchase history | UniVerse PO | ODBC or Informer Purchase History |
| Sales cost detail | UniVerse SALES | ODBC or Informer Sales Cost Detail |
| Employee hours (non-WO) | UniVerse EMPLOYEE | ERP process EMP.HOURS.BY.DATE |
| GL data | UniVerse GL | NOT ACCESSIBLE |
| Payroll data | UniVerse PAYROLL | NOT ACCESSIBLE |

### CSV Export Pipeline Data (Not Yet In SQLite)

| File | Lines | Size | Enriched |
|------|-------|------|----------|
| EMP.HOURS.BY.DATE_ALL.csv | 1,108,565 | 39MB | Yes (41MB) |
| CUST.PROD.EXPORT_ALL.csv | 134,869 | 7.4MB | Yes (6.5MB) |
| GM.BY.INV.EXPORT_ALL.csv | 129,165 | 8.4MB | Yes (7.0MB) |
| EXPORT.WIP.SUMMARY_C_ALL.csv | 67,997 | 9.1MB | No |
| SLSPER.PROD.EXPORT_ALL.csv | 63,421 | 4.5MB | Yes (4.1MB) |
| EXPORT.WO.LABOR.ANALYSIS_ALL.csv | 54,349 | 21MB | Yes (13MB) |
| EXPORT.WIP.SUMMARY_O_ALL.csv | 5,129 | 688KB | No |

---

## 10. Numbering Systems

### Three Distinct Systems

| System | Format | Range | Source |
|--------|--------|-------|--------|
| **SignX-Warehouse WO** | `NNNNN.N` | 1000.1 - 62206.1 | `so_contracts_parsed.csv` (wo_number column) |
| **SignX-Warehouse Quote** | 4-5 digit | 498 - 62172 | `so_contracts_parsed.csv` (quote_nbr column) |
| **ESC Job Number** | `MMYY-NNNNN-RR` | ~8000 - 40660+ | G: drive filenames |

### These Do NOT Directly Map

- WO `62200.2` (CAT Scale) is NOT ESC `30115` in filenames
- Pancheros WO `2214.1` with quote `5209` in warehouse but ESC `40654` in filenames
- ESC numbers come from KeyedIn's **quoting/estimating** module
- WO numbers come from the **production/billing** module
- The warehouse `quote_nbr` column is the closest match to ESC numbers (31.1% overlap)

### Cross-Reference Strategy

Customer name is the **only reliable bridge** between systems:
1. WO -> customer name -> G: drive folder -> browse for files
2. ESC number in filename -> lookup in esc_file_index_clean.csv -> get customer + path
3. Quote number -> check warehouse quote_nbr for billing data

---

## 11. Technical Reference

### Two ERP Systems

| System | URL | Technology | Status |
|--------|-----|------------|--------|
| KeyedIn ERP | `http://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/` | CGI (mvi.exe) | Extraction working |
| Informer BI | `https://eaglesign.keyedinsign.com:8443/eaglesign/Informer.html` | GWT-RPC v7 | 30 reports captured |

### ERP CGI Endpoints

```
LOGIN.START                    # Login page
DASHBOARD                     # Main dashboard
REPORT.IFRAME?REPORT_ID={id}  # Report viewer
CUST.PROD.EXPORT              # Customer product export
GM.BY.INV.EXPORT              # GM by invoice export
EMP.HOURS.BY.DATE             # Employee hours
SLSPER.PROD.EXPORT            # Salesperson product export
EXPORT.WO.LABOR.ANALYSIS      # WO labor analysis
EXPORT.WIP.SUMMARY            # WIP summary (C=closed, O=open)
```

### GWT-RPC Protocol

```
Module Base:    https://eaglesign.keyedinsign.com:8443/eaglesign/informer/
Permutation:    6823F3E0DFFF554BC1A7951AA98B182D
Protocol:       GWT RPC v7
Response:       //OK[<data>, ["string_table"], <offset>, <version>]
Page Size:      25 rows per request
Serialization:  Right-to-left HashMap<String, Value>
```

### Informer Version

```
Informer:  v4.7.0 Build 470031
Plugin:    v2 build 082914
Server:    Jetty 8.1.8
```

### Credentials

| Variable | Location | Purpose |
|----------|----------|---------|
| KEYEDIN_USERNAME | `C:\Scripts\keyedin-capture\.env` | ERP login |
| KEYEDIN_PASSWORD | `C:\Scripts\keyedin-capture\.env` | ERP login |
| JSESSIONID | Cookie (auto via SSO) | Informer session |
| authToken | Response header | GWT RPC auth |
| clientId | Response body | GWT RPC client ID |

---

## 12. Decision Engine

### 8 Analytical Modules

| Module | Purpose | Key Finding |
|--------|---------|-------------|
| Estimating Accuracy | Quoted vs actual costs | Avg variance -53% to -57% (consistent over-estimation across all estimators) |
| Shadow Burden | ERP burden rate analysis | Avg 1.35x labor cost; outliers up to 36.88x |
| Dead Stock | Inventory tied-up capital | 499 items, $241,702 tied up; H96W-SD-24V power supplies = $34,577 alone |
| Profitability | GM by customer/sign type/estimator | Top-line analysis available |
| Capacity | Labor utilization by dept | Hours capacity and bottleneck identification |
| Shop Efficiency | Est vs actual hours | 44 work codes scored |
| Customer Analytics | Customer value/retention | LTV and order frequency |
| Cash Flow | AR aging/payment patterns | DSO and aging buckets |

---

## 13. Known Issues

### Active

| Issue | Status | Detail |
|-------|--------|--------|
| License quota exceeded | ACTIVE | Too many concurrent ERP sessions from automation |
| Informer Consumer role | KNOWN | Can't create custom reports (need Designer role) |
| Material 2x duplication | FIXED but stale | Skip `****` lines applied but DB not rebuilt |
| Export CSV URL unknown | OPEN | 6 URL patterns tested, all 404 |
| SSO link intermittent | INTERMITTENT | Fallback lands on login page |
| Job 7880 not found | UNRESOLVED | Referenced for Ankeny Parks but doesn't exist in any data source |

### Bash/PowerShell Gotchas (Documented)

- `$_` gets mangled by bash into extglob — use `-File script.ps1`
- UNC backslashes mangled by MSYS — write to `.ps1` first
- `numpy.int64` breaks pandas `.join()` — use `dtype={'quote_number': str}`
- winget doesn't work inside `Start-Job` — use `Start-Process`

---

## 14. Deliverables

### For Brady (Estimation)

| Deliverable | Location | Purpose |
|-------------|----------|---------|
| Monday Estimation Briefs | `~/Desktop/MONDAY-ESTIMATION-BRIEFS.md` | Context for 3 pending jobs |
| Quote Lookup Tool | `scripts/lookup_job.py` | Instant quote-to-files + billing |

### For Analytics

| Deliverable | Location | Purpose |
|-------------|----------|---------|
| eagle_warehouse.db | `warehouse/production/` | 1.38M row SQLite analytics DB |
| Decision Report | `warehouse/reports/` | 8-module analysis output |
| Enriched CSVs | `warehouse/raw/csv_exports/` | Human-readable export data |

### For Integration

| Deliverable | Location | Purpose |
|-------------|----------|---------|
| ESC File Index | `esc_file_index_clean.csv` | 40,611 G: drive files indexed by quote# |
| Customer Match | `g_drive_matched_customers.csv` | 2,775 warehouse-to-G: mappings |
| G: Discovery | `g_drive_discovery.md` | Complete archive structure documentation |

---

## 15. Next Steps

### Immediate (Ready Now)

1. **Rebuild warehouse DB** with enriched CSVs (csv_exports data not yet in SQLite)
2. **Fix material dedup** — rebuild with `****` line skip applied
3. **Load into DuckDB/Pandas** for ad-hoc analytics
4. **Build dashboards** (Streamlit, Supabase, or Jupyter)

### Short-Term (Requires Browser Session)

5. **Automate remaining 29 Informer reports** via scrape_informer.py
6. **Capture additional MVI modules** (Quotes, GL, AP detail)
7. **Improve customer matching** — fuzzy match with Levenshtein, add numeric-prefix folders

### Strategic (Requires Vendor/IT)

8. **Request ODBC read-only access** to UniVerse database (eliminates all scraping)
9. **Request data dictionary** (table/field documentation)
10. **Upgrade Informer role** to Designer (custom report creation)
11. **Manage session licensing** (concurrent user quota)

### The Single Highest-Leverage Action

> **Get ODBC read-only access to the UniVerse database.**
>
> This eliminates all browser automation, GWT reverse-engineering, HTML scraping,
> field name discovery, pagination handling, and session management.
> Replace with: `SELECT * FROM {table}` via pyodbc.

---

## Resume Instructions

```bash
# Read this file to resume
Read C:\Scripts\signx-warehouse\SESSION_STATE.md

# Quick lookup tool
python C:\Scripts\signx-warehouse\scripts\lookup_job.py <quote_number>

# Estimation briefs
Read C:\Users\Brady.EAGLE\Desktop\MONDAY-ESTIMATION-BRIEFS.md
```

---

**Generated:** 2026-02-15 23:30 CST
**User:** Brady Flink
**Agent:** Claude Opus 4.6
**Commits:** 6 (ea086b1 -> ea772ab)
**Total Lines of Python:** 13,968 across 27 scripts
**Total Data Rows:** 1,376,130 (warehouse) + 40,611 (ESC index) + 1,563,495 (CSV exports)
