# Decision Log — SignX-Intake

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-15 | Use HTTP connector for Anthropic API | Anthropic IP connector confirmed unavailable in PA (Chrome ext audit 2026-02-14). HTTP connector (Premium, covered by M365 license) calls api.anthropic.com/v1/messages directly. Same cost, slightly more setup. |
| 2026-02-15 | Use Notion IP connector for DB writes | Notion Independent Publisher connector confirmed available with Create a Page action. Premium tier covered by M365 Business Standard license. |
| 2026-02-15 | Sonnet over Haiku for extraction | Better structured output reliability, cost difference negligible at volume (~$0.003/email). |
| 2026-02-15 | Phase 0 gate before building | Two dormant flows exist ("Jeff Bid Request to Task", "Joe Bid Requests to Tasks") — must understand before duplicating work. |
| 2026-02-15 | Temperature 0 for extraction | Deterministic output, no creativity needed for field parsing. |
| 2026-02-15 | Daily digest is Phase 4 (lowest priority) | Operational intake (Phases 1-3) delivers 10x more value. |
| 2026-02-15 | Strip code fences in PA flow | Sonnet wraps JSON in \`\`\`json fences despite prompt instruction. Add Compose step in PA to strip before Parse JSON. |
| 2026-02-15 | Start with Jeff Fye folder only (Phase 1) | Highest volume (24 emails), most representative sample for proof of concept. |
