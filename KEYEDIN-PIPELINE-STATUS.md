# KeyedIn Pipeline Status — Component by Component

**Date:** 2026-02-14
**Purpose:** Every pipeline component, its file path, tested/untested status, and what's needed next

---

## Pipeline 1: Authentication (Main App)

| Status | **WORKING** |
|--------|-------------|

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| Direct POST login | `Keyedin/extract_with_credentials.py` | TESTED, WORKING | Posts USERNAME/PASSWORD/SECURE |
| Chrome CDP cookie extraction | `Keyedin/keyedin_cdp_extractor.py` | TESTED, WORKING | Opens Chrome, user logs in, extracts cookies |
| Selenium cookie extraction | `Keyedin/extract_cookies_chrome.py` | TESTED, WORKING | WebDriver + ChromeDriver |
| Enhanced API wrapper | `Keyedin/keyedin_api_enhanced.py` | TESTED, WORKING | Session manager with auto-refresh |
| Legacy API wrapper | `Keyedin/keyedin_api.py` | TESTED, WORKING | Superseded by enhanced version |
| Session validation | `Keyedin/comprehensive_test.py` | TESTED, WORKING | 9/9 tests pass |
| Captured session cookies | `Keyedin/keyedin_session.json` | CAPTURED | 5 cookies, domain: eaglesign.keyedinsign.com |
| Chrome session capture | `Keyedin/keyedin_chrome_session.json` | CAPTURED | Alternative session source |

**Next steps:** Confirm whether login is still direct POST or has switched to Google SSO.

---

## Pipeline 2: Authentication (Informer BI)

| Status | **WORKING** |
|--------|-------------|

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| SSO URL pattern | `Keyedin/informer_portal_urls.json` | DOCUMENTED | `sso?u=BRADYF&t={token}` |
| JSESSIONID capture | `Keyedin/GWT Google Web Toolkit/keyedin_session.json` | CAPTURED | Java session cookie |
| authToken capture | `Keyedin/GWT Google Web Toolkit/keyedin_session.json` | CAPTURED | UUID auth token |
| clientId capture | `Keyedin/GWT Google Web Toolkit/keyedin_session.json` | CAPTURED | UUID client ID |
| PowerShell extractor | `Keyedin/GWT Google Web Toolkit/MASTER_EXTRACTOR.ps1` | TESTED, PARTIAL | Auth works, data extraction incomplete |
| Chrome session capture | `Keyedin/GWT Google Web Toolkit/session_cookies.json` | CAPTURED | Informer-specific cookies |

**Next steps:** Tokens likely expired. Re-authenticate to get fresh tokens.

---

## Pipeline 3: Endpoint Discovery & Mapping

| Status | **WORKING** |
|--------|-------------|

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| Menu discovery | `Keyedin/WEB.MENU.json` | TESTED, WORKING | 262 endpoints mapped |
| Endpoint categorization | `Keyedin/endpoint_map.json` | COMPLETE | Categorized by module |
| Full endpoint listing | `Keyedin/complete_endpoint_map.json` | COMPLETE | All details |
| Endpoint mapper script | `Keyedin/map_all_endpoints.py` | TESTED, WORKING | Automated mapping |
| Menu HTML capture | `Keyedin/WEB.MENU.html` | CAPTURED | HTML version |

**Next steps:** None — this pipeline is complete. 262 endpoints fully mapped.

---

## Pipeline 4: CGI/MVI Data Extraction (Read)

