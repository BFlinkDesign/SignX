from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field
from ..common.utils import build_envelope

router = APIRouter(prefix="/signage/common/cabinets", tags=["cabinets"])


class Cabinet(BaseModel):
    width_in: float = Field(ge=0)
    height_in: float = Field(ge=0)
    depth_in: float = Field(ge=0)
    density_lb_ft3: float = Field(default=0.0, ge=0.0)


@router.post("/derive")
async def derive(c: Cabinet):
    area_ft2 = (c.width_in * c.height_in) / 144.0
    volume_ft3 = (c.width_in * c.height_in * c.depth_in) / 1728.0
    weight_lb = volume_ft3 * c.density_lb_ft3
    res = {"area_ft2": round(area_ft2, 4), "volume_ft3": round(volume_ft3, 4), "weight_lb": round(weight_lb, 2)}
    return build_envelope(result=res, inputs=c.model_dump(), outputs=res)


class CabinetsAdd(BaseModel):
    items: list[Cabinet]


@router.post("/add")
async def add(payload: CabinetsAdd):
    total_area = sum((i.width_in * i.height_in) / 144.0 for i in payload.items)
    total_weight = sum(((i.width_in * i.height_in * i.depth_in) / 1728.0) * i.density_lb_ft3 for i in payload.items)
    res = {"total_area_ft2": round(total_area, 4), "total_weight_lb": round(total_weight, 2), "count": len(payload.items)}
    return build_envelope(result=res, inputs={"count": len(payload.items)}, outputs=res)
