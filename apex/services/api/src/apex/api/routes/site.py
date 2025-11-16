from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from ..common.utils import build_envelope

router = APIRouter(prefix="/signage/common/site", tags=["site"])


class SiteResolveRequest(BaseModel):
    address: str


@router.post("/resolve")
async def resolve_site(req: SiteResolveRequest):
    # Stub: returns mock location until geocoding service is integrated
    return build_envelope(
        result={
            "address": req.address,
            "latitude": 40.7128,
            "longitude": -74.0060,
            "zip_code": "10001",
            "wind_zone": "III",
        },
        assumptions=["mock_geocode", "mock_wind_zone"],
        confidence=0.5,
        inputs=req.model_dump(),
    )