| Status | **PARTIALLY WORKING** |
|--------|----------------------|

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| Bulk data extractor | `Keyedin/extract_all_data.py` | TESTED, WORKING | Extracts all endpoints |
| Everything extractor | `Keyedin/extract_everything_complete.py` | TESTED, PARTIAL | Some endpoints error |
| WO query | `Keyedin/fetch_work_orders.py` | TESTED, WORKING | Fetches WO data |
| WO query (all) | `Keyedin/get_all_work_orders.py` | TESTED, WORKING | Bulk WO fetch |
| HTML form analyzer | `Keyedin/analyze_form.py` | TESTED, WORKING | Parses form fields |
| WO inquiry analyzer | `Keyedin/analyze_wo_inquiry_form.py` | TESTED, WORKING | WO-specific analysis |
| Menu explorer | `Keyedin/explore_menu.py` | TESTED, WORKING | Interactive menu walk |
| HAR parser | `Keyedin/parse_har.py` | TESTED, WORKING | Network traffic analysis |
| Page analyzer | `Keyedin/analyze_pages.py` | TESTED, WORKING | HTML structure analysis |
| JSON inspector | `Keyedin/inspect_json.py` | TESTED, WORKING | JSON response analysis |
| Quick extract | `Keyedin/quick_extract.py` | TESTED, WORKING | Fast single-endpoint |
| Quick test | `Keyedin/quick_test.py` | TESTED, WORKING | Fast validation |
| WO endpoint tester | `Keyedin/test_wo_endpoints.py` | TESTED, WORKING | WO-specific tests |
| Endpoint tester | `Keyedin/test_endpoints.py` | TESTED, WORKING | General endpoint tests |
| Network capture | `Keyedin/capture_network.py` | TESTED, WORKING | HTTP capture |
| Extracted menu data | `Keyedin/extracted_data/menu_*.json` | CAPTURED | Menu JSON |
| Extracted WO data | `Keyedin/extracted_data/work_orders_*.json` | CAPTURED | WO form data |
| WO query results | `Keyedin/wo_query_results.json` | CAPTURED | Query responses |

**Result:** 13/14 endpoints (93%) return 200 OK. Only `WO.COST.DETAIL` fails (not in VOC).

**Next steps:** Build targeted parsers for specific pages: `QUOTE.ENTRY.DETAILS`, `WO.STATUS.SUM`, `ORDER.ENTRY`.

---

## Pipeline 5: Cost Summary Extraction

| Status | **BROKEN — Headers only, no data cells** |
|--------|----------------------------------------|

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| WO.STATUS.SUM extractor | `Keyedin/extract_all_cost_summaries.py` | TESTED, PARTIAL | 443 lines, gets headers but 0 usable data |
| Complete version | `Keyedin/extract_all_cost_summaries_complete.py` | TESTED, PARTIAL | Same issue |
| Detailed version | `Keyedin/extract_all_detailed_cost_summaries.py` | TESTED, PARTIAL | Same issue |
| SO.CONTRACT.RUN extractor | `Keyedin/extract_all_cost_summaries_via_report.py` | TESTED, FAILED | 10 SOs queried, ALL 0 data rows |
| Individual WO summaries (52) | `Keyedin/cost_summaries/individual_summaries/WO_*.json` | CAPTURED | Headers + partial data |
| Bulk summary JSON (5 files) | `Keyedin/cost_summaries/all_*.json` | CAPTURED | Headers only |
| CSV exports | `Keyedin/cost_summaries/*.csv` | CAPTURED | Minimal data |

**Root cause:** BeautifulSoup HTML parsing doesn't handle the MVI-generated HTML table structure correctly. Data cells are either empty or concatenated with labels.

**What DOES work (manual):** The detailed cost summary CSV in `Benchmark/storage/-Audit-/2025/307-0267.../Cost Summaries DETAILED *.csv` has full data with all fields (Est Hrs, Act Hrs, Est Cost, Act Lab, Act Bur, Act Mat, Act Out, Job Cost, Var Cost, GM). This was manually exported from KeyedIn.

**Next steps:**
1. Test Report Option 'D' + Send To 'P' via the quote entry screen
2. Fix BeautifulSoup selectors for `WO.STATUS.SUM` HTML tables
3. Or: automate the manual export process with Playwright

---

## Pipeline 6: Informer GWT-RPC Data Extraction

