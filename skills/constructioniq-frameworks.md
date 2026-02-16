# ConstructionIQ Frameworks — Tim Fairley Extraction
# Source: 380+ videos, ConstructionIQ YouTube channel
# Extracted: 2026-02-15 via Gemini → Claude diff pipeline
# Purpose: Domain grounding for SignX ecosystem sessions

---

## 1. Schemas

### Variation Register
| Column | Description |
|--------|-------------|
| ID | Auto-increment |
| Date | Date variation identified |
| Description | What changed and why |
| Status | Proposed → Estimated → Submitted → Approved → Claimed |
| Value | Dollar amount |
| Linked Site Instruction | Reference to written instruction that triggered the work |
| Notes | Two-part process: (1) Prove variation exists, (2) Price it separately. Never do both at once. |

### Cost-to-Complete (C2C)
| Col | Field | Source/Formula |
|-----|-------|---------------|
| A | Cost Code | Unique ID (maps to KeyedIn work codes: 0110, 0220, 0270, 0310, 0640, etc.) |
| B | Description | Task name |
| C | Original Budget | From original estimate/KeyedIn quote |
| D | Variations | Approved adjustments (link to Variation Register) |
| E | Total Budget | =SUM(C, D) |
| F | Actual Cost | Invoices + payroll (XLOOKUP from accounting/KeyedIn cost summary) |
| G | Qty to Complete | Physical count remaining — requires weekly field assessment |
| H | Rate to Complete | Forecasted productivity rate |
| I | Forecast C2C | =G * H |
| J | Cost at Completion | =F + I |
| K | Variance (G/L) | =E - J |

CPI (Cost Performance Index) = Earned Value / Actual Cost. If CPI < 1.0, you're losing money on that activity.

### Site Diary 2.0
| Field | Description |
|-------|-------------|
| Date | Entry date |
| Cost Code | Work code activity was performed against |
| Qty Completed | Physical units completed (linear ft, each, sq ft) |
| Hours Worked | Actual crew hours |
| Weather | Conditions + any impact on production |
| Notes | Sequence breaks, material delays, access issues |

Feeds EVM calculation: EV = Qty Completed × Budgeted Unit Rate. AC = Hours × Labor Rate.

### Correspondence Log
| Field | Description |
|-------|-------------|
| ID | Auto-increment |
| Date | Timestamp |
| Type | Drop-down: RFI / Variation / Delay / Instruction |
| Summary | AI-generated 1-sentence summary |
| Attachment | URL to original email/PDF |

Purpose: Searchable evidence database. When a variation is claimed, search Type=Instruction to find the exact client email that triggered extra work.

### Scope Interface Matrix
| Field | Description |
|-------|-------------|
| Item | Component or system |
| Who Supplies | Trade responsible for procurement |
| Who Installs | Trade responsible for installation |
| Who Tests | Trade responsible for commissioning/verification |
| Battery Limit Reference | Marked-up drawing reference showing exact physical handoff point |

Battery limit markups: Color-coded highlights on GA drawings showing where one trade's responsibility ends and another's begins. Exported as Exhibit A to subcontracts.

### Delay Log
| Field | Description |
|-------|-------------|
| Date | Event date |
| Event Type | Weather / Access / Design / Permit / Material |
| Hours Lost | Quantified impact |
| Photo/Evidence | Timestamped documentation |
| Linked to EOT Claim | Y/N — ties to Extension of Time entitlement |

---

## 2. AI Red Team Prompts (Verbatim)

### A. Bid Red Team / Aggressive Auditor
```
Act as a highly aggressive client auditor. I am submitting the following 
estimate/variation claim. Find 5 reasons to reject it. For each reason, 
cite the specific weakness — missing documentation, unsupported rates, 
scope ambiguity, or contractual non-compliance.
```

### B. Contractual Time-Bar Scanner
```
Analyze the uploaded [General Conditions] and [Scope of Works]. Identify 
any 'Time Bars' mentioned for 'Extensions of Time' (EOT). Specifically, 
look for phrases like 'must notify within' or 'forfeits entitlement.' 
List the clause number and the required notice period in a table.
```

### C. Estimate → Schedule Conversion
```
I am providing an [Estimate CSV/Table]. Act as a Senior Construction 
Planner. Extract the labor-heavy activities and their estimated man-hours. 
Using a crew size of [X], calculate the duration for each task. Output 
this as a Mermaid Gantt Chart code block with logical predecessors 
(e.g., Fabrication must finish before Painting starts).
```

### D. Drawing Symbol Counter (Gemini-specific)
```
I am uploading a drawing of a [Foundation Plan]. Your task is to count 
the total number of [Piles/Foundations]. Look for both the [Graphic 
Symbols] and the [Text Tags, e.g., P1, P2]. Carefully show your work 
by listing the count for each area. Perform a double-check by verifying 
the tags against the graphic count. Do not guess; if a symbol is 
unclear, flag it.
```

