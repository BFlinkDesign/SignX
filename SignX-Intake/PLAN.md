# Power Automate Build Plan — Eagle Sign Co.
## Bid Pipeline Automation System
**Date:** Feb 15, 2026
**Author:** Brady Flink + Claude
**Environment:** Power Automate (make.powerautomate.com) | M365 Business Standard | brady@eaglesign.net

---

## PROBLEM STATEMENT

Eagle Sign receives bid requests via email across multiple salespeople (Jeff Fye, Joe Fye, Chris Erickson, etc.). Emails land in `Inbox/BID REQUEST/{salesperson}` subfolders. Currently, Brady manually reads each bid email, extracts project details, creates a row in the Notion Bid Pipeline DB (304c1e58d2dd814aae63c6a0d44e6679), estimates labor/materials, and enters quotes into KeyedIn. The bottleneck is the intake — emails sit unprocessed because Brady is the only person who does estimation.

**Target outcome:** Every bid request email automatically becomes a tracked row in Notion within 5 minutes of arrival, with key fields pre-extracted, so nothing falls through the cracks and Brady can prioritize by dollar value instead of inbox position.

---

## EXISTING ASSETS

| Asset | Status | Notes |
|---|---|---|
| Jeff Bid Request to Task | ON (dormant) | Created Sep 2025, no recent runs. MUST INVESTIGATE before building |
| Joe Bid Requests to Tasks | ON (dormant) | Same. Could be sending to To-Do/Planner |
| Notion Bid Pipeline DB | Active | 21 quotes, $516K. ID: 304c1e58d2dd814aae63c6a0d44e6679 |
| Notion API token | Active | Set via NOTION_TOKEN env var |
| Notion IP connector | Confirmed available | Premium, covered by M365 license |
| HTTP connector (for Anthropic API) | Confirmed available | Premium, covered by M365 license. POST to api.anthropic.com/v1/messages with x-api-key header. Anthropic IP connector confirmed NOT available in PA (Chrome ext audit 2026-02-14). |
| Office 365 Outlook | Connected (x2) | Auto-authenticates to brady@eaglesign.net |
| BID REQUEST folder structure | Mapped | Inbox/BID REQUEST/Jeff Fye, /Joe Fye, /Chris Erickson, etc. |

---

## BUILD PHASES (Probe → Prove → Scale)

### PHASE 0: DISCOVER (30 min)
**Goal:** Understand what already exists before building anything new.

| # | Task | Tool | Output |
|---|---|---|---|
| 0.1 | Open Jeff + Joe flows in PA designer, document every step | Chrome ext | Flow architecture doc |
| 0.2 | Check run history — any runs ever? Where do tasks land? | Chrome ext | Run history report |
| 0.3 | Check Notion Bid Pipeline DB schema — what fields exist? | Claude (this chat) | Field list + types |
| 0.4 | Search for Anthropic connector in PA "Add a connection" | Chrome ext | Confirm availability |
| 0.5 | List all BID REQUEST subfolders + sample 3 bid emails | Outlook COM / Chrome | Email format patterns |

**Gate:** Cannot proceed to Phase 1 until 0.1-0.5 complete. Jeff/Joe flows may already solve part of the problem.

---

### PHASE 1: PROVE — Single-Folder Bid Intake (2 hrs)
**Goal:** One flow watches ONE subfolder, extracts fields, creates Notion row. Prove the pattern works end-to-end.

**Flow name:** `BID-INTAKE-PROOF`
**Scope:** Jeff Fye subfolder ONLY (highest volume)

#### Architecture:

```
TRIGGER: When a new email arrives (V3)
  → Folder: Inbox/BID REQUEST/Jeff Fye
  → Include attachments: Yes
  → Subject filter: (none — catch all)

STEP 1: HTML to Text (Content Conversion)
  → Input: Email body
  → Output: Clean text for parsing

STEP 2: Compose — Build extraction prompt
  → Concatenate: system prompt + email plain text + sender + subject + date

STEP 3: HTTP — Call Anthropic API
  → Method: POST
  → URI: https://api.anthropic.com/v1/messages
  → Headers: x-api-key: <ANTHROPIC_API_KEY>, anthropic-version: 2023-06-01, Content-Type: application/json
  → Body: {"model":"claude-sonnet-4-5-20250929","max_tokens":500,"temperature":0,"system":"<system_prompt>","messages":[{"role":"user","content":"<composed_prompt>"}]}
  → NOTE: Anthropic IP connector confirmed NOT available in PA (2026-02-14 audit). HTTP connector (Premium, covered by M365 license) used as direct replacement.

STEP 4: Parse JSON — Extract Claude API response envelope
  → Parse the JSON response from Claude into content array

STEP 4.5: Compose — Strip code fences from Claude's text
  → Expression: replace(replace(body('Parse_JSON')?['content'][0]?['text'], '```json', ''), '```', '')
  → NOTE: Sonnet sometimes wraps JSON in ```json fences despite prompt instructions

