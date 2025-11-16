"""Bill of Materials (BOM) generation endpoints."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..common.helpers import require_project
from ..common.models import make_envelope
from ..common.transactions import with_transaction
from ..db import ProjectPayload, get_db
from ..deps import get_code_version, get_model_config
from ..schemas import ResponseEnvelope, add_assumption

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["bom"])


def _generate_bom_items(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate BOM items from project configuration.
    
    Placeholder implementation that extracts materials and components
    from the design config.
    """
    items: list[dict[str, Any]] = []
    
    # Extract pole
    if "pole_size" in config:
        items.append({
            "item": config["pole_size"],
            "description": "Steel pole section",
            "quantity": config.get("num_supports", 1),
            "unit": "ea",
        })
    
    # Extract foundation
    if "footing" in config:
        footing = config["footing"]
        if footing.get("shape") == "round":
            diameter = footing.get("diameter_ft", 0)
            depth = footing.get("min_depth_ft", 0)
            volume_cy = 3.14159 * (diameter / 2) ** 2 * depth / 27
            items.append({
                "item": "Concrete",
                "description": "Foundation concrete",
                "quantity": round(volume_cy, 2),
                "unit": "cy",
            })
    
    # Extract baseplate if present
    if "baseplate" in config:
        bp = config["baseplate"]
        items.append({
            "item": "Base Plate",
            "description": f"Steel plate {bp.get('plate_w_in', 0)}x{bp.get('plate_l_in', 0)}x{bp.get('plate_thk_in', 0)}",
            "quantity": 1,
            "unit": "ea",
        })
    
    # Extract anchor bolts
    if "baseplate" in config:
        bp = config["baseplate"]
        num_anchors = bp.get("rows", 0) * bp.get("bolts_per_row", 0)
        if num_anchors > 0:
            items.append({
                "item": "Anchor Bolts",
                "description": f"{bp.get('anchor_dia_in', 0)}\" x {bp.get('anchor_embed_in', 0)}\"",
                "quantity": num_anchors,
                "unit": "ea",
            })
    
    return items


@router.get("/{project_id}/bom", response_model=ResponseEnvelope)
async def get_bom(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Get current BOM for a project.
    
    Retrieves the latest payload and generates BOM items.
    """
    logger.info("bom.get", project_id=project_id)
    assumptions: list[str] = []
    
    # Verify project exists
    await require_project(project_id, db)
    
    # Get latest payload
    query = await db.execute(
        select(ProjectPayload)
        .where(ProjectPayload.project_id == project_id)
        .order_by(ProjectPayload.created_at.desc())
        .limit(1)
    )
    payload = query.scalar_one_or_none()
    
    if not payload:
        raise HTTPException(status_code=404, detail="No payload found for project")
    
    # Generate BOM
    bom_items = _generate_bom_items(payload.config)
    
    result = {
        "project_id": project_id,
        "module": payload.module,
        "items": bom_items,
        "total_items": len(bom_items),
    }
    
    add_assumption(assumptions, "BOM generated from latest payload configuration")
    
    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=0.9,
        inputs={"project_id": project_id},
        intermediates={"payload_id": payload.payload_id, "sha256": payload.sha256},
        outputs={"bom_items_count": len(bom_items)},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.post("/{project_id}/bom", response_model=ResponseEnvelope)
async def regenerate_bom(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Regenerate BOM for a project.
    
    Same as GET but forces regeneration from latest payload.
    """
    return await get_bom(project_id, db)

