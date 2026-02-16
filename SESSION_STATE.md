# SignX Warehouse - Comprehensive Session State

**Generated:** 2026-02-15 23:45 CST
**Repository:** https://github.com/EAGLE605/signx-warehouse + https://github.com/EAGLE605/SignX
**Branch:** master
**Latest Commit:** 3794acb (2026-02-15 23:08:46 -0600)
**Total Size:** ~1.6 GB on disk (warehouse data + scripts)
**Agent:** Claude Opus 4.6
**Operator:** Brady Flink, Eagle Sign Co.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Session Timeline](#2-session-timeline)
3. [Git History](#3-git-history)
4. [Repository Structure](#4-repository-structure)
5. [Data Pipeline Architecture](#5-data-pipeline-architecture)
6. [DuckDB Warehouse](#6-duckdb-warehouse)
7. [SQLite Warehouse](#7-sqlite-warehouse)
8. [Scripts Inventory](#8-scripts-inventory)
9. [G: Drive Integration](#9-g-drive-integration)
10. [Data Coverage & Gaps](#10-data-coverage--gaps)
11. [Numbering Systems](#11-numbering-systems)
12. [Technical Reference](#12-technical-reference)
13. [Decision Engine](#13-decision-engine)
14. [Known Issues](#14-known-issues)
15. [Deliverables](#15-deliverables)
16. [Next Steps](#16-next-steps)

---

## 1. Project Overview

SignX Warehouse is a data extraction, parsing, and analytics toolkit that pulls operational data from Eagle Sign's KeyedIn Manufacturing ERP (Sign Edition) and maps it to the company's G: drive file archive. The goal is to build an independent data warehouse for estimation, analytics, and business intelligence.

### What It Does

1. **Extracts data** from two systems:
   - **KeyedIn ERP** (CGI-based, `mvi.exe`) - Work orders, labor, materials, invoices, sales, purchasing
   - **Informer BI** (GWT-RPC v7) - 30 pre-built reports on port 8443
2. **Parses HTML spool files** - 168 batch HTML files containing 33,428 work order cost details
3. **Scrapes reference tables** - 33 MVI reference code listings via Playwright (system Chrome)
4. **Exports CSV reports** - 6 endpoints x 22 years = 154 jobs, merged into 7 _ALL files, enriched with ref lookups
5. **Loads into DuckDB** - 40 tables (7 main + 33 ref), 609,132 rows, 18.0MB analytical database
6. **Maps the G: drive** (`\\ES-FS02\customers2`) - 6,861 customer folders, 456,030 files scanned
7. **Cross-references** warehouse data with G: drive files via customer name + ESC quote numbers
8. **Produces analytics** via decision engine (estimating accuracy, profitability, capacity, efficiency)

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
| **3** | 2026-02-15 (early) | Opus 4.6 | CSV export pipeline (6 endpoints x 22 years = 154 jobs), reference table scraper (33 tables via Playwright), enrichment engine (5 files at 98-100% join rate), crash recovery/resume |
| **4** | 2026-02-15 (mid) | Opus 4.6 | G: drive discovery (6,861 folders), ESC filename scanner (40,611 indexed files), quote lookup tool, estimation briefs, .gitignore security fix, full commit/push |
| **5** | 2026-02-15 (late) | Opus 4.6 | **DuckDB warehouse load** (40 tables, 609K rows, 18MB), clean CSV pipeline, multiline header fix, session state generation |

### Session 5 Detail (Current)

**Tasks completed this session:**

1. **DuckDB Database Creation**
   - Built `scripts/load_duckdb.py` (329 lines) - strips report-format artifacts, writes clean CSVs, loads via DuckDB native `read_csv`
   - Strips metadata rows, repeated year headers, subtotals, blank lines, "NO RECORDS FOUND" placeholders
   - First attempt used `executemany` with 463K rows - hung indefinitely
   - Rewrote to 2-pass: Python csv strips to clean CSV, DuckDB `read_csv` loads natively (completes in seconds)
   - 10 ref tables had multiline quoted headers (`"Sales\nAccount"`) that broke DuckDB auto-detect
   - Added Python csv fallback: read multiline, flatten newlines, write clean, reload
   - Final result: 40 tables, 609,132 rows, 18.0MB at `warehouse/signx.duckdb`

2. **Clean CSV Intermediate Layer**
   - Created `warehouse/clean/` directory (72MB total, 17 files)
   - 7 main table CSVs with normalized column names (snake_case, deduplicated)
   - 10 reference table CSVs with flattened multiline headers
   - These serve as DuckDB's import source and are reusable for other tools

3. **Data Validation**
   - Queried all tables to verify row counts match source CSVs
   - Validated enrichment columns populated (work_dept_name, salesperson_1_name, etc.)
   - Sample queries confirmed: Cat Scale = $29.2M top customer, Fabrication = 180K hrs top dept
   - DuckDB auto-detected date columns (time_date, inv_date as DATE type)

4. **Session State Documentation**
   - Updated SESSION_STATE.md with DuckDB warehouse details (this file)
   - Updated SESSION_HANDOFF.md in prior step

---

## 3. Git History

```
3794acb 2026-02-15 23:08:46 Add DuckDB loader script and ignore DuckDB binary files
0fcb009 2026-02-15 23:04:00 Add comprehensive session state document
ea772ab 2026-02-15 22:59:23 Update session handoff with Session 3 status (pipeline complete)
84bc856 2026-02-15 22:56:57 Add warehouse data extraction pipeline, parsed datasets, and skills
6086bbe 2026-02-15 22:53:05 Add CSV export pipeline: extract, reference tables, and enrichment
f7f12b5 2026-02-15 22:52:42 Add G: drive discovery, ESC file index, and quote lookup tool
dbf6d00 2026-02-06 17:46:58 Update session handoff with final status
ea086b1 2026-02-06 00:47:43 Initial commit: SignX Warehouse - KeyedIn data extraction toolkit
```

**Total:** 8 commits, 2 remotes (origin=signx-warehouse, signx=SignX)

---

## 4. Repository Structure

```
C:\Scripts\signx-warehouse\ (~1.6 GB)
├── .gitignore                         # Excludes: .env, *.duckdb, csv_exports/, etc.
├── AGENTS.md                          # Agent instructions (beads integration)
├── SESSION_HANDOFF.md                 # Session-by-session handoff notes
├── SESSION_STATE.md                   # THIS FILE - comprehensive state
├── SYSTEM_KNOWLEDGE_BASE.md           # Full technical reference (550 lines)
├── g_drive_discovery.md               # G: drive mapping report (293 lines)
├── g_drive_matched_customers.csv      # 2,775 warehouse->G: matches
├── g_drive_unmatched_customers.csv    # 466 unmatched customers
├── esc_file_index_clean.csv           # Clean ESC index (40,611 rows)
├── scan_esc_numbers.ps1               # PowerShell G: drive scanner (214 lines)
│
├── scripts/ (28 files, ~14,300 lines)
│   ├── load_duckdb.py                 # DuckDB warehouse loader (329 lines) [NEW]
│   ├── enrich_csv_exports.py          # Reference code enrichment (413 lines)
│   ├── extract_mvi_csv_exports.py     # Bulk CSV export from MVI (967 lines)
│   ├── scrape_ref_tables_playwright.py # Playwright ref table scraper (319 lines)
│   ├── build_warehouse.py             # Merge all CSVs into SQLite (1,034 lines)
│   ├── parse_full_cost_detail.py      # HTML -> 5 CSVs (907 lines)
│   ├── decision_engine.py             # 8-module analytics engine (711 lines)
│   ├── lookup_job.py                  # Quote-to-files lookup (203 lines)
│   ├── capture_all_reports.py         # Playwright GWT-RPC capture (1,093 lines)
│   ├── scrape_informer.py             # HTTP GWT-RPC extraction (1,748 lines)
│   ├── gwt_parser.py                  # GWT RPC v7 parser (1,259 lines)
│   ├── gwt_deserialize.py             # Right-to-left GWT deser (613 lines)
│   ├── ingest_local_files.py          # H:\ + OneDrive scanner (632 lines)
│   └── ... (14 more: extractors, tests, utilities)
│
├── warehouse/
│   ├── signx.duckdb                   # DuckDB database (18.0 MB, 40 tables, 609K rows) [NEW]
│   ├── clean/                         # Clean intermediate CSVs (72 MB, 17 files) [NEW]
│   │   ├── emp_hours.csv              # 463,825 rows, 14 cols (39.2MB)
│   │   ├── cust_prod.csv              # 26,947 rows, 28 cols (4.5MB)
│   │   ├── gm_by_inv.csv             # 26,947 rows, 33 cols (4.6MB)
│   │   ├── slsper_prod.csv            # 26,947 rows, 25 cols (3.9MB)
│   │   ├── wo_labor.csv               # 27,004 rows, 168 cols (12.3MB)
│   │   ├── wip_summary_closed.csv     # 33,880 rows, 34 cols (6.6MB)
│   │   ├── wip_summary_open.csv       # 2,447 rows, 36 cols (0.5MB)
│   │   └── ref_*.csv                  # 10 cleaned reference tables
│   ├── production/
│   │   ├── eagle_warehouse.db         # SQLite database (211 MB, 17 tables, 1.38M rows)
│   │   └── warehouse_manifest.json    # Build metadata + row counts
│   ├── staging/                       # (empty, used during builds)
│   ├── reports/
│   │   └── decision_report_*.md       # Decision engine output
│   └── raw/                           # (~1.4 GB, mostly .gitignored)
│       ├── csv_exports/               # 197 files: yearly CSVs, merged, enriched, ref tables
│       ├── so_contracts/              # .gitignored
│       ├── wo_batches/                # .gitignored
│       └── ...
│
├── config/                            # (empty)
├── skills/
│   └── constructioniq-frameworks.md   # Skill reference
└── tests/                             # (empty)
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
    |                  |          |    |         |
+---+---+  +----------+--+ +-----+--+ +----+---+
|fast_  |  |extract_mvi_ | |scrape_ | |capture_|
|extract|  |csv_exports  | |ref_    | |all_    |
|.py    |  |.py (HTTP)   | |tables  | |reports |
|(CDP)  |  |154 jobs     | |_playwt | |.py     |
+---+---+  +------+------+ +--+-----+ +---+----+
    |              |           |           |
    v              v           v           v
+---+---+  +------+------+ +--+----+ +---+----+
|168 HTML|  |7 merged CSVs| |33 ref | |30 GWT  |
|batches |  |1.56M lines  | |tables | |payloads|
+---+---+  +------+------+ +--+----+ +---+----+
    |              |           |           |
    v              v           v           |
+---+--------+ +---+----------+---+       |
|parse_full_ | |enrich_csv_exports|       |
|cost_detail | |.py (join refs)   |       |
+---+--------+ +---+--------------+       |
    |                |                    |
    v                v                    v
+---+-----+  +------+-------+  +--------+-------+
|5 parsed |  |5 enriched    |  |scrape_informer |
|CSVs     |  |CSVs          |  |.py (HTTP GWT)  |
+---+-----+  +------+-------+  +--------+-------+
    |                |                    |
    +--------+-------+----+------+--------+
             |            |      |
             v            v      v
    +--------+---+ +------+---+ +-+--------+
    |load_duckdb | |build_    | |decision_ |
    |.py [NEW]   | |warehouse | |engine.py |
    |strip+load  | |.py       | |(8 modules)|
    +--------+---+ +------+---+ +---+------+
             |            |         |
             v            v         v
    +--------+---+ +------+------+ +----+------+
    |signx.duckdb| |eagle_ware-  | |reports/   |
    |18MB, 40 tbl| |house.db     | |decision_  |
    |609K rows   | |211MB, 17tbl | |report.md  |
    +------------+ |1.38M rows   | +-----------+
                   +-------------+
```

### Two Analytical Databases

| Database | Engine | Size | Tables | Rows | Purpose |
|----------|--------|------|--------|------|---------|
| `signx.duckdb` | DuckDB | 18 MB | 40 | 609,132 | CSV exports + ref tables (2005-2026, enriched) |
| `eagle_warehouse.db` | SQLite | 211 MB | 17 | 1,376,130 | HTML batch data + local files (full history) |

### Trust Hierarchy (source_tier)

| Tier | Source | Status | Description |
|------|--------|--------|-------------|
| 1 | erp_fresh_scrape | **BLOCKED** | Direct UniVerse ODBC - requires vendor access |
| 2 | informer_bi_export | **PARTIAL** | GWT RPC extraction - 1/30 reports automated |
| 3 | html_reparse | **COMPLETE** | 168 HTML batch files -> 5 CSVs (33,428 WOs) |
| 4 | local_excel_csv | **COMPLETE** | 13 local file sources ingested |
| 5 | mvi_csv_export | **COMPLETE** | 6 endpoints x 22 years, enriched with ref lookups |

---

## 6. DuckDB Warehouse

### signx.duckdb (18.0 MB)

**Location:** `warehouse/signx.duckdb`
**Created:** 2026-02-15
**Loader:** `scripts/load_duckdb.py` (329 lines)
**Clean CSVs:** `warehouse/clean/` (72 MB, 17 files)

#### Main Tables (7)

| Table | Cols | Rows | Source File | Key Columns |
|-------|------|------|-------------|-------------|
| emp_hours | 14 | 463,825 | EMP.HOURS.BY.DATE_ALL_enriched | empno, employee_name, time_date (DATE), labor_hrs, work_code, work_dept_name |
| wip_summary_closed | 34 | 33,880 | EXPORT.WIP.SUMMARY_C_ALL | work_order, act_total, est_total, var_cost, act_gm_pct, customer_name |
| wo_labor | 168 | 27,004 | EXPORT.WO.LABOR.ANALYSIS_ALL_enriched | wo, due_date, customer, sign_type, template_code + 22 dept groups x 6 metrics |
| cust_prod | 28 | 26,947 | CUST.PROD.EXPORT_ALL_enriched | cust_no, customer_name, prod_code, gross_sales, gross_margin, salesperson_1_name |
| gm_by_inv | 33 | 26,947 | GM.BY.INV.EXPORT_ALL_enriched | invoice_no, inv_date, prod_code, gross_sales, total_cost, gross_margin, salesper_1_name |
| slsper_prod | 25 | 26,947 | SLSPER.PROD.EXPORT_ALL_enriched | invoice_no, inv_date, prod_code, gross_sales, gross_margin, salesperson_1_name |
| wip_summary_open | 36 | 2,447 | EXPORT.WIP.SUMMARY_O_ALL | work_order, act_total, est_total, customer_name, due_date |

#### Reference Tables (33)

| Table | Rows | Key Use |
|-------|------|---------|
| ref_salespersons_list | 15 | Salesperson code -> name (used in enrichment) |
| ref_states_list | 63 | State abbreviation -> name |
| ref_sales_taxes_list | 549 | Tax jurisdiction details |
| ref_work_code_list | 62 | Work code -> description + dept mapping |
| ref_sign_type_codes_listing | 38 | Sign type code -> description |
| ref_sign_template_listing | 55 | Template code -> description |
| ref_sales_codes_list | 39 | Product/sales code -> GL accounts |
| ref_show_inv_types | 52 | Inventory type codes |
| ref_show_um_codes | 32 | Unit of measure codes |
| ref_country_list | 31 | Country codes |
| ref_est_quote_status_code_list | 30 | Quote status codes |
| ref_work_dept_list | 21 | Work dept code -> name (FABRICATION, INSTALL, etc.) |
| ref_quote_sales_stage_code_listing | 21 | Sales pipeline stages |
| ref_territory_codes_list | 18 | Sales territory codes |
| ref_extra_charges_list | 16 | Extra charge codes |
| ref_show_adjust_code | 12 | Inventory adjustment codes |
| ref_show_buyers | 12 | Buyer/purchasing agents |
| ref_order_classes_list | 12 | Order classification codes |
| ref_price_codes_list | 8 | Price tier codes |
| ref_account_type_code_listing | 7 | Customer account types |
| ref_show_op_status | 7 | Operation status codes |
| ref_reason_codes_list | 6 | Return/adjustment reason codes |
| ref_show_issue_reason_codes | 5 | Inventory issue reasons |
| ref_call_method_codes_listing | 4 | CRM call method codes |
| ref_show_engr_status_codes | 4 | Engineering status codes |
| ref_call_type_codes_listing | 3 | CRM call type codes |
| ref_lead_source_event_listing | 3 | Lead source tracking |
| ref_price_class_code_list | 3 | Price class codes |
| ref_project_milestone_codes_listing | 3 | Project milestone tracking |
| ref_service_call_status_code_listing | 3 | Service call status |
| ref_order_types_list | 1 | Order type codes |
| ref_project_status_codes_listing | 0 | (empty - no active data) |
| ref_project_type_codes_listing | 0 | (empty - no active data) |

#### Key Analytics Queries (Validated)

```sql
-- Top 10 customers by gross sales
SELECT customer_name, count(*) as invoices, round(sum(gross_sales),2) as total_sales
FROM cust_prod WHERE gross_sales > 0
GROUP BY customer_name ORDER BY total_sales DESC LIMIT 10;

-- Result: Cat Scale $29.2M (2,510 invoices), Nagle Signs $2.1M, City of Des Moines $705K

-- Hours by department
SELECT work_dept_name, round(sum(labor_hrs),1) as total_hrs, count(*) as entries
FROM emp_hours WHERE work_dept_name != ''
GROUP BY work_dept_name ORDER BY total_hrs DESC;

-- Result: Fabrication 181K hrs, Installation 101K, Vinyl 31K, Paint 30K, Electrical 24K

-- Salesperson performance
SELECT salesperson_1_name, count(*) as invoices, round(sum(gross_sales),2) as sales
FROM cust_prod WHERE salesperson_1_name IS NOT NULL AND salesperson_1_name != ''
GROUP BY salesperson_1_name ORDER BY sales DESC;
```

#### DuckDB Loader Architecture

```
Raw enriched CSVs (report-format: metadata + repeated headers + subtotals + blank lines)
    |
    v
[strip_to_clean_csv()] Python csv reader
    - Skips blank rows, metadata (Eagle Sign, dates, timestamps)
    - Skips subtotals (*** Totals, Product Type Totals, Grand Total)
    - Skips repeated year headers (keeps first only)
    - Skips "NO RECORDS FOUND" rows
    - Normalizes column names (snake_case, deduplicated)
    - Pads/trims rows to header width
    |
    v
Clean CSVs in warehouse/clean/ (72 MB, single header + data rows only)
    |
    v
[DuckDB read_csv()] Native columnar import
    - auto_detect=true for type inference
    - ignore_errors=true for edge cases
    - null_padding=true for ragged rows
    |
    v
signx.duckdb (18.0 MB, 40 tables)

Reference table fallback:
    DuckDB read_csv fails on multiline quoted headers ("Sales\nAccount")
        -> Python csv.reader (handles RFC 4180 multiline)
        -> Flatten newlines in headers and values
        -> Write clean CSV -> DuckDB read_csv (10 tables needed this)
```

---

## 7. SQLite Warehouse

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

---

## 8. Scripts Inventory

### Data Extraction (6 scripts, ~4,400 lines)

| Script | Lines | Method | Status |
|--------|-------|--------|--------|
| extract_all_so_contracts.py | 724 | Chrome CDP -> HTML spool | COMPLETE (168 batches) |
| extract_mvi_csv_exports.py | 967 | HTTP POST -> CSV download | COMPLETE (154 jobs, resume/retry) |
| scrape_ref_tables_playwright.py | 319 | Playwright + system Chrome | COMPLETE (33/33 tables) |
| capture_all_reports.py | 1,093 | Playwright -> GWT-RPC payloads | COMPLETE (30 reports) |
| scrape_informer.py | 1,748 | HTTP GWT-RPC replay | PARTIAL (1/30 automated) |
| _get_session.py | 254 | Playwright SSO -> session tokens | WORKING |

### Data Parsing & Transformation (5 scripts, ~2,800 lines)

| Script | Lines | Input | Output |
|--------|-------|-------|--------|
| parse_full_cost_detail.py | 907 | 168 HTML batch files | 5 CSVs (WO headers, labor detail/summary, material, outplant) |
| gwt_parser.py | 1,259 | GWT-RPC responses | Parsed rows via extract_rows() |
| gwt_deserialize.py | 613 | GWT binary format | Right-to-left HashMap deserialization |
| enrich_csv_exports.py | 413 | Merged CSVs + ref tables | 5 enriched CSVs (98-100% join rates) |
| split_captures.py | 170 | Captured payloads | Split into individual files |

### Data Loading (3 scripts, ~2,000 lines)

| Script | Lines | Purpose |
|--------|-------|---------|
| load_duckdb.py | 329 | Strip report-format CSVs -> DuckDB (40 tables) [NEW] |
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

### Utilities, Debug & Tests (9 scripts, ~2,400 lines)

| Script | Lines | Purpose |
|--------|-------|---------|
| tracer_bullet.py | 451 | POC: CDP login -> Informer export |
| validate_so_contract.py | 408 | Data validation checks |
| gwt_analyze.py | 379 | GWT serialization diagnostics |
| extract_quote_report.py | 301 | Quote report extraction |
| extract_spooled_reports.py | 281 | Spooled report handling |
| gwt_dump_rows.py | 155 | Raw data dump around Row positions |
| test_pipeline_fixes.py | 269 | Pytest suite for extraction pipeline |
| test_quote_pagination.py | 292 | Quote pagination validation |
| test_field_mapping.py | 137 | Field mapping verification |
| test_extract_5pages.py | 118 | 5-page extraction test |

---

## 9. G: Drive Integration

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

---

## 10. Data Coverage & Gaps

### Total Data Inventory

| Store | Tables | Rows | Source |
|-------|--------|------|--------|
| signx.duckdb | 40 | 609,132 | MVI CSV exports (2005-2026) + 33 ref tables |
| eagle_warehouse.db | 17 | 1,376,130 | HTML batch parse + local files |
| csv_exports/ | 197 files | ~1.56M lines | Raw yearly + merged + enriched CSVs |
| esc_file_index_clean.csv | 1 file | 40,611 | G: drive filename scan |

### What's NOT In The Warehouse

| Data | Where It Lives | How to Get It |
|------|---------------|---------------|
| Full customer master | UniVerse CUSTOMER | ODBC or Informer Customer Listing |
| Vendor master | UniVerse VENDOR | ODBC or Informer Vendor Listing |
| Quote details | UniVerse QUOTE | ODBC or Informer Quote Status |
| AR open invoices | UniVerse AR | ODBC or Informer AR Open |
| GL data | UniVerse GL | NOT ACCESSIBLE |
| Payroll data | UniVerse PAYROLL | NOT ACCESSIBLE |

### Enrichment Join Results (from enrich_csv_exports.py)

| File | Column | Match Rate | Orphans |
|------|--------|------------|---------|
| EMP.HOURS | Work Code | 100% | 0 |
| EMP.HOURS | Work Dept | 100% | 0 |
| CUST.PROD | Prod Code | 100% | 0 |
| CUST.PROD | Salesperson #1 | 98.3% | 6 codes (BOBR, TOMW, JMC, JENNYF, JENP, LUIS) |
| GM.BY.INV | Prod Code | 100% | 0 |
| GM.BY.INV | SalesPer #1 | 98.2% | 6 codes |
| SLSPER.PROD | Prod Code | 100% | 0 |
| SLSPER.PROD | Salesperson #1 | 98.0% | 6 codes |
| WO.LABOR | Sign Type | 99.8% | 1 code |
| WO.LABOR | Template | 99.0% | 3 codes |

The 6 orphan salesperson codes (BOBR, TOMW, JMC, JENNYF, JENP, LUIS) are hard-deleted from KeyedIn — not recoverable even with SHOW_ALL_CODES enabled.

---

## 11. Numbering Systems

### Three Distinct Systems

| System | Format | Range | Source |
|--------|--------|-------|--------|
| **WO Number** | `NNNNN.N` | 1000.1 - 62206.1 | `so_contracts_parsed.csv` (wo_number column) |
| **Quote Number** | 4-5 digit | 498 - 62172 | `so_contracts_parsed.csv` (quote_nbr column) |
| **ESC Job Number** | `MMYY-NNNNN-RR` | ~8000 - 40660+ | G: drive filenames |

### Cross-Reference Strategy

Customer name is the **only reliable bridge** between systems:
1. WO -> customer name -> G: drive folder -> browse for files
2. ESC number in filename -> lookup in esc_file_index_clean.csv -> get customer + path
3. Quote number -> check warehouse quote_nbr for billing data

---

## 12. Technical Reference

### Two ERP Systems

| System | URL | Technology | Status |
|--------|-----|------------|--------|
| KeyedIn ERP | `https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/` | CGI (mvi.exe) | Extraction working |
| Informer BI | `https://eaglesign.keyedinsign.com:8443/eaglesign/Informer.html` | GWT-RPC v7 | 30 reports captured |

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

### Credentials

| Variable | Location | Purpose |
|----------|----------|---------|
| KEYEDIN_USERNAME | `C:\Scripts\keyedin-capture\.env` | ERP login |
| KEYEDIN_PASSWORD | `C:\Scripts\keyedin-capture\.env` | ERP login |
| JSESSIONID | Cookie (auto via SSO) | Informer session |

---

## 13. Decision Engine

### 8 Analytical Modules

| Module | Purpose | Key Finding |
|--------|---------|-------------|
| Estimating Accuracy | Quoted vs actual costs | Avg variance -53% to -57% (consistent over-estimation) |
| Shadow Burden | ERP burden rate analysis | Avg 1.35x labor cost; outliers up to 36.88x |
| Dead Stock | Inventory tied-up capital | 499 items, $241,702; H96W-SD-24V = $34,577 alone |
| Profitability | GM by customer/sign type/estimator | Cat Scale $29.2M, avg GM varies by product |
| Capacity | Labor utilization by dept | Fabrication 181K hrs dominant |
| Shop Efficiency | Est vs actual hours | 44 work codes scored |
| Customer Analytics | Customer value/retention | LTV and order frequency |
| Cash Flow | AR aging/payment patterns | DSO and aging buckets |

---

## 14. Known Issues

### Active

| Issue | Status | Detail |
|-------|--------|--------|
| License quota exceeded | ACTIVE | Too many concurrent ERP sessions from automation |
| Informer Consumer role | KNOWN | Can't create custom reports (need Designer role) |
| Material 2x duplication | FIXED but stale | Skip `****` lines applied but SQLite DB not rebuilt |
| Orphan salesperson codes | PERMANENT | 6 codes (BOBR, TOMW, etc.) hard-deleted from KeyedIn |
| SSO link intermittent | INTERMITTENT | Fallback lands on login page |

### Technical Gotchas (Documented)

- `executemany` with 400K+ rows hangs DuckDB Python — use native `read_csv` instead
- DuckDB `read_csv_auto` fails on multiline quoted headers — flatten with Python csv first
- Report-format CSVs have blank lines between every data row — strip before loading
- `$_` gets mangled by bash into extglob — use `-File script.ps1`
- UNC backslashes mangled by MSYS — write to `.ps1` first
- `numpy.int64` breaks pandas `.join()` — use `dtype={'quote_number': str}`
- Playwright bundled Chromium chmod fails on Windows — use `channel="chrome"` for system Chrome

---

## 15. Deliverables

### Databases

| Deliverable | Location | Size | Tables | Rows |
|-------------|----------|------|--------|------|
| DuckDB Warehouse | `warehouse/signx.duckdb` | 18 MB | 40 | 609,132 |
| SQLite Warehouse | `warehouse/production/eagle_warehouse.db` | 211 MB | 17 | 1,376,130 |

### For Estimation

| Deliverable | Location | Purpose |
|-------------|----------|---------|
| Quote Lookup Tool | `scripts/lookup_job.py` | Instant quote-to-files + billing |
| Monday Briefs | `~/Desktop/MONDAY-ESTIMATION-BRIEFS.md` | Context for 3 pending jobs |

### For Integration

| Deliverable | Location | Purpose |
|-------------|----------|---------|
| ESC File Index | `esc_file_index_clean.csv` | 40,611 G: drive files indexed by quote# |
| Customer Match | `g_drive_matched_customers.csv` | 2,775 warehouse-to-G: mappings |
| G: Discovery | `g_drive_discovery.md` | Complete archive structure documentation |
| Clean CSVs | `warehouse/clean/` | 17 analysis-ready CSVs (72 MB) |

---

## 16. Next Steps

### Immediate (Ready Now)

1. **Build dashboards** on DuckDB (Streamlit, Jupyter, or Evidence)
2. **Rebuild SQLite warehouse** with enriched CSVs (csv_exports data not yet in SQLite)
3. **Fix material dedup** — rebuild with `****` line skip applied
4. **Cross-reference DuckDB + SQLite** — bridge CSV export data with HTML batch data

### Short-Term (Requires Browser Session)

5. **Automate remaining 29 Informer reports** via scrape_informer.py
6. **Capture additional MVI modules** (Quotes, GL, AP detail)
7. **Improve customer matching** — fuzzy match with Levenshtein

### Strategic (Requires Vendor/IT)

8. **Request ODBC read-only access** to UniVerse database
9. **Request data dictionary** (table/field documentation)
10. **Upgrade Informer role** to Designer (custom report creation)

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

# Query the DuckDB warehouse
python -c "import duckdb; con = duckdb.connect('C:/Scripts/signx-warehouse/warehouse/signx.duckdb', read_only=True); print(con.execute('SELECT * FROM emp_hours LIMIT 5').fetchdf())"

# Quick lookup tool
python C:\Scripts\signx-warehouse\scripts\lookup_job.py <quote_number>

# Reload DuckDB from enriched CSVs
python C:\Scripts\signx-warehouse\scripts\load_duckdb.py
```

---

**Generated:** 2026-02-15 23:45 CST
**User:** Brady Flink
**Agent:** Claude Opus 4.6
**Commits:** 8 (ea086b1 -> 3794acb)
**Total Lines of Python:** ~14,300 across 28 scripts
**Total Data Rows:** 1,376,130 (SQLite) + 609,132 (DuckDB) + 40,611 (ESC index) = 2,025,873
