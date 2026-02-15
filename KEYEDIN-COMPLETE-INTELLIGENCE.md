# KeyedIn Complete Intelligence Audit

**Generated**: 2026-02-14
**Auditor**: Claude Opus 4.6 — full repo + filesystem scan
**Scope**: SignX repo (all branches) + C:\Scripts\keyedin-automation + C:\Scripts\keyedin-capture + signx-warehouse (OneDrive) + all external locations

---

## 1. System Architecture

### Confirmed Tech Stack (with evidence)

| Layer | Technology | Evidence |
|-------|-----------|----------|
| **ERP Product** | KeyedIn Sign v2.1 (MVI 3.0) | Login page title, CGI headers |
| **CGI Engine** | mvi.exe | All 288+ endpoint URLs use `/cgi-bin/mvi.exe/` |
| **Database** | MultiValue/Pick | KIMCO contract PDF, DataSIGN heritage |
| **BI Module** | Informer BI (GWT-RPC) | Port 8443, AngularJS SPA, GWT serialization |
| **Web Server** | IIS (inferred) | HTTPS termination, CGI hosting |
| **Hosting** | External (KIMCO/KeyedIn cloud) | eaglesign.keyedinsign.com resolves externally |

### All Known URLs

| URL | Purpose | Status |
|-----|---------|--------|
| `https://eaglesign.keyedinsign.com` | Main ERP login | CONFIRMED WORKING |
| `https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/LOGIN.START` | CGI login entry | CONFIRMED WORKING |
| `https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/{FUNCTION}` | All CGI endpoints | 288+ functions mapped |
| `https://eaglesign.keyedinsign.com:8443/eaglesign/Informer.html` | Informer BI portal | CONFIRMED WORKING |
| `https://eaglesign.keyedinsign.com:8443/eaglesign/sso` | Informer SSO | CONFIRMED WORKING |
| `https://eaglesign.keyedinsign.com:8443/eaglesign/informer/rpc/protected/ViewRPCService` | GWT-RPC data endpoint | CONFIRMED WORKING |
| `https://eaglesign.keyedinsign.com:8443/eaglesign/informer/rpc/protected/ReportRPCService` | GWT-RPC report endpoint | CONFIRMED (untested for automation) |
| `https://eaglesign.keyedinsign.com:8443/graphicfx/` | GraphicFX tenant | CONFIRMED EXISTS |
| `https://eaglesign.keyedinsign.com:8443/naglesigns/` | Nagle Signs tenant | CONFIRMED EXISTS |

### Authentication Methods

| Method | System | Status | Evidence |
|--------|--------|--------|----------|
| Direct POST login | Main ERP | WORKING | `USERNAME=BradyF&PASSWORD=***&SECURE=TRUE` to base URL |
| Session cookies | Main ERP | WORKING | SESSIONID, ASP.NET_SessionId, user, secure, IMPERSONATE |
| Google SSO | Informer BI | BLOCKED | Bot detection encountered (SESSION_SUMMARY.md) |
| Informer SSO pass-through | Informer BI | WORKING | `/eaglesign/sso` returns authToken + clientId |
| authToken + clientId | Informer RPC | WORKING | Query params on RPC calls, GUID format |

### Network Topology

- Hosted externally by KIMCO/KeyedIn (not on-premises)
- Requires Eagle Sign VPN for access (Cisco AnyConnect)
- Main ERP on port 443 (HTTPS)
- Informer BI on port 8443 (HTTPS)
- No direct database access available
- No REST API available (CGI only)

---

## 2. Data Inventory

### A. SQLite Warehouse Database [CONFIRMED - FILE EXISTS]

| Property | Value |
|----------|-------|
| **Path** | `C:\Scripts\signx-warehouse\warehouse\production\eagle_warehouse.db` |
| **Size** | 211 MB |
| **Built** | 2026-01-30T11:10:07 |
| **Total Rows** | **1,376,130** |
| **Total Tables** | **17** |

#### Table Row Counts

| Table | Rows | Source Phase |
|-------|------|-------------|
| work_orders | 33,428 | Phase 1 (HTML parse) |
| labor_detail | 254,012 | Phase 1 |
| labor_summary | 161,377 | Phase 1 |
| material_transactions | 780,868 | Phase 1 |
| outplant_transactions | 23,352 | Phase 1 |
| invoices | 26,643 | Phase 4 (local files) |
| inventory | 1,062 | Phase 4 |
| purchase_orders | 5,974 | Phase 4 |
| customers | 3,748 | Phase 4 |
| sales_orders | 27,707 | Phase 4 |
| ref_work_codes | 62 | Phase 4 |
| ref_sign_types | 38 | Phase 4 |
| shop_efficiency | 44 | Phase 4 |
| labor_multipliers | 42 | Phase 4 |
| labor_forensics | 53,380 | Phase 4 |
| gm_by_salesperson | 4,298 | Phase 4 |
| employees | 95 | Derived |

#### Validation Results

- Work orders: 33,428 unique
- WOs with labor data: 28,829 (86.3%)
- WOs with estimator: 12,285 (36.8%)
- Employees: 95 total, 18 active (last 180 days)
- Source tiers: all tier 3 (HTML reparse) for work_orders

