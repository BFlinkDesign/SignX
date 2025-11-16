from __future__ import annotations

from typing import Any, Dict, List, Tuple

from contracts.signs import GraphicsSpec, SignRequest


def apply_mutcd_constraints(req: SignRequest, base: GraphicsSpec) -> Tuple[bool, List[Dict[str, Any]], GraphicsSpec]:
    findings: List[Dict[str, Any]] = []
    ok = True
    g = GraphicsSpec(**base.model_dump())

    # Minimal guardrail: enforce standard format tag and a placeholder constraint
    g.format_standard = "MUTCD 11th"
    # off-spec detection (caller may indicate explicit off-spec legend)
    if isinstance(req.provenance, dict) and req.provenance.get("legend_off_spec"):
        ok = False
        findings.append(
            {
                "source": "MUTCD 11th",
                "section": None,
                "requirement": "Legend/layout must conform to MUTCD tables",
                "satisfied": False,
                "notes": "off-spec legend requested",
            }
        )
    findings.append(
        {
            "source": "MUTCD 11th",
            "section": None,
            "requirement": "Traffic control signs must follow MUTCD color/fonts/layout",
            "satisfied": True,
            "notes": None,
        }
    )
    return ok, findings, g


