from __future__ import annotations

from typing import Any, List, Dict

from contracts.signs import SignRequest

# UL 969 — Marking and Labeling Systems (Standard for Safety)
# NEC 600.4 — Sign markings visible after installation
# UL 48 §8 — Marking requirements for electric signs


def ul969_label_set(req: SignRequest) -> List[Dict[str, Any]]:
    """
    Return the set of required labels/markings for a sign.

    UL 969 applies to adhesive labels used as safety markings on listed equipment.
    Labels must meet UL 969 permanence tests (heat aging, UV, abrasion, moisture).

    NEC 600.4(A) — Nameplate marking requirements (permanent, visible after install).
    NEC 600.4(B) — Indoor/outdoor classification marking required.
    UL 48 §8.1   — Manufacturer ID, voltage, current on sign.
    """
    labels: List[Dict[str, Any]] = [
        {
            "name": "Nameplate",
            "content": [
                "Manufacturer name or trademark (UL 48 §8.1 / NEC 600.4(A)(1))",
                "Supply voltage (V) (NEC 600.4(A)(2))",
                "Full-load current (A) (NEC 600.4(A)(3))",
                "Frequency (Hz) if AC (NEC 600.4(A)(4))",
                "Number of signs if multiple on circuit (NEC 600.4(A)(5))",
                "Indoor / Outdoor rating (NEC 600.4(B))",
            ],
            "placement": "Exterior of sign enclosure, visible after installation without tools",
            "durability_standard": "UL 969 (adhesive labels must pass heat, UV, abrasion, moisture tests)",
            "code_ref": "NEC 600.4(A)-(B) / UL 48 §8.1",
        },
        {
            "name": "Disconnect Location Marker",
            "content": [
                "Arrow or text indicating location of disconnecting means (NEC 600.6(A)(1))",
            ],
            "placement": "On sign or adjacent structure, visible to service personnel",
            "durability_standard": "UL 969",
            "code_ref": "NEC 600.6(A)(1)",
        },
        {
            "name": "High-Voltage Warning (Neon / HV sections)",
            "content": [
                "WARNING: HIGH VOLTAGE — DO NOT TOUCH (required for neon secondary >1000 V)",
            ],
            "placement": "Access panels and any covers over HV secondary wiring",
            "durability_standard": "UL 969 / ANSI Z535.4",
            "code_ref": "UL 48 §8.4 / NEC 600.12",
            "conditional": req.illumination == "neon",
        },
        {
            "name": "Listing Mark",
            "content": [
                "UL Listing mark (or ETL, CSA equivalent) certifying sign meets UL 48",
            ],
            "placement": "Exterior of sign, adjacent to or incorporated in nameplate",
            "durability_standard": "UL 969",
            "code_ref": "UL 48 §8.2 / NEC 600.3",
        },
    ]
    # Filter out conditional labels that don't apply
    return [lbl for lbl in labels if lbl.get("conditional", True)]


