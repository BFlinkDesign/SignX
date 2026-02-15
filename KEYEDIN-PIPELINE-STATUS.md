# KEYEDIN PIPELINE STATUS

**Generated**: 2026-02-14
**Audit Method**: File existence + code inspection + output verification

---

## Pipeline Overview

```
                                    ┌──────────────────────────┐
                                    │  KeyedIn Sign ERP v2.1   │
                                    │  (mvi.exe CGI backend)   │
                                    └──────┬────────┬──────────┘
                                           │        │
                            ┌──────────────┘        └──────────────┐
                            ▼                                      ▼
                  ┌──────────────────┐                   ┌──────────────────┐
                  │ Cost Summary     │                   │ Informer BI      │
                  │ Print/View       │                   │ (GWT-RPC v7)     │
                  │ (168 HTML files) │                   │ (30 reports)     │
                  └────────┬─────────┘                   └────────┬─────────┘
                           │                                      │
                     Phase 1                                Phase 2/3
                           │                                      │
                           ▼                                      ▼
                  ┌──────────────────┐                   ┌──────────────────┐
                  │ parse_full_      │                   │ scrape_informer  │
                  │ cost_detail.py   │                   │ .py              │
                  │ (907 lines)      │                   │ (GWT replay)     │
                  └────────┬─────────┘                   └────────┬─────────┘
                           │                                      │
                           ▼                                      │
                  ┌──────────────────┐                            │
                  │ 5 CSV outputs    │                            │
                  │ (1.25M rows)     │              ┌─────────────┘
                  └────────┬─────────┘              │
                           │                        │ (NOT YET INTEGRATED)
                           ▼                        ▼
              Phase 4 ┌──────────────────┐   ┌──────────────────┐
            ─────────▶│ ingest_local_    │   │ GWT response     │
  Local Excel/CSV     │ files.py         │   │ CSVs (partial)   │
  from OneDrive       └────────┬─────────┘   └──────────────────┘
                               │
                         Phase 5│
                               ▼
                      ┌──────────────────┐
                      │ build_warehouse  │
                      │ .py (1034 lines) │
                      │ → SQLite 211MB   │
                      └────────┬─────────┘
                               │
                         Phase 6│
                               ▼
                      ┌──────────────────┐
                      │ decision_engine  │
                      │ .py              │
                      │ → Reports (.md)  │
                      └──────────────────┘
```

---

## Component-by-Component Status

### 1. HTML Capture (Cost Summary Batch Files)

