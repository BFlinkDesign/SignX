"""
Intelligence Module - Cost and labor prediction via 500IQ Knowledge Graph

This module provides predictions by querying the 500IQ graph for
tribal-knowledge heuristic adjustments, then applying them to base
estimates from the warehouse benchmark data.

Flow:
  1. Receive prediction request (drivers or work_codes)
  2. Query 500IQ /heuristic for applicable adjustments
  3. Apply combined adjustment factor to base estimate
  4. Return calibrated prediction with evidence chain

Replaces the former mock predictions with live graph queries.
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from signx_platform.events import event_bus, Event
from signx_platform.registry import registry, ModuleDefinition

logger = logging.getLogger(__name__)

IQ_BASE_URL = os.getenv("IQ_BASE_URL", "http://127.0.0.1:8500")


# Module definition
module_def = ModuleDefinition(
    name="intelligence",
    version="2.0.0",
    display_name="Intelligence",
    description="Cost and labor prediction via 500IQ Knowledge Graph",
    api_prefix="/api/v1/intelligence",
    ui_routes=["/projects/:id/intelligence", "/intelligence/insights"],
    nav_order=3,
    icon="brain",
    events_consumed=["design.completed", "calculations.completed", "project.submitted"],
    events_published=["prediction.generated", "anomaly.detected"]
)

# API router
router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])


# Request/Response models
class CostPredictionRequest(BaseModel):
    """Request for cost prediction."""
    project_id: str
    drivers: Dict[str, float]
    employee_id: Optional[str] = None
    sign_type: Optional[str] = None


class LaborPredictionRequest(BaseModel):
    """Request for labor hour prediction."""
    project_id: str
    work_codes: List[str]
    employee_id: Optional[str] = None
    sign_type: Optional[str] = None
    base_hours: Optional[Dict[str, float]] = None


# ── 500IQ client ──────────────────────────────────────────────────────────── #

async def _query_500iq_heuristic(
    employee_id: Optional[str] = None,
    work_code: Optional[str] = None,
    sign_type: Optional[str] = None,
) -> dict:
    """Query the 500IQ /heuristic endpoint for adjustment factors."""
    payload = {}
    if employee_id:
        payload["employee_id"] = employee_id
    if work_code:
        payload["work_code"] = work_code
    if sign_type:
        payload["sign_type"] = sign_type

    if not payload:
        return {"adjustments": [], "combined_factor": 1.0}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{IQ_BASE_URL}/heuristic", json=payload)
            resp.raise_for_status()
            envelope = resp.json()
            return envelope.get("result", {"adjustments": [], "combined_factor": 1.0})
    except httpx.HTTPError as exc:
        logger.warning(f"500IQ query failed ({exc}), falling back to neutral factor")
        return {"adjustments": [], "combined_factor": 1.0}


async def _query_500iq_stats() -> dict:
    """Fetch graph stats from 500IQ for the insights summary."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{IQ_BASE_URL}/stats")
            resp.raise_for_status()
            return resp.json().get("result", {})
    except httpx.HTTPError:
        return {}


# ── Endpoints ─────────────────────────────────────────────────────────────── #

@router.post("/predict/cost")
async def predict_cost(request: CostPredictionRequest):
    """
    Predict project cost using 500IQ heuristic adjustments.

    Base cost is derived from drivers (sign_area * rate), then adjusted
    by any tribal-knowledge factors found in the 500IQ graph.
    """
    # Base cost estimate from drivers
    sign_area = request.drivers.get("sign_area_sqft", 100)
    height = request.drivers.get("sign_height_ft", 20)
    base_rate_per_sqft = 125.0  # industry baseline $/sqft
    base_cost = sign_area * base_rate_per_sqft

    # Height premium: +2% per foot above 15ft
    if height > 15:
        base_cost *= 1 + 0.02 * (height - 15)

    # Query 500IQ for heuristic adjustments
    iq_result = await _query_500iq_heuristic(
        employee_id=request.employee_id,
        sign_type=request.sign_type,
    )
    combined_factor = iq_result.get("combined_factor", 1.0)
    adjustments = iq_result.get("adjustments", [])

    # Apply the 500IQ adjustment
    adjusted_cost = round(base_cost * combined_factor, 2)

    # Confidence: based on whether we have graph data
    confidence = 0.92 if adjustments else 0.70

    # Build spread for confidence interval
    spread = adjusted_cost * (1 - confidence) * 0.5
    result = {
        "predicted_cost": adjusted_cost,
        "confidence": confidence,
        "confidence_interval": [
            round(adjusted_cost - spread, 2),
            round(adjusted_cost + spread, 2),
        ],
        "cost_drivers": {
            k: round(v / sum(request.drivers.values()), 3)
            if sum(request.drivers.values()) > 0 else 0
            for k, v in request.drivers.items()
        },
        "iq_adjustments": adjustments,
        "iq_combined_factor": combined_factor,
        "model_version": "500iq-v2.0.0",
        "source": "500iq" if adjustments else "baseline",
    }

    await event_bus.publish(Event(
        type="prediction.generated",
        source="intelligence",
        project_id=request.project_id,
        data={
            "prediction_type": "cost",
            "predicted_cost": result["predicted_cost"],
            "confidence": result["confidence"],
            "iq_factor": combined_factor,
        }
    ))

    return result


