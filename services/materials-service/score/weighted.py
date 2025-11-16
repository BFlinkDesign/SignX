from __future__ import annotations

from typing import Dict, Iterable, Mapping, Tuple


def _min_max(values: Iterable[float]) -> Tuple[float, float]:
    vals = list(values)
    if not vals:
        return 0.0, 0.0
    v_min = min(vals)
    v_max = max(vals)
    return v_min, v_max


def normalize_property_values(
    materials: Iterable[Mapping[str, float]],
    property_name: str,
    higher_is_better: bool = True,
) -> Dict[int, float]:
    """Return per-index normalized value in [0,1] for a property across materials.

    If all values are equal or property is missing for all, returns 0.0 for all.
    For lower-is-better, we invert the min-max normalization.
    """
    values: list[float] = []
    present_mask: list[bool] = []
    for mat in materials:
        if property_name in mat and mat[property_name] is not None:  # type: ignore[index]
            values.append(float(mat[property_name]))  # type: ignore[index]
            present_mask.append(True)
        else:
            values.append(0.0)
            present_mask.append(False)

    v_min, v_max = _min_max([v for v, present in zip(values, present_mask) if present])
    denom = (v_max - v_min) if (v_max - v_min) != 0 else 0.0

    result: Dict[int, float] = {}
    for idx, (v, present) in enumerate(zip(values, present_mask)):
        if not present or denom == 0.0:
            result[idx] = 0.0
            continue
        norm = (v - v_min) / denom
        if not higher_is_better:
            norm = 1.0 - norm
        result[idx] = max(0.0, min(1.0, norm))
    return result


def compute_weighted_numeric_score(
    numeric_properties: list[Mapping[str, float]],
    weights: Mapping[str, float],
    higher_is_better: Mapping[str, bool] | None = None,
) -> list[float]:
    """Compute weighted numeric score per material in [0,1] by min-max normalization.

    - Missing properties contribute 0 for that feature
    - Scores are normalized by total positive weight actually considered
    """
    if not numeric_properties:
        return []

    higher = higher_is_better or {}

    # Precompute normalized values per property across all materials
    normalized_per_property: dict[str, Dict[int, float]] = {}
    for prop_name, weight in weights.items():
        if weight <= 0:
            continue
        normalized_per_property[prop_name] = normalize_property_values(
            materials=numeric_properties,
            property_name=prop_name,
            higher_is_better=higher.get(prop_name, True),
        )

    num_materials = len(numeric_properties)
    scores: list[float] = [0.0 for _ in range(num_materials)]
    # Effective weight is the sum over properties that exist for at least one material
    effective_weight = 0.0
    for prop_name, norm_map in normalized_per_property.items():
        w = float(weights.get(prop_name, 0.0))
        if w <= 0:
            continue
        # If every value is 0 (either missing or no spread), skip from effective weight
        if all(v == 0.0 for v in norm_map.values()):
            continue
        effective_weight += w
        for idx in range(num_materials):
            scores[idx] += w * norm_map.get(idx, 0.0)

    if effective_weight <= 0.0:
        return [0.0 for _ in range(num_materials)]

    # Normalize to [0,1] range by dividing by effective weight
    return [s / effective_weight for s in scores]