### E. Conflict/Ambiguity Finder
```
Using the tone and formatting requirements of Clause [X.X], analyze 
whether the scope document mentions anything about [Topic A] that the 
technical specification contradicts. Cite specific clause numbers from 
both documents.
```

---

## 3. Calibration Numbers

### Estimate Accuracy Bands
- Rough Order of Magnitude (feasibility): +/- 30%
- Budget Estimate (schematic): +/- 20%
- Detailed Tender Estimate: +/- 10%

### Allowances
- Weather buffer: 5% of total man-hours
- Black swan allowance: 2% flat on total estimate
- Wastage: Never order exact drawing quantities. Add sag, termination, and cutting waste. Tim lost 6 weeks and thousands on 5m of cable shortage.

### Margins
- GC target: 10% corporate overhead + 10% net profit = 20% total markup
- Specialty trade target (electrical, signage, mechanical): 20-40% margins due to higher technical risk and expertise
- Profit is a strategic business decision based on competition and backlog, not a fixed percentage

### Cash Flow
- Peak debt-to-revenue ratio: ~26% on standard 30-day EOM terms ($2.6M debt on $10M project before first payment)
- Front-loading: shift 5-20% of cost into early mobilization/site setup line items

### Variation Discipline
- Any spec change, no matter how small, triggers a formal RFI
- A single missed labeling requirement (every 2m vs endpoints only) can wipe $100K in margin across a program

### Professional vs Amateur Separators
- Amateurs price the job they hope to do; professionals price the job the contract requires
- Amateurs buy projects by being lowest bid; professionals walk away from commercially hostile clients
- It is always better to have zero work than negative-margin work

---

## 4. Operum Architecture

### Pipeline
```
[Tender PDF] 
  → Structure-aware parser (section numbers, headings, tables, "shall provide" patterns)
  → Chunked by work package
  → LLM summarizes chunks into WBS items
  
[Your Estimate XLSX/CSV]
  → Cost code + description extraction
  
[Cross-Check Engine]
  → Semantic vector matching (not keyword)
  → "Site Cleansing" matches "Daily Cleanup" via embedding similarity
  → Each match gets a confidence score
  → Low confidence → flagged for manual review
  
[Gap Report Output]
  → Unmatched tender requirements (no corresponding estimate line)
  → Categorized: Commercial Gap (costs money) vs Admin Gap (paperwork)
  → Cost code suggestions based on company's standard library (in development)
  
[Contract Clause Scanner]
  → Guided LLM with predefined risk patterns:
    - Liquidated damages
    - Uncapped liability  
    - Notice periods / time bars
    - Unlimited liability
  → Benchmarks against standard forms (AS-4100, JCT, NEC)
  → Highlights how far client has modified standard terms to push risk to contractor
  
[Hallucination Guardrail]
  → RAG architecture — forces citation to specific page/clause for every claim
  → No bulk context dumps (500MB into chat = hallucinations)
```

### Current State
- One-shot bid analysis tool. Analyze this bid, produce gap report, done.
- No persistence between projects.

### Roadmap (Tim's "Gold Standard" Goal)
- Project Data Library: closed-out project actuals stored as metadata
- Future bid scout: "On the last 3 similar bids, we underestimated X by Y% — adjust?"
- This is exactly what SignX-Intel is designed to be. Tim is building toward the corpus Eagle Sign already has (27K+ WOs with actuals).

---

## 5. Confidence Scoring UX Pattern

### The Problem
If the system surfaces "similar past jobs" but doesn't explain WHY they're similar, users won't trust it and won't act on the recommendation.

### The Pattern
Every match or recommendation must show:
1. **Similarity score** (0-100% or 0.0-1.0)
2. **Driving dimensions** — which factors created the similarity
3. **Divergence flags** — which factors are different

### Example Output
```
87% similar to WO-45221 (CAT Scale Speaker Sign, Tulsa OK)
  Match: sign type (speaker sign), size range (24"x36"), product code (221-0190)
  Diverge: region (Tulsa vs Des Moines), install season (July vs November)
  Historical: WO-45221 actual labor was 6.8 hrs vs 8.5 estimated (-20%)
  Suggestion: Consider 7.0 hr estimate based on 12 similar completions
```

Users need to see the reasoning to calibrate their trust. Confidence without explanation is a black box.

---

## 6. Feedback Loop Query Design