| Status | **BROKEN — 0 records extracted** |
|--------|--------------------------------|

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| Python extractor (complete) | `Keyedin/GWT Google Web Toolkit/keyedin_complete_extraction.py` | TESTED, PARTIAL | Auth works, getData fails |
| Python extractor (enhanced) | `Keyedin/GWT Google Web Toolkit/keyedin_enhanced_extractor.py` | TESTED, PARTIAL | Same |
| Python extractor (working) | `Keyedin/GWT Google Web Toolkit/keyedin_working_extractor.py` | TESTED, PARTIAL | Found 71 reports, 0 data |
| Python extractor (general) | `Keyedin/GWT Google Web Toolkit/keyedin_data_extractor.py` | TESTED, PARTIAL | Same |
| Python extractor (SQL) | `Keyedin/GWT Google Web Toolkit/keyedin_sql_extraction.py` | UNTESTED | SQL Server variant |
| PowerShell master extractor | `Keyedin/GWT Google Web Toolkit/MASTER_EXTRACTOR.ps1` | TESTED, PARTIAL | Auth OK, data fail |
| PowerShell test scripts (10) | `Keyedin/GWT Google Web Toolkit/test_*.ps1` | TESTED, FAILED | Various payload attempts |
| Cookie extractor | `Keyedin/GWT Google Web Toolkit/extract_cookies.py` | TESTED, WORKING | Gets Informer cookies |
| Session extractor | `Keyedin/GWT Google Web Toolkit/extract_keyedin_session.py` | TESTED, WORKING | Gets session tokens |
| HAR capture | `Keyedin/GWT Google Web Toolkit/eaglesign.keyedinsign.com.har` | CAPTURED | Full Informer traffic |
| Extraction summary | `Keyedin/GWT Google Web Toolkit/keyedin_extraction_*/extraction_summary.txt` | CAPTURED | 71 reports listed |
| HAR auto-capture | `Keyedin/auto_capture_har.py` | TESTED, WORKING | Automated HAR capture |
| Informer API capture | `Keyedin/capture_informer_api.py` | TESTED, PARTIAL | API call capture |
| Informer finder | `Keyedin/find_informer.py` | TESTED, WORKING | Finds Informer portal |
| BI report finder | `Keyedin/find_bi_reports.py` | TESTED, WORKING | Lists available reports |
| Informer tester | `Keyedin/test_informer.py` | TESTED, PARTIAL | Tests Informer API |
| Informer accessor | `Keyedin/access_informer.py` | TESTED, PARTIAL | Accesses Informer |

**Root cause:** GWT-RPC uses a specific serialization format (`7|0|22|...`) with policy file hashes (`327E0F303D0CA463050DC31340CFE01D`). The `getData` payload must exactly match the server's expected format. All 10+ PowerShell test scripts tried different payload formats — all got 500 errors.

**Next steps:**
1. Capture a WORKING `getData` request from the browser using Chrome DevTools Network tab
2. Replay that exact payload programmatically
3. OR: Use Informer's built-in export/download buttons via Playwright automation

---

## Pipeline 7: MCP Server (Claude Integration)

| Status | **BUILT, NOT VALIDATED** |
|--------|------------------------|

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| Secure MCP server (v2) | `Keyedin/KEYEDIN MCP/keyedin_mcp_server_secure.py` | BUILT | 533 lines, 7 tools |
| MCP validation | `Keyedin/KEYEDIN MCP/keyedin_mcp_validation.py` | BUILT | Validation tests |
| MCP quick setup | `Keyedin/KEYEDIN MCP/keyedin_quick_setup.py` | BUILT | Setup script |
| MCP test | `Keyedin/KEYEDIN MCP/keyedin_test_now2.py` | BUILT | Quick test |
| V1 MCP server (broken) | `Keyedin/KEYEDIN MCP/v1/Broke V1 (CLAUDE 4)/keyedin_mcp_server.py` | FAILED | Labeled "Broke V1" |
| V1 resilient agent | `Keyedin/KEYEDIN MCP/v1/Broke V1 (CLAUDE 4)/keyedin_resilient_agent.py` | FAILED | |
| V1 deployment | `Keyedin/KEYEDIN MCP/v1/Broke V1 (CLAUDE 4)/Deploy-KeyedInAgent.ps1` | FAILED | |
| V1 export test | `Keyedin/KEYEDIN MCP/v1/Broke V1 (CLAUDE 4)/test_export.py` | FAILED | |

