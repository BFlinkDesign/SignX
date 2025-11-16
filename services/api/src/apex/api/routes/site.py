"""Site and environmental data endpoints."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..common.models import SiteLoads, make_envelope
from ..deps import get_code_version, get_model_config, settings
from ..integrations.asce import fetch_asce_hazards
from ..schemas import ResponseEnvelope, add_assumption
from ..utils.geocoding import geocode_address
from ..utils.wind_data import fetch_snow_load, resolve_wind_speed

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/signage/common", tags=["site"])


class SiteResolveRequest(BaseModel):
    """Request to resolve site environmental data."""

    address: str = Field(..., description="Site address to geocode")
    exposure: str | None = Field(None, description="Wind exposure category (B, C, or D)")
    risk_category: str = Field("II", description="Risk category (I, II, III, or IV)")
    wind_speed_override: float | None = Field(None, description="Manual wind speed override (mph)")
    snow_load_override: float | None = Field(None, description="Manual snow load override (psf)")


@router.post("/site/resolve", response_model=ResponseEnvelope)
async def resolve_site(req: SiteResolveRequest) -> ResponseEnvelope:
    """Resolve site with geocoding and wind data.
    
    Body: {address: str, exposure?: str, risk_category?: str}
    Returns: SiteLoads with wind/snow, lat/lon, and source metadata.
    """
    logger.info("site.resolve", address=req.address)
    assumptions: list[str] = []
    
    address = req.address.strip()
    
    # Geocode address
    geocode_result = await geocode_address(address)
    lat: float | None = None
    lon: float | None = None
    
    if geocode_result:
        lat = geocode_result["lat"]
        lon = geocode_result["lon"]
        add_assumption(assumptions, f"Geocoded: {geocode_result.get('display_name', address)}")
    else:
        add_assumption(assumptions, "Geocoding failed; using manual overrides or defaults")
    
    # Try ASCE API first if we have coordinates
    asce_data = None
    if lat is not None and lon is not None:
        asce_data = await fetch_asce_hazards(lat, lon, req.risk_category)
    
    if asce_data:
        # Use ASCE API data
        result = {
            "wind_speed_mph": asce_data.wind_speed_mph,
            "snow_load_psf": asce_data.snow_load_psf,
            "exposure": asce_data.exposure_category,
            "lat": lat,
            "lon": lon,
            "source": "ASCE 7-22 API",
            "address_resolved": geocode_result.get("display_name", address) if geocode_result else None,
        }
        confidence = 0.95
        assumptions.append(f"ASCE API version: {asce_data.api_version}")
    elif req.wind_speed_override or req.snow_load_override:
        # Use manual overrides
        result = {
            "wind_speed_mph": req.wind_speed_override or 90.0,
            "snow_load_psf": req.snow_load_override or 25.0,
            "exposure": req.exposure or "C",
            "lat": lat,
            "lon": lon,
            "source": "Manual override",
            "address_resolved": geocode_result.get("display_name", address) if geocode_result else None,
        }
        confidence = 0.7
        assumptions.append("ASCE API unavailable - using manual values")
    else:
        # Fallback: use existing wind_data utility
        if lat is not None and lon is not None:
            wind_data = await resolve_wind_speed(lat, lon)
            wind_speed = wind_data["wind_speed_mph"]
            wind_source = wind_data.get("source", "unknown")
            add_assumption(assumptions, f"Wind speed from {wind_source}")
            
            # Get snow load
            snow_load = fetch_snow_load(lat, lon)
            if snow_load:
                add_assumption(assumptions, f"Snow load: {snow_load} psf")
        else:
            # Last resort: conservative defaults
            wind_speed = 100.0
            wind_source = "default_conservative"
            snow_load = None
            add_assumption(assumptions, "Wind speed from default V=100 mph (no geocoding)")
        
        # Default exposure handling
        exposure = req.exposure or "C"
        if exposure not in ["B", "C", "D"]:
            exposure = "C"
            add_assumption(assumptions, f"Exposure defaulted to C (was: {req.exposure})")
        
        result = {
            "wind_speed_mph": wind_speed,
            "snow_load_psf": snow_load,
            "exposure": exposure,
            "lat": lat,
            "lon": lon,
            "source": wind_source,
            "address_resolved": geocode_result.get("display_name", address) if geocode_result else None,
        }
        
        confidence = 0.7
        if lat is not None and lon is not None:
            confidence = 0.85

    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=confidence,
        inputs={"address": address, "exposure": req.exposure, "risk_category": req.risk_category},
        intermediates={"lat": lat, "lon": lon},
        outputs={"wind_speed_mph": result["wind_speed_mph"], "snow_load_psf": result["snow_load_psf"]},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )

