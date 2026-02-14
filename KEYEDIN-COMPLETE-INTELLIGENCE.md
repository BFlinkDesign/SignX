# KeyedIn Complete Intelligence Report

**Compiled:** 2026-02-14
**Method:** Exhaustive search of entire `/home/user/SignX` repo — all branches, all directories, all file types
**Scope:** Every reference to KeyedIn, SignX-Warehouse, cost summary pipeline, Informer BI, GWT-RPC, and integration attempts

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Data Inventory](#2-data-inventory)
3. [Pipeline Components](#3-pipeline-components)
4. [Extraction Attempts History](#4-extraction-attempts-history)
5. [Known Data Gaps](#5-known-data-gaps)
6. [API & Endpoint Map](#6-api--endpoint-map)
7. [Immediate Opportunities (Ranked)](#7-immediate-opportunities-ranked)
8. [Blockers & Unknowns](#8-blockers--unknowns)

---

## 1. System Architecture

### Identity

| Field | Value | Source |
|-------|-------|--------|
| Product | KeyedIn Sign v2.1 | Error messages in extracted HTML |
| MVI Version | 3.0 | Error response from invalid endpoint |
| Tenant ID | `eaglesign` | URL path component |
| Primary User | `BRADYF` (Brady F.) | Session cookies, menu requests |
| Email | `brady@eaglesign.net` | Script references |
| Product Lineage | DataSIGN (2006) → KeyedIn Sign → KIMCO ERP (2023+) | Web research |

### Network Architecture

```
Browser (Chrome)
    │
    ├── Port 80/443 ──→ IIS / ASP.NET ──→ mvi.exe (CGI) ──→ MultiValue/Pick DB
    │                   (web server)       (MV Interface 3.0)  (engine unknown)
    │
    └── Port 8443 ───→ Informer BI ──→ GWT-RPC Service ──→ Same DB (via SSO)
                       (Entrinsik 5.x)   (ViewRPCService)
```

### Technology Stack

| Layer | Technology | Evidence |
|-------|-----------|----------|
| Web Server | IIS + ASP.NET | `ASP.NET_SessionId` cookie |
| CGI Gateway | `mvi.exe` v3.0 (MultiValue Interface) | All URLs: `/cgi-bin/mvi.exe/` |
| Database | MultiValue/Pick (UniVerse, UniData, jBASE, or D3) | VOC file errors, ALLCAPS.DOT naming |
| BI Platform | Entrinsik Informer 5.x | GWT class: `com.entrinsik.informer.*` |
| BI Frontend | Google Web Toolkit (GWT) | `text/x-gwt-rpc` content type |
| BI Transport | GWT-RPC binary protocol | Captured payloads |
| Auth (Main) | Direct POST with USERNAME/PASSWORD/SECURE | Tested + validated |
| Auth (BI) | SSO token from main app → JSESSIONID | `sso?u=BRADYF&t={token}` pattern |

### Key Evidence for MultiValue/Pick

1. `mvi.exe` = MultiValue Interface — standard web gateway for Pick databases
2. VOC file reference: `"WO.COST.DETAIL is not defined in the VOC file."` — Pick concept
3. ALLCAPS.DOT.SEPARATED naming (e.g., `WO.COST.SUMMARY`) — Pick convention
4. `LOGIN.START` process name — Pick naming pattern
5. ASP.NET_SessionId alongside custom SESSIONID — IIS hosting MVI CGI

### Server Names Found in Repo

- `ES-FS02` — File server
- `ES-DC03` — Domain controller
- `ES-SecSer02` — Security server
- All on Eagle Sign's internal network

### CRITICAL: Legacy vs KIMCO

Eagle Sign runs the **legacy** KeyedIn Sign v2.1 (CGI/MVI/Pick). This is NOT:
- KIMCO ERP (the new .NET 5/Azure SQL/Azure platform)
- KeyedIn PPM (project portfolio management, acquired by Sciforma)

KIMCO is the upgrade path with modern APIs. Eagle Sign has NOT migrated.

---

## 2. Data Inventory

### 2A. KeyedIn API Extractions (`Keyedin/` — 35 MB)

| File | Content | Records | Date |
|------|---------|---------|------|
| `WEB.MENU.json` | 262 endpoint menu structure | 262 endpoints | 2025-11-12 |
| `endpoint_map.json` | Categorized endpoint listing | 262 | 2025-11-12 |
| `complete_endpoint_map.json` | Full endpoint details | 262 | 2025-11-12 |
| `keyedin_session.json` | 5 session cookies | 5 cookies | 2025-11-12 |
| `keyedin_chrome_session.json` | Chrome-extracted session | — | 2025-11-12 |
| `keyedin_chrome_session_network.json` | Network capture (8 requests) | 8 | 2025-11-12 |
| `keyedin_network_capture.json` | Network traffic capture | — | 2025-11-12 |
| `captured_all_requests.json` | All HTTP requests | — | 2025-11-12 |
| `extracted_data/extracted_data_*.json` | Menu + endpoint data | — | 2025-11-12 |
| `extracted_data/menu_*.json` | Menu structure | — | 2025-11-12 |
| `extracted_data/work_orders_*.json` | WO form data | — | 2025-11-12 |
| `wo_query_results.json` | WO query results | — | 2025-11-12 |
| `informer_portal_urls.json` | Informer SSO URLs | — | 2025-11-12 |

### 2B. Cost Summary Extractions (`Keyedin/cost_summaries/` — 528 KB)

| File | WOs Queried | Data Rows | Status |
|------|------------|-----------|--------|
| `all_cost_summaries_20251112_180327.json` | Multiple | Headers only, 0 data rows | PARTIAL |
| `all_cost_summaries_20251112_180352.json` | Multiple | Headers only, 0 data rows | PARTIAL |
| `all_cost_summaries_so_contract_20251112_181318.json` | 10 SOs | 10 tables, ALL 0 rows | FAILED |
| `all_detailed_cost_summaries_20251112_180422.json` | Multiple | — | PARTIAL |
| `all_detailed_cost_summaries_20251112_181028.json` | Multiple | — | PARTIAL |
| `individual_summaries/` (52 files) | WO 8343-8392 + 2 others | Headers + partial row data | PARTIAL |

**Key finding:** Individual WO summaries via `WO.STATUS.SUM?WONO={#}` returned some row data (table headers and field labels) but BeautifulSoup parsing didn't capture the actual cost values cleanly. The `SO.CONTRACT.RUN` approach returned 0 data rows.

### 2C. Informer BI Extractions (`Keyedin/GWT Google Web Toolkit/`)

| File | Content | Status |
|------|---------|--------|
| `extraction_summary.txt` | 71 reports discovered | SUCCESS |
| `keyedin_session.json` | JSESSIONID, authToken, clientId | SUCCESS |
| `eaglesign.keyedinsign.com.har` | Full HAR capture | SUCCESS |
| `session_cookies.json` | Informer cookies | SUCCESS |
| GWT-RPC data extraction | 14 reports attempted, 0 records | FAILED |

### 2D. CSV Data Exports from KeyedIn (`Keyedin/Data Exports/` + `Eagle Data/`)

| File | Content | Size | Records |
|------|---------|------|---------|
| `Closed WO 11-1-00 to 10-31-25.csv` | 25 years of closed WOs | 5.8 MB | ~33,080 |
| `BRADYF.WIP.SUMMARY 010106-062725.csv` | WIP summary 2006-2025 | Large | 19 years |
| `Sales Order Numbers by Customer 01012006-07182025.csv` | All SOs 2006-2025 | Large | 19 years |
| `Closed Sales Order Status by Customer.csv` | Closed SOs by customer | — | — |
| `Sales Summary - by Customer.csv` | Sales summary | — | — |
| `Vendor Listing.csv` | All vendors | — | — |
| `GM by Salesperson/*.CSV` | GM by salesperson reports | — | — |
| `SIGN_TYPE_CODES.csv` | 39 sign type codes | Small | 39 |
| `Work Codes and Pricing.csv` | 50+ work codes, 10 departments | Small | 50+ |
| `EMPLOYEE_HOURS_BY_WORK_CODE 01012006_05092025.csv` | Employee × work code matrix | Large | All employees |
| `Inventory List.csv` | Part Nbr, Description, Qty, Prices | — | — |

**These CSVs are the richest data source in the repo.** They were manually exported from KeyedIn's built-in export features.

### 2E. Benchmark/Audit Cost Data (`Benchmark/storage/` — 571 KB)

| Part Number | Description | Groups | WOs | Format |
|-------------|-------------|--------|-----|--------|
| 209-0385 | 5x20 Replacement Faces | 1 | 30 (incl WO 68441, 68417, 68416, 68415, 68414) | TXT + PDF + XLSX |
| 210-0180 | Guaranteed Faces | 1 | — | TXT + PDF |
| 210-0190 | Instruction Faces | 1 | — | TXT + PDF |
| 221-0190 | Intercom Sign | 5 | — | TXT + PDF |
| 221-0200 | Standard 5x20 Sign | 6 | — | TXT + PDF |
| 221-0210 | High Wind 5x20 Sign | 1 | — | TXT + PDF |
| 221-0220 | Hurricane 5x20 Sign | 1 | — | TXT + PDF |
| 221-0300 | Standard Poles | 4 | — | TXT + PDF |
| 221-0320 | High Wind Poles | 1 | — | TXT |
| 221-0330 | Hurricane Poles | 1 | — | TXT |
| 307-0267 | 5x20 NRG LED Conversion Kits | 1 | 5 (WO 68305, 68333, 68341, 68357, 68377) | TXT + PDF + CSV |
| 307-0268 | Intercom Sign NRG LED Conversion Kit | 1 | — | TXT + PDF |

**Detailed Cost Summary CSV fields (confirmed in `307-0267` CSV):**
- Work Order, Cost Type, Date, Work Dept, Work Code, Seq
- Emp/Part/Item, U/M
- **Est Hrs, Act Hrs, Var Hrs** (labor hours)
- **Est Qty, Act Qty, Var Qty** (material quantities)
- **Est Cost, Act Lab, Act Bur, Act Mat, Act Out, Use Tax, Job Cost**
- R/I, Var Cost, Gross Margin
- Description, Inv Type

### 2F. HTML Page Captures

| File | Content |
|------|---------|
| `Keyedin/login_page.html` | Login form |
| `Keyedin/login_start_page.html` | Login start redirect |
| `Keyedin/actual_login_page.html` | Actual form fields |
| `Keyedin/login_success.html` | Post-login page |
| `Keyedin/logged_in_page.html` | Authenticated state |
| `Keyedin/MAIN.html` | Main dashboard |
| `Keyedin/WEB.MENU.html` | Menu page |
| `Keyedin/WORKORDER_LIST.html` | WO list page |
| `Keyedin/SERVICE_CALL_LIST.html` | Service call list |
| `Keyedin/..KeyedIn_System_Map/.../00_logged_in_home.html` | Discovery capture |

### 2G. HAR Files

| File | Size | Content |
|------|------|---------|
| `Keyedin/GWT Google Web Toolkit/eaglesign.keyedinsign.com.har` | — | Full network capture of Informer session |
| `Keyedin/har_capture.json` | — | Additional HAR capture |

---

## 3. Pipeline Components

### 3A. Authentication Pipeline

**Status: WORKING**

```
Step 1: Chrome CDP → open browser with remote debugging
Step 2: User logs in manually (or script POSTs USERNAME/PASSWORD/SECURE)
Step 3: Extract 5 cookies via CDP or Selenium
Step 4: All subsequent HTTP requests use SESSIONID cookie
```

**Files:**
- `keyedin_cdp_extractor.py` — Chrome DevTools Protocol cookie extraction
- `extract_cookies_chrome.py` — Selenium-based extraction
- `extract_with_credentials.py` — Direct POST authentication
- `keyedin_api_enhanced.py` — Session management wrapper

### 3B. CGI/MVI Endpoint Access Pipeline

**Status: WORKING (93% success rate)**

```
Step 1: Authenticate (get SESSIONID cookie)
Step 2: GET /cgi-bin/mvi.exe/{PROCESS_NAME}[?params]
Step 3: Receive HTML response
Step 4: Parse with BeautifulSoup
```

**Files:**
- `extract_all_data.py` — Bulk endpoint extraction
- `map_all_endpoints.py` — Endpoint discovery and mapping
- `comprehensive_test.py` — Validation (9/9 tests pass)

### 3C. Cost Summary Extraction Pipeline

**Status: PARTIAL — headers extracted, data rows mostly empty**

```
Approach 1: WO.STATUS.SUM?WONO={#} → HTML table → BeautifulSoup
Approach 2: SO.CONTRACT.RUN?SONO={#}&REPORT_OPT=D&REPORT_WHERE=P → HTML table
```

**Files:**
- `extract_all_cost_summaries.py` (443 lines) — WO.STATUS.SUM approach
- `extract_all_cost_summaries_complete.py` — Complete version
- `extract_all_detailed_cost_summaries.py` — Detailed version
- `extract_all_cost_summaries_via_report.py` — SO.CONTRACT.RUN approach

**Result:** 52 individual WO cost summaries extracted with partial data. Table headers captured but many data cells came back empty or concatenated (parsing issue).

### 3D. Informer BI / GWT-RPC Pipeline

**Status: Auth WORKING, data extraction FAILED**

```
Step 1: Get SSO token from main app
Step 2: Navigate to /eaglesign/sso?u=BRADYF&t={token}
Step 3: Capture JSESSIONID, authToken, clientId
Step 4: POST GWT-RPC payload to ViewRPCService
Step 5: Parse GWT-RPC response (FAILED — 500 errors on getData)
```

**Files:**
- `GWT Google Web Toolkit/MASTER_EXTRACTOR.ps1` — PowerShell automation
- `GWT Google Web Toolkit/keyedin_complete_extraction.py` — Python version
- `GWT Google Web Toolkit/keyedin_enhanced_extractor.py` — Enhanced version
- `GWT Google Web Toolkit/keyedin_working_extractor.py` — Working variant
- `GWT Google Web Toolkit/keyedin_data_extractor.py` — General extractor
- 11 PowerShell test scripts for GWT-RPC payload formatting

### 3E. MCP Server Pipeline

**Status: BUILT, NOT VALIDATED IN PRODUCTION**

```
Playwright-based MCP server with 7 tools:
- login, navigate, get_data, fill_form, search, screenshot, list_sections
```

**Files:**
- `KEYEDIN MCP/keyedin_mcp_server_secure.py` (533 lines) — Main MCP server
- `KEYEDIN MCP/v1/Broke V1 (CLAUDE 4)/keyedin_mcp_server.py` — V1 (broken)
- `KEYEDIN MCP/v1/Broke V1 (CLAUDE 4)/keyedin_resilient_agent.py` — Agent (broken)
- `KEYEDIN MCP/discovery/keyedin_architecture_mapper.py` (669 lines) — Discovery mapper
- `KEYEDIN MCP/Test/keyedin_investigator_v5.py` — Investigation tool
- `KEYEDIN MCP/Test/keyedin_manual_login_mapper.py` — Login mapper

### 3F. Live Test Pipeline

**Status: BUILT, NOT YET RUN (requires VPN)**

```
recon-results/run_all_tests.py — Zero-dependency Python script
Tests: DNS, Auth, 6 Exports, Informer BI, Quote Entry
Must run from Brady's VPN-connected PC
```

---

## 4. Extraction Attempts History

### Timeline

| Date | Session | What Happened | Outcome |
|------|---------|---------------|---------|
| 2025-11-12 | Session 1 | Authentication + endpoint mapping | SUCCESS — 262 endpoints, 13/14 tested |
| 2025-11-12 | Session 1 | Cost summary extraction via WO.STATUS.SUM | PARTIAL — 52 WOs, headers only |
| 2025-11-12 | Session 1 | Cost summary via SO.CONTRACT.RUN | FAILED — 0 data rows |
| 2025-11-12 | Session 1 | Informer GWT-RPC report discovery | SUCCESS — 71 reports found |
| 2025-11-12 | Session 1 | Informer GWT-RPC data extraction | FAILED — 500 errors, 0 records |
| 2025-11-12 | Session 1 | Session validation (9/9 tests) | SUCCESS — all endpoints accessible |
| Pre-2025-11 | Earlier | MCP server v1 build | FAILED — labeled "Broke V1" |
| Pre-2025-11 | Earlier | MCP server v2 (secure) build | BUILT — untested in production |
| Pre-2025-11 | Earlier | Selenium login automation | WORKING — cookie capture confirmed |
| Pre-2025-11 | Earlier | Architecture mapper (669 lines) | BUILT — 18 sections mapped |
| 2026-02-14 | Current | Integration recon from cloud sandbox | BLOCKED — no network access |
| 2026-02-14 | Current | Legacy intel compilation | COMPLETE — `LEGACY-KEYEDIN-INTEL.md` |
| 2026-02-14 | Current | Live test script creation | COMPLETE — `run_all_tests.py` |

### What Was Attempted but NOT Committed

**[NOT IN REPO — FROM CONVERSATION HISTORY ONLY]**

The following items were referenced in mission briefs but DO NOT exist anywhere in the repository:

| Item | Search Result |
|------|--------------|
| 402 MB HTML files | NOT FOUND — no files of this size exist |
| 17 parsed tables | NOT FOUND — no reference in any file |
| 1.3M rows | NOT FOUND — no reference in any file |
| $241K dead stock finding | NOT FOUND in committed code — may be from conversation analysis |
| 54% labor below estimates | NOT FOUND in committed code — may be from conversation analysis |
| `EXTRACTION_SKILL` files | NOT FOUND — no such file or reference exists |
| `parse_cost_summary_printer.py` | NOT FOUND — no such file exists |
| 8-agent exploration | NOT FOUND — no multi-agent orchestration code committed |
| Workforce intelligence engine | NOT FOUND — no such code exists |
| `PROJECT-STATE` files | NOT FOUND — no such files exist |

**These findings likely came from interactive conversation sessions where data was analyzed in memory but never committed to the repo.**

### Data Analysis Findings (from Benchmark CSVs, verified in repo)

The detailed cost summary CSV at `Benchmark/storage/- Audit -/2025/307-0267 .../Cost Summaries DETAILED 68305 68333 68341 68357 68377.csv` contains real cost data for WOs 68305-68377:

| WO | Est Hrs | Act Hrs | Var Hrs | Est Cost | Job Cost | Var Cost |
|----|---------|---------|---------|----------|----------|----------|
| 68377 | 80 | 35.75 | -44.25 | $53,048 | $51,108 | -$1,940 |
| 68357 | 120 | 51.75 | -68.25 | $83,589 | $76,583 | -$7,006 |
| 68341 | 140 | 56.50 | -83.50 | $97,521 | $93,910 | -$3,611 |
| 68333 | 80 | 32.75 | -47.25 | $55,726 | $53,614 | -$2,113 |
| 68305 | 80 | 46.25 | -33.75 | $55,726 | $54,293 | -$1,433 |

**Labor actuals consistently below estimates** (avg ~55% of estimated hours) — this IS visible in the committed data, though the "54%" figure itself isn't explicitly stated in any file.

---

## 5. Known Data Gaps

### Gap 1: Cost Summary Programmatic Extraction

**Status:** BROKEN
**What's missing:** The extraction scripts connect and authenticate, but:
- `WO.STATUS.SUM` returns HTML that BeautifulSoup doesn't parse correctly (concatenated cells)
- `SO.CONTRACT.RUN` returns 0 data rows
- The DETAILED cost summary CSV was manually exported, not programmatically extracted

**Fix needed:** Either fix the HTML parser for WO.STATUS.SUM, or use Playwright to automate the manual export process (Report Option 'D' + Send To 'P').

### Gap 2: Informer Report Data

**Status:** BROKEN
**What's missing:** 71 reports discovered but 0 data rows extracted
**Root cause:** GWT-RPC `getData` calls fail with 500 Server Error — the binary payload format is wrong
**Fix needed:** Capture a working getData payload from the browser (via HAR) and reverse-engineer the exact format, OR use Informer's built-in export buttons via Playwright

### Gap 3: Quote Entry Read/Write

**Status:** UNTESTED
**What's missing:** Never attempted to:
- Read quote line items from `QUOTE.ENTRY.DETAILS?QUOTENO={#}&DEPTNO={code}`
- Write new quote line items via POST to `EST.QUOTE.ENTRY`
**Fix needed:** Test from VPN-connected PC using `run_all_tests.py`

### Gap 4: Export Endpoints

**Status:** UNTESTED
**What's missing:** 6 built-in export endpoints never tested:
1. `CUST.PROD.EXPORT`
2. `GM.BY.INV.EXPORT`
3. `SLSPER.PROD.EXPORT`
4. `USAGE.ANAL.FILE`
5. `EXPORT.WO.LABOR.ANALYSIS`
6. `EXPORT.WIP.SUMMARY`
**Fix needed:** Test from VPN-connected PC

### Gap 5: Import Endpoints

**Status:** UNTESTED
**What's missing:** 5 built-in import endpoints never tested:
1. `IMPORT.PARTS`
2. `IMPORT.BOM`
3. `IMPORT.ROUTING`
4. `IMPORT.CRM.NEW`
5. `IMPORT.SIGN.TEMPLATE`
**Fix needed:** Open each import screen, document file format requirements

### Gap 6: Network Location & Hosting

**Status:** UNKNOWN
**What's missing:** Cannot determine from cloud sandbox whether:
- Server is on-prem at Eagle Sign or hosted by KeyedIn/KIMCO
- Direct database access is possible
- What specific MultiValue/Pick engine runs
**Fix needed:** Brady runs network tests from VPN-connected PC

### Gap 7: Login Method

**Status:** CONTRADICTORY
**What's known:**
- Scripts use direct POST with USERNAME/PASSWORD/SECURE — this worked on 2025-11-12
- Mission briefs mention Google SSO with green "Sign In" button
- Could be that login method changed, or there are two login flows
**Fix needed:** Confirm current login method on-site

---

## 6. API & Endpoint Map

### Authentication

```
POST https://eaglesign.keyedinsign.com/
Body: USERNAME=BRADYF&PASSWORD={pwd}&SECURE=TRUE
Response: Set-Cookie: SESSIONID, ASP.NET_SessionId, user, secure, IMPERSONATE
```

### Informer SSO

```
GET https://eaglesign.keyedinsign.com:8443/eaglesign/sso
  ?u=BRADYF
  &t={sso_token}                    ← 25-char lowercase alphanum
  &initialAction.action=ReportRun
  &remoteId={report_id}             ← numeric
```

### Top-Level Modules (262 endpoints total)

| Module | Menu ID | Key Endpoints |
|--------|---------|---------------|
| CRM | `CRM.STD` | `CRM.CONTACT.MGT`, `CHANGE.SC.ACCOUNT` |
| Project Mgmt | `PROJECT.STD` | `#PROJECT.LISTING`, `#PROJECT.DETAILS` |
| Estimating | `EST.STD` | `EST.QUOTE.ENTRY`, `QUOTE.ENTRY.DETAILS`, `QUOTE.ENTRY.LIMITED` |
| Sales Orders | `SALES.STD` | `ORDER.ENTRY`, `EST.CREATE.SO`, `SO.PRINT` |
| Shipping | `SHIPPING.STD` | `SHIPLISTS`, `SHIPMENTS`, `SHIPMENTS.TRACKING` |
| Sales Analysis | `SA.STD` | GM reports, sales by product/customer |
| Purchasing | `PUR.STD` | `PURCHASE`, `PO.RECEIPTS`, `PO.CLOSE` |
| Inventory | `INV.STD` | `FIRST.ISSUE`, parts maint, BOM, routing |
| Job Cost | `JCOST.*` | `WO.HISTORY`, `WO.STATUS.SUM`, `SO.CONTRACT` |
| MRP | `MRP.*` | `PARTS.MRP`, `MRP.CALC` |
| Production | `PRODUCTION.STD` | `WO.PRINT`, `WO.INQUIRY`, `WO.CHANGE` |
| Labor | `PAY.*` | Employee hours by work code/date |
| AP | `AP.*` | Vendor master, invoice listing |
| AR | `AR.*` | Customer master, bill-to, ship-to |
| Reports | `RPT.STD` | `REPORT.VIEW.INDEX` |
| Admin | `ADMIN.STD` | Password change, clear locks, logoff |

### Tested Endpoints (13/14 = 93%)

| Endpoint | Status | Response |
|----------|--------|----------|
| `WEB.MENU?USERNAME=BRADYF` | 200 | 33,981 bytes JSON |
| `WO.INQUIRY` | 200 | HTML form |
| `WO.HISTORY` | 200 | HTML, 4 tables |
| `WO.COST.SUMMARY` | 200 | HTML |
| `SERVICE.CALL.LIST` | 200 | HTML, 2 tables |
| `WIDGET.ASSIGNED.SERVICE.CALLS?ACTION=AJAX` | 200 | JSON |
| `WIDGET.ASSIGNED.MILESTONES?ACTION=AJAX` | 200 | JSON |
| `WIDGET.CRM.TASKS?ACTION=AJAX` | 200 | JSON |
| `WIDGET.FYI?ACTION=AJAX` | 200 | JSON |
| `MAIN` | 200 | HTML |
| `HOME` | 200 | HTML |
| `WO.COMPLETION.INQUIRY` | 200 | HTML |
| `WO.GROUP.ANALYSIS` | 200 | HTML, 5 tables |
| `WO.COST.DETAIL` | ERROR | Not in VOC file |

### Export Endpoints (untested)

1. `CUST.PROD.EXPORT` — Sales by Customer by Product
2. `GM.BY.INV.EXPORT` — Gross Margin by Invoice
3. `SLSPER.PROD.EXPORT` — GM by Salesperson
4. `USAGE.ANAL.FILE` — Part Usage
5. `EXPORT.WO.LABOR.ANALYSIS` — WO Labor Analysis
6. `EXPORT.WIP.SUMMARY` — WIP Summary

### Import Endpoints (untested)

1. `IMPORT.PARTS`
2. `IMPORT.BOM`
3. `IMPORT.ROUTING`
4. `IMPORT.CRM.NEW`
5. `IMPORT.SIGN.TEMPLATE`

---

## 7. Immediate Opportunities (Ranked)

### Rank 1: Built-in Export Endpoints (Confidence: HIGH)

**Why:** These are pre-built by KeyedIn for CSV/Excel output. Zero reverse-engineering needed.
**Action:** Test the 6 EXPORT endpoints from Brady's PC.
**Effort:** 30 minutes
**If successful:** Immediate access to WO labor analysis, WIP summary, GM data, part usage
**Files:** None needed — just HTTP GET with session cookie

### Rank 2: CGI/MVI HTTP API — Read (Confidence: HIGH)

**Why:** Already proven working at 93% success rate. Just needs better HTML parsers.
**Action:** Build targeted parsers for `QUOTE.ENTRY.DETAILS`, `WO.STATUS.SUM`, `ORDER.ENTRY`
**Effort:** 1-2 days
**Files:** `keyedin_api_enhanced.py` (working session manager), new parsers needed

### Rank 3: Playwright Browser Automation (Confidence: MEDIUM-HIGH)

**Why:** Can handle dynamic forms, SSO, and any endpoint. Universal fallback.
**Action:** Build Playwright persistent context with manual first-login, then automate
**Effort:** 2-3 days
**Key advantage:** Can interact with forms (write capability) and handle JavaScript-rendered content
**Files:** `KEYEDIN MCP/keyedin_mcp_server_secure.py` (533 lines, needs production testing)

### Rank 4: Informer BI Export Buttons (Confidence: MEDIUM)

**Why:** Informer likely has built-in CSV/Excel export buttons on each report
**Action:** Open any report in browser, check for export button, automate with Playwright
**Effort:** 1 day (if export buttons exist)
**Unlocks:** All 71 BI reports as downloadable data

### Rank 5: Built-in Import Endpoints (Confidence: MEDIUM)

**Why:** Menu reveals 5 import screens — designed for bulk data ingest
**Action:** Open each import screen, document format requirements, test with sample data
**Effort:** 1-2 days
**Unlocks:** Write capability for parts, BOM, routing, CRM, sign templates

### Rank 6: CGI/MVI HTTP API — Write via POST (Confidence: MEDIUM)

**Why:** If forms accept POST data, we can create/update records programmatically
**Action:** Capture form fields from `EST.QUOTE.ENTRY`, replay as POST
**Effort:** 2-3 days
**Risk:** May require hidden form fields, CSRF tokens, or specific field sequences

### Rank 7: Informer GWT-RPC Data Extraction (Confidence: LOW)

**Why:** Authentication works but the binary protocol is hard to reverse-engineer
**Action:** Capture a working `getData` payload from browser HAR, replay exactly
**Effort:** 3-5 days
**Risk:** GWT-RPC is notoriously fragile — any version mismatch breaks payloads

### Rank 8: KIMCO Migration / Vendor API (Confidence: LOW for legacy)

**Why:** KIMCO has modern APIs, but migration is a major business decision
**Action:** Contact KIMCO sales, ask about API for current instance + migration timeline
**Effort:** Vendor-dependent
**Unlocks:** If migrated, full REST API access

### Rank 9: Direct Database Access (Confidence: VERY LOW)

**Why:** No credentials, unknown hosting, Pick database requires specialized ODBC
**Action:** Ask IT if server is on-prem, request database access
**Effort:** IT-dependent
**Risk:** Direct DB writes could corrupt data

---

## 8. Blockers & Unknowns

### Active Blockers

| Blocker | Impact | Resolution |
|---------|--------|------------|
| Cloud sandbox cannot reach `eaglesign.keyedinsign.com` | Cannot run any live tests | Brady runs `run_all_tests.py` from VPN PC |
| GWT-RPC binary protocol not reverse-engineered | Cannot extract Informer report data | Capture browser payload via HAR |
| HTML parser doesn't capture cost summary data cells | WO.STATUS.SUM returns data but parser misses values | Fix BeautifulSoup selectors or use Playwright |
| Export endpoints never tested | Don't know if they produce downloadable files | Test from VPN PC |

### Critical Unknowns

| Unknown | Why It Matters | Resolution |
|---------|---------------|------------|
| On-prem or hosted? | If on-prem, direct DB access possible | Ask IT |
| Which MultiValue engine? | Determines ODBC drivers, tools | Check server processes |
| Google SSO or direct login? | Determines auth automation approach | Load login page, confirm |
| IMPORT.* file format? | Enables write capability | Open import screens, document |
| Informer export buttons? | Enables easy bulk data extraction | Open any BI report, check UI |
| KIMCO migration timeline? | Invest in legacy or wait for modern? | Contact KIMCO |
| Do `#PROJECT.*` URLs work? | `#` prefix may break URL routing | Test with/without `#` |
| Report Option 'D' + Send To 'P' format? | Cost summary print output | Test from quote entry screen |

### Credentials in Repo (SECURITY NOTE)

The following are committed to the repository and should be rotated:
- Password `Eagle@605!` in `extract_with_credentials.py:11`
- URL-encoded password in `captured_all_requests.json:15`
- JSESSIONID `16zigc7ehs9816ham55pq7opc` (likely expired)
- Multiple authToken UUIDs (likely expired)
- Multiple clientId UUIDs

---

## Summary Table

| Component | Found | Tested | Working | Broken | Untested |
|-----------|-------|--------|---------|--------|----------|
| Authentication (Main) | YES | YES | YES | — | — |
| Authentication (Informer) | YES | YES | YES | — | — |
| Endpoint Discovery (262) | YES | YES | YES | — | — |
| CGI/MVI Read | YES | YES | YES (93%) | 1 endpoint | 248+ |
| CGI/MVI Write | YES | NO | — | — | ALL |
| Cost Summary Extract | YES | YES | PARTIAL | Parser broken | — |
| Informer Report Catalog | YES | YES | YES | — | — |
| Informer Data Extract | YES | YES | — | FAILED (500) | — |
| Export Endpoints (6) | YES | NO | — | — | ALL 6 |
| Import Endpoints (5) | YES | NO | — | — | ALL 5 |
| MCP Server | YES | NO | — | V1 broken | V2 untested |
| Playwright Automation | YES | NO | — | — | UNTESTED |
| Direct DB Access | NO | NO | — | — | N/A |
| Live Test Script | YES | NO | — | — | Awaiting Brady |

**Total scripts in `Keyedin/`:** 81 Python files, 12 PowerShell scripts
**Total data extracted:** 35 MB (KeyedIn) + 184 MB (Eagle Data) + 571 KB (Benchmark)
**Total endpoints mapped:** 262 (main) + 71 Informer reports = 333

---

*Compiled from exhaustive scan of all files in `/home/user/SignX`. Search covered: all branches, all directories, all file types. Items marked [NOT IN REPO] were referenced in conversation history but never committed.*
