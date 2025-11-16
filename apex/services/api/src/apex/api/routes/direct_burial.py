from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field
from ..common.utils import build_envelope

router = APIRouter(prefix="/signage/direct_burial/footing", tags=["foundations"])


class FootingSolveRequest(BaseModel):
    diameter_in: float = Field(ge=0)
    height_ft: float = Field(ge=0)


@router.post("/solve")
async def solve(req: FootingSolveRequest):
    # Stub: simple volume calculation
    volume_ft3 = 3.14159 * ((req.diameter_in / 12.0) / 2) ** 2 * req.height_ft
    weight_lb = volume_ft3 * 150.0  # concrete density
    return build_envelope(
        result={
            "diameter_in": req.diameter_in,
            "height_ft": req.height_ft,
            "volume_ft3": round(volume_ft3, 2),
            "weight_lb": round(weight_lb, 2),
        },
        assumptions=["simplified_calculation"],
        confidence=0.7,
        inputs=req.model_dump(),
    )
