"""ASCE 7-22 Hazard Tool API integration."""

import os

import httpx
import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class ASCEHazardResponse(BaseModel):
    """Response from ASCE Hazard Tool API."""

    wind_speed_mph: float = Field(..., description="Basic wind speed (mph)")
    snow_load_psf: float = Field(..., description="Ground snow load (psf)")
    exposure_category: str = Field(..., description="Wind exposure category (B, C, or D)")
    risk_category: str = Field(..., description="Risk category (I, II, III, or IV)")
    api_version: str = Field(..., description="API version")


async def fetch_asce_hazards(
    lat: float,
    lon: float,
    risk_category: str = "II",
) -> ASCEHazardResponse | None:
    """Fetch ASCE 7-22 hazard data for a given location.
    
    Args:
        lat: Latitude (decimal degrees)
        lon: Longitude (decimal degrees)
        risk_category: Risk category (I, II, III, or IV). Defaults to II.
    
    Returns:
        ASCEHazardResponse with wind speed, snow load, exposure category, and metadata.
        Returns None if API key is missing, request fails, or response is invalid.
    """
    api_key = os.getenv("ASCE_API_KEY")
    if not api_key:
        logger.debug("asce_api_key_missing")
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://ascehazardtool.org/api/v1/hazards",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "risk_category": risk_category,
                    "standard": "ASCE7-22",
                },
                headers={"X-API-Key": api_key},
            )
            response.raise_for_status()
            data = response.json()

            # Parse ASCE API response structure
            wind_speed_mph = data.get("wind", {}).get("speed", 0.0)
            snow_load_psf = data.get("snow", {}).get("ground_load", 0.0)
            exposure_category = data.get("wind", {}).get("exposure", "C")
            api_version = data.get("version", "unknown")

            result = ASCEHazardResponse(
                wind_speed_mph=wind_speed_mph,
                snow_load_psf=snow_load_psf,
                exposure_category=exposure_category,
                risk_category=risk_category,
                api_version=api_version,
            )

            logger.info(
                "asce_hazard_fetched",
                lat=lat,
                lon=lon,
                wind_speed_mph=wind_speed_mph,
                snow_load_psf=snow_load_psf,
            )
            return result

    except httpx.HTTPError as e:
        logger.warning("asce_api_http_error", error=str(e))
        return None
    except Exception as e:
        logger.warning("asce_api_error", error=str(e))
        return None

