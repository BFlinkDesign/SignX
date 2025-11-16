from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel, Field
import yaml
from ..common.utils import build_envelope

router = APIRouter(tags=["pricing"]) 


class EstimateRequest(BaseModel):
    project_id: str
    height_ft: float = Field(ge=0)
    addons: list[str] = Field(default_factory=list)


def _load_pricing(version: str) -> dict[str, Any]:
    """Load pricing config using shared utility."""
    from packages.utils import load_yaml
    
    # Resolve apex repo root, then config path under services/api/config
    repo_root = Path(__file__).resolve().parents[5]
    cfg_path = repo_root / f"services/api/config/pricing_{version}.yaml"
    if not cfg_path.exists():
        # fallback to v1
        cfg_path = repo_root / "services/api/config/pricing_v1.yaml"
    return load_yaml(cfg_path)


@router.post("/projects/{project_id}/estimate")
async def estimate(project_id: str, req: EstimateRequest):
    version = os.getenv("PRICING_VERSION", "v1")
    cfg = _load_pricing(version)
    brackets = cfg.get("base_brackets", [])
    addons_cfg = cfg.get("addons", {})

    base_cost = 0.0
    for b in brackets:
        if req.height_ft <= float(b.get("max_height_ft", 9e9)):
            base_cost = float(b.get("price", 0.0))
            break
    items: list[dict[str, Any]] = [{"item": "base", "price": round(base_cost, 2)}]

    for addon in req.addons:
        price = float(addons_cfg.get(addon, 0.0))
        items.append({"item": addon, "price": round(price, 2)})

    total = round(sum(i["price"] for i in items), 2)
    result = {"project_id": project_id, "version": version, "items": items, "total": total}
    return build_envelope(result=result, inputs=req.model_dump(), outputs={"total": total})
