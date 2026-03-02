# Competitor Analysis

## CalcuSign (Murdoch Engineering)

### Overview
- **Company**: Murdoch Engineering (murdochengineering.com)
- **Product**: CalcuSign (calcusign.com)
- **Model**: SaaS (Software as a Service), monthly subscription
- **Coverage**: Licensed for all 50 US states
- **Technology**: Blazor/WebAssembly web application
- **USPTO Trademark**: Serial #90099380

### What CalcuSign Generates
From the USPTO trademark filing (Goods & Services description):
1. **Construction drawings** - permit-ready structural drawings
2. **Materials lists** - bill of materials for fabrication
3. **Calculation sheets** - PE-stampable engineering calculations

### What We Know
- Blazor front-end means the app runs entirely client-side in WebAssembly
- Cannot be scraped or reverse-engineered via web fetching (returns empty HTML shell)
- YouTube channel exists at youtube.com/@calcusign (tutorials unavailable to AI fetchers)
- Website at calcusign.com returns "An unhandled error has occurred" when fetched (Blazor requires browser JS engine)

### What We Don't Know
- Exact code standards implemented (likely current IBC/ASCE 7)
- Specific calculation methods (ACI 318 checks, foundation method)
- Pricing structure
- Number of users/subscribers
- Which states have PE stamp arrangements

### CalcuSign's Key Differentiator
**PE-stampable output documents** - this is their primary value proposition. Sign companies pay for the subscription because they get permit-ready calculation packages they can submit to building departments. The engineering calculations themselves are table stakes; the output format and PE stamp are what customers pay for.

---

## ABC Accutrack

### Overview
- **Company**: ABC Sign Products
- **Product**: Accutrack estimating module
- **Model**: WAaaS (Web Application as a Service)
- **Technology**: Blazor/WebAssembly web application
- **Access**: Brady (Eagle Sign Co) has login credentials

### What We Know
- **Code version**: ASCE 7-10 / IBC 2015 (2 code cycles behind current)
- Blazor front-end (same technology as CalcuSign)
- Cannot be scraped or fetched (same Blazor limitation)
- Multiple attempts to screenshot via PowerShell automation failed:
  - screenshot3.ps1: Basic Chrome focus + Ctrl+Tab + screenshot
  - screenshot4.ps1: Added Explorer minimization, snipping tool minimize, Chrome maximize
  - screenshot5.ps1: Added focus-steal prevention bypass with Alt key simulation, console hiding
  - All failed because Chrome tab switching via SendKeys was unreliable from automation

### What We Don't Know (Gaps)
- **UI layout and workflow** - what inputs are on which screens
- **Calculation methods** - what engineering checks it performs
- **Output format** - what reports/documents it generates
- **Foundation design method** - IBC 1807.3 or simplified
- **Anchor bolt checks** - basic A307 only or ACI 318 full check
- **Specific features** - materials lists, construction drawings, pricing
- **Update plans** - whether they plan to update to ASCE 7-22

### Why We Couldn't Reverse Engineer It
1. Blazor/WASM apps render entirely in the browser's JS engine - no server-side HTML
2. WebFetch tools get empty HTML shells with just Blazor bootstrap code
3. PowerShell screenshot automation couldn't reliably switch Chrome tabs
4. The app requires authentication (login credentials)

### How to Capture It (Manual Steps Needed)
Brady would need to manually:
1. Log into Accutrack in Chrome
2. Take screenshots of each screen/tab
3. Note input fields, labels, and calculation outputs
4. Document the workflow (which inputs -> which outputs)
5. Save screenshots to C:\Tools\ for AI analysis

---

## Feature Comparison Matrix

| Feature | Our Playground | CalcuSign | Accutrack |
|---------|---------------|-----------|-----------|
| **Code Version** | ASCE 7-22 / IBC 2024 | Unknown (likely current) | ASCE 7-10 / IBC 2015 |
| **Wind Load** | Full ASCE 7 formula | Yes | Yes |
| **Section Modulus** | 21 pipe + 10 sq tube | Yes | Yes |
| **Anchor Bolts** | A307 basic tensile | Unknown | Unknown |
| **ACI 318 Anchoring** | Not yet | Unknown | Unknown |
| **Foundation** | Simplified OT/slide/bear | Unknown method | Unknown |
| **IBC 1807.3** | Not yet | Unknown | Unknown |
| **Baseplate Design** | Gusset table only | Unknown | Unknown |
| **PDF Reports** | Not yet | Yes (PE-stamp) | Unknown |
| **Construction Drawings** | No | Yes | No |
| **Materials Lists** | No | Yes | Unknown |
| **Auto-Feasibility** | Yes (unique feature) | Unknown | Unknown |
| **Real-time Recalc** | Yes | Unknown | Unknown |
| **Offline Use** | Yes (single HTML file) | No (SaaS) | No (SaaS) |
| **Open Source** | Full source visible | Proprietary | Proprietary |
| **Cost** | Free | Subscription | Subscription |
| **All 50 States** | Manual input | Licensed | Unknown |

## Competitive Advantages We Have
1. **Latest code** - ASCE 7-22/IBC 2024 vs Accutrack's outdated ASCE 7-10
2. **Offline/portable** - single HTML file, works anywhere, no subscription
3. **Transparent** - all calculations visible, auditable
4. **Auto-feasibility** - instant bolt/foundation/gusset sizing from section modulus
5. **Real-time** - every input change recalculates everything immediately
6. **Free** - no subscription cost

## Competitive Gaps (What We Need)
1. **PDF reports** - the #1 feature customers pay CalcuSign for
2. **ACI 318 anchor checks** - required for code-compliant engineering
3. **IBC 1807.3 foundation** - the actual code method vs our simplified approach
4. **PE stamp workflow** - the business model differentiator
5. **Construction drawings** - CalcuSign generates these
6. **Materials lists** - CalcuSign generates these

## Next-Level Features (Nobody Has These)
Based on research, features that would leapfrog all competitors:
1. **AI-powered PDF parsing** - extract sign dimensions from shop drawings (PyMuPDF)
2. **GD&T extraction** - read tolerances from engineering drawings (OpenCV/YOLOv11)
3. **Predictive pricing analytics** - estimate project costs from engineering data
4. **3D visualization** - three-dimensional sign structure preview
5. **AR site previews** - augmented reality sign placement
6. **Automated permit integration** - submit to building departments electronically
7. **Wind speed by zip code** - auto-lookup from ASCE 7 maps
8. **Multi-code comparison** - show results under all codes simultaneously
9. **Dynamic what-if analysis** - parameter sensitivity visualization
