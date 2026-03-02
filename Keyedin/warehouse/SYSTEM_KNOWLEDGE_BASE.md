# Eagle Sign Data Intelligence System — Complete Knowledge Base

**Generated:** 2026-02-03
**System:** KeyedIn Manufacturing (Sign Edition) + Entrinsik Informer BI
**Instance:** eaglesign.keyedinsign.com
**Operator:** Brady Flink, Eagle Sign Co.

---

## 1. System Architecture Overview

```
                        +---------------------------+
                        |   UniVerse / Pick DB       |
                        |   (Rocket U2 Engine)       |
                        |   NO DIRECT ACCESS         |
                        +---------------------------+
                           |                    |
                +----------+----------+    +----+----+
                |  KeyedIn ERP        |    | Informer |
                |  (CGI/mvi.exe)      |    | BI v4.7  |
                |  Port 80/443        |    | Port 8443|
                |  240 processes      |    | 30 rpts  |
                +----------+----------+    +----+----+
                           |                    |
              +------------+------------+  +----+----+
              | fast_extract.py         |  | capture_ |
              | (Chrome CDP)            |  | all_     |
              | Phase 1: HTML reports   |  | reports  |
              +------------+------------+  | .py      |
                           |               | (Playwrt)|
              +------------+------------+  +----+----+
              | parse_full_cost_detail  |       |
              | .py (BeautifulSoup)     |  +----+----+
              | 168 batch files         |  | scrape_  |
              +------------+------------+  | informer |
                           |               | .py      |
                           |               | (HTTP    |
              +------------+-------+       | GWT RPC) |
              | ingest_local_files  |       +----+----+
              | .py (Phase 4)       |            |
              | H:\ + OneDrive      |            |
              +------------+--------+            |
                           |                     |
                     +-----+-----+               |
                     | build_    |<--------------+
                     | warehouse |
                     | .py       |
                     +-----+-----+
                           |
                     +-----+-----+
                     | eagle_    |
                     | warehouse |
                     | .db       |
                     | (211 MB)  |
                     +-----+-----+
                           |
                     +-----+-----+
                     | decision_ |
                     | engine.py |
                     | (8 modules)|
                     +-----+-----+
```

### Trust Hierarchy (source_tier)

| Tier | Source | Status | Description |
|------|--------|--------|-------------|
| 1 | erp_fresh_scrape | **BLOCKED** | Direct U2 database — requires ODBC/UniObjects access |
| 2 | informer_bi_export | **PARTIAL** | GWT RPC extraction — 1 of 30 reports automated |
| 3 | html_reparse | **COMPLETE** | 168 HTML batch files parsed into 5 CSVs |
| 4 | local_excel_csv | **COMPLETE** | 13 local file sources ingested |

---

## 2. Infrastructure

### URLs

| System | URL | Protocol |
|--------|-----|----------|
| ERP Login | `http://eaglesign.keyedinsign.com/` | HTTP → CGI |
| ERP CGI Base | `http://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/` | HTTP |
| Informer BI | `https://eaglesign.keyedinsign.com:8443/eaglesign/Informer.html` | HTTPS |
| Informer SSO | `https://eaglesign.keyedinsign.com:8443/eaglesign/sso?u={user}&t={token}` | HTTPS |
| Informer RPC | `https://eaglesign.keyedinsign.com:8443/eaglesign/informer/rpc/protected/` | GWT RPC v7 |

### ERP CGI Endpoints

```
/cgi-bin/mvi.exe/LOGIN.START          # Login page
/cgi-bin/mvi.exe/DASHBOARD            # Main dashboard
/cgi-bin/mvi.exe/INFORMER             # Informer menu item
/cgi-bin/mvi.exe/BI.REPORTS           # BI Reports menu
/cgi-bin/mvi.exe/MENU.REPORTS         # Reports menu
/REPORT.IFRAME?REPORT_ID={id}&START_LINE=1&END_LINE=999999  # Report viewer
```

### Informer GWT RPC Endpoints

| Service | Path | Policy Key |
|---------|------|------------|
| AuthenticationRPCService | `/rpc/AuthenticationRPCService` | `51B059033C002274BD4151F7D17FC702` |
| ReportRPCService | `/rpc/protected/ReportRPCService` | `F94C0FA52A7B058D7077BFA6B82FF792` |
| ViewRPCService | `/rpc/protected/ViewRPCService` | `327E0F303D0CA463050DC31340CFE01D` |
| commandService | `/commandService` | `81D82B6C6154989542DE45F20CEB3EF0` |
| DocumentTemplateRPCService | `/rpc/protected/DocumentTemplateRPCService` | `05E06838523AECED1434383744A449D0` |

