# 40398 — GOVERNANCE & STATUS (binding on ALL artifacts in this folder)

## Hard labeling rule (Brady directive 2026-05-19)
Until Brady explicitly reviews and approves a given artifact, it is:

    STATUS: ????  — DRAFT / UNREVIEWED / UNAPPROVED

It MUST NOT be called, in any file, banner, report, filename, or speech:
- "source of truth"
- "canonical"
- "validated" / "verified" (as a conclusion)
- "final" / "approved" / "correct" / "PE-ready"

Allowed words for unapproved work: draft, candidate, proposed, computed,
unreviewed, pending-approval, "????".

"Extracted from source" statements (e.g. dimension text read out of the
.CDR) may say "extracted/observed", NOT "verified truth" — the extraction
is mechanical; its correctness is still Brady-pending.

## Approval ledger (only Brady writes APPROVED here)
| Artifact | Status | Approved by | Date |
|---|---|---|---|
| cdr_geometry_raw.json | ???? DRAFT | — | — |
| CHECKPOINT-geometry.md | ???? DRAFT | — | — |
| derive_pole_spacing.py result | ???? DRAFT (rejected as method) | — | — |
| (future) ASCE 7-22 oracle calc | NOT YET PRODUCED | — | — |
| (future) engineering drawing DXF | NOT YET PRODUCED | — | — |

## Current factual state (no overclaim)
- No St. Anthony ENGINEERING output (loads/member/footing/drawing) has been
  produced yet. Only: sign-envelope geometry extracted from the .CDR proof,
  and engine-grounding defects identified in apex_signcalc.
- Envelope dims extracted from the drawing's own callouts CORROBORATE the
  Cowork transcript — this is an observation, NOT an approval.
- Pole spacing deliberately NOT determined (refused to guess off a photo
  proof). To be a DESIGNED output per cited best practice, Brady-reviewed.

## Every future report in this folder must carry this header
    STATUS: ???? DRAFT — UNREVIEWED — PENDING BRADY APPROVAL
    Not a source of truth. Not canonical. Not for fab/permit.
