"""Synthetic monitoring: Cron job that runs key scenarios every 5 minutes."""

import asyncio
import os
import sys
from datetime import datetime
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

# Configuration
API_URL = os.getenv("APEX_API_URL", "http://localhost:8000")
WEBHOOK_URL = os.getenv("MONITORING_WEBHOOK_URL", "")
SCENARIOS = [
    "health_check",
    "create_project",
    "derive_cabinet",
    "get_pole_options",
]


async def run_scenario(name: str, client: httpx.AsyncClient) -> dict[str, Any]:
    """Run a synthetic monitoring scenario."""
    
    start = datetime.now()
    
    try:
        if name == "health_check":
            resp = await client.get("/health", timeout=5.0)
            
        elif name == "create_project":
            resp = await client.post(
                "/projects/",
                json={
                    "account_id": "synthetic_monitoring",
                    "name": f"Synthetic Test {start.isoformat()}",
                    "created_by": "monitoring_bot",
                },
                timeout=10.0,
            )
            
        elif name == "derive_cabinet":
            resp = await client.post(
                "/cabinets/derive",
                json={
                    "sign": {"height_ft": 10.0, "width_ft": 8.0},
                    "board": {"layers": []},
                },
                timeout=10.0,
            )
            
        elif name == "get_pole_options":
            resp = await client.post(
                "/poles/options",
                json={"loads": {"moment_kips_ft": 100}, "preferences": {}},
                timeout=10.0,
            )
            
        else:
            return {"status": "unknown_scenario", "error": f"Unknown scenario: {name}"}
        
        duration_ms = (datetime.now() - start).total_seconds() * 1000
        success = resp.status_code in (200, 201, 422)
        
        return {
            "scenario": name,
            "status": "success" if success else "failure",
            "status_code": resp.status_code,
            "duration_ms": duration_ms,
            "timestamp": start.isoformat(),
        }
        
    except Exception as e:
        duration_ms = (datetime.now() - start).total_seconds() * 1000
        return {
            "scenario": name,
            "status": "error",
            "error": str(e),
            "duration_ms": duration_ms,
            "timestamp": start.isoformat(),
        }


async def send_alert(webhook_url: str, results: list[dict[str, Any]]) -> None:
    """Send alert to webhook if any scenario failed."""
    
    failures = [r for r in results if r["status"] in ("failure", "error")]
    
    if not failures:
        return
    
    alert_data = {
        "text": f"⚠️ CalcuSign Monitoring Alert: {len(failures)} scenario(s) failed",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{len(failures)} of {len(results)} scenarios failed*",
                },
            },
        ],
    }
    
    for failure in failures:
        alert_data["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"• {failure['scenario']}: {failure['status']} ({failure.get('error', failure.get('status_code', 'unknown'))})",
            },
        })
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json=alert_data, timeout=5.0)
            resp.raise_for_status()
            logger.info("monitoring.alert_sent", webhook=webhook_url, failures=len(failures))
    except Exception as e:
        logger.error("monitoring.alert_failed", error=str(e))


async def main() -> None:
    """Run all monitoring scenarios."""
    
    logger.info("monitoring.start", scenarios=SCENARIOS)
    
    async with httpx.AsyncClient(base_url=API_URL, timeout=30.0) as client:
        results = await asyncio.gather(*[
            run_scenario(name, client) for name in SCENARIOS
        ])
    
    # Log results
    for result in results:
        if result["status"] == "success":
            logger.info("monitoring.success", **result)
        else:
            logger.error("monitoring.failure", **result)
    
    # Send alerts if configured
    if WEBHOOK_URL:
        await send_alert(WEBHOOK_URL, results)
    
    # Exit with non-zero if any failures
    has_failures = any(r["status"] in ("failure", "error") for r in results)
    sys.exit(1 if has_failures else 0)


if __name__ == "__main__":
    asyncio.run(main())