### GWT Protocol Details

```
Module Base:    https://eaglesign.keyedinsign.com:8443/eaglesign/informer/
Permutation:    6823F3E0DFFF554BC1A7951AA98B182D
Protocol:       GWT RPC v7
Response:       //OK[<data>, ["string_table"], <offset>, <version>]
Page Size:      25 rows per request
Serialization:  Right-to-left HashMap<String, Value> reading
```

### Informer Version

```
Informer:  v4.7.0 Build 470031
Plugin:    v2 build 082914
Server:    Jetty 8.1.8
```

### Credentials & Auth

| Variable | Location | Purpose |
|----------|----------|---------|
| KEYEDIN_USERNAME | `C:\Scripts\keyedin-capture\.env` | ERP login |
| KEYEDIN_PASSWORD | `C:\Scripts\keyedin-capture\.env` | ERP login |
| JSESSIONID | Cookie (auto-obtained via SSO) | Informer session |
| authToken | Response header (auto-extracted) | GWT RPC auth |
| clientId | Response body (auto-extracted) | GWT RPC client ID |

---

## 3. Access & Permissions

### Brady's ERP Access

- **Role:** Operational user (NOT admin)
- **Modules accessible:** 19 of 19 main modules
- **Processes accessible:** 240+ processes
- **Admin functions:** NONE (Administration menu locked)
- **License type:** Concurrent user (quota-limited)

### Brady's Informer Access

- **Role:** Consumer (NOT Designer)
- **Can access:** Data tab (raw grid view)
- **CANNOT access:** Report Template tab ("Not Authorized")
- **Reports visible:** 30
- **Reports on page 1:** 26 (page 2 has remaining 4)

### Access Gaps

| What | Status | Impact |
|------|--------|--------|
| UniVerse ODBC/JDBC | **NO ACCESS** | Cannot query database directly |
| Informer Designer role | **NO ACCESS** | Cannot create custom reports |
| Informer REST API | **UNKNOWN** | API keys not tested |
| ERP Admin panel | **NO ACCESS** | Cannot manage sessions/users |
| Data dictionary/schema | **NOT PROVIDED** | Reverse-engineering field names |

---

## 4. Informer Reports (30 total)

### Complete Catalog

| ID | Report Name | Category | Params | Behavior |
|----|-------------|----------|--------|----------|
| 1441842 | AR Invoice Details | Accounts Receivable | Date range | Required params |
| 1441843 | AR Invoice Listing | Accounts Receivable | Date range, Customer | Required params |
| 1441844 | AR Open Invoices | Accounts Receivable | None | Auto-run |
| 1441849 | Cash Receipts | Accounts Receivable | None | Standard launch |
| 1441850 | Customer Listing | Accounts Receivable | None | Standard launch |
| 1441851 | Customer Listing Export | Export | None | Export-only |
| 1441852 | Customer Location Listing | Accounts Receivable | None | Standard launch |
| 1441853 | Customer Location Listing Export | Export | None | Export-only |
| 1441854 | Inventory List | Inventory and Parts | None | Standard launch |
| 1441855 | Inventory List Export | Export | None | Export-only |
| 1441856 | Inventory Transaction History | Inventory and Parts | Date range | Required params |
| 1441857 | Invoice Register | Invoicing | None | Standard launch |
| 1441859 | Open Sales Order Backlog | Sales Orders | None | Standard launch |
| 1441860 | Open Sales Orders | Sales Orders | None | Auto-run |
| 1441861 | Open Work Orders | Production | None | Auto-run |
| 1441862 | Planned Part Activity | Inventory and Parts | None | Standard launch |
| 1441865 | Purchase History | Purchasing | Date range | Required params |
| 1441866 | Purchase Order Detail | Purchasing | Date range | Required params |
| 1441868 | Purchased Part Variance | Accounts Payable | Date range | Required params |
| 1441869 | Quote Status Report | Estimating | None | Standard launch |
| 1441870 | Sales Cost Detail Report | Sales Analysis | Date range | Required params |
| 1441872 | Sales Order Bookings By Line Date | Sales Orders | None | Standard launch |
| 1441873 | Sales Order Bookings By SO Date | Sales Orders | None | Standard launch |
| 1441874 | Sales Order Detail | Sales Orders | Date range | Required params |
| 1441875 | Sales Order Status by Customer | Sales Orders | Date range | Required params |
| 1441877 | Sales Summary by Customer | Sales Analysis | None | Standard launch |
| 1441878 | Sales Summary by Product Type | Sales Analysis | None | Standard launch |
| 1441883 | Vendor Listing | Accounts Payable | None | Standard launch |
| 1441884 | Vendor Listing Export | Export | None | Export-only |
| 1441887 | Work Order Listing | Production | None | Standard launch |

