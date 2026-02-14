# KeyedIn / KIMCO ERP Integration Recon — Findings Document

**Date:** 2026-02-14
**Status:** Research Complete — Ready for On-Site Validation
**For:** Eagle Sign Co. (Brady F.)
**Purpose:** Identify every viable method to programmatically read/write data in KeyedIn Manufacturing ERP

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Product Identity & Lineage](#product-identity--lineage)
3. [Technology Stack Findings](#technology-stack-findings)
4. [Integration Vectors — Ranked by Feasibility](#integration-vectors--ranked-by-feasibility)
5. [Specific Next Steps for Top 3 Vectors](#specific-next-steps-for-top-3-vectors)
6. [What Brady Needs to Check On-Site](#what-brady-needs-to-check-on-site)
7. [Questions to Ask KIMCO Vendor](#questions-to-ask-kimco-vendor)
8. [Dead Ends & Ruled Out Approaches](#dead-ends--ruled-out-approaches)
9. [Sources](#sources)

---

## Executive Summary

**The product Eagle Sign uses is now called KIMCO ERP** (formerly KeyedIn Sign / KeyedIn Manufacturing). It is a cloud-hosted, multi-tenant SaaS application built on **.NET / C# / SQL Server / Microsoft Azure**. The company KIMCO, LLC operates independently after the KeyedIn Projects (PPM) side was acquired by Sciforma in 2023.

**Three critical findings:**

1. **KIMCO explicitly advertises "open APIs" and "open architecture" with "unlimited integration capability."** No public API documentation exists, but KIMCO's vendor team can provide it. This is the single most important vector to pursue.

2. **The "Advanced BI" module includes "Live Excel" — a real-time data connection from KIMCO to Excel spreadsheets.** This means there is already a data extraction pathway built into the product that Eagle Sign may already have access to.

3. **KIMCO uses Jitterbit iPaaS for integration middleware.** Jitterbit can expose any KIMCO data as REST APIs. If Eagle Sign doesn't have Jitterbit configured, KIMCO's team can enable it.

**Bottom line:** The integration is not impossible — it's just undocumented publicly. The vendor has the capability; the question is cost and willingness.

---

## Product Identity & Lineage

This is critical context that resolves confusion about what product Eagle Sign actually uses.

### Evolution Timeline

| Year | Name | Event |
|------|------|-------|
| 2006 | **DataSIGN** | Founded as sign-industry ERP. Pioneer in the space. |
| 2011 | **KeyedIn Solutions** | Parent company founded by Lauri Klaus (ex-Epicor, 20 years). HQ: Minneapolis, MN. |
| ~2012 | **KeyedIn Sign** | DataSIGN rebranded under KeyedIn Solutions umbrella. |
| 2012 | **KeyedIn Manufacturing** | Created after acquisition of ICEBERG (Irish R&D firm), inventor of the Rapid Application Development Process Platform. |
| 2015 | **KeyedIn Manufacturing Cloud** | Full cloud SaaS launch on Azure with Konfigure aPaaS. |
| 2016 | **Advanced BI** launched | Live Excel, custom reports, dashboards for sign manufacturers. |
| 2018 | **API v3.0** launched | For KeyedIn Projects (PPM/PSA). Manufacturing API details unclear. |
| 2022 | **KeyedIn Manufacturing 7.0** | Major relaunch on .NET 5, Azure, multi-currency, multi-plant. |
| 2023 | **Sciforma acquires KeyedIn PPM** | STG Partners PE deal. Only the Projects/PPM side was acquired. |
| 2023 | **KIMCO, LLC formed** | Manufacturing/Sign ERP carved out as independent company. Formed from original DataCom shareholders + Klaus Enterprises. |
| 2024 | **KIMCO at IMTS** | Exhibited at International Manufacturing Technology Show. |

### Key Distinction

- **KeyedIn Projects** (PPM/PSA) → merged into **Sciforma** → has public API docs at `coreapi.keyedinprojects.com/apidocs/`
- **KeyedIn Manufacturing / KeyedIn Sign** → became **KIMCO, LLC** → operates at `kimco.io` / `keyedinerp.com`
- These are **different products on different code bases** under different ownership
- Eagle Sign uses the **KIMCO** (formerly KeyedIn Sign/Manufacturing) product

### Known URLs

| URL | Purpose |
|-----|---------|
| `kimco.io` | KIMCO marketing website |
| `keyedinerp.com` | KIMCO marketing website (alternate) |
| `live.kimcoerp.com` | **Live production instance** |
| `prototype.kimcoerp.com` | Prototype/staging instance |
| `go.keyedinerp.com` | Marketing/demo landing pages |

**[CONFIRM ON-SITE]:** What is the exact URL Eagle Sign uses to access their ERP? Is it `live.kimcoerp.com` or a custom subdomain?

---

## Technology Stack Findings

### Confirmed (with sources)

| Layer | Technology | Source |
|-------|-----------|--------|
| **Language** | C# / .NET 5+ | [KIMCO website](https://www.kimco.io/), [GlobeNewsWire 2022](https://www.globenewswire.com/news-release/2022/03/16/2404466/0/en/) |
| **Database** | SQL (Microsoft SQL Server / Azure SQL) | [KIMCO website](https://www.kimco.io/enterprise-software-solutions): "Built on standard SQL/MS/Azure/.NET" |
| **Cloud** | Microsoft Azure | Multiple sources confirm Azure partnership |
| **Architecture** | Multi-tenant SaaS | [GlobeNewsWire 2015](https://www.globenewswire.com/news-release/2015/11/09/785349/36362/en/) |
| **Platform** | KeyedIn Konfigure aPaaS | Drag-and-drop app builder, acquired from ICEBERG (Ireland) |
| **Integration middleware** | Jitterbit iPaaS | [Jitterbit case study](https://www.jitterbit.com/case-study/keyedin/) |
| **Auth** | Google SSO (for Eagle Sign) | Per task description — green "Sign In" button |
| **Deployment** | Cloud-hosted SaaS (no on-prem option found) | All marketing emphasizes cloud-native |
| **Security** | Dimension Data partnership | [KeyedIn press release](https://www.globenewswire.com/news-release/2015/11/09/785349/36362/en/) |
| **BI/Reporting** | Advanced BI with Live Excel | [GlobeNewsWire 2016](https://www.globenewswire.com/news-release/2016/04/20/830822/10161989/en/) |

### Suspected [LOW CONFIDENCE]

| Item | Reasoning |
|------|-----------|
| **Azure SQL Database** as the specific DB engine | .NET + Azure stack strongly implies Azure SQL, but could be SQL Server on Azure VMs |
| **SPA architecture** (Single Page Application) | Modern .NET web apps typically use SPA frontends (Angular/React/Blazor), but the `QUOTE.ENTRY.DETAILS?QUOTENO=` URL pattern could suggest server-rendered pages or a hybrid |
| **OAuth 2.0 / OpenID Connect** for auth | The KeyedIn Projects API uses OAuth 2.0 via IdentityServer. KIMCO may share this auth infrastructure |
| **IIS web server** | Standard for .NET apps on Azure, but Azure App Service abstracts this |

### The URL Pattern Mystery

The URL pattern `QUOTE.ENTRY.DETAILS?QUOTENO={#}&DEPTNO={code}` with ALL-CAPS dot-separated names is distinctive. Initial hypothesis was a Pick/MultiValue database system, but **no evidence links KeyedIn/KIMCO to Pick databases.** More likely explanations:

1. **Legacy naming convention** from the original DataSIGN (2006) codebase, carried forward through rebrands
2. **Konfigure aPaaS naming pattern** — the platform auto-generates screen names from entity definitions
3. **Custom routing convention** in the .NET application

This URL pattern does NOT necessarily indicate a legacy database — it's likely just a URL routing convention in the application layer.

---

## Integration Vectors — Ranked by Feasibility

### Vector 1: KIMCO's "Open API" (Direct Vendor Engagement)

| Attribute | Assessment |
|-----------|------------|
| **Feasibility** | **8/10** |
| **Risk** | Low — vendor-supported path |
| **Effort** | Medium — need vendor cooperation + documentation |
| **Enables** | Read/write on all modules (quotes, orders, inventory, production) |
| **Confidence** | MEDIUM — API exists per marketing, but no public docs |

**Evidence:**
- KIMCO website states: "open APIs" and "open architecture allows for unlimited integration capability"
- "Built on standard SQL/MS/Azure/.NET, supports BYOD, iPaaS, workflow-driven, low-code/no-code"
- KeyedIn Projects has a documented REST API with OAuth 2.0 — KIMCO likely has something similar
- Previous integrations exist with QuickBooks, Sage Live, Salesforce, Intacct

**Why this is #1:** If KIMCO provides API documentation, this solves everything cleanly. The API already exists — it's just not publicly documented. Every modern .NET/Azure SaaS app has a REST API the frontend calls.

**Risk factors:**
- KIMCO may charge for API access or require a higher subscription tier
- API might be limited in scope (read-only, or only certain modules)
- Documentation quality may be poor

---

### Vector 2: Hidden/Internal API Discovery (Browser DevTools)

| Attribute | Assessment |
|-----------|------------|
| **Feasibility** | **9/10** |
| **Risk** | Low-Medium — using existing session, reading not writing |
| **Effort** | Low — just open DevTools and observe |
| **Enables** | Reveals the actual API the frontend uses |
| **Confidence** | HIGH — every web app makes API calls |

**Evidence:**
- KIMCO is a modern web application on .NET/Azure
- The browser MUST make HTTP requests to load/save data
- These requests reveal the internal API structure, endpoints, and payloads
- Session cookies from a normal login can authenticate API calls

**Method:**
1. Log into KIMCO normally in Chrome
2. Open DevTools → Network tab → filter XHR/Fetch
3. Navigate through key workflows: open a quote, add a line item, save
4. Record every API call: URL, method, headers, request/response body
5. Document the API surface area

**Why this is #2:** This is the fastest path to understanding what's actually possible. Even if KIMCO refuses to provide API docs, the browser is already using the API. This can be done TODAY.

**Risk factors:**
- Internal APIs are undocumented and may change without notice
- Using undocumented APIs may violate KIMCO's Terms of Service
- Some operations may have CSRF protections that complicate programmatic access
- Rate limiting or anomaly detection could flag automated requests

---

### Vector 3: Advanced BI / Live Excel Data Connection

| Attribute | Assessment |
|-----------|------------|
| **Feasibility** | **7/10** |
| **Risk** | Very Low — built-in, vendor-supported feature |
| **Effort** | Low — configuration, not development |
| **Enables** | Read access to all reporting data |
| **Confidence** | MEDIUM — confirmed feature, but details unknown |

**Evidence:**
- KeyedIn Sign announced "Advanced BI" in 2016 with "Live Excel" capability
- "The ability to use Live Excel to easily export and manipulate real-time data in a spreadsheet"
- Creative Sign Designs (customer) reported "over 400 custom reports" using Advanced BI
- If Live Excel connects to a data source, that connection can potentially be reused programmatically

**Method:**
1. Check if Eagle Sign has the Advanced BI license/module enabled
2. If yes: set up Live Excel, identify the connection type (ODBC? OData? direct SQL?)
3. The underlying data connection may be usable from Python (pyodbc, requests, etc.)
4. Even if it's only Excel-based, Power Automate can read Excel files automatically

**Why this is #3:** This is a vendor-supported data extraction path that may already be available. It's read-only, but read access solves the biggest pain point (getting quote data out).

---

### Vector 4: Jitterbit iPaaS Integration

| Attribute | Assessment |
|-----------|------------|
| **Feasibility** | **6/10** |
| **Risk** | Low — vendor-supported, standard integration pattern |
| **Effort** | High — requires Jitterbit license, configuration, and KIMCO cooperation |
| **Enables** | Read/write via API, integration with any other system |
| **Confidence** | MEDIUM — KIMCO uses Jitterbit internally, but unclear if available to customers |

**Evidence:**
- [Jitterbit case study](https://www.jitterbit.com/case-study/keyedin/): KeyedIn uses Jitterbit for their integration layer
- "Development and engineering teams simply leverage the Jitterbit API platform to quickly expose data as APIs"
- KIMCO planned to extend Jitterbit integration to manufacturing customers

**Method:**
1. Ask KIMCO if Jitterbit integration is available for Eagle Sign's instance
2. If yes: Jitterbit can expose KIMCO data as REST APIs
3. APEX can then call those REST APIs directly
4. Jitterbit handles auth, data mapping, and error handling

**Risk factors:**
- Additional cost for Jitterbit license
- Requires KIMCO to configure connectors
- Jitterbit adds another dependency to the stack

---

### Vector 5: Browser Automation (Playwright with Persistent Context)

| Attribute | Assessment |
|-----------|------------|
| **Feasibility** | **7/10** |
| **Risk** | Medium — fragile, depends on UI stability |
| **Effort** | High — need to map DOM, handle SSO, build resilient selectors |
| **Enables** | Full read/write — anything a human can do |
| **Confidence** | HIGH — Playwright persistent context handles Google SSO |

**Evidence:**
- Previous automation attempts failed due to Google SSO and UI navigation issues
- Playwright's `launchPersistentContext` with `userDataDir` solves the SSO problem:
  1. First run: manual Google login in visible browser, session saved to disk
  2. Subsequent runs: session cookies restored automatically, no login needed
- [Playwright docs](https://playwright.dev/python/docs/auth): "Reusing authenticated state covers cookies, local storage, and IndexedDB-based authentication"

**Method:**
1. Use Playwright Python with `launchPersistentContext(user_data_dir="./browser-profile", headless=False)`
2. First time: manually complete Google SSO login. Browser profile saves session.
3. Map the DOM structure of key pages using `page.content()` and screenshots
4. Build selectors for quote entry fields (ITEM_TYPE, ITEM_NO, QTY, COST, MARKUP)
5. Automate the workflow: navigate to quote, read data, fill fields, save

**Why previous attempts failed and how to fix:**
- Google SSO requires a visible browser for initial login — `headless=False` is mandatory for first run
- After initial login, persistent context preserves the Google session
- Screenshots before interaction prevent blind navigation
- `page.wait_for_load_state('networkidle')` handles dynamic content loading

**Risk factors:**
- UI changes break selectors (brittle)
- Google SSO session may expire (typically 7-14 days, then manual re-login needed)
- Performance: each operation requires full page loads
- Cannot run in headless mode for initial auth

---

### Vector 6: Power Automate Desktop (RPA)

| Attribute | Assessment |
|-----------|------------|
| **Feasibility** | **6/10** |
| **Risk** | Low-Medium — Microsoft-supported, but fragile UI automation |
| **Effort** | Medium — visual flow builder, less coding required |
| **Enables** | Full read/write — anything a human can do |
| **Confidence** | MEDIUM |

**Evidence:**
- Eagle Sign has M365 — Power Automate Desktop is included with E3/E5 licenses
- PAD can automate any web application including those with Google SSO
- PAD handles "legacy line-of-business applications, homegrown tools, niche software packages"
- Can bridge to Power Automate cloud flows for scheduling and triggering

**Method:**
1. Confirm Eagle Sign's M365 license includes Power Automate Desktop
2. Install PAD on a workstation with access to KIMCO
3. Record UI flows for key operations (open quote, read data, enter line items)
4. Use PAD's web recorder to capture selectors automatically
5. Schedule flows via Power Automate cloud for batch operations

**Advantages over Playwright:**
- No coding required — visual flow builder
- Microsoft-supported tool with enterprise features
- Integrates with Power Automate cloud, SharePoint, Teams
- Eagle Sign may already have the license

**Disadvantages:**
- Runs only on Windows desktop (requires a logged-in session)
- Fragile UI automation — same selector issues as Playwright
- Slower than API-based integration
- Limited error handling compared to custom code

---

### Vector 7: Direct Database Access

| Attribute | Assessment |
|-----------|------------|
| **Feasibility** | **2/10** |
| **Risk** | High — could break things, likely violates ToS |
| **Effort** | Low (if accessible) to impossible (if not) |
| **Enables** | Full read access to all data |
| **Confidence** | LOW — cloud SaaS typically blocks direct DB access |

**Evidence:**
- KIMCO is a multi-tenant SaaS hosted on Azure
- No evidence of on-premise deployment option
- No evidence of customer-accessible database connections
- "Built on standard SQL/MS/Azure/.NET" confirms SQL backend but doesn't imply direct access

**Assessment:**
Direct database access is almost certainly not available for a cloud-hosted multi-tenant SaaS product. KIMCO would not expose their shared database infrastructure to individual customers.

**Exception:** If Eagle Sign has an **on-premise** or **dedicated instance** (unlikely but worth checking), direct DB access could be possible.

---

### Vector 8: Scheduled Report Export + PDF Parsing

| Attribute | Assessment |
|-----------|------------|
| **Feasibility** | **5/10** |
| **Risk** | Very Low — using built-in features |
| **Effort** | Medium — need to parse PDF output |
| **Enables** | Read-only for report data |
| **Confidence** | MEDIUM |

**Evidence:**
- The task description confirms: Report Option='D' + Send To='P' produces detailed print output
- KIMCO has reporting/BI capabilities
- Scheduled reports may be configurable to auto-export

**Method:**
1. Set up the detailed report (Option='D', Send To='P') for each quote
2. If KIMCO supports scheduled reports: auto-export to a shared folder or email
3. Use Python (pdfplumber, tabula-py) to parse the PDF output
4. Extract structured data from the known PDF layout

**Limitations:**
- Read-only (no write capability)
- PDF parsing is fragile if layout changes
- Limited to data available in reports
- Not real-time — batch only

---

## Vector Summary Table

| # | Vector | Feasibility | Risk | Effort | Read | Write | Recommended? |
|---|--------|-------------|------|--------|------|-------|--------------|
| 1 | KIMCO Open API (vendor) | 8 | Low | Medium | Yes | Yes | **YES — #1 priority** |
| 2 | Hidden API (DevTools) | 9 | Low-Med | Low | Yes | Yes | **YES — do immediately** |
| 3 | Advanced BI / Live Excel | 7 | Very Low | Low | Yes | No | **YES — quick win** |
| 4 | Jitterbit iPaaS | 6 | Low | High | Yes | Yes | Maybe — depends on cost |
| 5 | Playwright Automation | 7 | Medium | High | Yes | Yes | Fallback if no API |
| 6 | Power Automate Desktop | 6 | Low-Med | Medium | Yes | Yes | Fallback alternative |
| 7 | Direct Database | 2 | High | Varies | Yes | No | No — cloud SaaS blocks this |
| 8 | Report/PDF Parsing | 5 | Very Low | Medium | Yes | No | Supplement only |

---

## Specific Next Steps for Top 3 Vectors

### Next Steps: Vector 1 — KIMCO Open API

**Who:** Brady
**Timeline:** This week

1. **Contact KIMCO sales/support.** Ask specifically:
   - "We need API access to read and write quote data. What are our options?"
   - "Is the API included in our current subscription or is it an add-on?"
   - "Can we get API documentation?"
   - "Do you have a developer portal or sandbox environment?"
2. **Ask about Jitterbit.** "We understand you use Jitterbit for integrations. Can that be made available to us?"
3. **Ask about Advanced BI.** "Do we have the Advanced BI module? Can we use Live Excel?"
4. **Document the response.** Whatever they say, write it down verbatim. Even a "no" is useful — it tells us which vectors to invest in.

### Next Steps: Vector 2 — Hidden API Discovery

**Who:** Developer (can be done remotely via screen share with Brady)
**Timeline:** 30 minutes

1. **Brady logs into KIMCO in Chrome normally**
2. **Open DevTools** (F12) → **Network tab** → check "Preserve log" → filter to "Fetch/XHR"
3. **Navigate through a typical workflow:**
   - Open an existing quote
   - View line items
   - Add a new line item (don't save if you don't want to)
   - Run a report
4. **For each API call captured, document:**
   - Full URL (e.g., `live.kimcoerp.com/api/quotes/123`)
   - HTTP method (GET, POST, PUT)
   - Request headers (especially `Authorization`, `Cookie`, `Content-Type`)
   - Request body (for POST/PUT)
   - Response body structure
5. **Export the HAR file** (Network tab → gear icon → "Export HAR...") and share it
6. **Check for Swagger/OpenAPI:** Try navigating to:
   - `{base-url}/swagger`
   - `{base-url}/swagger/index.html`
   - `{base-url}/api-docs`
   - `{base-url}/.well-known/openid-configuration`
   - `{base-url}/api/v1`
   - `{base-url}/health`
   - These are standard .NET API documentation endpoints

### Next Steps: Vector 3 — Advanced BI / Live Excel

**Who:** Brady
**Timeline:** 15 minutes

1. **Check the KIMCO menu/settings** for any of these:
   - "Advanced BI" or "Business Intelligence"
   - "Reports" → look for "Live Excel" or "Export to Excel"
   - "Settings" → "Integrations" or "Data Connections"
   - "Admin" → "API" or "Webhooks" or "Data Export"
2. **If Live Excel is available:**
   - Open it and note what happens — does it download an Excel file? Open a connection?
   - Check the Excel file for any data connection strings (Data tab → Connections)
3. **If Advanced BI is not enabled:**
   - Ask KIMCO about enabling it and what it costs

---

## What Brady Needs to Check On-Site

These are things that can only be determined from inside Eagle Sign's network or with access to their KIMCO instance.

### Priority 1: Identify the Exact Product

- [ ] What URL does Eagle Sign use to access KIMCO/KeyedIn? (e.g., `live.kimcoerp.com`, custom subdomain?)
- [ ] What version number is displayed anywhere in the UI? (Help → About, or footer text)
- [ ] Is this called "KeyedIn Sign," "KeyedIn Manufacturing," or "KIMCO" in the application?
- [ ] What subscription tier/plan does Eagle Sign have?

### Priority 2: Network/API Discovery (30 minutes)

- [ ] Open Chrome DevTools (F12) → Network tab while using the ERP
- [ ] Record network activity while opening a quote, adding line items, saving
- [ ] Export the HAR file and share it
- [ ] Try navigating to `{your-erp-url}/swagger` — does anything load?
- [ ] Try navigating to `{your-erp-url}/.well-known/openid-configuration`
- [ ] Check what domain the API calls go to (same domain? different API subdomain?)

### Priority 3: Check Available Features

- [ ] Is "Advanced BI" available in the menu?
- [ ] Is "Live Excel" available anywhere?
- [ ] Are there any "Export" or "Download CSV" buttons on list/report pages?
- [ ] Is there an "Admin" section with integration/API settings?
- [ ] Is there a "Settings" → "API Keys" or "Webhooks" section?
- [ ] Check "Reports" section — what report formats are available? (PDF, CSV, Excel?)

### Priority 4: Authentication Details

- [ ] Does login use Google SSO exclusively, or is there a username/password option?
- [ ] If Google SSO: is this the only auth method, or can a service account use password auth?
- [ ] After login, does the URL change to a different domain?
- [ ] How long does a session last before you need to re-authenticate?

### Priority 5: Infrastructure Check

- [ ] Is there any on-premise server at Eagle Sign related to the ERP?
- [ ] Does Eagle Sign have any database servers (SQL Server) that might be connected to KIMCO?
- [ ] Is there any middleware, VPN, or special network configuration for ERP access?
- [ ] What M365 license tier does Eagle Sign have? (affects Power Automate Desktop availability)

---

## Questions to Ask KIMCO Vendor

### Critical (Ask First)

1. **"What API access is available with our subscription? Is there a REST API we can use to read/write quote and order data?"**

2. **"Is there API documentation or a developer portal? We're building an internal automation system and need to integrate with KIMCO."**

3. **"What does your integration package cost? We need to automate quote entry and data extraction."**

4. **"Do you support Jitterbit integration for customer instances? Can we get Jitterbit connectors configured for our account?"**

5. **"Is the Advanced BI module with Live Excel included in our plan? If not, what does it cost to add?"**

### Important (Ask Second)

6. "What authentication methods are available for API access? OAuth 2.0? API keys?"

7. "Is there a sandbox/test environment we can use for integration development?"

8. "Do you have any pre-built integrations or connectors for common business systems?"

9. "Can we get read-only database access or an ODBC connection for reporting purposes?"

10. "Do other customers have automated integrations with KIMCO? Can you share any case studies or examples?"

### Strategic (Ask Third)

11. "What is your API roadmap? Are you planning to expand API capabilities?"

12. "Do you have a partner ecosystem of consultants who specialize in KIMCO integrations?"

13. "Would you be open to a co-development arrangement where we help document/test APIs in exchange for early access?"

14. "What are the Terms of Service regarding automated access to our instance?"

---

## Dead Ends & Ruled Out Approaches

### 1. Pick/MultiValue Database Connection
- **Hypothesis:** The `QUOTE.ENTRY.DETAILS` URL pattern suggested a Pick/MultiValue database (UniVerse, jBASE, D3)
- **Result:** No evidence whatsoever linking KeyedIn/KIMCO to Pick databases
- **Conclusion:** The URL pattern is a application-level naming convention, not a database indicator
- **Status:** RULED OUT

### 2. Direct SQL Database Access
- **Hypothesis:** If the database is on Eagle Sign's servers, direct SQL access would solve everything
- **Result:** KIMCO is cloud-hosted multi-tenant SaaS on Azure. No on-premise option found.
- **Conclusion:** Direct database access is not available for cloud deployments
- **Status:** RULED OUT (unless on-site check reveals on-prem infrastructure)

### 3. KeyedIn Projects API for Manufacturing
- **Hypothesis:** The documented KeyedIn Projects API (`coreapi.keyedinprojects.com/apidocs/`) might work for Manufacturing
- **Result:** KeyedIn Projects and KeyedIn Manufacturing are different products. After the Sciforma acquisition, they are under different companies entirely. The Projects API does not apply to KIMCO.
- **Conclusion:** Cannot use Projects API for Manufacturing
- **Status:** RULED OUT

### 4. Public API Documentation
- **Hypothesis:** KIMCO might have public API docs
- **Result:** Extensive searching found zero public API documentation for KIMCO/KeyedIn Manufacturing. The "open API" claim on their website is marketing-facing, not developer-facing.
- **Conclusion:** API docs exist but are behind vendor/customer access
- **Status:** Dead end publicly; vendor engagement required

### 5. Third-Party Review Sites for Integration Intel
- **Hypothesis:** User reviews might reveal integration details
- **Result:** KeyedIn Manufacturing has virtually no user reviews on G2, Capterra, or other review sites. "No ratings yet" on Capterra.
- **Conclusion:** No community intelligence available via review sites
- **Status:** Dead end

---

## Sources

### Primary Sources

- [KIMCO Website — Features](https://www.kimco.io/features) — "open APIs, SQL/MS/Azure/.NET, iPaaS, BYOD"
- [KIMCO Website — Enterprise Solutions](https://www.kimco.io/enterprise-software-solutions) — "open architecture, unlimited integration"
- [KIMCO Website — Sign Manufacturing](https://www.kimco.io/sign-manufacturing-software) — sign industry focus
- [GlobeNewsWire — KeyedIn Manufacturing 7.0](https://www.globenewswire.com/news-release/2022/03/16/2404466/0/en/) — .NET 5, Azure, Konfigure aPaaS
- [GlobeNewsWire — KeyedIn Manufacturing Cloud Launch](https://www.globenewswire.com/news-release/2015/11/09/785349/36362/en/) — cloud architecture, Dimension Data security
- [GlobeNewsWire — Advanced BI for Sign Manufacturers](https://www.globenewswire.com/news-release/2016/04/20/830822/10161989/en/) — Live Excel, 400+ custom reports
- [GlobeNewsWire — KeyedIn Sign 10 Years](https://www.prweb.com/releases/2016/06/prweb13515163.htm) — DataSIGN (2006) history
- [Jitterbit Case Study — KeyedIn](https://www.jitterbit.com/case-study/keyedin/) — Jitterbit iPaaS usage
- [Enterprise Times — KeyedIn API v3.0](https://www.enterprisetimes.co.uk/2018/11/02/keyedin-updates-api/) — API capabilities
- [Enterprise Times — KeyedIn Manufacturing 7.0 Relaunch](https://www.enterprisetimes.co.uk/2022/03/18/keyedin-to-relaunch-updated-and-upgraded-manufacturing-erp/)
- [Sciforma — KeyedIn Acquisition](https://www.sciforma.com/company/acquisitions-keyedin/) — PPM merger, manufacturing carved out
- [AGC Partners — KeyedIn/Sciforma Deal](https://www.agcpartners.com/transactions/agc-partners-advises-keyedin-on-its-merger-with-sciforma-a-portfolio-company-of-stg-partners) — deal structure
- [IMTS 2024 — KIMCO ERP Exhibitor](https://directory.imts.com/8_0/exhibitor/1001744/KIMCO-ERP)
- [KeyedIn Projects API Docs](https://coreapi.keyedinprojects.com/apidocs/) — separate product, but shows KeyedIn's API patterns
- [KeyedIn Enterprise V7 Auth](https://auth.keyedinprojects.com/) — OAuth 2.0 / IdentityServer (Projects only)
- [Microsoft AppSource — KeyedIn Manufacturing](https://appsource.microsoft.com/en-us/product/web-apps/keyedinsolutionsinc1630501730514.kim)

### Technical References

- [Playwright — Authentication Docs](https://playwright.dev/python/docs/auth) — persistent context, storage state
- [Playwright — Persistent Context Guide](https://www.browserstack.com/guide/playwright-persistent-context)
- [Power Automate Desktop — Introduction](https://learn.microsoft.com/en-us/power-automate/desktop-flows/introduction)
- [Jitterbit iPaaS Documentation](https://docs.jitterbit.com/integration-studio/get-started/jitterbit-ipaas-best-practices/)

---

## Appendix: Recommended Action Plan

### Phase 1 — Immediate (This Week)

| Action | Owner | Time | Priority |
|--------|-------|------|----------|
| Open Chrome DevTools during normal KIMCO usage, capture HAR file | Brady | 30 min | **CRITICAL** |
| Try `/swagger`, `/api-docs`, `/.well-known/openid-configuration` URLs | Brady | 5 min | **CRITICAL** |
| Check for Advanced BI / Live Excel in KIMCO menu | Brady | 15 min | HIGH |
| Email KIMCO asking about API access (use questions above) | Brady | 15 min | HIGH |
| Confirm M365 license tier for Power Automate Desktop | Brady | 5 min | MEDIUM |

### Phase 2 — Next Week

| Action | Owner | Time | Priority |
|--------|-------|------|----------|
| Analyze HAR file to map internal API | Developer | 2-4 hrs | **CRITICAL** |
| If API found: build proof-of-concept to read one quote | Developer | 4-8 hrs | HIGH |
| If KIMCO responds with API docs: evaluate scope and auth | Developer | 2-4 hrs | HIGH |
| Set up Playwright persistent context with Google SSO | Developer | 2-4 hrs | MEDIUM |

### Phase 3 — Weeks 3-4

| Action | Owner | Time | Priority |
|--------|-------|------|----------|
| Build full read/write integration via best available vector | Developer | 1-2 weeks | HIGH |
| Integrate with APEX estimation pipeline | Developer | 1 week | HIGH |
| Set up monitoring and error handling | Developer | 2-3 days | MEDIUM |
| Document integration for maintenance | Developer | 1 day | MEDIUM |

---

*Document generated 2026-02-14. All findings are based on publicly available information. No systems were accessed during this research. Items marked [LOW CONFIDENCE] require on-site validation.*