**Next steps:** Test v2 MCP server from Brady's PC with active KeyedIn session.

---

## Pipeline 8: Architecture Discovery

| Status | **BUILT, PARTIALLY RUN** |
|--------|------------------------|

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| Architecture mapper | `Keyedin/KEYEDIN MCP/discovery/keyedin_architecture_mapper.py` | BUILT | 669 lines, maps 18 sections |
| Discovery analyzer | `Keyedin/KEYEDIN MCP/discovery/analyze_discovery.py` | BUILT | Analyzes discovery output |
| Discovery runner | `Keyedin/KEYEDIN MCP/discovery/run_complete_discovery.py` | BUILT | Full discovery automation |
| Discovery monitor | `Keyedin/KEYEDIN MCP/discovery/monitor_discovery.py` | BUILT | Progress monitoring |
| Button finder | `Keyedin/KEYEDIN MCP/discovery/find_button.py` | BUILT | UI element discovery |
| Report generators | `Keyedin/KEYEDIN MCP/discovery/report_generators.py` | BUILT | Generates discovery reports |
| Test discovery | `Keyedin/KEYEDIN MCP/discovery/test_discovery.py` | BUILT | Tests discovery flow |
| Login debug | `Keyedin/KEYEDIN MCP/discovery/test_login_debug.py` | BUILT | Login troubleshooting |
| Investigator v5 | `Keyedin/KEYEDIN MCP/Test/keyedin_investigator_v5.py` | BUILT | Investigation tool |
| Manual login mapper | `Keyedin/KEYEDIN MCP/Test/keyedin_manual_login_mapper.py` | BUILT | Maps login flow |
| KeyedIn module | `Keyedin/KEYEDIN MCP/Test/keyedin.py` | BUILT | Core module |
| Discovery data (HTML) | `Keyedin/..KeyedIn_System_Map/discovery_data/html_captures/` | CAPTURED | Home page HTML |

**Next steps:** Run full architecture discovery from VPN-connected PC.

---

## Pipeline 9: Login Flow Investigation

| Status | **COMPLETED** |
|--------|--------------|

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| Login flow investigator | `Keyedin/investigate_login_flow.py` | COMPLETED | Full login flow mapped |
| Login investigator | `Keyedin/investigate_login.py` | COMPLETED | Login page analysis |
| Login page finder | `Keyedin/find_actual_login.py` | COMPLETED | Actual login URL found |
| Corrected login | `Keyedin/corrected_login.py` | COMPLETED | Fixed login script |
| Selenium login | `Keyedin/selenium_login.py` | COMPLETED | Selenium-based login |
| Selenium entry | `Keyedin/selenium_enter.py` | COMPLETED | Form entry automation |
| Selenium fixed | `Keyedin/selenium_fixed.py` | COMPLETED | Fixed Selenium version |
| Manual submit | `Keyedin/manual_submit.py` | COMPLETED | Manual form submission |
| Simple capture | `Keyedin/simple_capture.py` | COMPLETED | Simple session capture |
| Auto login capture | `Keyedin/auto_login_capture.py` | COMPLETED | Automated login capture |
| Form debugger | `Keyedin/debug_form.py` | COMPLETED | Form field debugging |
| Login page HTML | `Keyedin/login_page.html` | CAPTURED | |
| Login start HTML | `Keyedin/login_start_page.html` | CAPTURED | |
| Actual login HTML | `Keyedin/actual_login_page.html` | CAPTURED | |
| Login success HTML | `Keyedin/login_success.html` | CAPTURED | |
| Logged-in HTML | `Keyedin/logged_in_page.html` | CAPTURED | |
| After login HTML | `Keyedin/after_login.html` | CAPTURED | |
| Chrome logged-in HTML | `Keyedin/chrome_logged_in.html` | CAPTURED | |
| Main page HTML | `Keyedin/MAIN.html` | CAPTURED | |