@router.post("/predict/labor")
async def predict_labor(request: LaborPredictionRequest):
    """
    Predict labor hours using 500IQ heuristic adjustments.

    For each work code, queries the graph for employee-specific or
    sign-type-specific adjustments and applies them to the base estimate.
    """
    breakdown = {}
    total_hours = 0.0
    total_confidence = 0.0
    all_adjustments = []

    for wc in request.work_codes:
        # Base hours: from request or default
        base = (request.base_hours or {}).get(wc, 8.0)

        # Query 500IQ for this specific work code
        iq_result = await _query_500iq_heuristic(
            employee_id=request.employee_id,
            work_code=f"WORK_CODE-{wc}" if not wc.startswith("WORK_CODE-") else wc,
            sign_type=request.sign_type,
        )
        factor = iq_result.get("combined_factor", 1.0)
        adjustments = iq_result.get("adjustments", [])
        all_adjustments.extend(adjustments)

        # Apply adjustment: if factor > 1, the estimate is padded —
        # divide by the factor to get the calibrated (de-padded) hours
        calibrated = round(base / factor, 1) if factor > 0 else base

        conf = 0.94 if adjustments else 0.75
        breakdown[wc] = {
            "base_hours": base,
            "calibrated_hours": calibrated,
            "iq_factor": factor,
            "confidence": conf,
        }
        total_hours += calibrated
        total_confidence += conf

    avg_confidence = round(total_confidence / len(request.work_codes), 2) if request.work_codes else 0.0

    result = {
        "total_hours": round(total_hours, 1),
        "confidence": avg_confidence,
        "confidence_interval": [
            round(total_hours * 0.92, 1),
            round(total_hours * 1.08, 1),
        ],
        "breakdown": breakdown,
        "iq_adjustments": all_adjustments,
        "model_version": "500iq-v2.0.0",
        "source": "500iq" if all_adjustments else "baseline",
    }

    await event_bus.publish(Event(
        type="prediction.generated",
        source="intelligence",
        project_id=request.project_id,
        data={
            "prediction_type": "labor",
            "total_hours": result["total_hours"],
            "confidence": result["confidence"],
        }
    ))

    return result


@router.get("/insights/summary")
async def get_insights_summary():
    """
    Business intelligence summary powered by 500IQ graph stats.
    """
    graph_stats = await _query_500iq_stats()

    total_nodes = graph_stats.get("total_nodes", 0)
    total_edges = graph_stats.get("total_edges", 0)
    nodes_by_type = {
        item["type"]: item["count"]
        for item in graph_stats.get("nodes_by_type", [])
    }

    return {
        "graph_nodes": total_nodes,
        "graph_edges": total_edges,
        "heuristics_captured": nodes_by_type.get("HEURISTIC", 0),
        "employees_modeled": nodes_by_type.get("EMPLOYEE", 0),
        "failure_modes_tracked": nodes_by_type.get("FAILURE_MODE", 0),
        "work_codes_covered": nodes_by_type.get("WORK_CODE", 0),
        "data_source": "500iq" if total_nodes > 0 else "unavailable",
    }


# ── Event handlers ────────────────────────────────────────────────────────── #

async def on_design_completed(event: Event):
    """Auto-predict cost when design completes."""
    project_id = event.project_id
    drivers = event.data.get("drivers", {})
    employee_id = event.data.get("employee_id")

    logger.info(f"Intelligence: Auto-predicting cost for project {project_id}")

    request = CostPredictionRequest(
        project_id=project_id,
        drivers=drivers,
        employee_id=employee_id,
    )
    await predict_cost(request)


async def on_calculations_completed(event: Event):
    """Check for anomalies when engineering calculations complete."""
    project_id = event.project_id

    logger.info(f"Intelligence: Checking for anomalies in project {project_id}")

    # Query 500IQ for failure modes related to this project's sign type
    sign_type = event.data.get("sign_type")
    if sign_type:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{IQ_BASE_URL}/traverse",
                    json={
                        "start_node_id": sign_type,
                        "relationship_types": ["CAUSED_BY"],
                        "max_depth": 2,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json().get("result", {})
                    failure_nodes = [
                        n for n in data.get("nodes", [])
                        if n.get("type") == "FAILURE_MODE"
                    ]
                    if failure_nodes:
                        logger.warning(
                            f"Intelligence: Found {len(failure_nodes)} failure modes "
                            f"for {sign_type} in project {project_id}"
                        )
                        await event_bus.publish(Event(
                            type="anomaly.detected",
                            source="intelligence",
                            project_id=project_id,
                            data={
                                "failure_modes": [n["label"] for n in failure_nodes],
                                "sign_type": sign_type,
                            }
                        ))
        except httpx.HTTPError:
            pass  # 500IQ unavailable — degrade gracefully


# Subscribe to events
event_bus.subscribe("design.completed", on_design_completed)
event_bus.subscribe("calculations.completed", on_calculations_completed)

# Register with platform
registry.register(module_def, router)