### Similarity Dimensions (Candidates)
- Sign type (channel letters, cabinet, monument, pylon, EMC, CAT Scale)
- Size range (SF of face area, linear feet of letters, overall dimensions)
- Product code / part number
- Customer type (GC, direct, national account, municipal)
- Location complexity (new install, retrofit, height, access constraints)
- Crew size and composition (2-man, 3-man, specialty equipment)
- Season / time of year (weather impact on outdoor installs)
- Distance from shop (drive time, lodging trigger)
- Material type (aluminum, steel, acrylic, LED type)
- Permit requirements (none, building, electrical, DOT)

### Critical Note
Not all dimensions predict cost variance equally. Let the data reveal which ones matter:
- Run correlation analysis: which dimensions explain the most variance between estimated and actual hours?
- Some may be noise (customer type might have zero correlation with labor overrun)
- Some not listed may matter a lot (specific crew lead assignment, for example)
- Start with all candidates, prune by statistical significance after first analysis pass

### Query Pattern
```sql
-- Find similar historical jobs for a new estimate
SELECT wo_number, sign_type, size_range, 
       estimated_hours, actual_hours,
       (actual_hours - estimated_hours) / estimated_hours AS variance_pct
FROM work_orders
WHERE sign_type = :new_sign_type
  AND size_range BETWEEN :min_size AND :max_size
  AND product_code = :product_code
ORDER BY similarity_score DESC
LIMIT 20;
```

The real implementation uses vector similarity across embedded job descriptions, not just SQL filters. The SQL is the fallback for structured dimensions; embeddings catch the unstructured similarity that keyword filters miss.

---

## Meta: Tim Fairley's Core Design Philosophy

1. **One trigger, one transformation, one output.** More steps = more breakage.
2. **Automate what you should do but don't** (follow-ups, logging, classification) — not what takes 2 minutes once a month.
3. **AI = unstructured → structured.** Automation = structured → structured. Don't mix them.
4. **Data reuse is the goal.** Every schema should feed the next project's estimate, not just this project's report.
5. **Data integrity separates professionals from amateurs.** Monday morning: ensure actuals are linked to forecasts. Don't guess from bank balance.
6. **Process before tools.** The tool doesn't fix the process. The process tells you which tool you need.

---

## 8. Applicability to Eagle Sign

### Context Translation
Tim Fairley operates in Australian commercial GC↔subcontractor frameworks (AS-4100, JCT, NEC contracts). Eagle Sign operates as:
- **Prime contractor** on most jobs (direct to end customer)
- **Named subcontractor** to GCs on commercial/municipal projects
- **National account vendor** on program work (CAT Scale 2,000+ locations)

Terminology substitution required when adapting:
| Tim's Term | Eagle Sign Equivalent |
|------------|----------------------|
| Site Instruction | Change Order / CO |
| IFC Drawings | Shop Drawings (internal) or Contract Drawings (from architect/GC) |
| Tender / RFT | Bid Package / RFQ |
| Programme | Schedule |
| Prelims | General Conditions / Mobilization |
| Defects Liability Period (DLP) | Warranty Period |
| Retention | Retainage |
| EOT (Extension of Time) | Schedule Extension / Time Extension Request |
| Practical Completion | Substantial Completion |
| Battery Limit | Scope Boundary / Trade Interface |

### Schema Applicability by Job Size

| Schema | <$10K jobs | $10K-$50K jobs | $50K+ / Program work |
|--------|-----------|---------------|---------------------|
| Variation Register | Skip — verbal COs suffice | Use simplified (3 columns: what/status/value) | Full 5-stage pipeline |
| C2C Sheet | Skip — not enough complexity | Use for jobs with >3 cost codes | Required — this is where margin leaks |
| Site Diary 2.0 | Skip | Use for field install tracking only | Required for all shop + field |
| Correspondence Log | Skip — email search is enough | Use for GC-managed jobs only | Required — this is your evidence trail |
| Scope Interface Matrix | Skip | Use when 2+ trades on site | Required on every multi-trade install |
| Delay Log | Skip | Use for field work with weather exposure | Required on all outdoor installs |

### Calibration Number Warnings
Tim's numbers are **benchmarks to test against your data, not gospel:**
- **20-40% specialty trade margins:** Eagle Sign's actual markup standards exist in `eagle-sign-markup-standards` skill. Tim's range is industry calibration. Eagle Sign's real numbers may differ.
- **Wastage factors (7-10% LED, 15% CNC):** Validate against actual material usage from KeyedIn cost summaries. If Eagle Sign's actual waste on CNC acrylic is 8%, don't use 15%.
- **26% cash burn ratio:** Directionally correct but Eagle Sign's payment terms vary by customer. National accounts (CAT Scale) pay differently than municipal contracts.
- **5% weather buffer:** Relevant for outdoor install hours only. Indoor shop fabrication is weather-independent. Apply selectively to work codes 0640/0650, not 0270/0310.

