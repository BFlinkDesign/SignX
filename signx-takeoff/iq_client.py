"""
iq_client.py — Async client for the 500IQ Knowledge Graph service.

Queries the /heuristic endpoint to get tribal-knowledge adjustment factors
for sign type + work code combinations. Designed for shadow mode first:
log adjustments alongside base estimates without altering output.

Feature flags (env vars):
  IQ_ENABLED        Master switch                  (default: false)
  IQ_SHADOW_MODE    Log adjustments, don't apply   (default: true)
  IQ_BASE_URL       500IQ service URL              (default: http://localhost:8500)
  IQ_TIMEOUT        HTTP timeout in seconds        (default: 0.4)
  IQ_MIN_CONFIDENCE Minimum confidence to consider (default: 0.75)
  IQ_FACTOR_FLOOR   Clamp floor for factor         (default: 0.6)
  IQ_FACTOR_CEILING Clamp ceiling for factor       (default: 1.8)

Safety gates (from Codex council recommendation):
  1. Feature flag off by default — must opt in
  2. Shadow mode on by default — log only, no output changes
  3. Confidence gating — ignore low-confidence adjustments
  4. Factor clamping — prevent runaway multipliers (0.6x–1.8x)
  5. Hard timeout — 400ms, fallback to neutral (1.0) on failure
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger("signx-takeoff.iq")

# ── Feature Flags ────────────────────────────────────────────────────────────

IQ_BASE_URL = os.environ.get("IQ_BASE_URL", "http://localhost:8500")
IQ_ENABLED = os.environ.get("IQ_ENABLED", "false").lower() in ("1", "true", "yes")
IQ_SHADOW_MODE = os.environ.get("IQ_SHADOW_MODE", "true").lower() in ("1", "true", "yes")
IQ_TIMEOUT = float(os.environ.get("IQ_TIMEOUT", "0.4"))
IQ_MIN_CONFIDENCE = float(os.environ.get("IQ_MIN_CONFIDENCE", "0.75"))
IQ_FACTOR_FLOOR = float(os.environ.get("IQ_FACTOR_FLOOR", "0.6"))
IQ_FACTOR_CEILING = float(os.environ.get("IQ_FACTOR_CEILING", "1.8"))


# ── Public API ───────────────────────────────────────────────────────────────

async def query_heuristic(
    sign_type: str,
    work_code: str,
    employee_id: Optional[str] = None,
) -> dict:
    """
    Query 500IQ for a single sign_type + work_code adjustment.

    Returns:
        {
            "factor": float,       # Clamped to [FLOOR, CEILING], 1.0 on failure
            "raw_factor": float,   # Unclamped value from 500IQ
            "confidence": float,   # Max confidence from matched heuristics
            "adjustments": list,   # Full heuristic details
            "source": str,         # "500iq", "fallback:timeout", "fallback:disabled", etc.
        }
    """
    if not IQ_ENABLED:
        return _fallback("disabled")

    try:
        async with httpx.AsyncClient(timeout=IQ_TIMEOUT) as client:
            payload = {
                "sign_type": f"SIGN_TYPE-{sign_type}",
                "work_code": f"WORK_CODE-{work_code}",
            }
            if employee_id:
                payload["employee_id"] = employee_id

            resp = await client.post(f"{IQ_BASE_URL}/heuristic", json=payload)
            resp.raise_for_status()

            data = resp.json()
            result_data = data.get("result", {})
            raw_factor = result_data.get("combined_factor", 1.0)
            adjustments = result_data.get("adjustments", [])

            # Max confidence from matched heuristics
            confidence = 0.0
            if adjustments:
                confidence = max(
                    a.get("confidence", 0.0) for a in adjustments
                )

            # Confidence gate
            if confidence < IQ_MIN_CONFIDENCE:
                logger.info(
                    "IQ: low confidence (%.2f < %.2f) for %s/%s — fallback",
                    confidence, IQ_MIN_CONFIDENCE, sign_type, work_code,
                )
                return _fallback(
                    "low_confidence",
                    raw_factor=raw_factor,
                    confidence=confidence,
                    adjustments=adjustments,
                )

            # Clamp factor to safety range
            clamped = max(IQ_FACTOR_FLOOR, min(IQ_FACTOR_CEILING, raw_factor))
            if clamped != raw_factor:
                logger.warning(
                    "IQ: clamped factor %.3f -> %.3f for %s/%s",
                    raw_factor, clamped, sign_type, work_code,
                )

            return {
                "factor": clamped,
                "raw_factor": raw_factor,
                "confidence": confidence,
                "adjustments": adjustments,
                "source": "500iq",
            }

    except httpx.TimeoutException:
        logger.warning(
            "IQ: timeout (%.1fs) for %s/%s", IQ_TIMEOUT, sign_type, work_code,
        )
        return _fallback("timeout")
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "IQ: HTTP %d for %s/%s", exc.response.status_code, sign_type, work_code,
        )
        return _fallback("http_error")
    except Exception as exc:
        logger.warning("IQ: error for %s/%s: %s", sign_type, work_code, exc)
        return _fallback("error")


async def batch_query(
    sign_type: str,
    work_codes: list[str],
    employee_id: Optional[str] = None,
) -> dict[str, dict]:
    """
    Query 500IQ for multiple work codes concurrently.

    Returns dict keyed by work_code, each value is query_heuristic() result.
    All queries run in parallel via asyncio.gather.
    """
    if not IQ_ENABLED:
        return {wc: _fallback("disabled") for wc in work_codes}

    tasks = [
        query_heuristic(sign_type, wc, employee_id)
        for wc in work_codes
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    out: dict[str, dict] = {}
    for wc, result in zip(work_codes, results):
        if isinstance(result, Exception):
            logger.warning("IQ: batch error for %s/%s: %s", sign_type, wc, result)
            out[wc] = _fallback("batch_error")
        else:
            out[wc] = result
    return out


def is_enabled() -> bool:
    """Check if 500IQ integration is enabled."""
    return IQ_ENABLED


def is_shadow_mode() -> bool:
    """Check if 500IQ is in shadow (log-only) mode."""
    return IQ_SHADOW_MODE


# ── Internal ─────────────────────────────────────────────────────────────────

def _fallback(
    reason: str,
    raw_factor: float = 1.0,
    confidence: float = 0.0,
    adjustments: list | None = None,
) -> dict:
    """Return neutral factor with reason for fallback."""
    return {
        "factor": 1.0,
        "raw_factor": raw_factor,
        "confidence": confidence,
        "adjustments": adjustments or [],
        "source": f"fallback:{reason}",
    }
