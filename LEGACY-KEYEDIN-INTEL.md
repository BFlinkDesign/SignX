# Legacy KeyedIn Intel — Consolidated Discovery Document

**Compiled:** 2026-02-14
**Sources:** All branches, scripts, docs, HTML captures, JSON data, and session logs in this repo
**Purpose:** Single source of truth for everything known about Eagle Sign's legacy KeyedIn ERP

---

## Table of Contents

1. [System Identity](#1-system-identity)
2. [Server Infrastructure](#2-server-infrastructure)
3. [Architecture & Technology Stack](#3-architecture--technology-stack)
4. [Authentication & Session Management](#4-authentication--session-management)
5. [URL Patterns & Endpoint Map](#5-url-patterns--endpoint-map)
6. [Informer BI Portal (Port 8443)](#6-informer-bi-portal-port-8443)
7. [Data Model — Entities & Fields](#7-data-model--entities--fields)
8. [What Worked](#8-what-worked)
9. [What Failed & Why](#9-what-failed--why)
10. [Extracted Data Inventory](#10-extracted-data-inventory)
11. [Integration Vectors — Status](#11-integration-vectors--status)
12. [Scripts & Tools Inventory](#12-scripts--tools-inventory)
13. [Gaps & Unknowns](#13-gaps--unknowns)

---

## 1. System Identity

| Field | Value | Source |
|-------|-------|--------|
| **Product** | KeyedIn Sign v2.1 | Error messages: `KeyedInSign v2.1` |
| **MVI Version** | 3.0 | Error messages: `MVI Version: 3.0` |
| **Tenant ID** | `eaglesign` | URL path component |
| **Primary User** | `BRADYF` (Brady F.) | Cookie data, menu requests |
| **Local Script Path** | `C:\Scripts\SignX\Keyedin\` | `SAVE_LOCATIONS.md`, `verify_setup.py` |

### Product Lineage

```
DataSIGN (2006) → KeyedIn Sign → KIMCO ERP (2023+)
```

- DataSIGN was the original sign-industry ERP, founded 2006
- Rebranded as "KeyedIn Sign" under KeyedIn Solutions (founded 2011, Minneapolis)
- In 2023, KeyedIn PPM merged into Sciforma; the manufacturing/sign ERP was carved out as **KIMCO, LLC**
- Eagle Sign's instance is the **legacy KeyedIn Sign v2.1** — NOT the newer KIMCO/.NET/Azure platform
- KIMCO is the upgrade path (new stack: .NET 5, C#, Azure SQL, Azure cloud)

**CRITICAL DISTINCTION:** The legacy system (what Eagle Sign currently runs) and the new KIMCO platform are completely different technology stacks. The legacy system is CGI/MVI/MultiValue-based. KIMCO is .NET/Azure/SQL.

---

## 2. Server Infrastructure

### Confirmed URLs & Ports

| URL | Port | Purpose | Protocol |
|-----|------|---------|----------|
| `eaglesign.keyedinsign.com` | 80/443 | **Main ERP application** (CGI/MVI) | HTTP/HTTPS |
| `eaglesign.keyedinsign.com` | **8443** | **Informer BI Portal** (GWT/RPC) | HTTPS |

### Hosting

| Question | Answer | Confidence |
|----------|--------|------------|
| On-prem or cloud? | **[UNKNOWN — NEEDS ON-SITE CHECK]** | — |
| Server OS | **[UNKNOWN — NEEDS ON-SITE CHECK]** | — |
| Database engine | Likely **MultiValue/Pick** (UniVerse, UniData, jBASE, or D3) based on `mvi.exe` and VOC file references | HIGH |
| Is there a local SQL Server? | Mentioned in extraction docs as a possibility but **not confirmed** — SQL access score was 2/10 | LOW |
| Can Eagle Sign access the server directly? | **[UNKNOWN — NEEDS ON-SITE CHECK]** | — |

### Key Evidence for MultiValue/Pick Database

1. **`mvi.exe`** in all CGI paths = **MultiValue Interface** — the standard web gateway for Pick/MultiValue databases
2. **`VOC file`** referenced in error messages: `"WO.COST.DETAIL is not defined in the VOC file."` — VOC (Vocabulary) is a fundamental Pick/MultiValue concept
3. **ALLCAPS.DOT.SEPARATED naming** for all processes (e.g., `WO.COST.SUMMARY`, `QUOTE.ENTRY.DETAILS`) — standard Pick naming convention
4. **`LOGIN.START`** process name — Pick-style naming
5. **Session cookie named `SESSIONID`** alongside `ASP.NET_SessionId` — suggests MVI runs on IIS with ASP.NET hosting the MultiValue CGI gateway

---

## 3. Architecture & Technology Stack

### Confirmed Architecture

```
Browser (Chrome)
    │
    ├── Port 80/443 ──→ IIS / ASP.NET ──→ mvi.exe (CGI) ──→ MultiValue DB
    │                   (web server)       (MV Interface)     (Pick-based)
    │
    └── Port 8443 ───→ Informer BI ──→ GWT RPC Service ──→ Same DB (via SSO)
                       (Java/Tomcat?)    (ViewRPCService)
```

### Layer Details

| Layer | Technology | Evidence |
|-------|-----------|----------|
| **Web Server** | IIS + ASP.NET | `ASP.NET_SessionId` cookie |
| **CGI Gateway** | `mvi.exe` v3.0 (MultiValue Interface) | All endpoint URLs use `/cgi-bin/mvi.exe/` |
| **Database** | MultiValue/Pick (specific engine unknown) | VOC file errors, naming conventions |
| **BI/Reporting** | Entrinsik Informer 5.x | GWT RPC class names: `com.entrinsik.informer.*` |
| **BI Frontend** | Google Web Toolkit (GWT) | GWT RPC payload format, `ViewRPCService` |
| **BI Transport** | GWT-RPC (text/x-gwt-rpc) | Captured request payloads |
| **Auth (BI)** | SSO token from main app | `sso?u=BRADYF&t={token}` URL pattern |

### Informer BI Stack (Port 8443)

Entrinsik Informer is a Java-based BI/reporting platform that connects to various data sources. For KeyedIn Sign, it connects to the same MultiValue database and provides:
- Pre-built reports (71 discovered)
- GWT-based web UI
- RPC API via `ViewRPCService`
- SSO integration with the main KeyedIn app

---

## 4. Authentication & Session Management

### Main Application (Port 80/443)

**Login Flow (confirmed and tested):**

```
1. GET  /cgi-bin/mvi.exe/LOGIN.START   → Redirects to base URL
2. GET  https://eaglesign.keyedinsign.com   → Returns login form HTML
3. POST https://eaglesign.keyedinsign.com   → Form data: USERNAME, PASSWORD, SECURE
4. Server sets cookies: SESSIONID, user, secure, ASP.NET_SessionId, IMPERSONATE
5. All subsequent requests use SESSIONID cookie
```

**Note on Google SSO:** The task description mentions Google SSO with a green "Sign In" button. However, the actual login flow documented in the codebase uses **direct username/password form submission** — NOT Google OAuth. The Google SSO reference may apply to the newer KIMCO system, or may be a separate portal.

**[NEEDS ON-SITE CHECK]:** Confirm whether the current login uses Google SSO or direct credentials.

### Session Cookies (5 cookies captured)

| Cookie | Value Example | HttpOnly | Expiry |
|--------|--------------|----------|--------|
| `SESSIONID` | `ry3ksqkgsxoisflzwrqm1den` | No | ~24 hours |
| `ASP.NET_SessionId` | Same as SESSIONID | Yes | Session |
| `user` | `BRADYF` | No | ~12 hours |
| `secure` | `TRUE` | No | ~12 hours |
| `IMPERSONATE` | (empty) | No | Session |

### Informer BI Portal (Port 8443)

**Authentication uses SSO from main app:**

```
URL: https://eaglesign.keyedinsign.com:8443/eaglesign/sso?u=BRADYF&t={SSO_TOKEN}&initialAction.action=ReportRun&remoteId={REPORT_ID}
```

**Informer session requires:**
- `JSESSIONID` cookie (Java session, e.g., `16zigc7ehs9816ham55pq7opc`)
- `authToken` (UUID, e.g., `a84254d8-0ad1-4951-beae-fcab814cdce7`)
- `clientId` (UUID, e.g., `7a91a9ef-aa03-46d2-93ee-f3afcc65cfe3`)

### Session Extraction Methods (all tested)

1. **Chrome CDP Extractor** (`keyedin_cdp_extractor.py`): Opens Chrome with remote debugging, user logs in manually, script captures cookies via Chrome DevTools Protocol
2. **Selenium Cookie Extractor** (`extract_cookies_chrome.py`): Uses Selenium WebDriver + ChromeDriver
3. **Manual Token Capture** (`MASTER_EXTRACTOR.ps1`): User opens Chrome DevTools Network tab, copies authToken/clientId/JSESSIONID manually

---

## 5. URL Patterns & Endpoint Map

### URL Structure

All main application endpoints follow this pattern:
```
/cgi-bin/mvi.exe/{PROCESS_NAME}[?PARAM1=value&PARAM2=value]
```

Where `{PROCESS_NAME}` is an ALL-CAPS.DOT.SEPARATED identifier that maps to a Pick/MultiValue program.

### Complete Menu Structure (262 endpoints mapped)

Captured from `/cgi-bin/mvi.exe/WEB.MENU?USERNAME=BRADYF` — returns JSON.

**Top-Level Modules:**

| Module | Menu ID | Key Processes |
|--------|---------|--------------|
| **Favorites** | `FAVORITES.STD` | User's bookmarked items |
| **CRM** | `CRM.STD` | `CRM.CONTACT.MGT`, `CHANGE.SC.ACCOUNT`, service calls |
| **Project Management** | `PROJECT.STD` | `#PROJECT.LISTING`, `#PROJECT.DETAILS`, milestones, quotes, WOs |
| **Estimating & Proposals** | `EST.STD` | `EST.QUOTE.ENTRY`, `QUOTE.ENTRY.LIMITED`, proposals, templates |
| **Sales Order Entry** | `SALES.STD` | `ORDER.ENTRY`, `EST.CREATE.SO`, `SO.PRINT` |
| **Shipping Tracking** | `SHIPPING.STD` | `SHIPLISTS`, `SHIPMENTS`, `SHIPMENTS.TRACKING` |
| **Sales Analysis** | `SA.STD` | GM reports, sales by product/customer/territory |
| **Purchasing** | `PUR.STD` | `PURCHASE`, `PO.RECEIPTS`, `PO.CLOSE`, vendor master |
| **Inventory & Parts** | `INV.STD` | `FIRST.ISSUE`, parts maintenance, BOM, routing |
| **Job Cost** | `JCOST.*` | `WO.HISTORY`, `WO.STATUS.SUM`, `SO.CONTRACT` (cost summary) |
| **MRP** | `MRP.*` | `PARTS.MRP`, `MRP.CALC`, planned orders |
| **Production (SFC)** | `PRODUCTION.STD` | `WO.PRINT`, `WO.INQUIRY`, `WO.CHANGE`, routing |
| **Resource Scheduling** | `RSC.STD` | `RESOURCE.LIST`, `RESOURCE.INQUIRY` |
| **Labor & Payroll** | `PAY.*` | Employee hours by work code/date/pay period |
| **Accounts Payable** | `AP.*` | Vendor master, invoice listing |
| **Accounts Receivable** | `AR.*` | Customer master, bill-to, ship-to |
| **Report Administration** | `RPT.STD` | `REPORT.VIEW.INDEX`, archived forms |
| **Administration** | `ADMIN.STD` | Password change, clear locks, logoff, profile |
| **System Management** | `SYS.*` | Buyer codes, import tools |

### Key Estimating/Quoting Endpoints

| Process | Purpose | Known Parameters |
|---------|---------|-----------------|
| `EST.QUOTE.ENTRY` | Main estimating maintenance | — |
| `QUOTE.ENTRY.LIMITED` | Limited estimating maintenance | — |
| `QUOTE.ENTRY.DETAILS` | Quote detail view | `QUOTENO={#}`, `DEPTNO={code}` |
| `EST.QUOTE.PRINT` | Print an estimate/quote | — |
| `EST.QUOTE.COPY` | Copy an estimate | — |
| `EST.QUOTE.STATUS` | Status of all quotes (BI) | — |
| `QUOTE.PIPELINE.REPORT` | Quote pipeline | — |
| `EST.SIGN.TEMPLATE.MAINT` | Sign template maintenance | — |
| `QUOTE.MASS.UPDATE` | Bulk update quotes | — |
| `QUOTE.MASS.COPY` | Bulk copy quotes | — |
| `EST.PROP.PRINT` | Create a proposal | — |

### Known Quote Entry Fields

From the task description:
- `ITEM_TYPE`: L=Labor, P=Part, D=Direct Purchase
- `ITEM_NO`: Item number
- `QTY`: Quantity
- `COST`: Cost value
- `MARKUP`: Markup percentage
- Report Option `'D'` + Send To `'P'` = full detail print output
- Gray fields turn white after type selection (dynamic form behavior)

### Tested & Working Endpoints

| Endpoint | Status | Response Size | Notes |
|----------|--------|---------------|-------|
| `/cgi-bin/mvi.exe/WEB.MENU?USERNAME=BRADYF` | 200 OK | 33,981 bytes | Returns full JSON menu |
| `/cgi-bin/mvi.exe/WO.INQUIRY` | 200 OK | 1,213 bytes | HTML form |
| `/cgi-bin/mvi.exe/WO.HISTORY` | 200 OK | 5,255 bytes | HTML with 4 tables |
| `/cgi-bin/mvi.exe/WO.COST.SUMMARY` | 200 OK | 466 bytes | HTML |
| `/cgi-bin/mvi.exe/SERVICE.CALL.LIST` | 200 OK | 357 bytes | HTML with 2 tables |
| `/cgi-bin/mvi.exe/WIDGET.ASSIGNED.SERVICE.CALLS?ACTION=AJAX` | 200 OK | — | AJAX/JSON |
| `/cgi-bin/mvi.exe/WIDGET.ASSIGNED.MILESTONES?ACTION=AJAX` | 200 OK | — | AJAX/JSON |
| `/cgi-bin/mvi.exe/WIDGET.CRM.TASKS?ACTION=AJAX` | 200 OK | — | AJAX/JSON |
| `/cgi-bin/mvi.exe/WIDGET.FYI?ACTION=AJAX` | 200 OK | — | AJAX/JSON |
| `/cgi-bin/mvi.exe/MAIN` | 200 OK | — | Main page |
| `/cgi-bin/mvi.exe/HOME` | 200 OK | — | Home page |
| `/cgi-bin/mvi.exe/WO.COMPLETION.INQUIRY` | 200 OK | — | HTML |
| `/cgi-bin/mvi.exe/WO.GROUP.ANALYSIS` | 200 OK | — | HTML with 5 tables |
| `/cgi-bin/mvi.exe/WORKORDER.LIST` | 200 OK | — | HTML with 2 tables |

**Success rate: 13/14 endpoints (93%)**

### Failed Endpoints

| Endpoint | Error | Details |
|----------|-------|---------|
| `/cgi-bin/mvi.exe/WO.COST.DETAIL` | Error 2002 | `"WO.COST.DETAIL is not defined in the VOC file."` — This process doesn't exist |

---

## 6. Informer BI Portal (Port 8443)

### Architecture

The Informer portal runs on port 8443 and uses **Entrinsik Informer** — a Java-based BI platform with a **Google Web Toolkit (GWT)** frontend.

### GWT RPC API

**Endpoint:**
```
POST https://eaglesign.keyedinsign.com:8443/eaglesign/informer/rpc/protected/ViewRPCService?authToken={TOKEN}&clientId={CLIENT_ID}
```

**Headers:**
```
Content-Type: text/x-gwt-rpc; charset=UTF-8
Cookie: JSESSIONID={SESSION_ID}
```

**GWT RPC Payload Structure (captured):**
```
7|0|22|https://eaglesign.keyedinsign.com:8443/eaglesign/informer/|
327E0F303D0CA463050DC31340CFE01D|
com.entrinsik.informer.core.client.service.ViewRPCService|
getData|
[Lcom.entrinsik.gwt.data.shared.ViewToken;/2990910562|
[Lcom.entrinsik.gwt.data.shared.LoadOptions;/2486573562|
com.entrinsik.gwt.data.shared.ViewToken/3777265110|
...
```

**Key GWT Classes:**
- `com.entrinsik.informer.core.client.service.ViewRPCService` — Main RPC service
- `com.entrinsik.gwt.data.shared.ViewToken` — Report/view identifier
- `com.entrinsik.gwt.data.shared.LoadOptions` — Pagination, filtering
- `com.entrinsik.gwt.data.shared.criteria.impl.JunctionImpl` — Query criteria
- `com.entrinsik.informer.core.domain.report.ReportSearchOptions` — Report search

**Successful GWT-RPC Response:** Starts with `//OK[...` when successful.

### Discovered Reports (71 reports via Informer)

| # | Report Name | Category |
|---|------------|----------|
| 1 | AR Invoice Details | Accounts Receivable |
| 2 | AR Invoice Listing | Accounts Receivable |
| 3 | AR Open Invoices | Accounts Receivable |
| 4 | Cash Receipts | Accounts Receivable |
| 5 | Customer Listing | Customers |
| 6 | Customer Listing (Export) | Customers |
| 7 | Customer Location Listing | Customers |
| 8 | Customer Location Listing (Export) | Customers |
| 9 | Customer Portal | Customers |
| 10 | Inventory List | Inventory |
| 11 | Inventory List (Export) | Inventory |
| 12 | Inventory Transaction History | Inventory |
| 13 | Invoice Register | Invoicing |
| 14 | Open Sales Order Backlog | Sales Orders |
| 15 | Open Sales Orders | Sales Orders |
| 16 | Open Work Orders | Production |
| 17 | Planned Part Activity | MRP |
| 18 | Purchase History | Purchasing |
| 19 | Purchase Order Detail | Purchasing |
| 20 | Purchased Part Variance | Purchasing |
| 21 | Quote Status Report | Estimating |
| 22 | Sales Cost Detail Report | Sales Analysis |
| 23 | Sales Order Bookings - By Order Line Date | Sales Orders |
| 24 | Sales Order Bookings - By Sales Order Date | Sales Orders |
| 25 | Sales Order Detail | Sales Orders |
| 26 | Sales Order Status by Customer | Sales Orders |
| ... | *(71 total — see `Keyedin/GWT Google Web Toolkit/keyedin_extraction_20251112_162438/extraction_summary.txt`)* | Various |

### Informer Extraction Status

- **Report catalog discovery:** SUCCESSFUL (71 reports found)
- **Authentication with Informer:** SUCCESSFUL
- **GWT-RPC API calls:** SUCCESSFUL (returned `//OK` responses)
- **Actual data extraction from reports:** NOT COMPLETED — requires building `getData` payloads for each specific report and parsing GWT-RPC response format

---

## 7. Data Model — Entities & Fields

### Entities Identified from Menu & Endpoints

| Entity | Key Processes | Likely DB Files (Pick) |
|--------|--------------|----------------------|
| **Quotes/Estimates** | `EST.QUOTE.ENTRY`, `QUOTE.ENTRY.DETAILS` | QUOTES, EST.DETAILS |
| **Proposals** | `EST.PROP.PRINT`, `EST.PROP.REPRINT` | PROPOSALS |
| **Sign Templates** | `EST.SIGN.TEMPLATE.MAINT` | SIGN.TEMPLATES |
| **Sales Orders** | `ORDER.ENTRY`, `LOOK.SO` | SALES.ORDERS |
| **Work Orders** | `WO.INQUIRY`, `WO.PRINT`, `WO.CHANGE` | WORK.ORDERS |
| **Purchase Orders** | `PURCHASE`, `PO.RECEIPTS` | PURCHASE.ORDERS |
| **Customers** | `CUSTOMERS`, `BILL.TO`, `SHIP.TO` | CUSTOMERS, CUSTOMER.LOCATIONS |
| **Vendors** | `VENDORS`, `VM.INQUIRY` | VENDORS |
| **Parts (Purchased)** | `RAW.MATL.MAINT` | PARTS, RAW.MATERIALS |
| **Parts (Manufactured)** | `ASSEMBLY.MAINT` | ASSEMBLIES |
| **Bill of Materials** | `BOM`, `COPY.BILL` | BOM |
| **Routings** | `ROUTING.MAINT`, `WO.ROUTING.MAINT` | ROUTINGS |
| **Inventory** | `FIRST.ISSUE`, `ISSUE`, `ADJUST` | INVENTORY |
| **Projects** | `#PROJECT.LISTING`, `#PROJECT.DETAILS` | PROJECTS |
| **CRM Contacts** | `CRM.CONTACT.MGT` | CRM.CONTACTS |
| **Service Calls** | `SERVICE.CALL.LIST`, `CHANGE.SC.ACCOUNT` | SERVICE.CALLS |
| **Employees** | `EMP.HOURS.BY.OP`, `EMP.EFF` | EMPLOYEES |
| **Shipments** | `SHIPLISTS`, `SHIPMENTS` | SHIPMENTS |
| **AP Invoices** | `LIST.AP.DET`, `AP.DETAIL` | AP.INVOICES |
| **AR Invoices** | Invoice Register report | AR.INVOICES |

### Quote Entry Detail Fields (from task description)

```
QUOTE.ENTRY.DETAILS?QUOTENO={#}&DEPTNO={code}

Fields:
  ITEM_TYPE   → L=Labor, P=Part, D=Direct Purchase
  ITEM_NO     → Item/part number
  QTY         → Quantity
  COST        → Cost per unit
  MARKUP      → Markup percentage

Behavior:
  - Gray fields turn white after ITEM_TYPE selection
  - Report Option='D' + Send To='P' → full detail print output
```

### Import Capabilities (built-in)

The menu reveals built-in import endpoints:
- `IMPORT.PARTS` — Import parts data
- `IMPORT.BOM` — Import bill of materials
- `IMPORT.ROUTING` — Import routing data
- `IMPORT.CRM.NEW` — Import CRM contacts
- `IMPORT.SIGN.TEMPLATE` — Import sign templates

**[UNKNOWN — NEEDS ON-SITE CHECK]:** What format do these importers accept? CSV? Fixed-width? What are the field mappings?

---

## 8. What Worked

### Successful Operations (confirmed in validation report 2025-11-12)

1. **Login via direct POST** — Username/password form submission works programmatically
2. **Cookie extraction via Chrome CDP** — Selenium + ChromeDriver extracts all 5 session cookies
3. **Menu structure retrieval** — `/cgi-bin/mvi.exe/WEB.MENU?USERNAME=BRADYF` returns complete JSON menu (262 endpoints)
4. **Endpoint access with session cookies** — 13/14 endpoints returned 200 OK with data
5. **HTML table parsing** — BeautifulSoup successfully extracts structured data from HTML responses
6. **Widget AJAX endpoints** — Return data in JSON-friendly format
7. **Informer GWT-RPC authentication** — Successfully authenticated and discovered 71 reports
8. **Informer report catalog discovery** — Full catalog of available BI reports retrieved
9. **Session validation** — Programmatic session health checking works
10. **Cost summary extraction** — `extract_all_cost_summaries.py` extracted cost data (with some errors)

### Performance Benchmarks

- API initialization: < 1 second
- Session validation: < 1 second
- Endpoint access: < 2 seconds per endpoint
- Cookie extraction: ~30 seconds (includes Chrome startup)
- Full 14-endpoint extraction: ~7 seconds

---

## 9. What Failed & Why

### Failed Attempt: WO.COST.DETAIL Endpoint

- **Error:** `Error Code: 2002 — "WO.COST.DETAIL is not defined in the VOC file."`
- **Why:** This process name doesn't exist in the system's VOC (Vocabulary). The correct endpoint may be `WO.STATUS.SUM` or `WO.COST.SUMMARY`.
- **Fix:** Use the correct process names from the menu structure.

### Failed Attempt: Informer Data Extraction

- **Status:** Authenticated and discovered reports, but did NOT extract actual data rows
- **Why:** Extracting data requires building specific `getData` GWT-RPC payloads for each report, and parsing the GWT-RPC serialized response format
- **What's needed:** A GWT-RPC serializer/deserializer, or intercepting the browser's own requests during report viewing

### Failed Attempt: SQL Server Direct Access

- **Extraction recommendation score:** SQL access = 2/10, Informer = 9/10
- **Why:** No SQL Server credentials found; the backend is likely MultiValue/Pick, not SQL Server
- **Status:** Ruled out unless IT provides database access information

### Failed Attempt: Previous Scraping (404 errors mentioned in task)

- **Likely cause:** Incorrect URLs — scraping may have targeted wrong paths without the `/cgi-bin/mvi.exe/` prefix
- **Fix:** All endpoints must use the full CGI path: `/cgi-bin/mvi.exe/{PROCESS_NAME}`

### Failed Attempt: Browser Automation (MCP/Claude)

- **Mentioned in task:** "Browser automation via Claude Code has failed to navigate the UI reliably"
- **Likely causes:**
  - Google SSO complication (if the newer login flow is used)
  - Dynamic form behavior (gray→white field transitions)
  - Possibly iframes or frameset-based layout
  - The MVI-based pages may use non-standard HTML patterns
- **Fix:** Use Playwright persistent context (not headless) for initial auth, then automate with careful DOM mapping

### Failed Attempt: Automated GWT-RPC Data Extraction (0 records)

- **Extraction summary:** 14 reports processed, 0 records extracted, 0MB database
- **Why:** The extraction script connected and authenticated but didn't successfully parse data rows from the GWT-RPC responses
- **What's needed:** Proper GWT-RPC response parsing or use the Informer export-to-file features instead

---

## 10. Extracted Data Inventory

### Files in Repo

| File | Content | Date |
|------|---------|------|
| `Keyedin/WEB.MENU.json` | Complete 262-endpoint menu structure | 2025-11-12 |
| `Keyedin/endpoint_map.json` | 262 endpoints categorized | 2025-11-12 |
| `Keyedin/complete_endpoint_map.json` | Full endpoint listing | 2025-11-12 |
| `Keyedin/keyedin_session.json` | Session cookies (5 cookies) | 2025-11-12 |
| `Keyedin/keyedin_chrome_session.json` | Chrome-extracted session | 2025-11-12 |
| `Keyedin/keyedin_chrome_session_network.json` | Network capture (8 requests) | 2025-11-12 |
| `Keyedin/keyedin_network_capture.json` | Network traffic capture | 2025-11-12 |
| `Keyedin/captured_all_requests.json` | All HTTP requests captured | 2025-11-12 |
| `Keyedin/extracted_data/extracted_data_20251112_180236.json` | Menu + endpoint data | 2025-11-12 |
| `Keyedin/extracted_data/menu_20251112_180236.json` | Menu structure | 2025-11-12 |
| `Keyedin/extracted_data/work_orders_20251112_180236.json` | Work order form data | 2025-11-12 |
| `Keyedin/cost_summaries/all_cost_summaries_20251112_*.json` | Cost summary attempts | 2025-11-12 |
| `Keyedin/cost_summaries/cost_summaries_20251112_*.csv` | Cost summary CSV exports | 2025-11-12 |
| `Keyedin/wo_query_results.json` | Work order query results | 2025-11-12 |
| `Keyedin/informer_portal_urls.json` | Informer SSO URLs | 2025-11-12 |
| `Keyedin/GWT Google Web Toolkit/keyedin_session.json` | Informer session (JSESSIONID, authToken, clientId) | 2025-11-12 |
| `Keyedin/GWT Google Web Toolkit/eaglesign.keyedinsign.com.har` | Full HAR capture | 2025-11-12 |
| `Keyedin/GWT Google Web Toolkit/session_cookies.json` | Informer cookies | 2025-11-12 |
| `Keyedin/GWT Google Web Toolkit/keyedin_extraction_20251112_162438/extraction_summary.txt` | 71 reports discovered | 2025-11-12 |

### HTML Page Captures

| File | Content |
|------|---------|
| `Keyedin/login_page.html` | Login form HTML |
| `Keyedin/login_start_page.html` | Login start page |
| `Keyedin/actual_login_page.html` | Actual login form |
| `Keyedin/login_success.html` | Post-login page |
| `Keyedin/logged_in_page.html` | Logged-in state |
| `Keyedin/after_login.html` | After login |
| `Keyedin/chrome_logged_in.html` | Chrome logged-in state |
| `Keyedin/MAIN.html` | Main page HTML |
| `Keyedin/WEB.MENU.html` | Menu page HTML |
| `Keyedin/WORKORDER_LIST.html` | Work order list page |
| `Keyedin/SERVICE_CALL_LIST.html` | Service call list page |
| `Keyedin/..KeyedIn_System_Map/discovery_data/html_captures/00_logged_in_home.html` | Home page after login |

### Data Exports from KeyedIn (CSVs)

| File | Content |
|------|---------|
| `Keyedin/Data Exports/Closed WO 11-1-00 to 10-31-25.csv` | 25 years of closed work orders |
| `Eagle Data/BOT TRAINING/Eagle Keyedin Files/BRADYF.WIP.SUMMARY 010106-062725.csv` | WIP summary 2006-2025 |
| `Eagle Data/BOT TRAINING/Eagle Data/Sales Order Numbers by Customer 01012006-07182025.csv` | All sales orders 2006-2025 |
| `Eagle Data/BOT TRAINING/Eagle Data/combined for llm use/Closed Sales Order Status by Customer.csv` | Closed SO by customer |
| `Eagle Data/BOT TRAINING/Eagle Data/combined for llm use/Sales Summary - by Customer.csv` | Sales summary |
| `Eagle Data/BOT TRAINING/Eagle Data/Vendor Listing.csv` | All vendors |
| `Eagle Data/BOT TRAINING/Sales/GM by Salesperson/*.CSV` | GM by salesperson reports |

---

## 11. Integration Vectors — Status

### Vector A: CGI/MVI HTTP API (Session + HTML Parsing)

| Attribute | Status |
|-----------|--------|
| **Feasibility** | **9/10 — PROVEN WORKING** |
| **Status** | Validated on 2025-11-12. 93% endpoint success rate. |
| **What works** | Login, session management, all menu endpoints, HTML table extraction |
| **What's needed** | Build parsers for specific pages (quote entry, line items) |
| **Read capability** | YES — all data accessible via HTTP GET |
| **Write capability** | LIKELY — POST with form data should work (not yet tested) |
| **Tools built** | `keyedin_api_enhanced.py`, `keyedin_cdp_extractor.py`, `extract_all_data.py` |

### Vector B: Informer GWT-RPC API (Port 8443)

| Attribute | Status |
|-----------|--------|
| **Feasibility** | **6/10 — Authentication works, data extraction incomplete** |
| **Status** | Authenticated, 71 reports discovered, 0 data rows extracted |
| **Blocker** | GWT-RPC serialization format is complex to parse |
| **What's needed** | GWT-RPC deserializer or use Informer's built-in export features |
| **Read capability** | YES (once parsing works) |
| **Write capability** | NO — Informer is read-only BI reporting |
| **Tools built** | `MASTER_EXTRACTOR.ps1`, `keyedin_complete_extraction.py`, `keyedin_enhanced_extractor.py` |

### Vector C: Built-in Informer Export

| Attribute | Status |
|-----------|--------|
| **Feasibility** | **7/10** |
| **Status** | **[UNKNOWN — NEEDS ON-SITE CHECK]** |
| **Theory** | Informer likely has CSV/Excel export buttons on reports |
| **What's needed** | Check if Brady can manually export from Informer and whether that can be automated |
| **Read capability** | YES |
| **Write capability** | NO |

### Vector D: Built-in Import Processes

| Attribute | Status |
|-----------|--------|
| **Feasibility** | **5/10** |
| **Status** | Menu reveals import endpoints exist: `IMPORT.PARTS`, `IMPORT.BOM`, `IMPORT.ROUTING`, `IMPORT.CRM.NEW`, `IMPORT.SIGN.TEMPLATE` |
| **What's needed** | Determine import file formats, field mappings, and whether they can be triggered via HTTP POST |
| **Read capability** | NO |
| **Write capability** | YES (if format is known) |

### Vector E: Browser Automation (Playwright)

| Attribute | Status |
|-----------|--------|
| **Feasibility** | **7/10** |
| **Status** | Not yet attempted with Playwright. Previous MCP attempts failed. |
| **Fix for SSO** | Use `launchPersistentContext` with `userDataDir` — manual login once, then automated |
| **Key advantage** | Can handle dynamic form behavior (gray→white field transitions) |
| **Read capability** | YES |
| **Write capability** | YES |

### Vector F: Direct Database Access (MultiValue/Pick)

| Attribute | Status |
|-----------|--------|
| **Feasibility** | **2/10** |
| **Status** | No database credentials found. Hosting model unknown. |
| **What's needed** | On-site investigation: Is the server at Eagle Sign? Can IT provide access? |
| **If on-prem** | Pick databases can be accessed via ODBC, telnet, or native tools |
| **Read capability** | YES (if accessible) |
| **Write capability** | YES (if accessible, but risky) |

### Vector G: Vendor Engagement (KIMCO/KeyedIn)

| Attribute | Status |
|-----------|--------|
| **Feasibility** | **4/10 for legacy; 8/10 for new KIMCO** |
| **Status** | Not yet attempted |
| **Legacy system** | Vendor is unlikely to add API features to the legacy product |
| **KIMCO upgrade** | New platform has "open APIs" — migration would unlock proper integration |
| **What's needed** | Contact KIMCO, ask about API access for current instance AND migration timeline |

---

## 12. Scripts & Tools Inventory

### Core API Tools

| Script | Purpose | Status |
|--------|---------|--------|
| `keyedin_api_enhanced.py` | Enhanced API client with auto-session management | WORKING |
| `keyedin_api.py` | Legacy API wrapper | WORKING (superseded) |
| `keyedin_cdp_extractor.py` | Chrome CDP cookie extractor | WORKING |
| `extract_cookies_chrome.py` | Selenium cookie extractor | WORKING |
| `extract_with_credentials.py` | Credential-based extraction | WORKING |

### Data Extraction Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `extract_all_data.py` | Extract all endpoint data | WORKING |
| `extract_all_cost_summaries.py` | Extract cost summaries | PARTIAL (some endpoints don't exist) |
| `extract_all_cost_summaries_complete.py` | Complete cost summary extraction | PARTIAL |
| `extract_all_detailed_cost_summaries.py` | Detailed cost summaries | PARTIAL |
| `extract_everything_complete.py` | Full extraction attempt | PARTIAL |
| `map_all_endpoints.py` | Map all menu endpoints | WORKING |
| `parse_har.py` | Parse HAR files | WORKING |

### GWT/Informer Tools

| Script | Purpose | Status |
|--------|---------|--------|
| `MASTER_EXTRACTOR.ps1` | PowerShell automated Informer extraction | PARTIAL |
| `keyedin_complete_extraction.py` | Python Informer extraction | PARTIAL (auth works, data parsing not) |
| `keyedin_enhanced_extractor.py` | Enhanced Informer extractor | PARTIAL |
| `keyedin_working_extractor.py` | Working Informer variant | PARTIAL |
| `keyedin_sql_extraction.py` | SQL Server extraction (if available) | UNTESTED |
| `keyedin_data_extractor.py` | General data extractor | PARTIAL |
| `auto_capture_har.py` | Automated HAR capture | WORKING |
| `capture_informer_api.py` | Informer API capture | PARTIAL |

### Test & Validation Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `comprehensive_test.py` | Full validation suite (9/9 tests pass) | WORKING |
| `test_enhanced_api.py` | Enhanced API tests | WORKING |
| `test_api_with_cookies.py` | Cookie-based API tests | WORKING |
| `verify_setup.py` | Setup verification | WORKING |
| `final_validation.py` | Final validation | WORKING |

### Investigation Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `investigate_login_flow.py` | Login flow analysis | COMPLETED |
| `investigate_login.py` | Login investigation | COMPLETED |
| `find_actual_login.py` | Find login page | COMPLETED |
| `analyze_pages.py` | Page analysis | COMPLETED |
| `analyze_wo_inquiry_form.py` | WO inquiry form analysis | COMPLETED |
| `explore_menu.py` | Menu exploration | COMPLETED |
| `debug_form.py` | Form debugging | COMPLETED |

### MCP Server Attempts

| Script | Purpose | Status |
|--------|---------|--------|
| `KEYEDIN MCP/keyedin_mcp_server_secure.py` | MCP server for Claude | BUILT (not validated in production) |
| `KEYEDIN MCP/v1/Broke V1 (CLAUDE 4)/keyedin_mcp_server.py` | V1 MCP server (broken) | FAILED |
| `KEYEDIN MCP/v1/Broke V1 (CLAUDE 4)/keyedin_resilient_agent.py` | Resilient agent | FAILED |
| `KEYEDIN MCP/discovery/keyedin_architecture_mapper.py` | Architecture discovery tool | BUILT |
| `KEYEDIN MCP/Test/keyedin_investigator_v5.py` | Investigation tool | BUILT |
| `KEYEDIN MCP/Test/keyedin_manual_login_mapper.py` | Manual login mapper | BUILT |

---

## 13. Gaps & Unknowns

### Critical Unknowns

| Question | Why It Matters | How to Resolve |
|----------|---------------|----------------|
| **Is the server on-prem or hosted?** | If on-prem, direct DB access may be possible | [NEEDS ON-SITE CHECK] — ask IT |
| **What specific MultiValue/Pick engine?** | Determines ODBC drivers, API options | [NEEDS ON-SITE CHECK] — check server, or look for UniVerse/UniData/jBASE/D3 processes |
| **Does Eagle Sign use Google SSO or direct login?** | Determines automation approach | [NEEDS ON-SITE CHECK] — load the login page and document |
| **What format do the IMPORT.* endpoints accept?** | Enables programmatic data write | [NEEDS ON-SITE CHECK] — try each import screen, document the file format requirements |
| **Does the Informer portal have CSV/Excel export buttons?** | Enables easy bulk data extraction | [NEEDS ON-SITE CHECK] — open any BI report, check for export options |
| **Is KIMCO migration planned? Timeline?** | Determines whether to invest in legacy integration | Ask KIMCO sales team |
| **What write operations work via POST?** | Enables automation of quote entry | [NEEDS TESTING] — attempt POST to `EST.QUOTE.ENTRY` with form data |
| **Does `QUOTE.ENTRY.DETAILS` accept query params for read?** | Enables direct quote data retrieval | [NEEDS TESTING] — try GET with QUOTENO param |
| **What BI reports have "Export" versions?** | Some reports explicitly have "(Export)" variants designed for CSV output | Several found: `CUST.PROD.EXPORT`, `GM.BY.INV.EXPORT`, `SLSPER.PROD.EXPORT`, `USAGE.ANAL.FILE`, `EXPORT.WO.LABOR.ANALYSIS`, `EXPORT.WIP.SUMMARY` |
| **What is the `#` prefix on project process names?** | `#PROJECT.LISTING`, `#PROJECT.DETAILS` etc. may indicate a different routing | [NEEDS TESTING] — try with and without `#` |

### Data Model Unknowns

| Unknown | How to Resolve |
|---------|----------------|
| Quote-to-Sales Order relationship fields | Parse `EST.CREATE.SO` page HTML |
| Quote line item field names and validation rules | Inspect `QUOTE.ENTRY.DETAILS` page DOM |
| Work order cost breakdown structure | Parse `WO.STATUS.SUM`, `WO.STATUS.MATL`, `WO.STATUS.LABR` |
| Customer/project/quote linking keys | Inspect CRM and project management pages |
| File attachment storage mechanism | Check if BLOBs in DB or file system |

---

## Appendix A: Known SSO Token Format

From `informer_portal_urls.json`:
```
HTTPS://EAGLESIGN.KEYEDINSIGN.COM:8443/eaglesign/sso
  ?u=BRADYF
  &t=4vjbm1rhvjfqw2c3vtmpxcqs     ← SSO token (lowercase alphanum, 25 chars)
  &initialAction.action=ReportRun
  &remoteId=7831576                 ← Report ID (numeric)
```

## Appendix B: Export-Ready Endpoints

These process names contain "EXPORT" and are likely designed to produce CSV/Excel output:

1. `CUST.PROD.EXPORT` — Sales by Customer by Product - Export
2. `GM.BY.INV.EXPORT` — Gross Margin by Invoice Export
3. `SLSPER.PROD.EXPORT` — GM By Salesperson - Export
4. `USAGE.ANAL.FILE` — Part Usage Export
5. `EXPORT.WO.LABOR.ANALYSIS` — WO Labor Analysis Export
6. `EXPORT.WIP.SUMMARY` — WIP Open or Closed Summary Export

**These are the lowest-risk data extraction paths — they're built-in export features.**

## Appendix C: Recommended Priority Actions

### Immediate (Brady, 30 minutes)

1. Open `eaglesign.keyedinsign.com` and confirm: is login Google SSO or username/password?
2. Navigate to any `(BI)` report and check for export/download buttons
3. Try the 6 EXPORT endpoints listed above — do they produce downloadable files?
4. Ask IT: "Is the KeyedIn server at our office or hosted remotely?"

### Short-Term (Developer, 1-2 days)

1. Build HTML parsers for `QUOTE.ENTRY.DETAILS` page
2. Test POST operations to `EST.QUOTE.ENTRY` with form data
3. Capture full HAR of a quote creation workflow
4. Set up Playwright persistent context for reliable automation

### Medium-Term (Developer, 1-2 weeks)

1. Build full read/write Python client for quote management
2. Integrate with APEX estimation pipeline
3. If KIMCO migration is planned, pivot to KIMCO API integration instead

---

*Compiled from 206 files across all branches. No new research performed. All findings from existing repo content.*
