# PROJECT STATE — KeyedIn Export Endpoint Testing

**Generated:** 2026-02-14T17:00
**Branch:** `claude/keyedin-integration-recon-sd8Ug`
**Status:** BLOCKED — cloud sandbox cannot reach `eaglesign.keyedinsign.com`
**Next:** Run from Brady's VPN-connected PC

---

## What's Done

| Deliverable | Status | File |
|-------------|--------|------|
| Initial recon (KIMCO research) | COMPLETE | `KEYEDIN-RECON-FINDINGS.md` |
| Legacy system intel consolidation | COMPLETE | `LEGACY-KEYEDIN-INTEL.md` (755 lines) |
| Live test script (5 tests) | COMPLETE | `recon-results/run_all_tests.py` |
| Test results template | COMPLETE | `RECON-TEST-RESULTS.md` |
| Complete intelligence audit | COMPLETE | `KEYEDIN-COMPLETE-INTELLIGENCE.md` |
| Pipeline status (113 components) | COMPLETE | `KEYEDIN-PIPELINE-STATUS.md` |
| HTML field audit | COMPLETE | `KEYEDIN-HTML-FIELD-AUDIT.md` |
| Export endpoint test script | COMPLETE | `test_export_endpoints.py` |
| Export endpoint results | **BLOCKED** | Needs VPN-connected PC |

## What's Next (THE MISSION)

### Goal: Test 14 KeyedIn endpoints from VPN-connected PC

**6 Export Endpoints** (these are the highest-priority — built-in CSV/Excel exporters):
1. `CUST.PROD.EXPORT` — Sales by Customer by Product
2. `GM.BY.INV.EXPORT` — Gross Margin by Invoice
3. `SLSPER.PROD.EXPORT` — GM by Salesperson
4. `USAGE.ANAL.FILE` — Part Usage Export
5. `EXPORT.WO.LABOR.ANALYSIS` — WO Labor Analysis
6. `EXPORT.WIP.SUMMARY` — WIP Summary (Open or Closed)

**5 Import Endpoints** (GET only — capture form structure, DO NOT write data):
1. `IMPORT.PARTS`
2. `IMPORT.BOM`
3. `IMPORT.ROUTING`
4. `IMPORT.CRM.NEW`
5. `IMPORT.SIGN.TEMPLATE`

**3 Untested CGI Endpoints** (spot-check for data):
1. `WO.STATUS.MATL` — Costing - Material breakdown
2. `WO.STATUS.LABR` — Costing - Labor breakdown
3. `QUOTE.PIPELINE.REPORT` — Quote pipeline

---

## How to Run

### Option A: Run the automated test script

```bash
# 1. Pull the branch
git pull origin claude/keyedin-integration-recon-sd8Ug

# 2. Run the test script (zero external dependencies, uses only stdlib)
python test_export_endpoints.py

# 3. Results saved to ./export-test-results/
#    - all_results.json (machine-readable)
#    - {ENDPOINT_NAME}_raw.html (every response captured)
#    - Any CSV/file downloads saved with proper extension
```

The script will:
- Authenticate via POST with BradyF credentials (already in repo)
- Verify session by hitting WEB.MENU
- Test all 14 endpoints (GET, then POST fallback if GET returns a form)
- Save all responses to `export-test-results/`
- Print a summary table

### Option B: Continue with Claude Code on the connected PC

```bash
# 1. Pull the branch
git pull origin claude/keyedin-integration-recon-sd8Ug

# 2. Start Claude Code
claude

# 3. Give it this prompt:
```

**Handoff prompt for Claude Code (copy-paste this):**

```
Read PROJECT-STATE.md for full context. You are continuing a KeyedIn ERP integration
recon mission on branch claude/keyedin-integration-recon-sd8Ug.

This PC is on Eagle Sign's VPN and CAN reach eaglesign.keyedinsign.com.

YOUR MISSION: Run test_export_endpoints.py, then compile the results into
EXPORT-ENDPOINT-TEST-RESULTS.md using the format specified in PROJECT-STATE.md.

If the automated script fails, manually test each endpoint using Python urllib or
the requests library. The auth flow is:
  POST https://eaglesign.keyedinsign.com
  Body: USERNAME=BradyF&PASSWORD=[REDACTED]&SECURE=TRUE
  Capture cookies: SESSIONID, ASP.NET_SessionId, user, secure, IMPERSONATE
  Then GET https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/{ENDPOINT_NAME}

For each endpoint, capture: HTTP status, content-type, response type
(FORM/FILE/DATA/ERROR), form fields if applicable, first 5 rows if file download.

After testing, commit EXPORT-ENDPOINT-TEST-RESULTS.md and all files in
export-test-results/ to branch claude/keyedin-integration-recon-sd8Ug and push.
```

