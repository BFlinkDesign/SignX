"""Geocoding utilities for address resolution."""

from __future__ import annotations

import os
from typing import Optional

import aiohttp
import logging

logger = logging.getLogger(__name__)


async def geocode_address(address: str, api_key: Optional[str] = None) -> Optional[dict[str, float]]:
    """Geocode address to lat/lon.
    
    Returns: {"lat": float, "lon": float} or None if failed.
    
    Supports:
    - OpenStreetMap Nominatim (free, no key)
    - Google Geocoding API (requires key)
    """
    if not address or address.strip() == "":
        return None
    
    # Try OpenStreetMap Nominatim first (free, rate-limited)
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": address,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
            }
            headers = {"User-Agent": "APEX-Engineering/1.0"}
            async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and len(data) > 0:
                        result = data[0]
                        return {
                            "lat": float(result["lat"]),
                            "lon": float(result["lon"]),
                            "display_name": result.get("display_name", address),
                        }
    except Exception as e:
        logger.warning("Exception in geocoding.py: %s", str(e))
        pass  # Fallback to Google or return None
    
    # Try Google Geocoding API if key provided
    google_key = api_key or os.getenv("GOOGLE_GEOCODING_API_KEY")
    if google_key:
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://maps.googleapis.com/maps/api/geocode/json"
                params = {"address": address, "key": google_key}
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("status") == "OK" and data.get("results"):
                            location = data["results"][0]["geometry"]["location"]
                            return {
                                "lat": float(location["lat"]),
                                "lon": float(location["lng"]),
                                "display_name": data["results"][0].get("formatted_address", address),
                            }
        except Exception as e:
            logger.warning("Exception in geocoding.py: %s", str(e))
            pass
    
    return None

