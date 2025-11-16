from __future__ import annotations

from typing import Dict, Mapping


DEFAULT_QUALITATIVE_SCALE: Dict[str, float] = {
    "excellent": 1.0,
    "good": 0.75,
    "fair": 0.5,
    "poor": 0.25,
}


def compute_qualitative_score(
    qualitative_properties: list[Mapping[str, str]],
    weights: Mapping[str, float],
    scale: Mapping[str, float] | None = None,
) -> list[float]:
    """Compute weighted qualitative score per material in [0,1].

    - Category labels are matched case-insensitively
    - Missing properties contribute 0 for that feature
    - Scores are normalized by total positive weight actually considered
    """
    if not qualitative_properties:
        return []

    scale_map: Dict[str, float] = {k.lower(): float(v) for k, v in (scale or DEFAULT_QUALITATIVE_SCALE).items()}

    num_materials = len(qualitative_properties)
    scores: list[float] = [0.0 for _ in range(num_materials)]
    effective_weight = 0.0

    for feature, w in weights.items():
        if w <= 0:
            continue
        any_present = False
        for idx, mat in enumerate(qualitative_properties):
            label = str(mat.get(feature, "")).lower()
            if not label:
                continue
            val = scale_map.get(label)
            if val is None:
                continue
            any_present = True
            scores[idx] += w * float(val)
        if any_present:
            effective_weight += w

    if effective_weight <= 0.0:
        return [0.0 for _ in range(num_materials)]

    return [s / effective_weight for s in scores]