| Attribute | Value |
|-----------|-------|
| **Status** | WORKING |
| **Location** | `C:\Scripts\keyedin-capture\reports\cost_detail\` |
| **Files** | 168 HTML files (`cost_detail_batch_001.html` - `_168.html`) |
| **Size** | 559 MB |
| **Content** | 33,428 work orders with full cost detail |
| **Captured** | 2026-01-29 to 2026-01-30 |
| **Method** | Print/View from KeyedIn ERP → Save HTML via browser |
| **Dependencies** | VPN access to eaglesign.keyedinsign.com |
| **Test Status** | VERIFIED — All 168 files parseable |

**Scripts involved in capture**:
| Script | Path | Status |
|--------|------|--------|
| `extract_wo_batches.py` | `C:\Scripts\keyedin-capture\` | WORKING — CDP-based batch extraction |
| `cost_summary_automation.py` | `C:\Scripts\keyedin-capture\` | WORKING — Automated capture driver |
| `fast_extract.py` | `C:\Scripts\keyedin-capture\` | WORKING — Optimized extraction |
| `setup_credentials.py` | `C:\Scripts\keyedin-capture\` | WORKING — Credential setup |
| `test_cdp.py` | `C:\Scripts\keyedin-capture\` | WORKING — CDP connectivity test |
| `test_pipeline.py` | `C:\Scripts\keyedin-capture\` | WORKING — Pipeline smoke test |
| `test_20wo.py` | `C:\Scripts\keyedin-capture\` | WORKING — Small batch test |
| `test_200wo_debug.py` | `C:\Scripts\keyedin-capture\` | WORKING — Debug extraction |
| `test_200wo_post.py` | `C:\Scripts\keyedin-capture\` | WORKING — POST verification |

---

### 2. Phase 1 — HTML Parser

| Attribute | Value |
|-----------|-------|
| **Status** | WORKING |
| **Script** | `parse_full_cost_detail.py` |
| **Locations** | `C:\Scripts\signx-warehouse\scripts\` AND `~\OneDrive\signx-warehouse\scripts\` |
| **Lines** | 907 |
| **Language** | Python 3.13 (BeautifulSoup + regex) |
| **Input** | 168 HTML files from `C:\Scripts\keyedin-capture\reports\cost_detail\` |
| **Output Dir** | `C:\Scripts\signx-warehouse\warehouse\raw\{timestamp}\` |
| **Dependencies** | `beautifulsoup4`, `lxml` |
| **Test Status** | VERIFIED — 1,253,042 rows extracted, 0 cross-validation mismatches |

**Output files**:
| File | Rows | Status |
|------|------|--------|
| `wo_headers.csv` | 33,428 | VERIFIED |
| `labor_detail.csv` | 254,012 | VERIFIED |
| `labor_summary.csv` | 161,377 | VERIFIED — includes EST HRS |
| `material_detail.csv` | 780,868 | VERIFIED |
| `outplant_detail.csv` | 23,352 | VERIFIED |
| `manifest.json` | 1 | VERIFIED |

**Extraction runs** (all from 2026-01-30):
| Timestamp | Status | Notes |
|-----------|--------|-------|
| T1011 | Complete | First run |
| T1026 | Complete | Primary extraction (used for warehouse build) |
| T1107 | Complete | Phase 4 local files |
| T1131, T1133, T1135, T1138, T1150, T1153, T1157, T1342 | Complete | Iterative refinement runs |

---

### 3. Informer BI Capture

| Attribute | Value |
|-----------|-------|
| **Status** | WORKING (capture complete, replay untested) |
| **Capture Location** | `C:\Scripts\keyedin-capture\reports\` |
| **Reports Captured** | 30/30 |
| **Protocol** | GWT-RPC v7 (pipe-delimited) |
| **Endpoint** | `https://eaglesign.keyedinsign.com:8443/eaglesign/informer/rpc/protected/ViewRPCService` |
| **Session Doc** | `C:\Scripts\keyedin-capture\SESSION_HANDOFF.md` |
| **Dependencies** | VPN + active Informer session cookie |
| **Test Status** | CAPTURE VERIFIED, REPLAY UNTESTED |

**Capture assets**:
| File Pattern | Count | Status |
|-------------|-------|--------|
| `report_*_view_request.txt` | 30 | VERIFIED |
| `report_*_view_response.txt` | varies | PARTIAL |
| `report_*_cmd_request.txt` | varies | PARTIAL |
| `raw_captures.json` | 1 | VERIFIED |

