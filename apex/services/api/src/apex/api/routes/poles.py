from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field
from ..common.utils import build_envelope

router = APIRouter(prefix="/signage/common/poles", tags=["poles"])


class PoleOptionsRequest(BaseModel):
    moment_required_ft_lb: float = Field(ge=0)
    deflection_allow_in: float | None = None
    material: str = "steel"


@router.post("/options")
async def options(req: PoleOptionsRequest):
    # Stub: returns mock pole options based on moment requirement
    options = []
    if req.moment_required_ft_lb < 1000:
        options.append({"diameter_in": 3.5, "material": req.material, "moment_capacity_ft_lb": 1200})
    elif req.moment_required_ft_lb < 5000:
        options.append({"diameter_in": 4.5, "material": req.material, "moment_capacity_ft_lb": 5500})
    else:
        options.append({"diameter_in": 6.625, "material": req.material, "moment_capacity_ft_lb": 12000})
    return build_envelope(
        result={"options": options, "moment_required_ft_lb": req.moment_required_ft_lb},
        assumptions=["mock_catalog"],
        confidence=0.6,
        inputs=req.model_dump(),
    )
