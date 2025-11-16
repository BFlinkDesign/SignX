"""Pricing and estimation endpoints."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import structlog
import yaml
from fastapi import APIRouter

from ..common.models import make_envelope
from ..deps import get_code_version, get_model_config
from ..schemas import ResponseEnvelope

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["pricing"])


_PRICING_CACHE: Dict[str, Dict[str, Any]] = {}


def _load_pricing(version: str) -> Dict[str, Any]:
    """Load pricing config YAML by version (e.g., v1). Cached in-process."""
    if version in _PRICING_CACHE:
        return _PRICING_CACHE[version]
    # Resolve path: services/api/config/pricing_{version}.yaml
    base_dir = Path(__file__).resolve().parents[4]
    cfg_path = base_dir / "config" / f"pricing_{version}.yaml"
    with cfg_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # Support both legacy flat schema and new structured schema under root key "pricing"
    if isinstance(data, dict) and "pricing" in data and isinstance(data["pricing"], dict):
        data = data["pricing"]
    _PRICING_CACHE[version] = data
    return data


@router.post("/{project_id}/estimate", response_model=ResponseEnvelope)
async def estimate(project_id: str, req: dict) -> ResponseEnvelope:
    """Generate instant price estimate with add-ons (no submit).
    
    Body: {addons: [str], height_ft: float}
    Returns: Line items + total
    """
    logger.info("pricing.estimate", project_id=project_id)

    version = os.getenv("APEX_PRICING_VERSION", "v1")
    cfg = _load_pricing(version)

    height_ft = float(req.get("height_ft", 0.0) or 0.0)
    addons = list(req.get("addons", []) or [])

    # Base pricing (deterministic bracket selection)
    base_cfg = cfg.get("base", {})
    # Structured rates list: [{bracket: "<=25ft"|">25ft", amount_usd: 200, description: "..."}]
    rates = base_cfg.get("rates") or []
    lte_25 = None
    gt_25 = None
    if isinstance(rates, list):
        for r in rates:
            if not isinstance(r, dict):
                continue
            br = str(r.get("bracket", "")).strip()
            amt = float(r.get("amount_usd", 0))
            if br == "<=25ft":
                lte_25 = amt
            elif br == ">25ft":
                gt_25 = amt
    # Fallback to legacy flat keys if structured not present
    if lte_25 is None:
        lte_25 = float(base_cfg.get("lte_25_ft_usd", 200))
    if gt_25 is None:
        gt_25 = float(base_cfg.get("gt_25_ft_usd", 300))
    base_rate = lte_25 if height_ft <= 25.0 else gt_25
    line_items = [
        {
            "code": "base",
            "label": f"{base_cfg.get('name', 'Engineering')} {'≤25' if height_ft <= 25.0 else '>25'} ft",
            "amount_usd": base_rate,
            "quantity": 1,
            "subtotal_usd": base_rate,
        }
    ]

    # Add-ons
    addons_cfg = cfg.get("addons", {})
    unknown_addons: list[str] = []
    for code in addons:
        if code in addons_cfg:
            entry = addons_cfg[code]
            # Support structured object or legacy scalar amount
            if isinstance(entry, dict):
                amount = float(entry.get("amount_usd", 0))
                label = str(entry.get("name", code.replace("_", " ").title()))
            else:
                amount = float(entry)
                label = code.replace("_", " ").title()
            line_items.append(
                {
                    "code": code,
                    "label": label,
                    "amount_usd": amount,
                    "quantity": 1,
                    "subtotal_usd": amount,
                }
            )
        else:
            unknown_addons.append(code)

    total = sum(item["subtotal_usd"] for item in line_items)

    result = {
        "line_items": line_items,
        "total_usd": total,
        "pricing_version": version,
    }

    assumptions = [f"pricing_table={version}"]
    if unknown_addons:
        assumptions.append(f"ignored_unknown_addons={','.join(sorted(unknown_addons))}")

    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=0.99,
        inputs={"project_id": project_id, "addons": addons, "height_ft": height_ft},
        intermediates={},
        outputs={"total_usd": total},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )

