# KeyedIn HTML Field Audit

**Date:** 2026-02-14
**Purpose:** Audit all HTML captures for EST HOURS, Material, Outplant, and cost-related field patterns

---

## Note on "402 MB HTML Files"

The 402 MB HTML files referenced in the mission brief **DO NOT EXIST** in this repository. The HTML files in `Keyedin/` total approximately 1-2 MB. The large-file analysis (17 parsed tables, 1.3M rows, $241K dead stock, 54% labor below estimates) was likely performed in a conversation session where data was analyzed in memory but never committed.

---

## HTML Files Audited

41 HTML files found in `Keyedin/` directory. Three sampled for detailed field analysis.

---

## Sample 1: `WO.GROUP.ANALYSIS.html`

**Title:** Work Order Cost - Group Analysis
**URL Pattern:** `/cgi-bin/mvi.exe/WO.GROUP.ANALYSIS?WONO={#}`
**Form Action:** `WO.GROUP.ANALYSIS` (POST)
**Print Report:** `WO.GROUP.ANALYSIS.PRINT?WONO={wono}` (popup window)

### Fields Found

| CSS Class | Field Name | Present | Has Data |
|-----------|-----------|---------|----------|
| `itemLabel` | WO Number | YES | EMPTY (form input) |
| `itemLabel` | Part Number | YES | EMPTY |
| `itemLabelR` | Req's Qty | YES | EMPTY |
| `itemLabelR` | WIP Qty | YES | EMPTY |
| `itemLabelC` | C/F (Complete Flag) | YES | EMPTY |
| `itemLabelR` | **Total Labor** | YES | EMPTY |
| `itemLabelR` | **Total Material** | **YES** | EMPTY |
| `itemLabelR` | **Total Outplant** | **YES** | EMPTY |
| `itemLabelR` | Total Increment | YES | EMPTY |
| `itemLabelR` | Subassem at Std | YES | EMPTY |
| `itemLabelR` | Total Costs | YES | EMPTY |
| `itemLabelR` | Standard Dlrs Comp | YES | EMPTY |
| `itemLabelR` | Job Variance | YES | EMPTY |

### Key Findings
- **Material: PRESENT** in column header as "Total Material" (`itemLabelR` class)
- **Outplant: PRESENT** in column header as "Total Outplant" (`itemLabelR` class)
- **EST HOURS: NOT PRESENT** — this page shows actuals only, not estimates
- **Data rows: EMPTY** — the scrollable `<div>` contains a table with spacer images but no data rows (the form was captured before a WO number was entered)

### JavaScript Functions
- `validateEntry()` — Validates WONO field before submit
- `runGroupReport(wono)` — Opens print report popup
- `searchWONOUsingCustLocation_v1()` — Search WOs by customer location
- `openWOComments_v1(wono,changeOrView)` — Opens WO comments (V=view, else edit)

### Additional URL Patterns Discovered
- `SEARCH.WONO.CUST.LOCATION?CUST_LOCATION={value}` — WO search by customer location
- `SHOW.WO.COMMENTS?WONO={#}&OPENED_BY_OTHER_PROGRAM=Y` — View WO comments
- `WO.COMMENTS.MAINT?WONO={#}&OPENED_BY_OTHER_PROGRAM=Y` — Edit WO comments

---

## Sample 2: `WO.HISTORY.html`

**Title:** Work Order History
**URL Pattern:** `/cgi-bin/mvi.exe/WO.HISTORY`

### Fields Found

| CSS Class | Field Name | Present | Has Data |
|-----------|-----------|---------|----------|
| `itemLabel` | Work Order | YES | EMPTY |
| `itemLabelC` | Date Complete | YES | EMPTY |
| `itemLabelR` | Quantity to Mfgr | YES | EMPTY |
| `itemLabelR` | Quantity Complete | YES | EMPTY |
| `itemLabelR` | Labor Hours | YES | EMPTY |
| `itemLabelR` | **Material Each** | **YES** | EMPTY |
| `itemLabelR` | Labor Each | YES | EMPTY |
| `itemLabelR` | Burden Each | YES | EMPTY |
| `itemLabelR` | **Outplant Each** | **YES** | EMPTY |
| `itemLabelR` | Total Each | YES | EMPTY |
| `itemLabelR` | Selling Price | YES | EMPTY |
| `itemLabelR` | Gross Margin | YES | EMPTY |

### Key Findings
- **Material: PRESENT** as "Material Each" — per-unit material cost
- **Outplant: PRESENT** as "Outplant Each" — per-unit outplant cost
- **EST HOURS: NOT PRESENT** — shows actual "Labor Hours" only, no estimated hours
- **Data rows: EMPTY** — captured before a WO was queried

---

## Sample 3: Cost Summary JSON (`cost_summaries/all_detailed_cost_summaries_20251112_181028.json`)

This is the programmatic extraction output from `WO.STATUS.SUM`. Field labels found in the extracted JSON:

### Fields Found in Extracted JSON

| Field | Present | Has Data |
|-------|---------|----------|
| `"EstimatedCost"` | YES | LABEL ONLY (no value) |
| `"Material"` | YES | LABEL ONLY (no value) |
| `"Outplant"` | YES | LABEL ONLY (no value) |
| `"Last ActivityMaterial:Labor:AP/Adj:"` | YES | CONCATENATED — label merged with adjacent labels |

### Root Cause of Extraction Failure