STEP 5: Parse JSON — Extract bid fields from cleaned text
  → Input: output of Step 4.5 (cleaned JSON string)

STEP 6: Notion — Create a Page
  → Database ID: 304c1e58d2dd814aae63c6a0d44e6679
  → Properties: Map extracted fields to Notion DB columns

STEP 7: (Optional) Mark email as read / move to processed folder
```

#### Claude System Prompt for Extraction:

```
You are a bid request parser for Eagle Sign Co., a commercial sign manufacturer.
Extract project details from this bid request email. Return ONLY valid JSON, no markdown, no backticks.

{
  "quote_name": "short descriptive project name — used as the Notion title",
  "customer": "company or person name requesting the sign",
  "location": "city, state if mentioned, else null",
  "sign_type": one of: "EMC_MONUMENT", "EMC_POLE", "EMC_RETROFIT", "EMC", "CHANNEL_LETTERS", "CHANNEL_LOGO", "MONUMENT_BASE", "MONUMENT_MANUAL_READER", "CABINET_ILLUMINATED", "INFO_PANEL", "MASONRY_SUB", "REMOVAL", "STRUCTURAL_BASE", or null if unclear,
  "estimated_value": dollar amount as number if mentioned, else null,
  "description": "1-3 sentence summary of what they need",
  "sq_ft": number if sign dimensions mentioned (calculate from W×H), else null,
  "faces": number of sign faces if mentioned (typically 1 or 2), else null,
  "cabinet_dims": "W x H format if cabinet dimensions mentioned", else null,
  "pixel_pitch": number in mm if EMC pixel pitch mentioned, else null,
  "delivery_date": "YYYY-MM-DD" if deadline mentioned, else null,
  "is_redo": true if this is a re-bid or revision of a previous quote, else false,
  "has_drawings": true if email mentions attached drawings/plans/specs,
  "has_specs": true if email mentions specifications document,
  "blocking": list from ["watchfire_pricing", "needs_drawings", "needs_specs", "masonry_sub_quote"] — include any that seem needed based on context, else []
}

Rules:
- If sign_type is unclear from the email, use null — don't guess.
- For EMC projects, try to extract pixel pitch from specs.
- "is_redo" = true ONLY if email explicitly references a previous quote number or says "re-bid" / "revise".
- estimated_value: only if the email states a budget or target price. Don't fabricate.
- If estimated_value is $1.00 or $1, set estimated_value to null (this is a KeyedIn placeholder, not a real budget).
```

#### Notion Bid Pipeline DB — Actual Schema (25 properties):

```
Database: "Bid Pipeline Command Center"
ID: 304c1e58d2dd814aae63c6a0d44e6679

TITLE:
  Quote #              title          ← Claude "quote_name"

TEXT FIELDS:
  Customer             rich_text      ← Claude "customer"
  Location             rich_text      ← Claude "location"
  Description          rich_text      ← Claude "description"
  Cabinet Dims         rich_text      ← Claude "cabinet_dims"
  CRM ID               rich_text      ← blank (filled later by Brady)

SELECT FIELDS:
  Salesman             select         → [Jeff Fye, Joe Phillips, Rich Thompson, House]
                                        ← Hardcoded per flow (Phase 1 = "Jeff Fye")
  Sign Type            select         → [EMC_MONUMENT, EMC_POLE, EMC_RETROFIT, EMC,
                                         CHANNEL_LETTERS, CHANNEL_LOGO, MONUMENT_BASE,
                                         MONUMENT_MANUAL_READER, CABINET_ILLUMINATED, INFO_PANEL,
                                         MASONRY_SUB, REMOVAL, STRUCTURAL_BASE]
                                        ← Claude "sign_type"
  Pipeline Stage       select         → [INTAKE, NEEDS_INFO, NEEDS_VENDOR_QUOTE, NEEDS_SUB_QUOTE,
                                         READY_TO_TAKEOFF, IN_PROGRESS, QUOTED, WON, LOST]
                                        ← Auto-set to "INTAKE"
  Status               select         → [BID REQUEST, REDO BID REQUEST]
                                        ← Based on Claude "is_redo"
  Value Source          select         → [estimated, warehouse_median, actual_quote]
                                        ← "estimated" if Claude provides value, else blank
  Blocking Owner       select         → [brady, salesman, vendor, sub]
                                        ← "brady" default for new intake

