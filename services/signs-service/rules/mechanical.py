from __future__ import annotations

from typing import Dict, List


def mechanical_from_env(environment: str, mounting_type: str) -> Dict[str, object]:
    coastal = environment == "coastal"
    return {
        "mounting_pattern": "4x M8 on 200x200mm" if mounting_type in {"wall", "raceway"} else "per supplier",
        "min_fastener_grade": "316 SS" if coastal else "A2-70",
        "sealants": ["silicone RTV"],
        "gasket_material": "EPDM" if environment in {"outdoor", "coastal"} else None,
    }


