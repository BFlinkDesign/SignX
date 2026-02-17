# Phase 0 Gap Analysis — SignX Estimation Engine

**Generated:** 2026-02-16
**Sources:** File audit (1,072 files), 10 web research queries, 5 DuckDB warehouse queries, ABC pricing guide sections

---

## 1. MARGIN FRAMEWORK (Architectural Constraint)

This framework governs ALL estimation decisions. It is non-negotiable.

| Layer | Source | Purpose | Rule |
|-------|--------|---------|------|
| **ABC Rates** | 1974 ABC Pricing Guide (Sections 2, 4, 5, 10) | PRICING ENGINE — what customer pays | Always use when available |
| **Warehouse Actuals** | signx.duckdb (12,189 jobs, 54K labor records) | BENCHMARK — what it actually costs Eagle | Compare, never replace ABC |
| **Delta** | ABC rate - Warehouse actual | MARGIN INDICATOR | Positive delta = profit. Negative delta = margin leak. |

### Decision Rules

| Scenario | Action |
|----------|--------|
| ABC rate exists AND ABC > warehouse actual | **KEEP ABC** — the delta is profit margin |
| ABC rate exists AND ABC < warehouse actual | **FLAG as MARGIN LEAK** — investigate why actual exceeds estimate |
| ABC rate missing (no section) | **Use warehouse P50 + 20% buffer**, mark as `[PROVISIONAL]` |
| Warehouse data sparse (<10 jobs) | **Use warehouse mean + 30% buffer**, mark as `[LOW CONFIDENCE]` |
| No ABC rate AND no warehouse data | **DO NOT ESTIMATE** — flag for manual pricing |

---

## 2. ABC PRICING GUIDE — SECTION INVENTORY

### Sections Present (in abc-labor-rates-complete.md)

