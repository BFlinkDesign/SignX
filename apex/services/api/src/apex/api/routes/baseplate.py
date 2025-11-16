from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from ..common.utils import build_envelope

router = APIRouter(prefix="/signage/baseplate", tags=["baseplate"])


class BaseplateCheck(BaseModel):
    plate_thickness_in: float
    weld_size_in: float
    anchors: int


@router.post("/checks")
async def checks(payload: BaseplateCheck):
    # Stub: basic checks
    area_in2 = 12.0 * 12.0  # assume 12x12 baseplate
    stress_psi = 1000.0 / area_in2  # assume 1000 lb load
    return build_envelope(
        result={
            "plate_thickness_in": payload.plate_thickness_in,
            "weld_size_in": payload.weld_size_in,
            "anchors": payload.anchors,
            "stress_psi": round(stress_psi, 2),
            "status": "ok" if stress_psi < 36000 else "review_required",
        },
        assumptions=["simplified_analysis"],
        confidence=0.6,
        inputs=payload.model_dump(),
    )