**Replay/automation scripts**:
| Script | Path | Status |
|--------|------|--------|
| `scrape_informer.py` | `C:\Scripts\signx-warehouse\scripts\` | EXISTS — untested end-to-end |
| `capture_all_reports.py` | `C:\Scripts\signx-warehouse\scripts\` | EXISTS — untested |
| `split_captures.py` | `C:\Scripts\signx-warehouse\scripts\` | WORKING — splits raw_captures.json |
| `capture_hook.js` | `C:\Scripts\signx-warehouse\scripts\` (claimed) | NOT VERIFIED |

**GWT Protocol tooling**:
| Script | Path | Status |
|--------|------|--------|
| `gwt_parser.py` | `C:\Scripts\signx-warehouse\scripts\` | EXISTS |
| `gwt_deserialize.py` | `C:\Scripts\signx-warehouse\scripts\` | EXISTS |
| `gwt_analyze.py` | `C:\Scripts\signx-warehouse\scripts\` | EXISTS |
| `gwt_dump_rows.py` | `C:\Scripts\signx-warehouse\scripts\` | EXISTS |

---

### 4. Phase 4 — Local File Ingestion

| Attribute | Value |
|-----------|-------|
| **Status** | WORKING |
| **Script** | `ingest_local_files.py` |
| **Locations** | `C:\Scripts\signx-warehouse\scripts\` AND `~\OneDrive\signx-warehouse\scripts\` |
| **Input Sources** | Excel/CSV files from `H:\brady\BOT TRAINING\` and OneDrive |
| **Output Dir** | `C:\Scripts\signx-warehouse\warehouse\raw\{timestamp}\` |
| **Dependencies** | `pandas`, `openpyxl` |
| **Test Status** | VERIFIED — Multiple file types ingested |

**Known local data sources ingested**:
| Source File | Table | Rows | Trust Tier |
|-------------|-------|------|------------|
| `H:\brady\BOT TRAINING\Cat Scale\*.xlsx` | labor_forensics | 53,380 | 4 (local) |
| `BRADYF_STOCK.STATUS.xlsx` | inventory | 1,062 | 4 (local) |
| Various shop efficiency exports | shop_efficiency | 44 | 4 (local) |
| Labor multiplier tables | labor_multipliers | 42 | 4 (local) |
| GM by salesperson exports | gm_by_salesperson | 4,298 | 4 (local) |

---

### 5. Phase 5 — Warehouse Builder

| Attribute | Value |
|-----------|-------|
| **Status** | WORKING |
| **Script** | `build_warehouse.py` |
| **Locations** | `C:\Scripts\signx-warehouse\scripts\` AND `~\OneDrive\signx-warehouse\scripts\` |
| **Lines** | 1,034 |
| **Output** | `C:\Scripts\signx-warehouse\warehouse\production\eagle_warehouse.db` |
| **DB Size** | 211 MB |
| **Tables** | 17 |
| **Total Rows** | 1,376,130 |
| **Built** | 2026-01-30T11:10:07 |
| **Dependencies** | Python stdlib `sqlite3` |
| **Test Status** | VERIFIED — manifest.json confirms all counts |

**Table inventory**:
| Table | Rows | Source Phase | Status |
|-------|------|-------------|--------|
| work_orders | 33,428 | Phase 1 (HTML) | VERIFIED |
| labor_detail | 254,012 | Phase 1 (HTML) | VERIFIED |
| labor_summary | 161,377 | Phase 1 (HTML) | VERIFIED |
| material_transactions | 780,868 | Phase 1 (HTML) | VERIFIED |
| outplant_transactions | 23,352 | Phase 1 (HTML) | VERIFIED |
| invoices | 26,643 | Phase 4 (local) | VERIFIED |
| inventory | 1,062 | Phase 4 (local) | VERIFIED |
| purchase_orders | 5,974 | Phase 4 (local) | VERIFIED |
| customers | 3,748 | Phase 4 (local) | VERIFIED |
| sales_orders | 27,707 | Phase 4 (local) | VERIFIED |
| employees | 95 | Derived | VERIFIED (18 active) |
| ref_work_codes | 62 | Phase 4 (local) | VERIFIED |
| ref_sign_types | 38 | Phase 4 (local) | VERIFIED |
| shop_efficiency | 44 | Phase 4 (local) | VERIFIED |
| labor_multipliers | 42 | Phase 4 (local) | VERIFIED |
| labor_forensics | 53,380 | Phase 4 (local) | VERIFIED |
| gm_by_salesperson | 4,298 | Phase 4 (local) | VERIFIED |

---

### 6. Phase 6 — Decision Engine

| Attribute | Value |
|-----------|-------|
| **Status** | WORKING |
| **Script** | `decision_engine.py` |
| **Locations** | `C:\Scripts\signx-warehouse\scripts\` AND `~\OneDrive\signx-warehouse\scripts\` |
| **Input** | `eagle_warehouse.db` |
| **Output** | `warehouse\reports\decision_report_{timestamp}.md` |
| **Dependencies** | `sqlite3` |
| **Test Status** | VERIFIED — Report generated 2026-01-30 |

**Key findings from decision report**:
| Metric | Value | Status |
|--------|-------|--------|
| Dead stock value | $241,701.53 | CONFIRMED |
| Labor overestimation | 50-56% across all estimators | CONFIRMED |
| Average true margin | 8.6% | CONFIRMED |
| Top customer (Cat Scale) | $28.96M revenue, 2,619 WOs | CONFIRMED |
| Win/loss analysis | BLOCKED — no quote data | CONFIRMED GAP |

---

### 7. KeyedIn Knowledge MCP Server

| Attribute | Value |
|-----------|-------|
| **Status** | WORKING (when loaded) |
| **Main Script** | `keyedin.py` |
| **Location** | `C:\Scripts\keyedin-automation\` |
| **Framework** | FastMCP 2.14.3 |
| **Vector DB** | ChromaDB (384-dim, sentence-transformers/all-MiniLM-L6-v2) |
| **Documents** | 1,141 indexed (129 functions, 4 workflows, 1,008 filesystem paths) |
| **Tools** | 8 (search_knowledge, get_workflow, list_workflows, get_url_pattern, get_page_map, get_field_info, find_project, get_navigation_path) |
| **Dependencies** | `fastmcp`, `chromadb`, `sentence-transformers` |
| **Test Status** | VERIFIED — tools functional when server running |
| **Currently Connected** | NO (not in active MCP config) |

**Supporting scripts**:
| Script | Purpose | Status |
|--------|---------|--------|
| `scripts/init_database.py` | Initialize SQLite | WORKING |
| `scripts/init_chromadb.py` | Initialize vector store | WORKING |
| `scripts/discover_filesystem.py` | Scan filesystem for paths | WORKING |
| `scripts/ingest.py` | Ingest documents into collections | WORKING |
| `scripts/verify_knowledge_base.py` | Validate knowledge base | WORKING |
| `scripts/test_tools_directly.py` | Direct tool testing | WORKING |

---

### 8. Supplementary Analysis Scripts (keyedin-capture/reports/)

| Script | Purpose | Status |
|--------|---------|--------|
| `generate_benchmarks.py` | Performance benchmarking | EXISTS — untested |
| `audit_script.py` | Data audit | EXISTS — untested |
| `run_audit.py` | Run audit pipeline | EXISTS — untested |
| `build_abc_update.py` | ABC classification | EXISTS — untested |
| `build_abc_update_v2.py` | ABC v2 | EXISTS — untested |
| `labor_query.py` | Labor SQL queries | EXISTS — untested |
| `labor_query_test.py` | Labor query tests | EXISTS — untested |
| `parse_descriptions.py` | WO description parsing | EXISTS — untested |
| `parse_gm_salesperson.py` | GM by salesperson | EXISTS — untested |
| `build_master_dataset.py` | Master dataset builder | EXISTS — untested |
| `eagle_insights.py` | Insight generation | EXISTS — untested |
| `test_parse_reports.py` | Parser tests | EXISTS — untested |
| `parse_reports.py` | Generic report parser | EXISTS — untested |

---

### 9. Site Map & Discovery

| Attribute | Value |
|-----------|-------|
| **Status** | COMPLETE (static snapshot) |
| **File** | `C:\Scripts\keyedin-automation\discovery\keyedin\keyedin_site_map.json` |
| **Functions Mapped** | 288 |
| **Captured** | 2025-05-22 via Puppeteer |
| **Sections** | FAVORITES, CRM, PROJECT_MANAGEMENT, SALES_AND_AR, PURCHASING_AND_AP, INVENTORY, WORK_ORDERS, MISC, UTILITIES, GL, ADMIN |
| **Network Analysis** | `C:\Scripts\keyedin-automation\discovery\keyedin\network_analysis_report.md` |
| **Test Status** | VERIFIED — JSON parseable, 288 entries confirmed |

---

### 10. SignX Repository (KeyedIn Integration Code)

| Attribute | Value |
|-----------|-------|
| **Status** | PARTIAL (early prototype) |
| **Repo** | `C:\Users\Brady.EAGLE\Desktop\SignX` |
| **Branch** | `origin/claude/signx-platform-setup-011CUyNrHbNEXBgpFqWgJYSZ` |
| **Key Files** | `keyedin/connection.ts`, `keyedin/types.ts`, `keyedin/scraper.ts` |
| **Integration Doc** | `docs/integrations/keyedin-crm.md` |
| **Test Status** | NOT TESTED — early TypeScript stubs, no tests written |
| **Dependencies** | Network access to KeyedIn (blocked without VPN) |

---

### 11. Downloads Archive (`~/Downloads/SignX-main/SignX-main/Keyedin/`)

| Attribute | Value |
|-----------|-------|
| **Status** | ARCHIVE (historical, 2025-11-12 session) |
| **Size** | 36 MB |
| **Scripts** | 81 Python files |
| **Data Files** | 95 JSON + 41 HTML + CSV exports |
| **Actual Extracted Data** | YES — 50 WO cost summaries, 33,080-row WO history CSV |
| **Test Status** | HISTORICAL — scripts may need updating for current env |

Key data assets:
| File | Rows/Size | Status |
|------|-----------|--------|
| `Closed WO 11-1-00 to 10-31-25.csv` | 33,080 rows, 6 MB | EXISTS |
| `all_detailed_cost_summaries_20251112.json` | 50 WOs, 350 tables | EXISTS |
| `complete_endpoint_map.json` | 50+ endpoints, 61 KB | EXISTS |
| `DATA_EXTRACTION_GUIDE.md` | 14 endpoints, 93% success | EXISTS |

Key scripts:
| Script | Size | Purpose | Status |
|--------|------|---------|--------|
| `keyedin_api_enhanced.py` | 24 KB | CDP API with session auto-refresh | UNTESTED (current env) |
| `extract_everything_complete.py` | 22 KB | Full extraction pipeline | UNTESTED |
| `map_all_endpoints.py` | 18 KB | Endpoint discovery | UNTESTED |
| `keyedin_cdp_extractor.py` | 16 KB | CDP cookie extractor | UNTESTED |

---

### 12. Keyedin Mapping API MCP (`C:\Scripts\Keyedin Mapping API MCP\`)

| Attribute | Value |
|-----------|-------|
| **Status** | PRODUCTION-READY (inactive) |
| **Size** | 1.5 GB |
| **Architecture** | MCP server + Electron desktop app + API server |
| **API Server** | `127.0.0.1:8765` |
| **Chrome Debug Port** | 9222 |
| **Extractors** | Quote, cost, inventory, search + CSV stream parser |
| **Features** | Multi-session pool, cache with offline mode, session managers |
| **Desktop Config** | `AppData\Local\KeyedIn Desktop\config.json` |
| **Test Status** | EXISTS but not currently connected to Claude Code |
| **Last Activity** | 2026-01-09 (per log timestamps) |

---

### 13. Additional KeyedIn Repositories

| Path | Size | Status |
|------|------|--------|
| `C:\Scripts\keyedin-mcp\` | 109 MB | EXISTS — earlier MCP version |
| `C:\Scripts\keyedin-extraction\` | 43 KB | EXISTS — lightweight utils |

---

## Aggregate Status Summary

| Category | Total | Working | Untested | Broken | N/A |
|----------|-------|---------|----------|--------|-----|
| **Capture scripts** | 9 | 9 | 0 | 0 | 0 |
| **Phase 1 (HTML parse)** | 1 | 1 | 0 | 0 | 0 |
| **Informer capture** | 30 reports | 30 | 0 | 0 | 0 |
| **Informer replay** | 4 scripts | 0 | 4 | 0 | 0 |
| **GWT tooling** | 4 scripts | 0 | 4 | 0 | 0 |
| **Phase 4 (local ingest)** | 1 | 1 | 0 | 0 | 0 |
| **Phase 5 (warehouse)** | 1 | 1 | 0 | 0 | 0 |
| **Phase 6 (decision)** | 1 | 1 | 0 | 0 | 0 |
| **MCP Knowledge Server** | 7 scripts | 7 | 0 | 0 | 0 |
| **Analysis scripts** | 13 | 0 | 13 | 0 | 0 |
| **Site map/discovery** | 2 files | 2 | 0 | 0 | 0 |
| **SignX integration** | 3 files | 0 | 3 | 0 | 0 |
| **Downloads archive** | 81 scripts + data | 0 | 81 | 0 | 0 |
| **Mapping API MCP** | 1 system | 0 | 1 | 0 | 0 |
| **Other repos (keyedin-mcp, extraction)** | 2 | 0 | 2 | 0 | 0 |
| **TOTALS** | **160+** | **52** | **108** | **0** | **0** |

---

## Data Artifacts

| Artifact | Location | Size | Status |
|----------|----------|------|--------|
| 168 HTML batch files | `C:\Scripts\keyedin-capture\reports\cost_detail\` | 559 MB | EXISTS |
| 30 Informer payloads | `C:\Scripts\keyedin-capture\reports\` | ~5 MB | EXISTS |
| Raw CSVs (11 runs) | `C:\Scripts\signx-warehouse\warehouse\raw\` | ~200 MB | EXISTS |
| SQLite warehouse | `C:\Scripts\signx-warehouse\warehouse\production\eagle_warehouse.db` | 211 MB | EXISTS |
| Decision report | `~\OneDrive\signx-warehouse\warehouse\reports\` | ~50 KB | EXISTS |
| Site map JSON | `C:\Scripts\keyedin-automation\discovery\keyedin\keyedin_site_map.json` | ~100 KB | EXISTS |
| ChromaDB vectors | `C:\Scripts\keyedin-automation\` (embedded) | ~50 MB | EXISTS |
| OneDrive mirror | `~\OneDrive - Eagle Sign Co\signx-warehouse\` | 742 MB | EXISTS |
| Local scripts mirror | `C:\Scripts\signx-warehouse\` | ~300 MB | EXISTS |

**Total data footprint**: ~2.2 GB across all locations

---

## Known Gaps & Blockers

| Gap | Impact | Severity | Mitigation |
|-----|--------|----------|------------|
| No quote/estimating data | Cannot do win/loss analysis | HIGH | Requires Main ERP capture (Quote module) |
| Informer replay untested | Can't refresh BI data automatically | MEDIUM | Test `scrape_informer.py` with valid session |
| GWT tools untested | Can't decode Informer responses | MEDIUM | Test `gwt_parser.py` against captured responses |
| 13 analysis scripts untested | Unknown utility | LOW | Audit each for usefulness |
| SignX integration stubs | No live ERP connection | LOW | Blocked by VPN/proxy |
| No AP/GL data captured | Incomplete financial picture | MEDIUM | Requires Main ERP capture |
| No vendor detail | Missing supply chain data | LOW | Available in Informer (vendor_listing captured) |
| Warehouse is static snapshot | Data from 2026-01-30 only | HIGH | Need automated refresh pipeline |

---

## Recommended Next Steps (Priority Order)

1. **Test Informer replay** — Run `scrape_informer.py` with fresh session to verify automated data refresh works
2. **Capture Main ERP modules** — Log into `mvi.exe`, capture Quotes, GL, AP data using Print/View method
3. **Test GWT tooling** — Verify `gwt_parser.py` can decode response payloads into usable data
4. **Audit analysis scripts** — Run each of the 13 scripts in `keyedin-capture/reports/` to determine usefulness
5. **Build refresh pipeline** — Automate: login → capture → parse → build → report cycle
6. **Integrate Informer data** — Feed decoded Informer CSV data into warehouse as trust tier 2