MULTI-SELECT:
  Blocking             multi_select   → [watchfire_pricing, needs_drawings, needs_specs, masonry_sub_quote]
                                        ← Claude "blocking" array

NUMBER FIELDS:
  Est. Value           number         ← Claude "estimated_value"
  Sq Ft                number         ← Claude "sq_ft"
  Faces                number         ← Claude "faces"
  Pixel Pitch (mm)     number         ← Claude "pixel_pitch"
  Age (Days)           number         ← (Notion formula, auto)
  Days to Delivery     number         ← (calculated, manual)

DATE FIELDS:
  Email Received       date           ← Email received timestamp from trigger
  Delivery Date        date           ← Claude "delivery_date"

CHECKBOXES:
  Is Redo              checkbox       ← Claude "is_redo"
  ✅ Takeoff Done      checkbox       ← false (default)
  ✅ Quoted            checkbox       ← false (default)
  ✅ Job Complete      checkbox       ← false (default)
```

**Success criteria:**
- [ ] Send test email to Jeff Fye BID REQUEST subfolder
- [ ] Flow triggers within 5 minutes
- [ ] Claude extracts fields correctly
- [ ] Notion row appears with correct data
- [ ] No errors in flow run history
- [ ] Verify cost: ~$0.003-0.005 per email (Sonnet input + output tokens)

**Gate:** Must pass all 6 criteria on 3 different test emails before Phase 2.

---

### PHASE 2: SCALE — All Salespeople (1 hr)
**Goal:** Extend to all BID REQUEST subfolders.

Two approaches (decide during Phase 1):

**Option A: Single flow, root folder trigger**
- Trigger on `Inbox/BID REQUEST` (parent folder, include subfolders if supported)
- Extract salesperson name from subfolder path or email metadata
- Pro: One flow to maintain. Con: May not support subfolder triggers.

**Option B: Parameterized child flow**
- Create a child flow that takes (email_body, subject, sender, salesperson) as inputs
- Create one trigger flow per salesperson subfolder, each calling the child flow
- Pro: Clean separation. Con: More flows to manage (but they're identical clones).

**Option C: Shared mailbox or rule-based**
- If PA supports "When email arrives in any subfolder" — single trigger
- Otherwise, use Outlook rule to copy/tag emails, trigger on tag

**Decision deferred to Phase 1 results.** Testing Phase 1 will reveal whether subfolder-level triggers work and what metadata is available.

---

### PHASE 3: ENRICH — Vendor Quote Extraction (2 hrs)
**Goal:** When vendor/supplier quotes arrive (Daktronics, Grimco, etc.), extract pricing into structured format.

**Flow name:** `VENDOR-QUOTE-EXTRACT`

```
TRIGGER: When a new email arrives (V3)
  → Folder: Inbox (or specific vendor subfolder)
  → From filter: List of known vendor domains
    (dfrequipment.com, grimco.com, sfrequipment.com, etc.)

STEP 1: HTML to Text
STEP 2: Check for PDF attachment
  → If PDF: Use Adobe PDF Services connector (already connected!) to extract text
  → If no PDF: Use email body text

STEP 3: Anthropic — Create a Message
  → System prompt: Vendor quote extraction schema
  → Content: Email text + PDF text
  → Output: JSON with line items, quantities, unit prices, totals, terms

STEP 4: Write to Excel or Notion
  → Option A: Notion page under vendor quotes section
  → Option B: Excel Online row in a vendor quotes tracker
  → Option C: Both
```

**Claude System Prompt for Vendor Extraction:**
```
You are a procurement parser for Eagle Sign Co.
Extract pricing from this vendor quote. Return ONLY valid JSON.

{
  "vendor": "company name",
  "quote_number": "if present",
  "quote_date": "YYYY-MM-DD",
  "valid_until": "YYYY-MM-DD or null",
  "items": [
    {
      "part_number": "vendor part #",
      "description": "what it is",
      "quantity": number,
      "unit_price": number,
      "extended_price": number
    }
  ],
  "subtotal": number,
  "shipping": number or null,
  "tax": number or null,
  "total": number,
  "payment_terms": "Net 30, etc.",
  "notes": "any special conditions"
}
```

**Dependencies:** Phase 1 must be proven first. Adobe PDF connector already connected (Test1, 1 year old — may need reauth).

---

### PHASE 4: AUTOMATE — Daily Digest (1 hr)
**Goal:** Morning summary of previous day's bid activity pushed to Notion vault.

**Flow name:** `DAILY-BID-DIGEST`

```
TRIGGER: Recurrence — Daily at 6:00 AM CT

