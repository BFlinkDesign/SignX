"""Uptime checks: GET /health every 1 minute."""

import asyncio
import os
import sys
from datetime import datetime, timedelta

import httpx
import structlog

logger = structlog.get_logger(__name__)

API_URL = os.getenv("APEX_API_URL", "http://localhost:8000")
CHECK_INTERVAL = int(os.getenv("UPTIME_CHECK_INTERVAL", "60"))  # seconds


async def check_health(client: httpx.AsyncClient) -> dict[str, any]:
    """Perform health check."""
    
    start = datetime.now()
    
    try:
        resp = await client.get("/health", timeout=5.0)
        duration_ms = (datetime.now() - start).total_seconds() * 1000
        
        return {
            "timestamp": start.isoformat(),
            "status_code": resp.status_code,
            "duration_ms": duration_ms,
            "healthy": resp.status_code == 200,
        }
        
    except Exception as e:
        duration_ms = (datetime.now() - start).total_seconds() * 1000
        return {
            "timestamp": start.isoformat(),
            "error": str(e),
            "duration_ms": duration_ms,
            "healthy": False,
        }


async def run_uptime_monitoring() -> None:
    """Run continuous uptime monitoring."""
    
    logger.info("uptime.start", url=API_URL, interval=CHECK_INTERVAL)
    
    async with httpx.AsyncClient(base_url=API_URL) as client:
        while True:
            result = await check_health(client)
            
            if result["healthy"]:
                logger.info("uptime.healthy", **result)
            else:
                logger.error("uptime.unhealthy", **result)
            
            # Wait for next check
            await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(run_uptime_monitoring())
    except KeyboardInterrupt:
        logger.info("uptime.stopped")
        sys.exit(0)