**Conclusion:** Login is direct POST to `https://eaglesign.keyedinsign.com` with `USERNAME`, `PASSWORD`, `SECURE` fields. Returns 5 cookies.

---

## Pipeline 10: Live Test Suite

| Status | **BUILT, NOT RUN** |
|--------|-------------------|

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| All-in-one test script | `recon-results/run_all_tests.py` | BUILT | Zero-dependency, 5 tests |
| Network location test | `recon-results/01-network-location.md` | BLOCKED | Needs VPN |
| Test results template | `RECON-TEST-RESULTS.md` | CREATED | Awaiting live results |

**Tests included:**
1. DNS resolution + network path analysis
2. Direct POST authentication
3. 6 export endpoint tests
4. Informer BI SSO probe
5. Quote entry read test

**Next steps:** Brady runs `python run_all_tests.py --username BRADYF --quote 39430` from VPN-connected PC.

---

## Pipeline 11: Benchmark Cost Analysis

| Status | **DATA PRESENT, MANUALLY SOURCED** |
|--------|-----------------------------------|

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| Cost history (Part 209-0385) | `Benchmark/storage/-Audit-/2025/209-0385.../Cost History/Group 1.txt` | DATA PRESENT | 30 WOs incl 68441-68414 |
| Cost summary CSV (Part 307-0267) | `Benchmark/storage/-Audit-/2025/307-0267.../Cost Summaries DETAILED *.csv` | DATA PRESENT | Full detail with all cost fields |
| Cost summary PDFs (12+ parts) | `Benchmark/storage/-Audit-/2025/*/Cost Summary/*.pdf` | DATA PRESENT | PDF format |
| Cost history TXT (12+ parts) | `Benchmark/storage/-Audit-/2025/*/Cost History/Group *.txt` | DATA PRESENT | WO number listings |
| Audit prompt | `Benchmark/storage/-Audit-/2025/AuditPrompt.txt` | PRESENT | Analysis instructions |
| Cost history format prompt | `Benchmark/storage/-Audit-/2025/CostHistoryFormatPrompt.txt` | PRESENT | Data format spec |
| Cost history prompt | `Benchmark/storage/-Audit-/2025/CostHistoryPrompt.txt` | PRESENT | Analysis prompt |
| Complete analysis reports | `Benchmark/storage/-Audit-/2025/*_complete_analysis.txt` | PRESENT | AI-generated analyses |
| Master cost summaries PDF | `Benchmark/storage/-Audit-/2025/2025 Cost Summaries By Part Number.pdf` | PRESENT | All parts combined |

**Key data:** This is the ONLY source of properly formatted, field-complete cost summary data. All programmatic extraction attempts failed to capture the same level of detail.

---

## Summary

| Pipeline | Components | Tested | Working | Broken | Untested |
|----------|-----------|--------|---------|--------|----------|
| 1. Auth (Main) | 8 | 6 | 6 | 0 | 2 |
| 2. Auth (Informer) | 6 | 4 | 4 | 0 | 2 |
| 3. Endpoint Discovery | 5 | 5 | 5 | 0 | 0 |
| 4. CGI/MVI Read | 18 | 16 | 15 | 1 | 2 |
| 5. Cost Summary | 7 | 5 | 0 | 5 | 2 |
| 6. Informer GWT-RPC | 18 | 14 | 6 | 8 | 4 |
| 7. MCP Server | 8 | 0 | 0 | 4 | 4 |
| 8. Architecture Discovery | 12 | 0 | 0 | 0 | 12 |
| 9. Login Investigation | 19 | 19 | 19 | 0 | 0 |
| 10. Live Test Suite | 3 | 0 | 0 | 0 | 3 |
| 11. Benchmark Cost | 9 | N/A | N/A | N/A | N/A |
| **TOTALS** | **113** | **69** | **55** | **18** | **31** |

**81 Python scripts + 12 PowerShell scripts = 93 total automation scripts**

---

*Component inventory complete. Every file path verified via repo scan.*
