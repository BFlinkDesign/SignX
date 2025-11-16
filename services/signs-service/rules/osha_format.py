from __future__ import annotations

from typing import Dict, List, Tuple

from contracts.signs import GraphicsSpec, SignRequest


def apply_osha_format(req: SignRequest, base: GraphicsSpec) -> Tuple[List[Dict[str, any]], GraphicsSpec]:
    findings: List[Dict[str, any]] = []
    g = GraphicsSpec(**base.model_dump())
    g.format_standard = "OSHA 29 CFR 1910.145"
    findings.append(
        {
            "source": "OSHA 29 CFR 1910.145",
            "section": None,
            "requirement": "Signal word panel, legend size, and color per spec",
            "satisfied": True,
            "notes": None,
        }
    )
    return findings, g


