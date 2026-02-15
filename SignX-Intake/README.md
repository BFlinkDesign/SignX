# SignX-Intake

Automated bid request intake for Eagle Sign Co. Captures bid emails from salesperson subfolders, extracts project data via Claude (Anthropic IP connector), and creates tracked rows in the Notion Bid Pipeline Command Center.

## Architecture

Power Automate cloud flows (M365 Business Standard license) → Anthropic IP connector (Claude Sonnet) → Notion IP connector → Bid Pipeline Command Center (304c1e58d2dd814aae63c6a0d44e6679)

## Dependencies

- Power Automate (make.powerautomate.com)
- Anthropic API key (Premium connector, included in M365 Business Standard license)
- Notion integration token (ntn_52048...)
- Office 365 Outlook (brady@eaglesign.net)
- BID REQUEST subfolder structure: Inbox/BID REQUEST/{salesperson}

## Pipeline Position
```
Email → [SignX-Intake] → Notion Bid Pipeline → [eagle-sign-takeoff] → [SignX-Intel] → [SignX-Studio] → [SignX-Draw] → KeyedIn
```

## Flows

| Flow | Phase | Purpose |
|------|-------|---------|
| BID-INTAKE-PROOF | 1 (Prove) | Single folder (Jeff Fye), end-to-end extraction |
| BID-INTAKE-ALL | 2 (Scale) | All salesperson subfolders |
| VENDOR-QUOTE-EXTRACT | 3 (Enrich) | Supplier/vendor quote parsing |
| DAILY-BID-DIGEST | 4 (Automate) | Morning summary of pipeline activity |

## Existing Assets

Two dormant flows exist from Sep 2025 ("Jeff Bid Request to Task", "Joe Bid Requests to Tasks"). Phase 0 investigates these before building anything new.

## Cost

~$1-3/month (Anthropic API). All connectors included in M365 Business Standard license.

## Status

Phase 0: DISCOVER — Investigating existing Jeff/Joe flows before building.