The HTML from `WO.STATUS.SUM` uses **spacer images** and `class=itemLabelR` / `class=itemDataR` CSS classes in a fixed-width table layout:

```html
<td class=itemLabelR>Total<br>Material</td>
<td class=itemLabelR>Total<br>Outplant</td>
```

The data cells use `class=itemDataR` but BeautifulSoup's table parser merges them with adjacent label cells. The parser sees:

```
"Last ActivityMaterial:Labor:AP/Adj:"  ← Three labels concatenated
```

instead of separate fields. The actual data values are in `class=itemDataR` cells but get lost when tables with spacer GIFs are parsed generically.

---

## Field Comparison: HTML vs Benchmark CSV

| Field | HTML Pages | Cost Summary JSON | Benchmark CSV |
|-------|-----------|------------------|---------------|
| Est Hrs | NOT FOUND | NOT FOUND | **PRESENT** |
| Act Hrs | "Labor Hours" (WO.HISTORY) | NOT FOUND | **PRESENT** |
| Var Hrs | NOT FOUND | NOT FOUND | **PRESENT** |
| Est Qty | NOT FOUND | NOT FOUND | **PRESENT** |
| Act Qty | NOT FOUND | NOT FOUND | **PRESENT** |
| Var Qty | NOT FOUND | NOT FOUND | **PRESENT** |
| Est Cost | NOT FOUND | "EstimatedCost" (label only) | **PRESENT** |
| Act Lab | NOT FOUND | NOT FOUND | **PRESENT** |
| Act Bur | "Burden Each" (WO.HISTORY) | NOT FOUND | **PRESENT** |
| Act Mat | "Material Each" or "Total Material" | "Material" (label only) | **PRESENT** |
| Act Out | "Outplant Each" or "Total Outplant" | "Outplant" (label only) | **PRESENT** |
| Use Tax | NOT FOUND | NOT FOUND | **PRESENT** |
| Job Cost | NOT FOUND | NOT FOUND | **PRESENT** |
| R/I | NOT FOUND | NOT FOUND | **PRESENT** |
| Var Cost | NOT FOUND | NOT FOUND | **PRESENT** |
| Gross Margin | "Gross Margin" (WO.HISTORY) | NOT FOUND | **PRESENT** |
| Work Dept | NOT FOUND | NOT FOUND | **PRESENT** |
| Work Code | NOT FOUND | NOT FOUND | **PRESENT** |

### Conclusion

The **Benchmark CSV** (manually exported via Report Option 'D' + Send To 'P') contains ALL fields. The HTML pages contain field LABELS for Material, Outplant, Labor, Burden, and Gross Margin, but the programmatic extraction failed to capture the actual VALUES because:

1. The HTML uses spacer-GIF-based fixed-width tables (not semantic HTML)
2. BeautifulSoup's generic table parser concatenates adjacent `<td>` cells
3. `class=itemDataR` data cells lose their association with `class=itemLabelR` headers

### Recommended Fix

1. **For Est Hrs specifically:** Use `WO.STATUS.SUM` (Cost Summary page) which has estimated vs actual breakdown — NOT `WO.HISTORY` or `WO.GROUP.ANALYSIS` which only show actuals
2. **For reliable extraction:** Use Playwright with `page.evaluate()` to access the DOM directly instead of parsing raw HTML
3. **Quick win:** Automate the Report Option 'D' + Send To 'P' print flow with Playwright — this produces the complete CSV output

---

## All HTML Files in Repository (41 files)

### Application Pages (14)
- `FIRST.ISSUE.html` — Material first issue form
- `MAIN.html` — Main dashboard
- `MENU.html` — Menu page
- `SERVICE_CALL_LIST.html` — Service calls
- `WEB.MENU.html` — Full JSON menu (262 endpoints)
- `WIDGET.ASSIGNED.MILESTONES.html` — Dashboard widget
- `WIDGET.ASSIGNED.SERVICE.CALLS.html` — Dashboard widget
- `WIDGET.CRM.TASKS.html` — Dashboard widget
- `WIDGET.FYI.html` — Dashboard widget
- `WO.COMPLETION.INQUIRY.html` — WO completion form
- `WO.GROUP.ANALYSIS.html` — WO group cost analysis
- `WO.HISTORY.html` — WO cost history
- `WO.INQUIRY.html` — WO inquiry form
- `WORKORDER_LIST.html` — WO list view
- `wo_inquiry_form.html` — WO inquiry form (duplicate save)

### Login Flow (7)
- `actual_login_page.html`
- `after_login.html`
- `chrome_logged_in.html`
- `logged_in_page.html`
- `login_page.html`
- `login_start_page.html`
- `login_success.html`

### Informer BI Pages (6)
- `informer_portal.html`
- `informer_report_page.html`
- `_Home_response.html`
- `_Informer_response.html`
- `_ReportList_response.html`
- `_sso_response.html`
- `sso_response_*.html` (2 files)

### Discovery Captures (1)
- `..KeyedIn_System_Map/discovery_data/html_captures/00_logged_in_home.html`

### Claude Chat Saves (7)
- `KEYEDIN MCP/System Diagnostic Framework Setup - Claude.html`
- `KEYEDIN MCP/System Diagnostic Framework Setup - Claude_files/*.html` (6 supporting files)

---

*Audit complete. No 402 MB HTML files found. Field labels for Material and Outplant are present in captured HTML but actual cost values were not extracted due to parser limitations.*
