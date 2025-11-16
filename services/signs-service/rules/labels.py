from __future__ import annotations

from typing import Any, List, Dict

from contracts.signs import SignRequest


def ul969_label_set(req: SignRequest) -> List[Dict[str, Any]]:
    return [
        {"name": "Nameplate", "content": ["Voltage", "Current", "Phase", "Manufacturer"], "durability": "UL 969"},
        {"name": "Disconnect Marking", "content": ["Location per NEC 600"], "durability": "UL 969"},
    ]