### Report Categories

- **Standard Launch (13):** No parameters, click Launch or Data tab to view
- **Required Parameters (10):** Need date range before execution
- **Auto-Run (3):** Execute immediately on navigation
- **Export-Only (4):** No Launch link, use Export flow

### Known Field Names (Customer Listing — Report 1441850)

```
custNo, name, address, address_2, city, state, zip, phone,
contact, taxCode, desc, linkToSalesperson_assoc_name,
customer, linkToPymtTerms_assoc_desc
```

---

## 5. ERP Processes (240+ discovered)

### Confirmed Working Extraction

| Process | Method | Output | Status |
|---------|--------|--------|--------|
| SO.CONTRACT (Cost Summary Detail) | CDP + CGI POST | HTML spool → CSV | **COMPLETE** (168 batches, 33,428 WOs) |
| EXPORT.WIP.SUMMARY | CGI form submit | CSV download | **CONFIRMED** (WIP_CLOSED_FINANCIALLY.csv exists) |

### High-Value Targets (Not Yet Automated)

| Process | Expected Output | Priority |
|---------|----------------|----------|
| EXPORT.WO.LABOR.ANALYSIS | CSV (labor analysis by date + sign type) | HIGH |
| LIST.AP.DET | AP detail listing | MEDIUM |
| EMP.HOURS.BY.DATE | Employee hours report | MEDIUM |
| EMP.EFF | Employee efficiency | MEDIUM |
| SUM.DEPT.EFF | Department efficiency summary | MEDIUM |

### ERP Module Map (19 modules, 240 processes)

Full mapping documented in: `C:\Scripts\keyedin-capture\ERP_ADMIN_MAPPING.md` (32 KB)

---

## 6. Warehouse Database Schema

### Database: `eagle_warehouse.db` (211 MB SQLite)