### Option C: Manual browser testing (fastest, 15 min)

1. Open Chrome, go to `https://eaglesign.keyedinsign.com`
2. Log in as BradyF
3. For each export endpoint, navigate to:
   `https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/CUST.PROD.EXPORT`
   (repeat for each of the 6 EXPORT endpoints)
4. Document what happens: Does it download a file? Show a form? Error?
5. For any forms, screenshot or note the field names
6. Save any downloaded files to `export-test-results/`

---

## Expected Deliverable Format

File: `EXPORT-ENDPOINT-TEST-RESULTS.md`

Summary table at top:

```
| Endpoint | Type | Status | Actionable? | Next Step |
|----------|------|--------|-------------|-----------|
| CUST.PROD.EXPORT | EXPORT | 200 | YES | Parse CSV output |
| ... | ... | ... | ... | ... |
```

Per-endpoint detail:

```
## ENDPOINT_NAME
- URL: https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/ENDPOINT_NAME
- Method: GET/POST
- Status: {HTTP status}
- Content-Type: {header value}
- Response: {FORM_REQUIRING_PARAMS | FILE_DOWNLOAD | DATA_RESPONSE | ERROR | REDIRECT}
- If form: field names and types
- If file: filename, size, format, first 5 rows
- If error: exact error text
- Time: {ms}
```

---

## System Reference (quick facts)

| Item | Value |
|------|-------|
| Product | KeyedIn Sign v2.1 |
| MVI Version | 3.0 |
| Base URL | `https://eaglesign.keyedinsign.com` |
| CGI Pattern | `/cgi-bin/mvi.exe/{PROCESS_NAME}` |
| Informer BI | Port 8443, GWT-RPC |
| Username | BradyF |
| Password | [REDACTED] (already in repo) |
| Auth Method | POST with USERNAME, PASSWORD, SECURE fields |
| Session Cookies | SESSIONID, ASP.NET_SessionId, user, secure, IMPERSONATE |
| Verified working | WEB.MENU, WO.INQUIRY, WO.HISTORY, WO.COST.SUMMARY (13/14 = 93%) |
| Known broken | WO.COST.DETAIL (not in VOC file) |
| Total endpoints mapped | 262 CGI + 71 Informer = 333 |
| Branch | `claude/keyedin-integration-recon-sd8Ug` |

---

## Files in This Branch

### Intelligence Documents
- `KEYEDIN-COMPLETE-INTELLIGENCE.md` — Master intel (8 sections, ranked opportunities)
- `KEYEDIN-PIPELINE-STATUS.md` — 113 components, 55 working / 18 broken / 31 untested
- `KEYEDIN-HTML-FIELD-AUDIT.md` — HTML field patterns for Material, Outplant, Est Hrs
- `LEGACY-KEYEDIN-INTEL.md` — Consolidated legacy system knowledge (755 lines)
- `KEYEDIN-RECON-FINDINGS.md` — Initial KIMCO research (wrong product, kept for reference)
- `RECON-TEST-RESULTS.md` — Data inventory + test framework

### Test Scripts
- `test_export_endpoints.py` — **THE SCRIPT TO RUN** (zero dependencies, tests all 14 endpoints)
- `recon-results/run_all_tests.py` — Earlier 5-test script (DNS, auth, exports, Informer, quote)

### Existing KeyedIn Scripts (81 Python + 12 PowerShell in `Keyedin/`)
- `Keyedin/keyedin_api_enhanced.py` — Best API wrapper (tested, working)
- `Keyedin/extract_with_credentials.py` — Credential-based extraction
- `Keyedin/comprehensive_test.py` — Validation suite (9/9 pass)
- Full inventory in `KEYEDIN-PIPELINE-STATUS.md`

---

## What Happens After the Export Test

Based on results, the next steps are:

1. **If exports return CSV files:** Parse them, document field schemas, integrate into APEX pipeline
2. **If exports show forms:** Document required parameters, build targeted requests
3. **If exports fail:** Fall back to Playwright browser automation (MCP server at `Keyedin/KEYEDIN MCP/keyedin_mcp_server_secure.py`)
4. **Import endpoint forms:** Document field mappings for future write capability
5. **Update KEYEDIN-PIPELINE-STATUS.md** with new test results

---

*This is a self-contained handoff. Everything needed is in this branch.*
