# Phase 0 Manual Checklist

Complete these in Power Automate (make.powerautomate.com) before Phase 1.

## 0.A — Investigate existing flows (PARTIALLY DONE)

Chrome extension audit confirmed both flows exist and are ON but dormant (zero runs in 28 days).
A follow-up Chrome extension prompt was generated to investigate flow internals but results NOT received yet.

- [ ] Open "Jeff Bid Request to Task" in PA designer
  - What trigger? (email arrival? manual?)
  - What actions? (create Planner task? To-Do? something else?)
  - Where do tasks land? (which Planner board/To-Do list?)
  - Screenshot the flow steps → save to `recon/jeff-flow-screenshot.png`
- [ ] Check run history — any successful runs ever? Last run date?
- [ ] Open "Joe Bid Requests to Tasks" — same questions
- [ ] Decision: Disable both? Repurpose? Leave running in parallel?
  → Record decision in DECISION-LOG.md
- **NOTE:** If Chrome extension already captured this, paste results into `recon/existing-flows-audit.md` instead of re-running

## 0.B — Anthropic connector: CONFIRMED NOT AVAILABLE

Per Chrome extension audit (2026-02-14): No Anthropic connector exists in PA.
**Fallback confirmed:** HTTP connector (Premium, covered by M365 license) calls Anthropic API directly.

- [x] ~~Search "Anthropic" in PA connectors~~ → NOT FOUND
- [x] ~~HTTP connector available~~ → CONFIRMED (Premium, included)
- [ ] No action needed here — Phase 1 build guide uses HTTP connector

## 0.C — Notion connector: CONFIRMED AVAILABLE

Per Chrome extension audit (2026-02-14): Notion Independent Publisher connector available.
Actions confirmed: Append block children, Query a database, Create comment, Retrieve page property.

- [x] ~~Notion connector exists~~ → CONFIRMED
- [ ] **STILL NEEDED:** Test "Create a Page" action with Bid Pipeline DB ID to confirm field mapping works
  1. In the PA flow editor, add a Notion "Create a Page" action
  2. Database ID: `304c1e58d2dd814aae63c6a0d44e6679`
  3. Try setting just `Quote #` (title) to a test value like "TEST-DELETE-ME"
  4. Run the flow manually — does a row appear in Notion?
  5. If yes, delete the test row from Notion and confirm connector works
  6. Record results here

## 0.D — Test subfolder trigger behavior

- [ ] Create a new flow → "When a new email arrives (V3)"
- [ ] Can you select `Inbox/BID REQUEST/Jeff Fye` as the folder?
- [ ] Does it support "Include subfolders" toggle?
- [ ] If subfolder selection works: Phase 2 can use Option A (single flow with subfolder extraction)
- [ ] If NO subfolder selection: Phase 2 must use Option B (one trigger flow per salesperson)
- [ ] Record findings in DECISION-LOG.md → this determines Phase 2 architecture

## 0.E — API Key Storage Decision

Before building the Phase 1 flow, decide how to store the Anthropic API key:

- [ ] **Option 1 (Recommended for proof):** Paste API key directly in HTTP action header
  - Pros: Fast to set up, no extra config
  - Cons: Visible in flow definition, less secure
  - Acceptable for proof phase, migrate to Option 2 for production
- [ ] **Option 2 (Production):** PA Environment Variable
  - Settings → Solutions → Environment Variables → New
  - Name: `ANTHROPIC_API_KEY`, Type: Secret
  - Reference in flow via `@parameters('ANTHROPIC_API_KEY')`
- [ ] Record decision in DECISION-LOG.md