STEP 1: Notion — Query Database
  → Database: Bid Pipeline
  → Filter: Created in last 24 hours

STEP 2: Notion — Query Database
  → Filter: Status changed to "Quoted" or "Won" or "Lost" in last 24 hours

STEP 3: Anthropic — Create a Message
  → System: "Summarize this bid pipeline activity for a daily briefing"
  → Content: JSON of new + updated bids
  → Output: Formatted summary

STEP 4: Notion — Append Block Children
  → Page: Session Log or dedicated Daily Digest page
  → Content: Formatted summary
```

**This is lowest priority.** Phases 1-3 deliver direct operational value. Phase 4 is nice-to-have visibility.

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|---|---|---|
| ~~Anthropic IP connector not found~~ | ~~Blocks Phases 1-3~~ | **CONFIRMED 2026-02-14:** Anthropic IP connector does NOT exist in PA. RESOLVED: Using HTTP connector (Premium, covered by M365 license) to call api.anthropic.com/v1/messages directly. No functional impact. |
| Notion IP connector auth fails with integration token | Blocks all Notion writes | Fallback: HTTP connector + Notion API direct calls (proven in this session) |
| Subfolder triggers not supported by Outlook V3 | Complicates Phase 2 scaling | Use Outlook rules to tag/copy to flat folder, trigger on that |
| Claude extraction hallucinates fields | Bad data in pipeline | Temperature 0, strict JSON schema, validation step in flow |
| API costs accumulate | Budget concern | Sonnet at ~$0.003-0.005/email = ~$1-2/month at Eagle's volume. Negligible. |
| Jeff/Joe existing flows conflict | Duplicate processing | Phase 0 discovers what they do. Disable or integrate. |
| Rate limiting (100 calls/60s per connector) | Unlikely at Eagle's email volume | Not a concern — maybe 5-10 bid emails/day |

---

## COST ANALYSIS

| Component | Monthly Cost |
|---|---|
| Power Automate | $0 (included in M365 Business Standard) |
| Notion connector | $0 (Premium included in license) |
| Anthropic connector | N/A — using HTTP connector (same $0 Premium tier) |
| Anthropic API usage | ~$1-3/month (Sonnet, ~10-20 emails/day) |
| **Total** | **~$1-3/month** |

Compare to: Brady's time @ ~$50/hr effective × 30 min/day manual intake = ~$750/month saved.

---

## IMMEDIATE NEXT ACTIONS

| # | Action | Who | When |
|---|---|---|---|
| 1 | Investigate Jeff/Joe existing flows (prompt already prepared) | Brady + Chrome ext | Next work session |
| 2 | Verify Anthropic IP connector in PA "New Connection" search | Brady + Chrome ext | Same session |
| 3 | Pull Notion Bid Pipeline DB schema | Claude (this chat) | On demand |
| 4 | Build PHASE 1 proof flow | Brady + Claude | After actions 1-3 |
| 5 | Test with 3 real bid emails | Brady | After flow built |
| 6 | Decide Phase 2 scaling approach | Brady + Claude | After proof passes |

---

## DECISION LOG

| Date | Decision | Rationale |
|---|---|---|
| 2026-02-15 | ~~Use Anthropic IP connector over HTTP~~ | ~~Simpler, no custom headers~~ — **REVERSED 2026-02-15** |
| 2026-02-15 | Use HTTP connector for Anthropic API | Anthropic IP connector confirmed unavailable in PA audit (2026-02-14). HTTP connector (Premium, covered by M365 license) calls api.anthropic.com/v1/messages directly. Same cost, slightly more setup. |
| 2026-02-15 | Use Notion IP connector over HTTP | Same — native connector with Create a Page action |
| 2026-02-15 | Sonnet over Haiku for extraction | Better structured output reliability, cost difference negligible at volume |
| 2026-02-15 | Phase 0 gate before any building | Two dormant flows exist — must understand before duplicating |
| 2026-02-15 | Temperature 0 for extraction | Deterministic output, no creativity needed for field parsing |
| 2026-02-15 | Daily digest is Phase 4 (lowest priority) | Operational intake (Phases 1-3) delivers 10x more value |