| Section | Coverage | Unit | Status |
|---------|----------|------|--------|
| **2A-2D** | Sheet Metal Cabinets | per SF | Complete — 6 construction types, constant 2.5h |
| **2E** | Deck Cabinets & Raceways | per LF | Complete — straight/curved rates |
| **3F** | Faux Neon Retrofit (Eagle Custom) | per LF | Complete — 0270=LF×0.31, 0340=LF×0.13 |
| **4A** | Strip Channel Letters (25"+) | per PF | Complete — 3 height ranges, 4 work codes |
| **4B** | Pan Channel Letters | per PF | Complete — 3 height ranges, 4 work codes |
| **4C** | Reverse Channel Letters | per PF | Complete — 3 height ranges, 4 work codes |
| **4D** | LED Wiring | per PF | Complete — single rate 0.015 |
| **5A** | Paint (per SF) | per SF | Complete — 1-5 color variants |
| **5B** | Raceway/Deck Cab Paint (per LF) | per LF | Complete — raceways/deck cabs |
| **10A** | Cabinet Installation | per SF | Complete — wall/roof/pipe, 1st/add'l, crew-hrs |
| **10A-g** | Letters on Deck Cabinet Install | per SF | Complete — const 2.00, rate 0.040 |
| **10A-h** | Remote Wiring | per LF | Complete — const 1.00/0.50, rate 0.043 |
| **10B** | Metal Letters Wall Install | per PF | Complete — 2 height ranges |
| **Hardware** | Raceway SF conversion | LF→SF | Complete — LF × 10 = SF, $0.58/SF |
| **Material Waste** | Waste factors | percentage | Complete — Acrylic 15%, Return 5%, Trim 5%, Back 10%, LED 5% |

### Sections MISSING

| Section | Expected Coverage | Impact | Mitigation |
|---------|-------------------|--------|------------|
| **1** | Unknown (possibly sign bodies/structures?) | Unknown | Use warehouse data `[PROVISIONAL]` |
| **3 (standard)** | Standard neon fabrication | LOW — neon is legacy, LED replaced it | Section 3F covers Eagle's faux neon retrofit |
| **6** | Unknown | Unknown | Use warehouse data `[PROVISIONAL]` |
| **7** | Unknown | Unknown | Use warehouse data `[PROVISIONAL]` |
| **8** | Unknown | Unknown | Use warehouse data `[PROVISIONAL]` |
| **9** | Unknown | Unknown | Use warehouse data `[PROVISIONAL]` |

### Missing Section Investigation

**Priority:** LOW. The existing sections cover the primary sign types that Eagle fabricates:
- Cabinets (Section 2) → ALULIT, ALUNON, MONDF cab components
- Channel Letters (Section 4) → CLLIT, CLNON
- Paint (Section 5) → applies to all types
- Installation (Section 10) → applies to all types

**Recommendation:** Check the original `ABC PRICING GUIDE 1974.xlsx` (5,738 lines) and `ABC 6th Edition Handbook.pdf` for the missing sections. The PDF reader failed in this session (pdftoppm not available), but Excel can be read.

---

## 3. WAREHOUSE DATA COVERAGE

### Sign Types with Strong Data (>100 labor-bearing jobs)

| Type | Jobs w/Labor | Confidence | ABC Coverage |
|------|-------------|------------|--------------|
| POLLIT | 461 | HIGH | Sections 2, 5, 10 (cabinet/install) |
| CLLIT | 442 | HIGH | Sections 4, 5, 10B (channel letter primary path) |
| MONDF | 188 | HIGH | Sections 2, 5, 10 (cabinet components only) |
| DIRECT | 162 | HIGH | No ABC section — `[PROVISIONAL]` |
| GEMINI | 115 | MODERATE | No ABC section — `[PROVISIONAL]` |

### Sign Types with Weak Data (<50 labor-bearing jobs)

| Type | Jobs w/Labor | Confidence | Recommendation |
|------|-------------|------------|----------------|
| AWNNON | 48 | LOW | Use warehouse P50 + 20% buffer |
| MONSF | 43 | LOW | Cross-reference with MONDF patterns |
| LED | 53 | LOW | Install-focused, use warehouse data |
| ALULIT | 31 | VERY LOW | Group with MONDF for estimation |
| ALUNON | 13 | INSUFFICIENT | Group with MONDF + 30% buffer |

### Sign Types with NO Warehouse Labor Data

These types exist in so_contracts but have insufficient labor records for profiling:
- FORMED, STLLIT, AWNILL, AWNREC, POLNON, BLDNON
- **Action:** Manual pricing only, or use closest type's profile as `[LOW CONFIDENCE]`

---

## 4. SYSTEMATIC ESTIMATION ERRORS (Warehouse Evidence)

### Universal Problems (Every Sign Type)

| Problem | Evidence | Impact |
|---------|----------|--------|
| **Installation always underestimated** | 0630 variance ranges from +1.45h (LED) to +13.98h (AWNNON) | 5-14h of uncosted labor per job |
| **Overtime never estimated** | 9200/9600 always est=0.00 but appear in 30-80% of jobs | 4-9h of invisible labor per job |
| **Travel underestimated** | 0620 variance +0.88 to +1.43h across all types | Small per-job but $50K+ annually |

### Type-Specific Critical Gaps

| Type | Code | Problem | Hours Lost |
|------|------|---------|-----------|
| **CLLIT** | 0270 Misc Fab | +56.88h average variance | This is the #1 margin leak |
| **AWNNON** | 0630 Install | +13.98h average variance | Awning installs massively undercosted |
| **POLLIT** | 0215 Structural | +11.03h average variance | Large structural fab underestimated |
| **MONSF** | 9200 Fab OT | +8.71h (never estimated) | 81% of MONSF jobs have fab overtime |
| **MONDF** | 0270 Misc Fab | +7.23h average variance | Monument misc fab consistently short |

### Margin Leak Quantification

Assuming $65/hr blended labor rate:
- CLLIT misc fab: 228 jobs × 56.88h × $65 = **$843K leaked** (investigate — likely catch-all code issue)
- AWNNON install: 44 jobs × 13.98h × $65 = **$40K leaked**
- POLLIT structural: 94 jobs × 11.03h × $65 = **$67K leaked**
- Universal OT (all types): ~1,000 jobs × 5h × $65 = **$325K leaked**

**Total estimated margin leak: >$1.2M** (with CLLIT 0270 being the largest anomaly to investigate)

---

## 5. INDUSTRY RESEARCH FINDINGS

### Modern Estimation Software

| Tool | Type | Price | Relevance |
|------|------|-------|-----------|
| shopVOX | Full shop management | $215-$366/mo | Component-based costing, QuickBooks sync |
| SignTracker | Job management | Undisclosed | Job tracking, scheduling, not estimation-focused |
| EstiMate | Sign estimation | Undisclosed | 15 sign categories, channel letter PF pricing |
| Accutrack (ABC) | Engineering only | Contact ABC | Web-based, IBC 2015 compliant. NOT pricing — structural only now |
| LED Wizard | LED layout | Undisclosed | Module counts, power calcs. Eagle already has v8 |

**Key Insight:** ABC Accutrack has evolved from a pricing calculator into a pure structural engineering tool. The 1974 pricing guide formulas are NOT available in modern Accutrack. Eagle's `abc-labor-rates-complete.md` is the only digitized version of these rates.

### CNC Impact on 1974 Rates

| Operation | 1974 Method | 2024 Method | Labor Reduction |
|-----------|-------------|-------------|----------------|
| Letter cutting | Hand shears/brake | CNC router/plasma | 30-50% |
| Cabinet fabrication | Manual layout + cut | CNC router + bend | 30-40% |
| Routing/engraving | Manual router | CNC router | 40-60% |
| Installation | Crane + crew | Crane + crew | ~0% (unchanged) |
| Painting | Spray booth | Spray booth | ~0% (unchanged) |

**Recommendation:** Apply CNC discount factor to fabrication codes (0210, 0215, 0220, 0230, 0235, 0240, 0270) but NOT to installation, painting, electrical, or vinyl codes.

### Modern Markup Standards

| Component | Markup | Source |
|-----------|--------|--------|
| Materials | 1.5x (50%) | Industry consensus |
| Labor | 1.3x (30%) | Industry consensus |
| Profit | 20-30% of total | Manufacturing standard |
| Complexity adj. | 0.90x (simple) to 1.20x (complex) | shopVOX methodology |

### Channel Letter PF Status

PF (Peripheral Feet) is **still used** for internal estimation but the industry has shifted to hybrid pricing:
- Per-letter pricing for customer quotes ($150-$550/letter)
- Per-LF for raceways ($35-$65/LF)
- LED modules by count (avg 20/letter)

**Recommendation:** Keep PF for internal ABC formula calculations. Convert to per-letter for customer-facing quotes.

### Monument Pricing Benchmarks

| Size | Industry Range | Eagle Avg (MONDF) | Eagle Avg (MONSF) |
|------|---------------|-------------------|-------------------|
| Overall | $150-$400/SF | $6,169 avg revenue | $7,192 avg revenue |
| Small (<10ft) | $5K-$10K | Matches | Matches |
| Medium (10-20ft) | $10K-$20K | Matches | Matches |
| Large (20+ft) | $20K-$50K | Matches upper range | Matches |

Eagle's monument pricing aligns with industry benchmarks. The issue is LABOR estimation, not pricing.

---

## 6. EXISTING CODE INVENTORY (Build-On vs Build-New)

### HIGH VALUE — Integrate Into Engine

| File | What to Extract | Lines |
|------|----------------|------:|
| `eagle_pricing_guide.py` | Work code→dept mapping (40+ codes), sign type enum, workflow sequences (MONDF=[0110,0200,0215,...]) | 476 |
| `sign_type_analyzer.py` | Sign type regex patterns, real labor examples | 196 |
| `eagle_analyzer_final.py` | Complete work code list with depts/phases (lines 66-106), standard rates (lines 308-316) | 880 |
| `Work Codes and Pricing.csv` | All 64 Eagle work codes with department mapping | 64 |
| `abc-labor-rates-complete.md` | Digitized ABC formulas — Sections 2, 3F, 4, 5, 10 | 244 |
| `constructioniq-frameworks.md` | Cost-to-Complete schema, variation registers, specialty trade margins 20-40% | 401 |

### MEDIUM VALUE — Reference Only

| File | Useful For | Lines |
|------|-----------|------:|
| `eagle_implementation.py` | Monument crew templates (welders=2, fab=1, elec=1, install=3) | 455 |
| `eagle_memory_cost_database.py` | CostDatabase pattern, memory-augmented estimation | 567 |
| `docs/guides/pricing-estimation.md` | General pricing methodology documentation | 311 |
| `Benchmark/` | Cat Scale production cheat sheets, delta analysis | 2,088 |

### LOW VALUE — Do Not Use

| File | Why Skip |
|------|----------|
| `setup_monument.py`, `create_monument_module.py` | ASCE 7-22 structural engineering, NOT labor estimation |
| `modules/quoting/__init__.py` | Flat-rate instant quoting, not connected to signx-takeoff |
| `contracts/signs.py` | APEX Pydantic models, different system |
| `ConstructIQ/` stubs | 81 files but mostly 13-line YouTube transcript placeholders |

---

## 7. ACCUTRACK SOFTWARE ASSESSMENT

Eagle has Accutrack v3.8.1 installed at `Eagle Data/BOT TRAINING/Estimating/ABC ESTIMATING FILE/ABC381Client/`.

### What Accutrack v3.8.1 Covers

From the readme.txt changelog (v2.5.1→v3.8.1):
- Channel letters (all types)
- Cabinets (standard and deck)
- Post & panel signs
- Awnings
- Neon → LED conversions (added in v3.x)
- Routed faces
- Wireways
- Curved frames

### Accutrack vs SignX-Takeoff

| Feature | Accutrack | SignX-Takeoff |
|---------|-----------|---------------|
| Platform | Desktop Win32 | Web (FastAPI, port 8765) |
| Data source | Hardcoded ABC rates | ABC rates + warehouse benchmarks |
| PDF extraction | No | Yes (extract PF from PDFs) |
| Warehouse comparison | No | Yes (2,443+ channel letter jobs) |
| Sign type routing | Manual selection | Automated classification |
| Margin analysis | No | Yes (ABC vs actual delta) |
| Modern API | No | REST API endpoints |

**Recommendation:** Accutrack is legacy reference software. SignX-Takeoff supersedes it by adding warehouse benchmarking, automated PDF extraction, and margin analysis. However, check if Accutrack has any rates not captured in abc-labor-rates-complete.md (particularly Sections 1, 6-9).

---

## 8. RECOMMENDED PHASE 1 PRIORITIES

### Tier 1: Build First (Highest ROI)

1. **Sign type router** — Classify incoming jobs by type using `sign_type_classifier.json` patterns
2. **Monument estimation (MONDF/MONSF)** — ABC Section 2 (cabinet components) + warehouse P50 for non-cabinet work codes
3. **Cabinet estimation (ALULIT)** — ABC Section 2 + Section 10A installation
4. **Overtime buffer** — Add automatic overtime estimate (warehouse shows 30-80% of jobs need it)

### Tier 2: Build Second

5. **Installation recalibration** — Replace current install estimates with warehouse P50 (current estimates are off by 5-14h)
6. **Directional estimation** — No ABC section. Pure warehouse-based with `[PROVISIONAL]` flag
7. **GEMINI/dimensional letters** — Lightweight profile, candidate for simplified flat-rate

### Tier 3: Investigate First

8. **CLLIT 0270 anomaly** — 56.88h variance on misc fabrication needs investigation before any changes
9. **Missing ABC sections (1, 6-9)** — Read the original xlsx/pdf for these
10. **CNC discount factors** — Need actual Eagle CNC vs hand-fab timing data to calibrate

---

## 9. DATA GAPS REQUIRING MANUAL INPUT

| Gap | What's Needed | Source |
|-----|---------------|--------|
| Monument dimensions | SF, height, face count per WO | Not in warehouse — need from quotes/drawings |
| Cabinet dimensions | SF, construction type per WO | Not in warehouse — need from quotes/drawings |
| CNC vs hand timing | Actual hours for same operation CNC vs manual | Shop floor timing study |
| ABC Sections 1, 6-9 | Full rate tables | `ABC PRICING GUIDE 1974.xlsx` (5,738 lines) |
| Site complexity | Installation site accessibility scores | Estimator judgment / site photos |
| Crew composition | Who was on each install crew | Not tracked in KeyedIn labor data |

---

## 10. FILE MANIFEST SUMMARY

| Location | Files | Lines | Purpose |
|----------|------:|------:|---------|
| SIGNX/ (all) | 1,072 | 687,362 | Complete SignX project tree |
| signx-takeoff/ | 10 | 2,108 | Active estimation app |
| eagle_analyzer_v1/ | 11 | 3,782 | Legacy v1 estimator |
| Eagle Data/BOT TRAINING/Estimating/ | ~50+ | ~10,000+ | ABC source materials, Accutrack, work codes |
| signx-warehouse/ | 31 scripts + data | 254K+ raw records | DuckDB/SQLite data warehouse |
| Keyedin/ | 119 | 61,102 | KeyedIn ERP automation |
| docs/ | ~200 | ~60,000 | Architecture, guides, research |

**Total estimation-relevant files:** ~300 (out of 1,072)
**Total estimation-relevant lines:** ~80,000 (out of 687,362)
**The rest is infrastructure, docs, scaffolds, and archived experiments.**