**Location:** `C:\Scripts\signx-warehouse\warehouse\production\`
**Built:** 2026-01-30T11:10:07
**Total rows:** 1,376,130

### Tables (17 + metadata)

#### Core Data Tables

| Table | Rows | PK | Key Columns |
|-------|------|----|-------------|
| **work_orders** | 33,428 | wo_number | customer_id, customer_name, location, status, date_completed, sign_type, sales_code, estimator, quote_nbr, total_labor_cost, total_burden_cost, total_material_cost, total_outplant_cost, total_use_tax, total_cost, quoted_price, sale_price, gross_margin, gm_pct |
| **labor_detail** | 254,012 | id (auto) | wo_number, labor_date, work_dept, work_code, employee_name, actual_hrs, job_cost |
| **labor_summary** | 161,377 | id (auto) | wo_number, work_dept, work_code, est_hrs, actual_hrs, hrs_variance, est_cost, job_cost, cost_variance, description |
| **material_transactions** | 780,868 | id (auto) | wo_number, material_date, work_dept, inventory_item, uom, est_qty, actual_qty, qty_variance, est_cost, job_cost, cost_variance |
| **outplant_transactions** | 23,352 | id (auto) | wo_number, outplant_date, work_dept, sub_contractor, uom, est_qty, actual_qty, qty_variance, est_cost, job_cost, cost_variance |
| **invoices** | 26,643 | id (auto) | invoice_number, invoice_date, product_code, customer_id, customer_name, gross_sales, total_cost, gross_margin, gm_pct, salesperson, wo_number |
| **customers** | 3,748 | customer_id | customer_name, customer_type, invoice_lines, gross_sales, total_cost, gross_margin, gm_pct |
| **sales_orders** | 27,707 | id (auto) | customer_name, po_number, so_number, order_date, ship_date, invoices, order_status |
| **purchase_orders** | 5,974 | id (auto) | po_number, po_line, po_date, vendor_id, vendor_name, buyer, order_status, wo_number, part_number, order_qty, received_qty, unit_price |
| **inventory** | 1,062 | part_number | description, inventory_type, sales_code, qty_on_hand, uom, unit_price, acctg_cost |
| **employees** | 95 | employee_name | first_seen, last_seen, total_hours, primary_dept, departments, is_active |

#### Reference Tables

| Table | Rows | Purpose |
|-------|------|---------|
| **ref_work_codes** | 62 | Work code → description + department |
| **ref_sign_types** | 38 | Sign type code → description |

#### Analytics Tables

| Table | Rows | Purpose |
|-------|------|---------|
| **shop_efficiency** | 44 | Efficiency score per work code (est vs actual) |
| **labor_multipliers** | 42 | Labor time stats (avg, min, max, std_dev per code) |
| **gm_by_salesperson** | 4,298 | Gross margin detail by salesperson |
| **labor_forensics** | 53,380 | Deep labor analysis (Cat Scale project) |

#### Indexes (19)

```sql
idx_labor_detail_wo, idx_labor_detail_emp, idx_labor_detail_dept, idx_labor_detail_date
idx_labor_summary_wo, idx_material_wo, idx_outplant_wo
idx_invoices_cust, idx_invoices_date, idx_wo_customer, idx_wo_sign_type
idx_wo_estimator, idx_wo_date, idx_po_vendor, idx_sales_orders_so
idx_forensics_wo, idx_forensics_emp, idx_gm_sp_cust
```

---

## 7. Data Pipeline Scripts

### Repository: `C:\Scripts\signx-warehouse\scripts\`

| Script | Lines | Phase | Purpose |
|--------|-------|-------|---------|
| **parse_full_cost_detail.py** | 907 | 1 | Parse 168 HTML batch files → 5 CSVs (wo_headers, labor_detail, labor_summary, material_detail, outplant_detail) |
| **scrape_informer.py** | 1,664 | 2 | HTTP extraction via GWT RPC replay — 30 reports |
| **capture_all_reports.py** | ~1,100 | 2 | Playwright browser automation — capture GWT RPC payloads |
| **ingest_local_files.py** | 650 | 4 | Scan H:\ and OneDrive for Excel/CSV → local_*.csv |
| **build_warehouse.py** | 1,000+ | 5 | Merge all CSVs into SQLite with trust-based upsert |
| **decision_engine.py** | 800 | 6 | 8 analytical modules (estimating accuracy, profitability, capacity) |
| **gwt_parser.py** | 1,100 | Lib | GWT RPC v7 response parser (extract_rows, discover_field_names) |
| **gwt_deserialize.py** | 650 | Lib | Right-to-left GWT deserialization |
| **gwt_analyze.py** | 400 | Debug | GWT Row serialization diagnostics |
| **gwt_dump_rows.py** | 300 | Debug | Raw data dump around Row positions |
| **_get_session.py** | 280 | Util | Playwright SSO → fresh Informer session |
| **tracer_bullet.py** | 550 | POC | Proof-of-concept CDP login → Informer export |
| **test_pipeline_fixes.py** | 270 | Test | Pytest suite for extraction pipeline |

### Repository: `C:\Scripts\keyedin-capture\`

| Script | Lines | Purpose |
|--------|-------|---------|
| **fast_extract.py** | 696 | Chrome CDP batch extraction (SO.CONTRACT → HTML) |
| **cost_summary_automation.py** | ~500 | Playwright version of batch extraction |
| **parse_reports.py** | 728 | Parse HTML Cost Summary → labor CSV |
| **extract_wo_batches.py** | ~100 | Split WO numbers into 168 batch files |
| **setup_credentials.py** | ~100 | Store ERP credentials |

---

## 8. GWT Parser Technical Details

### Public API

| Function | Input | Output |
|----------|-------|--------|
| `parse_gwt_response(text)` | Raw `//OK[...]` response | `dict` with data, strings, offset, version |
| `extract_rows(response_text, field_names)` | Response + field list | `list[dict]` — one dict per row |
| `discover_field_names(response_text)` | Response text | `list[str]` — auto-discovered column names |
| `extract_view_token(response_text)` | Response text | `str` — UUID for pagination |
| `extract_total_count(response_text)` | Response text | `int` — total rows available |

### Row Extraction Algorithm

1. Parse `//OK[data, ["strings"], offset, version]`
2. Build type reference map from string table
3. Find Row/HashMap markers in string table
4. **Pass 1:** Process rightmost full Row to discover field order (HashMap keys are new String objects or backreferences)
5. **Pass 2:** Apply field order positionally to ALL rows
6. Each row is a `HashMap<String, Value>` where Value = StringValue | NumberValue | NullValue | ArrayValue