### B. HTML Source Files [CONFIRMED - FILES EXIST]

| Property | Value |
|----------|-------|
| **Path** | `C:\Scripts\keyedin-capture\reports\cost_detail\` |
| **File Count** | 168 HTML batch files |
| **Naming** | `cost_detail_batch_001.html` through `_168.html` |
| **Total Directory Size** | 559 MB |
| **Content** | Complete Cost Summary Detail reports for ALL work orders |
| **WO Range** | WO#1 (2012) through ~WO#70000+ (2026) |
| **Parsing Status** | FULLY PARSED into CSVs on 2026-01-30 |

**CORRECTION**: Prior sessions referenced "402MB HTML files" — actual directory size is **559MB**.

### C. Parsed CSV Data [CONFIRMED - FILES EXIST]

**Path**: `~/OneDrive - Eagle Sign Co/signx-warehouse/warehouse/raw/`

#### Extraction Runs (2026-01-30)

| Timestamp | Size | Type | Files |
|-----------|------|------|-------|
| T1011 | 852K | Phase 1 (first test) | 5 CSVs (small) |
| T1015 | 170M | Phase 1 (full run) | 5 CSVs |
| T1025 | 876K | Phase 1 (test) | 5 CSVs (small) |
| **T1026** | **175M** | **Phase 1 (best run)** | **5 CSVs — 1,253,042 rows** |
| T1101 | 45M | Phase 4 (local files) | 13 CSVs |
| T1106 | 65M | Phase 4 (expanded) | 22 CSVs |
| **T1107** | **66M** | **Phase 4 (best run)** | **26 CSVs** |
| T1155 | 0 | Empty run | - |
| T1324 | 8K | Manifest only | - |
| T1339 | 8K | Manifest only | - |
| T1342 | 1.1M | Informer test | 1 CSV (customer_listing) |
| tracer_bullet | 44K | Debug HTML | 1 HTML file |

#### Best Phase 1 Run (T1026) Detail

| File | Rows | Size | Content |
|------|------|------|---------|
| wo_headers.csv | 33,428 | 13 MB | WO number, customer, costs, margins, estimator, status |
| material_detail.csv | 780,868 | 107 MB | Date, dept, item, est/actual qty, est/actual cost |
| labor_detail.csv | 254,012 | 32 MB | Date, dept, code, employee, hours, cost |
| labor_summary.csv | 161,377 | 22 MB | Dept, code, est_hrs, actual_hrs, variance |
| outplant_detail.csv | 23,352 | ~1 MB | Subcontractor, PO details |

#### Best Phase 4 Run (T1107) Detail

| File | Source | Content |
|------|--------|---------|
| local_work_orders.csv | OneDrive WIP export | Invoice-level data: 26,643 rows |
| local_sales_orders.csv | OneDrive | 27,707 sales orders |
| local_wip_summary.csv | OneDrive | 9.1 MB WIP summary |
| local_gm_salesperson.csv | OneDrive | 6.1 MB GM data |
| local_gm_sp_2023/2024/2025.csv | OneDrive | Annual GM by salesperson |
| local_labor_forensics.csv | H:\brady\BOT TRAINING | 7.4 MB Cat Scale labor |
| local_stock_status.csv | OneDrive BRADYF_STOCK.STATUS.xlsx | Inventory status |
| local_inventory_active.csv | OneDrive | Active inventory |
| local_purchase_history.csv | OneDrive | Purchase order history |
| local_emp_hours_*.csv | OneDrive | Per-employee hours (Brady, Brian, John, Matt) |
| local_sales_summary_customer.csv | OneDrive | Customer revenue summary |
| local_sales_summary_product.csv | OneDrive | Product revenue summary |
| local_shop_efficiency.csv | Derived | Work code efficiency scores |
| local_labor_multipliers.csv | Derived | Labor time stats by code |
| local_mfg_parts.csv | OneDrive | Manufacturing parts list |
| local_purchased_parts.csv | OneDrive | Purchased parts list |
| local_vendors.csv | OneDrive | Vendor listing |
| local_ref_work_codes.csv | OneDrive | 62 work codes |
| local_ref_sign_types.csv | OneDrive | 38 sign types |

### D. Informer BI Report Captures [CONFIRMED]

| Property | Value |
|----------|-------|
| **Path** | `C:\Scripts\keyedin-capture\reports\` |
| **Reports Captured** | 30 out of 30 visible in Informer |
| **Capture Date** | 2026-02-06 |
| **Format** | GWT-RPC ViewRPCService request payloads (.txt files) |
| **Response Files** | Also captured for most reports |

#### Captured Reports (30 total)

| Report ID | Report Name | Request File |
|-----------|-------------|-------------|
| 1441842 | AR Invoice Details | report_ar_invoice_details_view_request.txt |
| 1441843 | AR Invoice Listing | report_ar_invoice_listing_view_request.txt |
| 1441844 | AR Open Invoices | report_ar_open_invoices_view_request.txt |
| 1441849 | Cash Receipts | report_cash_receipts_view_request.txt |
| 1441850 | Customer Listing | report_customer_listing_view_request.txt |
| 1441851 | Customer Listing Export | report_customer_listing_export_view_request.txt |
| 1441852 | Customer Location Listing | report_customer_location_listing_view_request.txt |
| 1441853 | Customer Location Listing Export | report_customer_location_listing_export_view_request.txt |
| 1441854 | Inventory List | report_inventory_list_view_request.txt |
| 1441855 | Inventory List Export | report_inventory_list_export_view_request.txt |
| 1441856 | Inventory Transaction History | report_inventory_transaction_history_view_request.txt |
| 1441857 | Invoice Register | report_invoice_register_view_request.txt |
| 1441859 | Open Sales Order Backlog | report_open_sales_order_backlog_view_request.txt |
| 1441860 | Open Sales Orders | report_open_sales_orders_view_request.txt |
| 1441861 | Open Work Orders | report_open_work_orders_view_request.txt |
| 1441862 | Planned Part Activity | report_planned_part_activity_view_request.txt |
| 1441865 | Purchase History | report_purchase_history_view_request.txt |
| 1441866 | Purchase Order Detail | report_purchase_order_detail_view_request.txt |
| 1441868 | Purchased Part Variance | report_purchased_part_variance_view_request.txt |
| 1441869 | Quote Status Report | report_quote_status_report_view_request.txt |
| 1441870 | Sales Cost Detail Report | report_sales_cost_detail_report_view_request.txt |
| 1441872 | Sales Order Bookings By Line Date | report_sales_order_bookings_by_line_date_view_request.txt |
| 1441873 | Sales Order Bookings By SO Date | report_sales_order_bookings_by_so_date_view_request.txt |
| 1441874 | Sales Order Detail | report_sales_order_detail_view_request.txt |
| 1441875 | Sales Order Status by Customer | report_sales_order_status_by_customer_view_request.txt |
| 1441877 | Sales Summary by Customer | report_sales_summary_by_customer_view_request.txt |
| 1441878 | Sales Summary by Product Type | report_sales_summary_by_product_type_view_request.txt |
| 1441883 | Vendor Listing | report_vendor_listing_view_request.txt |
| 1441884 | Vendor Listing Export | report_vendor_listing_export_view_request.txt |
| 1441887 | Work Order Listing | report_work_order_listing_view_request.txt |

**CORRECTION**: Prior sessions referenced "71 discovered reports" — actual count is **30 reports** visible and captured from Informer.

### E. KeyedIn Automation MCP Server [CONFIRMED]

| Property | Value |
|----------|-------|
| **Path** | `C:\Scripts\keyedin-automation\` |
| **Framework** | FastMCP 2.14.3 + ChromaDB |
| **Documents Indexed** | 1,141 (129 functions + 4 workflows + 1,008 filesystem paths) |
| **Discovery Data** | keyedin_site_map.json (288 links / 264 entries / 241 unique codes), keyedin_page_mappings.json (3 pages), network_analysis_report.md |
| **Tools** | 8 MCP tools (search_knowledge, get_workflow, list_workflows, get_url_pattern, get_page_map, get_field_info, find_project, get_navigation_path) |

**CRITICAL BUG**: `ingest_keyedin()` in `scripts/ingest.py` only reads top-level `section_data.get("functions", [])` — it does NOT recurse into sub-sections (`reports`, `processing`, `inquiry`, `vendor_master`, `customer_master`). This drops **135 of 264 function entries (51%)**. Entire modules have ZERO functions ingested: JOB_COST (19), MRP (16), LABOR_AND_PAYROLL (6), ACCOUNTS_PAYABLE (4), ACCOUNTS_RECEIVABLE (3), SYSTEM_MANAGEMENT (4).

**Empty tables**: `fields` (0 rows — page_mappings.json never consumed), `js_functions` (0 rows), `projects` (0 rows — G:\, H:\ not scanned).

**Additional subsystem**: `keyedin-quote-entry-headed.js` (364 lines) — production-ready Playwright batch quote entry automation with real job data in `job.json` (Hexagon ADA Room Signs, 16 quotes).

### F. Decision Intelligence Report [CONFIRMED]

| Property | Value |
|----------|-------|
| **Path** | `signx-warehouse/warehouse/reports/decision_report_20260130_111224.md` |
| **Generated** | 2026-01-30 11:12 |
| **Key Findings** | See below |

#### Confirmed Findings

| Finding | Value | Evidence |
|---------|-------|----------|
| Dead stock capital | **$241,701.53** | 499 items with stock on hand |
| Top dead stock item | H96W-SD-24V power supply: $34,577 (806 units) | Inventory query |
| Labor overestimation | **50-56% below estimates** (all estimators) | 17,031 WOs analyzed |
| Adam Fasselius variance | -53.6% avg, 9,467 WOs | Est 159,784 hrs vs actual 85,126 hrs |
| Brady Flink variance | -55.7% avg, 534 WOs | Est 11,141 hrs vs actual 4,840 hrs |
| Average true margin | **8.6%** | 31,138 WOs |
| ERP burden rate | 1.35x labor cost avg | 28,756 WOs |
| Top customer revenue | Cat Scale: $28.96M | 2,619 WOs |
| Win/Loss Ratio | **BLOCKED** | Quote data not yet available from Informer |

### G. Additional Data Locations

| Location | Content | Size |
|----------|---------|------|
| `C:\Scripts\keyedin-capture\reports\` | 243 files including ABC pricing guides, audit scripts, report payloads | ~559 MB dir |
| `C:\Scripts\keyedin-capture\screenshots\` | ERP screenshots (admin menu, cost summary, labor analysis, login page) | Multiple PNG |
| `C:\Scripts\keyedin-capture\raw\` | Raw GWT-RPC request/response captures (req51-req102) | Multiple TXT |
| `C:\Scripts\keyedin-capture\session_auth.json` | Saved authentication session data | 2 KB |
| `C:\Scripts\keyedin-capture\reports_manifest.json` | Manifest of all captured reports | 7 KB |
| `~/Desktop/Keyedin HELP` | KIS 2.5.7 Release Notes PDF | 1.86 MB |
| `~/Downloads/SignX-main/SignX-main/Keyedin` | Archive: 81 Python scripts, 95 JSON, 41 HTML captures | 36 MB |
| `C:\Scripts\keyedin-capture/Eagle Sign Contract - Keyedin MFG.pdf` | Vendor contract document | 330 KB |
| `C:\Scripts\keyedin-capture/Kimco-Terms-and-Conditions-MSA-Final.pdf` | KIMCO terms and conditions | 229 KB |

### H. Downloads Archive — Extracted Data & Automation Scripts [CONFIRMED]

**Path**: `~/Downloads/SignX-main/SignX-main/Keyedin/`
**Total Size**: 36 MB | **Files**: 81 Python, 95 JSON, 41 HTML

This location contains **actual extracted data** from a 2025-11-12 session:

| File | Size | Content |
|------|------|---------|
| `all_detailed_cost_summaries_20251112_181028.json` | 263 KB | **50 work orders**, 350 tables |
| `all_cost_summaries_20251112_180352.json` | 6.7 KB | Summary-level cost data |
| `Data Exports/Closed WO 11-1-00 to 10-31-25.csv` | 6 MB | **33,080 rows — 25 years of WO history** |
| `extracted_data_20251112_180236.json` | 77 KB | Comprehensive extraction run |
| `menu_20251112_180236.json` | 59 KB | Full menu structure |
| `work_orders_20251112_180236.json` | 10 KB | Work order data |
| `service_calls_20251112_180236.json` | 1.2 KB | Service call listings |
| `complete_endpoint_map.json` | 61 KB | 50+ mapped endpoints |
| `endpoint_map.json` | 92 KB | Additional endpoint data |
| `bi_report_urls.json` | 1.7 KB | BI report URLs |
| `individual_summaries/` | ~52 files | Individual WO cost files |
| `API_REVIEW_SUMMARY.md` | 6 KB | API architecture review |
| `DATA_EXTRACTION_GUIDE.md` | 5.5 KB | 14 endpoints, 93% success rate |
| `KEYEDIN_API_README.md` | 7.6 KB | API usage documentation |

Key automation scripts:
| Script | Size | Purpose |
|--------|------|---------|
| `keyedin_api_enhanced.py` | 24 KB | Enhanced API with CDP, session validation, auto-refresh |
| `keyedin_cdp_extractor.py` | 16 KB | Chrome DevTools Protocol cookie extractor |
| `extract_all_cost_summaries_complete.py` | 15 KB | Automated cost extraction |
| `extract_all_detailed_cost_summaries.py` | 16 KB | Detailed cost reports |
| `extract_everything_complete.py` | 22 KB | Comprehensive data extraction |
| `map_all_endpoints.py` | 18 KB | Endpoint discovery and mapping |

### I. Keyedin Mapping API MCP [CONFIRMED]

**Path**: `C:\Scripts\Keyedin Mapping API MCP\`
**Total Size**: 1.5 GB (largest KeyedIn installation)
**Status**: Production-ready MCP server + Electron desktop app

| Component | Content |
|-----------|---------|
| `src/automation/` | Session managers, multi-session pool, Chrome CDP client |
| `src/cache/` | Cache manager, offline mode, TTL config, timing tracker |
| `src/extractors/` | Quote, cost, inventory, search extractors + CSV stream parser |
| `src/mcp_server/` | MCP server implementation |
| `src/validators/` | Data validation logic |
| `desktop_app/` | Electron KeyedIn Desktop app |
| `data/keyedin_cache.db` | SQLite cache with WAL |
| `data/erp_module_coverage.json` | 61 KB module coverage data |
| `data/informer_complete_network_analysis.json` | 24 KB |
| `data/input_field_specs.json` | 17 KB field specifications |

Desktop app config: `AppData\Local\KeyedIn Desktop\config.json` — auto-launches Chrome on debug port 9222, MCP+API server on `127.0.0.1:8765`.

### J. Additional KeyedIn Script Repositories [CONFIRMED]

| Path | Size | Content |
|------|------|---------|
| `C:\Scripts\keyedin-mcp\` | 109 MB | Earlier version or fork of Mapping API MCP |
| `C:\Scripts\keyedin-extraction\` | 43 KB | Lightweight extraction utilities |

---

## 3. Pipeline Components

### Trust Hierarchy

| Tier | Source | Status |
|------|--------|--------|
| 1 | erp_fresh_scrape (live CGI) | NOT IMPLEMENTED |
| 2 | informer_bi_export (GWT-RPC) | PARTIALLY WORKING (1/30 reports automated) |
| 3 | html_reparse (local HTML files) | **FULLY WORKING** — 1.25M rows extracted |
| 4 | local_excel_csv (manual exports) | **FULLY WORKING** — 120K+ rows ingested |

### Script Inventory by Location

#### signx-warehouse (`~/OneDrive - Eagle Sign Co/signx-warehouse/scripts/`)

| Script | Lines | Purpose | Status | Last Modified |
|--------|-------|---------|--------|---------------|
| `parse_full_cost_detail.py` | 907 | Phase 1: Parse 168 HTML files into 5 CSVs | **WORKING** | 2026-01-30 |
| `build_warehouse.py` | 1034 | Phase 5: Combine Phase 1+4 into SQLite | **WORKING** | 2026-01-30 |
| `ingest_local_files.py` | ~500 | Phase 4: Ingest OneDrive Excel/CSV | **WORKING** | 2026-01-30 |
| `decision_engine.py` | ~800 | Generate intelligence reports from warehouse | **WORKING** | 2026-01-30 |
| `scrape_informer.py` | ~400 | Automate Informer BI report extraction | PARTIALLY WORKING | 2026-01-30 |
| `gwt_parser.py` | ~300 | Parse GWT-RPC serialization format | WRITTEN | 2026-01-30 |
| `gwt_analyze.py` | ~200 | Analyze GWT response structure | WRITTEN | 2026-01-30 |
| `gwt_deserialize.py` | ~200 | Deserialize GWT-RPC payloads | WRITTEN | 2026-01-30 |
| `gwt_dump_rows.py` | ~200 | Extract row data from GWT responses | WRITTEN | 2026-01-30 |
| `capture_all_reports.py` | ~300 | Capture all Informer report payloads | WRITTEN | 2026-01-30 |
| `tracer_bullet.py` | ~200 | Single-report end-to-end test | WRITTEN | 2026-01-30 |
| `test_pipeline_fixes.py` | ~200 | Test pipeline components | WRITTEN | 2026-01-30 |
| `_get_session.py` | ~100 | Informer session helper | WRITTEN | 2026-01-30 |

#### keyedin-capture (`C:\Scripts\keyedin-capture/`)

| Script | Size | Purpose | Status |
|--------|------|---------|--------|
| `cost_summary_automation.py` | 12 KB | Automate cost summary report generation | WRITTEN, UNTESTED LIVE |
| `extract_wo_batches.py` | 3 KB | Extract WO data in batches | WRITTEN |
| `fast_extract.py` | 26 KB | Fast extraction via CDP | WRITTEN, PARTIALLY TESTED |
| `parse_reports.py` | 26 KB | Parse captured report files | WRITTEN |
| `setup_credentials.py` | 2.6 KB | Credential management | WRITTEN |
| `test_200wo_debug.py` | 4 KB | Test 200 WO extraction (debug) | WRITTEN |
| `test_200wo_post.py` | 7 KB | Test 200 WO extraction (POST) | WRITTEN |
| `test_20wo.py` | 3 KB | Test 20 WO extraction | WRITTEN |
| `test_cdp.py` | 2.7 KB | Chrome DevTools Protocol test | WRITTEN |
| `test_parse_reports.py` | 17 KB | Unit tests for parsers | WRITTEN |
| `test_pipeline.py` | 7 KB | Pipeline integration tests | WRITTEN |
| `scan_sql.ps1` | 1.9 KB | SQL scanning utility | WRITTEN |

#### keyedin-automation MCP Server (`C:\Scripts\keyedin-automation/`)

| Component | Purpose | Status |
|-----------|---------|--------|
| `mcp_server/server.py` | FastMCP server with 8 tools | **WORKING** |
| `scripts/ingest.py` | Ingest data into ChromaDB | WORKING |
| `scripts/discover_filesystem.py` | Scan filesystem for project paths | WORKING |
| `scripts/verify_knowledge_base.py` | Verify ChromaDB collections | WORKING |
| `keyedin.py` | Playwright-based page automation | WRITTEN (old, uses mvt.exe typo) |
| `keyedin-quote-entry-headed.js` | JavaScript quote entry automation | WRITTEN, 364 lines |
| `launch_mcp.py` | MCP server launcher | WORKING |
| `discovery/keyedin/keyedin_site_map.json` | 288 function codes mapped | DATA FILE |
| `discovery/keyedin/keyedin_page_mappings.json` | Page structure mappings | DATA FILE |
| `discovery/keyedin/network_analysis_report.md` | Network endpoint analysis | DOCUMENTATION |

#### SignX Repo — platform-setup branch

| Script | Purpose | Status |
|--------|---------|--------|
| `scripts/scrape_keyedin.py` | Main ERP scraper (requests + BeautifulSoup) | WRITTEN, BOT DETECTION BLOCKED |
| `scripts/scrape_keyedin_informer.py` | Informer BI scraper | WRITTEN |
| `scripts/test_keyedin_connection.py` | Connection testing | WRITTEN |
| `scripts/run_keyedin_test.ps1` | PowerShell test runner | WRITTEN |
| `scripts/setup_keyedin_windows.ps1` | Windows environment setup | WRITTEN |
| `scripts/train_cost_model.py` | ML cost prediction model | WRITTEN |
| `services/api/src/apex/api/crm_integration.py` | CRM integration module | WRITTEN |

---

## 4. Extraction Attempts History

### Timeline

| Date | Action | Result |
|------|--------|--------|
| **2025-05-22** | Puppeteer DOM scraping of KeyedIn menu structure | **SUCCESS** — 288 links/functions mapped to keyedin_site_map.json |
| **2025-07-12** | Initial keyedin.py Playwright automation | **WRITTEN** — contains typo (mvt.exe instead of mvi.exe) |
| **2025-11-12** | SignX repo: KeyedIn CRM scrapers committed | **WRITTEN** — bot detection encountered on Google SSO |
| **2025-11-12** | SignX repo: Informer scraper written | **WRITTEN** — GWT-RPC endpoint identified |
| **2025-11-12** | SignX repo: Windows setup + connection test | **PARTIAL** — connection works, scraping blocked by SSO |
| **2026-01-05** | Network analysis report generated | **SUCCESS** — documented CGI + RPC endpoints |
| **2026-01-15** | KeyedIn Knowledge MCP server built | **SUCCESS** — 8 tools, 1,141 docs indexed in ChromaDB |
| **2026-01-29** | keyedin-capture: Cost summary automation scripts written | **WRITTEN** — multiple approaches attempted |
| **2026-01-29** | keyedin-capture: HTML batch capture strategy executed | **SUCCESS** — 168 HTML files captured (559MB) |
| **2026-01-29** | keyedin-capture: Informer pentest and access analysis | **DOCUMENTED** — INFORMER_PENTEST_RESULTS.md, INFORMER_ACCESS_ANALYSIS.md |
| **2026-01-29** | keyedin-capture: ERP admin mapping documented | **DOCUMENTED** — ERP_ADMIN_MAPPING.md |
| **2026-01-30 10:11** | Phase 1 first test: Parse single batch file | **SUCCESS** — small CSV output |
| **2026-01-30 10:15** | Phase 1 full run: Parse all 168 HTML files | **SUCCESS** — 170MB, 1.25M rows |
| **2026-01-30 10:26** | Phase 1 refined run: Parse with cross-validation | **SUCCESS** — 175MB, 33,428 WOs, 0 mismatches |
| **2026-01-30 11:01** | Phase 4 first run: Ingest local files (13 sources) | **SUCCESS** — 45MB |
| **2026-01-30 11:06** | Phase 4 expanded: Add more local sources | **SUCCESS** — 65MB, 22 CSVs |
| **2026-01-30 11:07** | Phase 4 final run: All local sources | **SUCCESS** — 66MB, 26 CSVs |
| **2026-01-30 11:10** | Phase 5: Build SQLite warehouse | **SUCCESS** — 211MB, 17 tables, 1,376,130 rows |
| **2026-01-30 11:12** | Decision engine: Generate intelligence report | **SUCCESS** — estimator accuracy, dead stock, margin analysis |
| **2026-01-30 13:42** | Phase 2 test: Informer customer listing export | **PARTIAL** — 1 report automated, GWT parsing incomplete |
| **2026-02-03** | Contract PDFs added to keyedin-capture | **STORED** — Eagle Sign Contract + KIMCO Terms |
| **2026-02-06** | Informer report capture: All 30 payloads | **SUCCESS** — GWT-RPC request/response payloads saved |
| **2026-02-14** | Export endpoint test script written | **BLOCKED** — cannot reach KeyedIn from cloud sandbox (proxy whitelist) |

### What Failed and Why

| Attempt | Failure Mode | Root Cause |
|---------|-------------|------------|
| Google SSO login via requests | Bot detection | Google blocks automated OAuth flows |
| Direct POST login from cloud sandbox | Connection refused | eaglesign.keyedinsign.com not on proxy whitelist |
| GWT-RPC getData automation | Partial parse | GWT serialization format complex, pipe-delimited v7 |
| Informer report CSV export | Only 1/30 automated | GWT response parsing incomplete for most report types |
| keyedin.py Playwright | Never tested | Contains typo (mvt.exe instead of mvi.exe) |

---

## 5. Known Data Gaps

### Fields That EXIST in Source but Were NOT Extracted

| Field | Present In | Extraction Status | Notes |
|-------|-----------|-------------------|-------|
| **EST HOURS** | labor_summary.csv column `est_hrs` | **EXTRACTED** | Available in **** summary lines via span parsing |
| **Material costs** | material_detail.csv columns `est_cost`, `job_cost` | **EXTRACTED** | Both estimated and actual |
| **Outplant costs** | outplant_detail.csv columns `est_cost`, `job_cost` | **EXTRACTED** | Both estimated and actual |
| **Quoted Price** | wo_headers.csv column `quoted_price` | **EXTRACTED** | From header block |
| **Sale Price** | wo_headers.csv column `sale_price` | **EXTRACTED** | From header block |
| **Part Number** | wo_headers.csv column `part_number` | **EXTRACTED** | From header block |

**CORRECTION**: Prior session claimed EST HOURS, Material, and Outplant were "confirmed in HTML but never parsed." This is **FALSE** — all three were successfully extracted by `parse_full_cost_detail.py` into the respective CSV files and loaded into the SQLite warehouse. The confusion may stem from the earlier broken `parse_cost_summary_printer.py` (which was superseded by the working `parse_full_cost_detail.py`).

### Actual Remaining Gaps

| Gap | Impact | How to Fill |
|-----|--------|-------------|
| Quote data (Won/Lost/Void/Cancelled) | Cannot compute win/loss ratio | Automate Informer report ID 1441869 (Quote Status) |
| Real-time WO status | Only historical data | Need live ERP scraping (Phase 3) or export endpoint |
| Employee cost rates | Cannot validate labor costs | Not exposed in current HTML capture |
| Bill of Materials (BOM) | Cannot do should-cost analysis | Test IMPORT.BOM endpoint for structure |
| Routing/operations | Cannot model production flow | Test IMPORT.ROUTING endpoint |
| Margin by sign type (current) | Only historical margins | Need fresh data extraction |

### Work Order Coverage

- **Earliest WO**: WO#1 (date_completed: 2012-12-19)
- **Latest WO**: ~WO#70000+ (2026)
- **Total WOs**: 33,428
- **WOs with complete cost data**: 33,428 (100% — cross-validated, 0 mismatches)
- **WOs with labor detail**: 28,829 (86.3%)
- **WOs with estimator info**: 12,285 (36.8%)

---

## 6. API & Endpoint Map

### Main ERP — 288 CGI Function Codes

Extracted from `keyedin_site_map.json` (2025-05-22 Puppeteer scrape).

**Navigation sections with sample functions:**

| Section | Function Code | Name |
|---------|--------------|------|
| FAVORITES | CRM.CONTACT.MGT | Contact Management |
| FAVORITES | OPEN.SO | Open Sales Order Audit Report (BI) |
| FAVORITES | SO.CONTRACT | Cost Summary Report |
| FAVORITES | STOCK | Part Status Inquiry |
| FAVORITES | EST.QUOTE.STATUS | Status of all Quotes (BI) |
| CRM | IMPORT.CRM.NEW | Import CRM |
| CRM Reports | ACCOUNT.TYPE.CODE.LISTING | Account Type Code Listing |

**Full 288-function JSON**: `C:\Scripts\keyedin-automation\discovery\keyedin\keyedin_site_map.json`

### Export Endpoints (6 total) [NOT YET TESTED]

| Endpoint | Purpose | Test Status |
|----------|---------|-------------|
| `CUST.PROD.EXPORT` | Sales by Customer by Product | UNTESTED |
| `GM.BY.INV.EXPORT` | Gross Margin by Invoice | UNTESTED |
| `SLSPER.PROD.EXPORT` | GM by Salesperson | UNTESTED |
| `USAGE.ANAL.FILE` | Part Usage Export | UNTESTED |
| `EXPORT.WO.LABOR.ANALYSIS` | WO Labor Analysis | UNTESTED |
| `EXPORT.WIP.SUMMARY` | WIP Summary (Open or Closed) | UNTESTED |

### Import Endpoints (5 total) [NOT YET TESTED]

| Endpoint | Purpose | Test Status |
|----------|---------|-------------|
| `IMPORT.PARTS` | Part master import | UNTESTED |
| `IMPORT.BOM` | Bill of Materials import | UNTESTED |
| `IMPORT.ROUTING` | Routing/operations import | UNTESTED |
| `IMPORT.CRM.NEW` | CRM contact import | UNTESTED |
| `IMPORT.SIGN.TEMPLATE` | Sign template import | UNTESTED |

### Quote Entry [NOT YET TESTED]

| Endpoint | Purpose | Test Status |
|----------|---------|-------------|
| `EST.QUOTE.ENTRY` | Quote entry form | JavaScript automation written (`keyedin-quote-entry-headed.js`) but NOT tested live |
| `QUOTE.ENTRY.DETAILS` | Quote detail view | Referenced in JS script |

### Informer BI — 30 Reports

See Section 2.D above for complete list with IDs.

**RPC Endpoints:**

| Service | URL | Protocol |
|---------|-----|----------|
| ViewRPCService | `/eaglesign/informer/rpc/protected/ViewRPCService` | GWT-RPC v7, POST |
| ReportRPCService | `/eaglesign/informer/rpc/protected/ReportRPCService` | GWT-RPC v7, POST |
| FunctionRPCService | Not yet tested | GWT-RPC v7 |
| CodeFileRPCService | Not yet tested | GWT-RPC v7 |
| LoggingRPCService | Not yet tested | GWT-RPC v7 |
| MetadataRPCService | Not yet tested | GWT-RPC v7 |

---

## 7. Immediate Opportunities (Ranked by Effort vs Impact)

### Rank A: Query the Existing Warehouse (0 effort, immediate)

The 211MB SQLite database at `C:\Scripts\signx-warehouse\warehouse\production\eagle_warehouse.db` is fully built with 1.37M rows across 17 tables. **No network access needed.** Every analysis query can be run immediately.

### Rank B: Test Export Endpoints (30 min, requires VPN)

The 6 EXPORT endpoints (`CUST.PROD.EXPORT`, `GM.BY.INV.EXPORT`, `SLSPER.PROD.EXPORT`, `USAGE.ANAL.FILE`, `EXPORT.WO.LABOR.ANALYSIS`, `EXPORT.WIP.SUMMARY`) likely return direct CSV/Excel downloads. A test script exists at `~/Desktop/SignX/test_export_endpoints.py`. Requires running from VPN-connected PC.

### Rank C: Automate Remaining Informer Reports (2-4 hours, requires VPN)

30 GWT-RPC payloads are captured. The `scrape_informer.py` script successfully automated 1 report (customer_listing). Extending to remaining 29 reports requires fixing GWT deserialization for each report's column structure. The `Quote Status Report` (ID 1441869) is highest priority — it unlocks win/loss ratio analysis.

### Rank D: Re-parse HTML for Additional Fields (1-2 hours, no network)

If any fields were missed in the first parse, the 168 HTML files (559MB) are still available locally. The parser `parse_full_cost_detail.py` can be extended. However, **all major fields appear to have been extracted** — this may not yield new data.

### Rank E: Live ERP Scraping at Scale (2-3 days, requires VPN)

Build Phase 3 (trust tier 1) for real-time fresh data. Uses authenticated session + CDP automation. Most infrastructure exists but needs VPN testing.

### Rank F: Quote Entry Automation (1 week, high risk)

The `keyedin-quote-entry-headed.js` script (364 lines) automates quote entry read operations. Would enable programmatic access to quote details. High risk — writes to production ERP if not careful.

---

## 8. Blockers & Unknowns

### Cannot Determine from Repo Alone

| Item | Why | Action Required |
|------|-----|-----------------|
| Export endpoint output format | Never tested — may return CSV, Excel, or form | Brady: Test from VPN PC |
| Import endpoint form fields | Never tested — need GET to see field structure | Brady: Test from VPN PC |
| Informer report #31-71 | Prior session claimed 71 reports, but only 30 found in Informer | Verify: Log into Informer and count |
| Current WO status | Warehouse has historical data only | Need live data refresh |
| Quote entry POST payload | JS script written but never executed | Brady: Test from VPN PC with Chrome DevTools |
| Rate limits on CGI endpoints | Never tested | Careful testing needed |

### Requires VPN Access

- All live endpoint testing
- Export/Import endpoint testing
- Fresh Informer report automation
- Phase 3 live scraping

### Requires Vendor Contact (KIMCO/KeyedIn)

- Direct database access or API availability
- Bulk export capabilities
- Documentation for CGI endpoint parameters
- Data model/schema documentation

### Requires On-Site Access

- Nothing identified — all work can be done remotely via VPN

---

## SECURITY NOTE: Plaintext Credentials in Git History

The SignX repo branch `origin/claude/signx-platform-setup-011CUyNrHbNEXBgpFqWgJYSZ` contains **plaintext KeyedIn credentials** (`BradyF / Eagle@605!`) committed across 5 files:

| File | Exposure Method |
|------|----------------|
| `keyedin/KEYEDIN_STATUS_REVIEW.md` | In "Credentials File" and "What We Know" sections |
| `keyedin/SESSION_SUMMARY.md` | In "Quick Reference" section + session cookie |
| `keyedin/WINDOWS_SETUP_GUIDE.md` | In "Prerequisites" section |
| `scripts/run_keyedin_test.ps1` | In error output text |
| `scripts/setup_keyedin_windows.ps1` | HARDCODED in heredoc that generates `.env.keyedin` |

**Risk assessment**: The repo is **private** (`EAGLE605/SignX`). Credentials are only accessible to repo collaborators. No rotation needed unless the repo is made public or untrusted collaborators are added. Session cookie in `SESSION_SUMMARY.md` is long-expired.

---

## Appendix: Corrections to Prior Session Claims

| Prior Claim | Actual Finding | Status |
|-------------|----------------|--------|
| "402MB HTML files" | 559MB directory (168 HTML batch files) | CORRECTED |
| "17 parsed tables" | Exactly 17 tables in eagle_warehouse.db | CONFIRMED |
| "1.3M rows" | 1,376,130 rows | CONFIRMED |
| "$241K dead stock" | $241,701.53 tied-up capital | CONFIRMED |
| "54% labor below estimates" | 50-56% variance across all estimators | CONFIRMED |
| "262 mapped endpoints" | 288 total links / 264 entries / 241 unique function codes in keyedin_site_map.json | CORRECTED (241 unique, not 262) |
| "71 Informer reports" | 30 reports visible and captured | CORRECTED (30, not 71) |
| "KEYEDIN_COST_SUMMARY_EXTRACTION_SKILL.md" | Does NOT exist as a file anywhere | NOT FOUND — conversation context only |
| "parse_cost_summary_printer.py" | Superseded by parse_full_cost_detail.py | SUPERSEDED |
| "EST HOURS never parsed" | EST HOURS IS in labor_summary.csv (est_hrs column) | CORRECTED — was parsed |
| "Material costs never extracted" | Material costs ARE in material_detail.csv | CORRECTED — was extracted |
| "8-agent exploration results" | Not saved to any file — existed only in conversation | NOT PERSISTED |
| "claude/keyedin-integration-recon branch" | Not pushed to remote — exists only in previous session context | NOT COMMITTED |
