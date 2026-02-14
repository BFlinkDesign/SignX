# KeyedIn Legacy ERP — Recon Test Results

**Date:** 2026-02-14
**Status:** Live tests BLOCKED from cloud sandbox — executable script provided for Brady's PC
**Companion:** `LEGACY-KEYEDIN-INTEL.md` (consolidated intel), `recon-results/run_all_tests.py` (test script)

---

## Executive Summary

All five live tests against `eaglesign.keyedinsign.com` are **blocked** — this Claude Code session runs in a cloud sandbox that cannot resolve or reach Eagle Sign's internal network. DNS resolution for the hostname fails from here.

**What was completed:**
1. Full executable test script (`recon-results/run_all_tests.py`) that Brady can run from his VPN-connected PC
2. Complete data inventory of all KeyedIn exports already in the repo (25 years of work orders, 19 years of sales orders, labor data, parts, inventory, benchmarks)
3. Network test documentation with exact commands for Brady
4. Write test plan (documentation only, awaiting Brady's approval)

---

## TEST 1: Network Location

**Result:** BLOCKED — DNS fails from cloud sandbox

```
Target: eaglesign.keyedinsign.com
DNS: [Errno -3] Temporary failure in name resolution
```

**What this tells us:** The hostname either resolves only on Eagle Sign's network (ON-PREM) or this sandbox simply lacks external DNS. Previous sessions from `C:\Scripts\SignX\Keyedin` connected successfully, confirming the host IS reachable from Brady's PC.

**Brady must run:**
```powershell
nslookup eaglesign.keyedinsign.com
# If IP starts with 10., 172.16-31., or 192.168. → ON-PREM
# If public IP → HOSTED by KeyedIn/KIMCO
```

**Full results:** `recon-results/01-network-location.md`

---

## TEST 2: Direct Authentication

**Result:** BLOCKED — cannot reach host

**What we already know from previous sessions (2025-11-12):**
- Login via direct POST **worked** — `POST https://eaglesign.keyedinsign.com` with `USERNAME=BRADYF`, `PASSWORD=<pwd>`, `SECURE=TRUE`
- Server returned 5 session cookies: `SESSIONID`, `ASP.NET_SessionId`, `user`, `secure`, `IMPERSONATE`
- Session lasted ~12-24 hours before needing refresh
- 13/14 endpoints returned 200 OK with valid data using these cookies

**Open question:** Does current login use Google SSO or direct credentials? The test script (`run_all_tests.py`) will detect this automatically — if the login page redirects to `accounts.google.com`, it flags SSO.

---

## TEST 3: Export Endpoints

**Result:** BLOCKED — cannot reach host

**The 6 export endpoints to test:**

| # | Process | Description |
|---|---------|-------------|
| 1 | `CUST.PROD.EXPORT` | Sales by Customer by Product |
| 2 | `GM.BY.INV.EXPORT` | Gross Margin by Invoice |
| 3 | `SLSPER.PROD.EXPORT` | GM By Salesperson |
| 4 | `USAGE.ANAL.FILE` | Part Usage |
| 5 | `EXPORT.WO.LABOR.ANALYSIS` | WO Labor Analysis |
| 6 | `EXPORT.WIP.SUMMARY` | WIP Open or Closed Summary |

**Expected outcomes:**
- **Best case:** Returns CSV/Excel file with `Content-Disposition: attachment` header
- **Likely case:** Returns HTML form asking for date range / filter parameters, then generates export
- **Worst case:** VOC error (process not defined) — but unlikely since these came from the menu

**Why these matter:** If they return downloadable files, they're the safest, vendor-supported data extraction path.

---

## TEST 4: Informer BI Access

**Result:** BLOCKED — cannot reach port 8443

**What we already know from previous sessions:**
- Informer portal runs on port 8443 at `eaglesign.keyedinsign.com:8443/eaglesign/informer/`
- Authentication requires SSO token from main app: `sso?u=BRADYF&t={token}`
- GWT-RPC API at `ViewRPCService` endpoint works — returned `//OK` responses
- **71 reports discovered** including Quote Status, Sales Orders, Work Orders, etc.
- **0 data rows extracted** — GWT-RPC response parsing incomplete

---

## TEST 5: Quote Entry Read

**Result:** BLOCKED — cannot reach host

**What we already know:**
- `EST.QUOTE.ENTRY` — main quote entry screen (HTML form)
- `QUOTE.ENTRY.DETAILS?QUOTENO={#}&DEPTNO={code}` — quote detail view
- Fields: ITEM_TYPE (L/P/D), ITEM_NO, QTY, COST, MARKUP
- Gray fields turn white after ITEM_TYPE selection
- Report Option='D' + Send To='P' for full detail print

**The test script will:**
1. GET `EST.QUOTE.ENTRY` — capture the form structure and all field names
2. GET `QUOTE.ENTRY.DETAILS?QUOTENO=<number>` — capture actual data values
3. GET `EST.QUOTE.STATUS` — capture the full quote listing
4. Parse and document every form field, input, select, hidden value

---

## TEST 6: Write Test Plan

**Status:** PLAN DOCUMENTED — awaiting Brady's approval

**Proposed approach:**
1. Brady creates a dedicated test quote in KeyedIn (e.g., "TEST-AUTOMATION-001")
2. GET the form to capture hidden fields (CSRF, session tokens)
3. POST form data mimicking what the browser sends (same fields, same format)
4. Verify the line item was added by re-reading the quote
5. Delete/undo the test line item

**Will NOT execute** without Brady's explicit go-ahead on a specific test quote number.

---

## Data Already Extracted — Complete Inventory

These files already exist in the repo from previous extraction sessions. This IS Eagle Sign's data warehouse.

### KeyedIn Direct Exports (CSV)

| File | Records | Date Range | Key Fields |
|------|---------|------------|------------|
| `Keyedin/Data Exports/Closed WO 11-1-00 to 10-31-25.csv` | ~25 years | 2000-2025 | Work Order, Quote/Part, Qty, Act Material/Labor/Burden, Est Material/Labor/Burden, Var Cost, GM%, Close Date, Customer, Est/Act Hrs |
| `Eagle Data/.../Sales Order Numbers by Customer 01012006-07182025.csv` | ~19 years | 2006-2025 | Customer, PO Nbr, SO Nbr, SO Date, Invoices, Order Status, Line Status |
| `Eagle Data/.../BRADYF.WIP.SUMMARY 010106-062725.csv` | ~19 years | 2006-2025 | WIP summary data |
| `Eagle Data/.../Closed Sales Order Status by Customer.csv` | — | — | Customer, SO status, billing |
| `Eagle Data/.../Sales Summary - by Customer.csv` | — | — | Sales by customer |
| `Eagle Data/.../Purchase History.csv` | — | — | Purchasing data |
| `Eagle Data/.../Vendor Listing.csv` | — | — | All vendors |
| `Eagle Data/.../Inventory List.csv` | — | — | Part Nbr, Description, Inv Type, Sales Code, Qty On Hand, List Price, Acctg Cost |

### Reference Data (Lookup Tables)

| File | Content | Records |
|------|---------|---------|
| `Eagle Data/.../SIGN_TYPE_CODES.csv` | 39 sign type codes (ADA, ALULIT, CLLIT, POLLIT, etc.) | 39 |
| `Eagle Data/.../Work Codes and Pricing.csv` | Work codes with descriptions and departments | 50+ |
| `Eagle Data/.../Work Codes.csv` | Same structure, possibly different vintage | 50+ |
| `Eagle Data/.../Inventory Types Code.csv` | Inventory classification codes | — |
| `Eagle Data/.../Cleaned_Parts_Listing_072524.csv` | Cleaned parts master | — |
| `Eagle Data/.../Parts Listing RAW 072524.csv` | Raw parts listing | — |
| `Eagle Data/.../BRADYF_STOCK.STATUS.csv` | Stock status | — |

### Employee Labor Data

| File | Content | Date Range |
|------|---------|------------|
| `EMPLOYEE_HOURS_BY_WORK_CODE 01012006_05092025.csv` | All employees, all work codes, hours matrix | 2006-2025 |
| `Brady Flink/BRADYF_EMP.HOURS.BY.DATE 12.1.11 - 2.27.25.csv` | Brady's hours by date | 2011-2025 |
| `Brian Fontaine/BRIANF_EMP.HOURS.BY.DATE Start - 2.27.25.csv` | Brian's hours | Start-2025 |
| `John Redig/JOHNR_EMP.HOURS.BY.DATE 12.1.11 - 2.27.25.csv` | John's hours | 2011-2025 |
| `Matt Reis/MATTREIS_EMP.HOURS.BY.DATE.1.1.11 - 2.27.25.csv` | Matt's hours | 2011-2025 |

### Sales/GM Analysis

| File | Content |
|------|---------|
| `GM by Salesperson/BRADYF_GM_SALESPERSON 11-1-05 to 10-31-25.CSV` | 20 years of GM data |
| `GM by Salesperson/BRADYF_GM_SALESPERSON 2018.CSV` | 2018 GM |
| `GM by Salesperson/BRADYF_GM_SALESPERSON 2024.CSV` | 2024 GM |
| `GM by Salesperson/BRADYF_GM_SALESPERSON 2025.CSV` | 2025 GM |
| `Sales Summary - by Product Type.csv` | Sales by product type |

### Benchmark Data (Cost History & Analysis)

The `Benchmark/` directory contains extensive cost analysis data for Eagle Sign's standard products:

| Product | Data Available |
|---------|---------------|
| 209-0385 5x20 Replacement Faces | Cost history, cost summary PDFs, analysis |
| 210-0180 Guaranteed Faces | Cost history, analysis |
| 210-0190 Instruction Faces | Cost history, cost summary |
| 221-0190 Intercom Sign | 5 groups, cost history, combined analysis |
| 221-0200 Standard 5x20 Sign | 6 groups, cost history, combined analysis |
| 221-0210 High Wind 5x20 Sign | Cost history, analysis |
| 221-0220 Hurricane 5x20 Sign | Cost history, QTY by year |
| 221-0300 Standard Poles | 4 groups, cost history, combined summary |
| 221-0320 High Wind Poles | Cost history |
| 221-0330 Hurricane Poles | Cost history |
| 307-0267 5x20 NRG LED Conversion Kits | Cost history, audit, detailed CSV |
| 307-0268 Intercom Sign NRG LED Kit | Cost history, analysis |
| Bottom C Cover | Work orders back to 2018, proposals, analysis |

### KeyedIn System Discovery Data

| File | Content |
|------|---------|
| `Keyedin/WEB.MENU.json` | Complete 262-endpoint menu structure |
| `Keyedin/endpoint_map.json` | Categorized endpoints |
| `Keyedin/complete_endpoint_map.json` | Full flat endpoint list |
| `Keyedin/keyedin_session.json` | 5 session cookies (expired) |
| `Keyedin/keyedin_chrome_session_network.json` | 8 network requests captured |
| `Keyedin/informer_portal_urls.json` | Informer SSO URL pattern |
| `Keyedin/GWT.../extraction_summary.txt` | 71 Informer reports discovered |
| `Keyedin/GWT.../keyedin_session.json` | Informer JSESSIONID + authToken + clientId |
| `Keyedin/GWT.../eaglesign.keyedinsign.com.har` | Full HAR network capture |
| 10+ HTML page captures | Login pages, menus, work orders, service calls |

---

## Work Department Structure (from Work Codes)

| Dept Code | Department | Work Codes |
|-----------|-----------|------------|
| 0099 | Permitting | 0098, 0099 |
| 0100 | Art/Design | 0110, 0120, 0130 |
| 0200 | Fabrication | 0200-0282 (sheet metal, structural steel, extrusions, channel letters, routing, faces, awnings, crating) |
| 0300 | Electrical | 0310-0340 (ballast wiring, neon, electrical) |
| 0400 | Paint | 0410-0430 (clean/etch, prime/finish, spray faces) |
| 0500 | Vinyl/Graphics | 0510-0550 (layout, cut/weed, printed graphics, application) |
| 0600 | Installation | 0605-0650 (footing, load/unload, install, wiring, travel, removal, crew sizes) |
| 0700 | Service | 0710-0720 (load/unload, service) |
| 0800 | Delivery | 0621, 0810-0830 |
| 5200 | Shop Maintenance | 5200 |
| 5300 | Estimating | 5300 |

---

## How to Run the Tests

### From Brady's PC (VPN connected)

```powershell
# Option 1: Pull the test script from git
cd C:\Scripts\SignX
git pull origin claude/keyedin-integration-recon-sd8Ug
python recon-results/run_all_tests.py --username BRADYF

# Option 2: With a specific quote number for the read test
python recon-results/run_all_tests.py --username BRADYF --quote 39430

# It will:
# 1. Resolve DNS and determine on-prem vs hosted
# 2. Attempt direct login and capture session cookies
# 3. Test all 6 export endpoints
# 4. Probe the Informer BI portal
# 5. Read the quote entry form structure
# 6. Save the write test plan
# All results go to recon-results/test_output/
```

### Quick Manual DNS Check (5 seconds)

```powershell
nslookup eaglesign.keyedinsign.com
# Private IP (10.x, 172.16-31.x, 192.168.x) = ON-PREM
# Public IP = HOSTED
```

---

## Next Steps — Ranked by Priority

### 1. Brady Runs Test Script (15 minutes)

The single most valuable thing right now. All 5 tests in one shot. Run `run_all_tests.py` and share the `test_output/` folder.

### 2. If Auth Works: Test Export Endpoints Manually (10 minutes)

Log into KeyedIn normally, navigate to each of the 6 EXPORT endpoints from the menu. Do they produce files? What format?

### 3. If On-Prem: Ask IT About Database Access (1 conversation)

If the DNS resolves to a private IP, the server is at Eagle Sign. Ask IT:
- "What server runs our KeyedIn system?"
- "Can I get read-only database access for reporting?"
- "Is it a MultiValue/Pick database or SQL Server?"

### 4. If Auth Works: Build Quote Parser (2-4 hours, developer)

Parse the HTML returned by `QUOTE.ENTRY.DETAILS` and `EST.QUOTE.ENTRY` to extract structured data.

### 5. Contact KIMCO About Migration (1 email)

"We're evaluating our upgrade path. What API access comes with the new KIMCO platform? Timeline and pricing?"

---

*Generated 2026-02-14. Live tests blocked from cloud sandbox. All data inventory from existing repo content.*