### What Applies Directly (No Translation Needed)
- AI Red Team prompts — use as-is on any estimate
- Monday Morning Rule — actuals into C2C by 10 AM Monday
- Two-Part Variation Process — prove it exists, THEN price it. Universal.
- Bid scrubbing trigger words ("all", "every", "inclusive") — language is the same in US specs
- Process before tools philosophy — universal truth
- Data Validation on status fields — applies to any Excel workflow
- Confidence scoring UX pattern — applies to any recommendation system

---

## 9. Skill Cross-References & Schema Integration

### Related Eagle Sign Skills
| Skill | Relationship to This File |
|-------|--------------------------|
| `eagle-sign-takeoff` | **Wastage validation.** Tim's 7-10% LED and 15% CNC factors should be tested against actual material consumption extracted via `keyedin-cost-summary-parser`. The takeoff skill has ABC formulas for material quantities — add wastage buffer AFTER ABC calculation, not before. |
| `eagle-sign-markup-standards` | **Margin calibration.** Tim's 20-40% specialty trade range is industry benchmark. Eagle Sign's actual markups (1.75 standard, 1.20-1.34 EMC sliding scale) are the ground truth. Use Tim's range to evaluate whether Eagle Sign is pricing within or outside industry norms. |
| `keyedin-cost-summary-parser` | **Actuals extraction.** This is the tool that populates C2C Column F (Actual Cost). Parser extracts EST HRS, ACTUAL HRS, and VARIANCE by work code from KeyedIn PDFs. Every C2C sheet and feedback loop query depends on clean actuals from this parser. |
| `signx-engineering` | **Foundation/structural scope.** Tim's Scope Interface Matrix and Battery Limit concepts apply when sign foundations interface with GC's site work. Who pours the caisson — Eagle Sign or GC's concrete sub? That interface must be explicit in every bid. ASCE 7-22 wind loads feed the structural design that drives foundation size, which drives the scope boundary discussion. |
| `keyedin-quote-entry` | **Budget source.** C2C Column C (Original Budget) comes from the KeyedIn quote. Work code mapping (0110, 0220, 0270, 0310, 0640, 0650) is shared vocabulary between the C2C sheet and KeyedIn entry conventions. |
| `awning-estimator` | **Wastage validation (fabric).** Tim's general wastage philosophy applies. Awning fabric yardage calculations already include cutting waste — verify the built-in waste factor matches actual consumption. |
| `daktronics-emc-quoting` | **Direct purchase scope boundary.** EMCs from Daktronics are the classic case where Scope Interface Matrix matters: Who mounts it? Who provides power? Who does commissioning? Battery Limit concept applies directly. |

### Schema Data Flow Map
```
                    ┌─────────────────┐
                    │ Correspondence  │
                    │      Log        │
                    │ (email evidence)│
                    └────────┬────────┘
                             │ proves
                             ▼
┌──────────┐    feeds    ┌─────────────────┐    feeds    ┌──────────┐
│  Delay   │───────────→ │   Variation     │───────────→ │   C2C    │
│   Log    │  EOT claim  │   Register      │  Column D   │  Sheet   │
└──────────┘             └─────────────────┘             └────┬─────┘
                                                              │
┌──────────┐    feeds                                         │
│  Site    │───────────────────────────────────────────────────┘
│  Diary   │  Column F (actual cost) + Column G (qty remaining)
└──────────┘

┌──────────────────┐    defines scope for    ┌──────────┐
│ Scope Interface  │────────────────────────→ │ Variation│
│    Matrix        │  (proves whose problem)  │ Register │
└──────────────────┘                          └──────────┘

┌──────────────────┐
│ KeyedIn Quote    │──→ C2C Column C (Original Budget)
│ (quote entry)    │
└──────────────────┘

┌──────────────────┐
│ KeyedIn Cost     │──→ C2C Column F (Actual Cost) — extracted by
│ Summary Parser   │    keyedin-cost-summary-parser skill
└──────────────────┘

┌──────────────────┐
│ SignX-Intel      │←── C2C Variance (Column K) feeds feedback loop
│ (future)         │←── Site Diary actuals feed similarity matching
│                  │←── 27K+ WOs = training corpus
└──────────────────┘
```

### Integration Sequence (When Building)
1. **KeyedIn quote entry** creates the budget baseline (C2C Column C)
2. **Scope Interface Matrix** defines trade boundaries at bid time
3. **Site Diary** captures daily actuals during execution
4. **Correspondence Log** timestamps all communications as evidence
5. **Delay Log** tracks disruptions with quantified impact
6. **Variation Register** formalizes scope changes with 5-stage pipeline
7. **C2C Sheet** synthesizes everything into one variance view per cost code
8. **KeyedIn cost summary parser** extracts closed-job actuals for benchmarking
9. **SignX-Intel** (future) queries historical C2C data for similar-job recommendations

Build in this order. Each schema depends on the one before it being populated.
