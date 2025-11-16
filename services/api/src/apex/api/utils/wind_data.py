"""Wind speed and snow load resolution utilities."""

from __future__ import annotations

import os
from typing import Optional

import aiohttp
import logging

logger = logging.getLogger(__name__)


def _get_asce7_default_v(lat: float, lon: float) -> float:
    """Get default V from ASCE 7-16 wind speed map (simplified lookup).
    
    Uses approximate zones:
    - Gulf/Atlantic Coast: 140-170 mph
    - Hurricane-prone regions: 140-150 mph
    - Mountain/West Coast: 110-130 mph
    - Interior: 90-115 mph
    - Special wind regions: 115-130 mph
    
    Returns conservative default if no precise match.
    """
    # Simplified lookup based on lat/lon zones
    # For production, would use digitized ASCE 7-16 Figure 26.5-1 map
    
    # Hurricane-prone (Gulf Coast, Florida, Carolinas)
    if (24.0 <= lat <= 35.0 and -97.0 <= lon <= -80.0) or (25.0 <= lat <= 32.0 and -84.0 <= lon <= -79.0):
        return 150.0
    
    # Atlantic Coast
    if 35.0 <= lat <= 45.0 and -80.0 <= lon <= -70.0:
        return 130.0
    
    # Mountain/West Coast
    if lat >= 35.0 and lon <= -105.0:
        return 115.0
    
    # Interior (default)
    return 100.0


async def fetch_wind_speed_openweather(lat: float, lon: float, api_key: Optional[str] = None) -> Optional[dict]:
    """Fetch wind speed from OpenWeatherMap API.
    
    Returns: {"wind_speed_mph": float, "source": "openweathermap"} or None
    """
    api_key = api_key or os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return None
    
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"lat": lat, "lon": lon, "appid": api_key, "units": "imperial"}
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    wind_mps = data.get("wind", {}).get("speed", 0.0)  # m/s
                    wind_mph = wind_mps * 2.237  # Convert to mph
                    # Note: This is current wind, not design wind speed
                    # For design, would need historical data or wind map lookup
                    return {
                        "wind_speed_mph": max(50.0, wind_mph),  # Minimum reasonable design value
                        "source": "openweathermap_current",
                        "note": "Current wind speed; ASCE 7 map recommended for design",
                    }
    except Exception as e:
        logger.warning("Exception in wind_data.py: %s", str(e))
        pass
    
    return None


async def fetch_wind_speed_noaa(lat: float, lon: float) -> Optional[dict]:
    """Fetch wind speed from NOAA ASOS nearest station.
    
    Returns: {"wind_speed_mph": float, "source": "noaa"} or None
    
    Note: Requires NOAA API access and station lookup.
    """
    # TODO: Implement NOAA ASOS nearest-neighbor lookup
    # Would need:
    # 1. Find nearest ASOS station by lat/lon
    # 2. Query historical wind speed data
    # 3. Return 50-year recurrence interval value
    return None


async def resolve_wind_speed(lat: float, lon: float, api_keys: Optional[dict] = None) -> dict:
    """Resolve wind speed from multiple sources with fallback.
    
    Priority:
    1. ASCE 7-16 map lookup (deterministic)
    2. OpenWeatherMap API (if key provided)
    3. Default conservative value
    
    Returns: {"wind_speed_mph": float, "source": str, "confidence": float}
    """
    api_keys = api_keys or {}
    
    # Try ASCE 7 default lookup first (deterministic, no API needed)
    v_asce7 = _get_asce7_default_v(lat, lon)
    result = {
        "wind_speed_mph": v_asce7,
        "source": "asce7-16_approximate",
        "confidence": 0.85,
        "assumption": "ASCE 7-16 wind speed map approximation by lat/lon zone",
    }
    
    # Try OpenWeatherMap for additional data (but don't override design wind speed)
    owm_data = await fetch_wind_speed_openweather(lat, lon, api_keys.get("openweather"))
    if owm_data:
        result["current_wind_mph"] = owm_data["wind_speed_mph"]
        result["note"] = "Design wind from ASCE 7 map; current wind shown for reference"
    
    return result


def fetch_snow_load(lat: float, lon: float) -> Optional[float]:
    """Fetch ground snow load from ASCE 7-16 Figure 7.2-1.
    
    Returns: snow_load_psf or None
    
    Note: Simplified lookup; production would use digitized map.
    """
    # Simplified zones (production would use digitized ASCE 7 Figure 7.2-1)
    # Heavy snow regions (mountain, upper midwest)
    if (lat >= 42.0 and lon <= -105.0) or (lat >= 45.0 and -97.0 <= lon <= -85.0):
        return 50.0  # Heavy snow zone
    
    # Moderate snow
    if lat >= 40.0 and lon <= -90.0:
        return 30.0
    
    # Light snow / none
    if lat >= 35.0:
        return 20.0
    
    # Very light or none
    return None