### 3-Tier Field Discovery Fallback

```
Tier 1: REPORT_FIELDS.get(report_id)     → Hardcoded (highest confidence)
Tier 2: field_names_manifest.json         → Saved by capture script
Tier 3: gwt_discover_field_names(resp)    → Auto-discovery from response
```

---

## 9. HTML Cost Detail Parser

### Input

- **168 HTML batch files** in `C:\Scripts\keyedin-capture\reports\cost_detail\`
- Each file contains ~200 work orders in `<pre>` formatted text
- Fixed-width columns with `<span>` tags around numeric values

### Section Detection

```
LABOR section:    "LABOR   WORK  WORK" in line
MATERIAL section: "MATERIAL  WORK  INVENTORY" in line
OUTPLANT section: "OUTPLANT  WORK" in line
```

### Output (5 CSV types)

| File | Content | Key Fields |
|------|---------|------------|
| wo_headers.csv | 1 row per WO | wo_number, customer, costs, margins, estimator |
| labor_detail.csv | 1 row per time entry | wo_number, date, employee, dept, code, hours, cost |
| labor_summary.csv | 1 row per WO/dept/code rollup | est vs actual hours and costs |
| material_detail.csv | 1 row per material issuance | wo_number, date, item, qty, cost |
| outplant_detail.csv | 1 row per subcontractor line | wo_number, date, vendor, qty, cost |

### Material Dedup Fix (applied 2026-02-02)

- `****` summary lines were being mixed with detail lines, causing 2x row count
- Fix: Skip lines starting with `****` in material and outplant sections
- Expected result: material_transactions drops from ~780K to ~390K rows

---

## 10. ERP Extraction Protocol (fast_extract.py)

### 5-Step CDP Protocol

```
1. APPLOAD    → Navigate to SO.CONTRACT page
2. POST       → Submit form with WO batch (sono_pipe = WO1|WO2|...|WO200)
3. VIEW.LOG   → Poll progress log until "ENDED" (3s intervals, max 360s)
4. .RUN       → Extract REPORT_ID from log
5. Download   → GET REPORT.IFRAME?REPORT_ID={id}&START_LINE=1&END_LINE=999999
```

### Two Output Patterns

| Pattern | Method | Used By |
|---------|--------|---------|
| Pattern A | HTML spool via REPORT.IFRAME | SO.CONTRACT (Cost Summary) |
| Pattern B | CSV via "View File" link download | EXPORT.WO.LABOR.ANALYSIS, EXPORT.WIP.SUMMARY |

---

## 11. Decision Engine (8 Modules)

| Module | Purpose | Key Metrics |
|--------|---------|-------------|
| Estimating Accuracy | Compare quoted vs actual costs | Variance %, top over/under |
| Profitability Analysis | GM by customer, sign type, estimator | GM%, revenue concentration |
| Capacity Planning | Labor utilization by dept/code | Hours capacity, bottlenecks |
| Shop Efficiency | Est vs actual hours by work code | Efficiency score, variance |
| Material Analysis | Material cost patterns and waste | Cost per WO, waste % |
| Customer Analytics | Customer value and retention | LTV, order frequency |
| Vendor Performance | Supplier delivery and pricing | On-time %, price trends |
| Cash Flow Indicators | AR aging and payment patterns | DSO, aging buckets |

---

## 12. Known Issues & Bugs

| Issue | Status | Details |
|-------|--------|---------|
| License quota exceeded | **ACTIVE** | Too many concurrent ERP sessions from Playwright runs |
| Informer "Not Authorized" on Report Template tab | **KNOWN** | Consumer role lacks template access. Use Data tab instead. |
| GWT PushButton clicks don't trigger events | **WORKAROUND** | Playwright mouse events don't fire GWT internal handlers. Use `launch=true` URL or Data tab click. |
| Material transaction 2x duplication | **FIXED** | Was counting both detail + summary lines. Fix: skip `****` lines. |
| `launch=true` triggers "Access Denied" | **KNOWN** | Opens Report Template tab which Consumer role can't access. Switch to Data tab approach. |
| SSO link not always found after ERP login | **INTERMITTENT** | Fallback to `/eaglesign/sso` without token lands on login page. |
| Export CSV URL unknown | **OPEN** | 6 URL patterns tested, all 404. Export servlet path not discovered. |

---

## 13. File Inventory

### signx-warehouse (735 MB total)

```
scripts/                          13 Python scripts (596 KB)
warehouse/raw/                    10 timestamped ingestion runs + recon data
warehouse/production/             eagle_warehouse.db (211 MB) + manifest
warehouse/reports/                Decision engine output (23 KB)
.omc/                            PRD + progress tracking
```

### keyedin-capture (556 MB total)

```
(root)                            11 Python scripts + 5 Markdown docs
reports/cost_detail/              168 HTML batch files (402 MB)
reports/wo_batches/               168 TXT batch files
reports/                          Analysis scripts + outputs (Excel, JSON, CSV)
raw/                              48 captured GWT RPC files (306 KB)
screenshots/                     15 UI screenshots (1.3 MB)
```

---

## 14. What We Have vs What We Need

### Data Currently in Warehouse (1.38M rows)

| Data | Rows | Source | Completeness |
|------|------|--------|-------------|
| Work order costs & margins | 33,428 | HTML parse (tier 3) | HIGH — all historical WOs |
| Labor transactions | 254,012 | HTML parse (tier 3) | HIGH — full detail |
| Labor est vs actual | 161,377 | HTML parse (tier 3) | HIGH — summary rollup |
| Material transactions | 780,868 | HTML parse (tier 3) | MEDIUM — contains dupes (fix pending) |
| Outplant transactions | 23,352 | HTML parse (tier 3) | HIGH |
| Invoices | 26,643 | Local Excel (tier 4) | MEDIUM — may be subset |
| Customers | 3,748 | Local Excel (tier 4) | LOW — summary only |
| Sales orders | 27,707 | Local Excel (tier 4) | MEDIUM |
| Purchase orders | 5,974 | Local Excel (tier 4) | LOW — may be subset |
| Inventory | 1,062 | Local Excel (tier 4) | MEDIUM — snapshot only |
| Employees | 95 | Derived from labor | HIGH — 18 active |

### Data NOT in Warehouse (gaps)

| Data | Where It Lives | How to Get It |
|------|---------------|---------------|
| Full customer master (all fields) | UniVerse CUSTOMER table | ODBC or Informer Customer Listing |
| Vendor master | UniVerse VENDOR table | ODBC or Informer Vendor Listing |
| Quote details | UniVerse QUOTE table | ODBC or Informer Quote Status Report |
| AR open invoices (current) | UniVerse AR table | ODBC or Informer AR Open Invoices |
| Inventory transactions (history) | UniVerse INV.TRANS table | ODBC or Informer Inv Transaction History |
| Purchase history | UniVerse PO table | ODBC or Informer Purchase History |
| Sales cost detail | UniVerse SALES table | ODBC or Informer Sales Cost Detail |
| Employee hours (non-WO) | UniVerse EMPLOYEE table | ERP process EMP.HOURS.BY.DATE |
| Department efficiency | UniVerse derived | ERP process SUM.DEPT.EFF |
| AP detail | UniVerse AP table | ERP process LIST.AP.DET |
| Full GL data | UniVerse GL table | NOT ACCESSIBLE |
| Payroll data | UniVerse PAYROLL table | NOT ACCESSIBLE |
| System config / audit logs | UniVerse SYSTEM tables | Admin access required |

### The Single Highest-Leverage Action

**Get ODBC read-only access to the UniVerse database.**

This eliminates:
- All browser automation (Playwright, CDP)
- All GWT RPC reverse-engineering
- All HTML scraping and parsing
- All field name discovery
- All pagination handling
- All session management

Replace with: `SELECT * FROM {table}` via pyodbc.

---

## 15. Strategic Asks for KeyedIn Meeting

### Priority 1: Database Access

> "We need an ODBC connection string to our UniVerse database. Read-only is fine."

### Priority 2: Data Dictionary

> "We need a complete list of all tables and fields in our instance."

### Priority 3: Session Management

> "We're hitting license quota errors. How do we manage active sessions?"

### Priority 4 (fallback): Informer Designer

> "If ODBC isn't available, upgrade our Informer role to Designer so we can build custom reports."

### Justification

- IRS record retention (IRC Section 6001) — 7 year minimum
- Iowa Department of Revenue — books and records inspection
- Business continuity — independent data copy required
- Internal analytics — 30 pre-built reports insufficient
- **It's our data.**
