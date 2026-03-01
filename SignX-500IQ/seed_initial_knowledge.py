"""
seed_initial_knowledge.py — Inject the first tribal knowledge into 500IQ.

Seeds the Jeff Factor: the discovery that Estimator Jeff consistently
rounds up cabinet shop-fab labor by ~15%, causing a 94% overestimation
on Work Code 0270 (Shop Fabrication) for cabinet signs.

Graph structure created:

  EMPLOYEE-JEFF  --USES-->  HEURISTIC-CABINET-PADDING
                              --IMPACTS-->  WORK_CODE-0270

  SIGN_TYPE-CABINET  --ADJUSTS-->  HEURISTIC-CABINET-PADDING

  JOB-BENCHMARK-0270  --LEARNED_FROM-->  HEURISTIC-CABINET-PADDING

Run:
    cd SignX-500IQ
    python seed_initial_knowledge.py
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone

from database import init_db, get_db
from models import Edge, Node


NODES = [
    Node(
        id="EMPLOYEE-JEFF",
        type="EMPLOYEE",
        label="Jeff",
        properties={
            "name": "Jeff",
            "role": "Estimator",
            "years_experience": 22,
            "specialty": "cabinets",
            "notes": "Senior estimator, trained on ABC system. Tends to pad estimates for safety.",
        },
        source="manual",
    ),
    Node(
        id="WORK_CODE-0270",
        type="WORK_CODE",
        label="0270 — Shop Fabrication",
        properties={
            "code": "0270",
            "description": "Shop Fabrication",
            "department": "Manufacturing",
            "avg_historical_hours": 16.2,
            "notes": "Primary work code for in-house cabinet and channel letter fab.",
        },
        source="warehouse",
    ),
    Node(
        id="HEURISTIC-CABINET-PADDING",
        type="HEURISTIC",
        label="Jeff cabinet labor padding (+15%)",
        properties={
            "description": "Rounds up labor hours by 15% on cabinet signs to create a safety buffer",
            "adjustment_factor": 1.15,
            "confidence": 0.94,
            "discovery_method": "Statistical analysis of ABC estimates vs actual WO hours",
            "sample_size": 47,
            "overestimation_pct": 94,
            "note": "Found during 2025 audit: Jeff's cabinet estimates consistently "
                    "exceed actuals by ~15%. This is a learned habit from early career "
                    "when cabinet builds had higher rework rates. Rework rates have "
                    "since improved but the padding habit persists.",
        },
        source="extracted",
    ),
    Node(
        id="SIGN_TYPE-CABINET",
        type="SIGN_TYPE",
        label="Cabinet Signs",
        properties={
            "codes": ["CABLIT", "CABNON"],
            "description": "Internally illuminated cabinet-style signs",
            "typical_fab_hours_range": [8, 32],
        },
        source="warehouse",
    ),
    Node(
        id="JOB-BENCHMARK-0270",
        type="JOB",
        label="Benchmark: WC-0270 analysis (2025 audit)",
        properties={
            "description": "Aggregate benchmark from 2025 cost audit on Work Code 0270",
            "matching_jobs": 47,
            "avg_estimated_hours": 18.6,
            "avg_actual_hours": 16.2,
            "overestimation_ratio": 1.15,
            "audit_date": "2025-06",
        },
        source="extracted",
    ),
    Node(
        id="FAILURE_MODE-OVERESTIMATE",
        type="FAILURE_MODE",
        label="Systematic overestimation",
        properties={
            "description": "Estimator consistently pads hours beyond actual labor required",
            "impact": "Lost bids due to inflated pricing; margin appears higher on paper",
            "severity": "medium",
            "mitigation": "Calibrate estimate using 500IQ adjustment factor",
        },
        source="manual",
    ),
]


EDGES = [
    # Jeff USES the cabinet padding heuristic
    Edge(
        source_id="EMPLOYEE-JEFF",
        target_id="HEURISTIC-CABINET-PADDING",
        relationship_type="USES",
        weight=1.0,
        confidence=0.94,
        status="validated",
        evidence={
            "source": "2025 cost audit",
            "sample_size": 47,
            "method": "compared ABC estimate vs actual WO labor on WC-0270",
        },
    ),
    # The heuristic IMPACTS Work Code 0270
    Edge(
        source_id="HEURISTIC-CABINET-PADDING",
        target_id="WORK_CODE-0270",
        relationship_type="IMPACTS",
        weight=1.0,
        confidence=0.94,
        status="validated",
        evidence={
            "overestimation_pct": 94,
            "avg_delta_hours": 2.4,
        },
    ),
    # Cabinet sign type ADJUSTS via the heuristic
    Edge(
        source_id="SIGN_TYPE-CABINET",
        target_id="HEURISTIC-CABINET-PADDING",
        relationship_type="ADJUSTS",
        weight=1.0,
        confidence=0.90,
        status="validated",
        evidence={
            "applies_to": ["CABLIT", "CABNON"],
            "note": "Padding habit is specific to cabinet-type signs",
        },
    ),
    # The heuristic was LEARNED_FROM the benchmark analysis
    Edge(
        source_id="HEURISTIC-CABINET-PADDING",
        target_id="JOB-BENCHMARK-0270",
        relationship_type="LEARNED_FROM",
        weight=1.0,
        confidence=1.0,
        status="validated",
        evidence={
            "audit": "2025 cost audit",
            "analyst": "500IQ knowledge extraction",
        },
    ),
    # The heuristic CAUSED_BY the overestimation failure mode
    Edge(
        source_id="HEURISTIC-CABINET-PADDING",
        target_id="FAILURE_MODE-OVERESTIMATE",
        relationship_type="CAUSED_BY",
        weight=0.8,
        confidence=0.85,
        status="validated",
        evidence={
            "note": "The padding habit is the root cause of systematic overestimation",
        },
    ),
    # Jeff WORKED_ON the benchmark jobs
    Edge(
        source_id="EMPLOYEE-JEFF",
        target_id="JOB-BENCHMARK-0270",
        relationship_type="WORKED_ON",
        weight=1.0,
        confidence=1.0,
        status="validated",
        evidence={"role": "estimator"},
    ),
]


async def seed():
    """Insert all nodes and edges into the 500IQ database."""
    await init_db()

    async with get_db() as session:
        # Check if already seeded
        existing = await session.get(Node, "EMPLOYEE-JEFF")
        if existing is not None:
            print("Database already seeded — EMPLOYEE-JEFF exists. Skipping.")
            return

        # Insert nodes
        for node in NODES:
            session.add(node)
            print(f"  + Node: {node.id:40s}  type={node.type}")

        await session.flush()

        # Insert edges
        for edge in EDGES:
            session.add(edge)
            print(
                f"  + Edge: {edge.source_id:40s} --{edge.relationship_type:-<15s}--> "
                f"{edge.target_id}"
            )

        await session.flush()

    print(f"\nSeeded {len(NODES)} nodes and {len(EDGES)} edges into 500IQ.")
    print("The brain is alive.")


if __name__ == "__main__":
    asyncio.run(seed())
