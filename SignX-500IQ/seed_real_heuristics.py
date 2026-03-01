"""
seed_real_heuristics.py — Inject 5 real tribal-knowledge heuristics into 500IQ.

ADDS to the existing Jeff Factor data (does NOT delete anything).
Uses upsert behavior: checks if nodes exist, merges metadata if so.

Run:
    cd SignX-500IQ
    python seed_real_heuristics.py

Heuristics seeded:
  1. Two-Person Brake Press Rule (cabinets > 6ft)
  2. CNC Grain Rotation (15° for brushed aluminum)
  3. Work Code 0310 Dead Code (zero utilization)
  4. Supplier X Aluminum Defect (Job 45678 rework)
  5. Joe's Channel Letter Padding (unconfirmed)
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, init_db
from models import Edge, Node


# ── Helper: deep merge ──────────────────────────────────────────────────── #

def _deep_merge(base: dict, incoming: dict) -> dict:
    merged = dict(base)
    for k, v in incoming.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = _deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


# ── Upsert helpers ──────────────────────────────────────────────────────── #

async def upsert_node(
    session: AsyncSession,
    node_id: str,
    node_type: str,
    label: str,
    properties: dict,
    source: str = "manual",
) -> str:
    """Insert node if new, merge metadata if exists. Returns 'created'|'merged'|'skipped'."""
    existing = await session.get(Node, node_id)
    if existing is None:
        node = Node(
            id=node_id,
            type=node_type,
            label=label,
            properties=properties,
            source=source,
        )
        session.add(node)
        return "created"
    else:
        if existing.type != node_type:
            print(f"  ! SKIP {node_id}: type mismatch ({existing.type} != {node_type})")
            return "skipped"
        existing.properties = _deep_merge(existing.properties or {}, properties)
        existing.label = label or existing.label
        return "merged"


async def upsert_edge(
    session: AsyncSession,
    source_id: str,
    target_id: str,
    relationship_type: str,
    confidence: float,
    evidence: dict | None = None,
    status: str = "validated",
) -> str:
    """Insert edge if new, update confidence if exists. Returns 'created'|'updated'|'skipped'."""
    # Check endpoints exist
    if await session.get(Node, source_id) is None:
        print(f"  ! SKIP edge {source_id}-->{target_id}: source node missing")
        return "skipped"
    if await session.get(Node, target_id) is None:
        print(f"  ! SKIP edge {source_id}-->{target_id}: target node missing")
        return "skipped"

    stmt = select(Edge).where(
        Edge.source_id == source_id,
        Edge.target_id == target_id,
        Edge.relationship_type == relationship_type,
    )
    result = await session.execute(stmt)
    existing = result.scalars().first()

    if existing is None:
        edge = Edge(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            confidence=confidence,
            status=status,
            evidence=evidence or {},
        )
        session.add(edge)
        return "created"
    else:
        existing.confidence = max(existing.confidence, confidence)
        if evidence:
            existing.evidence = _deep_merge(existing.evidence or {}, evidence)
        return "updated"


# ── Seed definitions ────────────────────────────────────────────────────── #

NODES = [
    # --- Heuristic 1: Two-Person Brake Press Rule ---
    ("EQUIPMENT-BRAKE-PRESS", "EQUIPMENT", "Brake Press", {
        "name": "Brake Press",
        "location": "fab shop",
    }),
    ("HEURISTIC-BRAKE-PRESS-TWO-PERSON", "HEURISTIC", "Two-person brake press rule (>6ft cabinets)", {
        "description": "Cabinet signs over 6 feet require two people on the brake press. "
                       "The 1974 ABC pricing guide never accounted for this because they didn't have a brake press.",
        "threshold": "sign_height > 6ft",
        "labor_multiplier": 2.0,
        "confidence": 0.95,
        "source": "shop floor observation",
    }),

    # --- Heuristic 2: CNC Grain Rotation ---
    ("EMPLOYEE-CNC-OPERATOR", "EMPLOYEE", "CNC Plasma Operator", {
        "name": "CNC Plasma Operator",
        "role": "fabricator",
    }),
    ("MATERIAL-BRUSHED-ALUMINUM", "MATERIAL", "Brushed Aluminum Sheet", {
        "name": "Brushed Aluminum Sheet",
    }),
    ("HEURISTIC-GRAIN-ROTATION", "HEURISTIC", "CNC grain rotation (15° for brushed alu)", {
        "description": "CNC plasma operator nests parts at 15-degree rotation for grain direction "
                       "on brushed aluminum. Reduces scrap by approximately 8 percent.",
        "rotation_angle": 15,
        "scrap_reduction_pct": 8.0,
        "confidence": 0.80,
        "source": "operator preference",
    }),

    # --- Heuristic 3: Work Code 0310 Dead Code ---
    ("WORK_CODE-0310", "WORK_CODE", "0310 — Dead Code (zero utilization)", {
        "description": "Unknown - zero utilization",
        "status": "dead",
    }),
    ("HEURISTIC-0310-ZERO-UTIL", "HEURISTIC", "WC-0310 zero utilization (remove from templates)", {
        "description": "Work code 0310 has had zero utilization across all analyzed jobs. "
                       "SignX-Intel confirmed this. Should be removed from estimation templates.",
        "utilization_rate": 0.0,
        "confidence": 1.0,
        "source": "SignX-Intel analysis",
        "jobs_analyzed": 2443,
    }),

    # --- Heuristic 4: Supplier X Aluminum Defect ---
    ("SUPPLIER-X", "SUPPLIER", "Supplier X", {
        "name": "Supplier X",
    }),
    ("FAILURE-ALUMINUM-OUT-OF-SPEC", "FAILURE_MODE", "Aluminum extrusion out of spec (Supplier X)", {
        "description": "Aluminum extrusion from Supplier X was out of spec. "
                       "Caused 12 hours of rework on frame welding.",
        "rework_hours": 12,
        "confidence": 0.90,
        "source": "welder report",
    }),
    ("JOB-45678", "JOB", "Job 45678 (welding rework from material defect)", {
        "description": "Job with welding rework due to material defect",
    }),

    # --- Heuristic 5: Joe's Channel Letter Padding ---
    ("EMPLOYEE-JOE", "EMPLOYEE", "Joe", {
        "name": "Joe",
        "role": "Estimator",
    }),
    ("HEURISTIC-JOE-CHANNEL-PADDING", "HEURISTIC", "Joe's channel letter labor padding (unconfirmed)", {
        "description": "Joe adds labor padding on channel letter estimates. "
                       "Pattern detected by SignX-Intel but exact multiplier unknown.",
        "sign_type": "channel_letters",
        "multiplier": None,
        "confidence": 0.70,
        "source": "SignX-Intel pattern detection, unconfirmed with Joe",
    }),
]

EDGES = [
    # --- Heuristic 1: Brake Press ---
    ("HEURISTIC-BRAKE-PRESS-TWO-PERSON", "EQUIPMENT-BRAKE-PRESS", "REQUIRES", 0.95,
     {"source": "shop floor observation", "note": "Large cabinets need two operators on press"}),
    ("HEURISTIC-BRAKE-PRESS-TWO-PERSON", "WORK_CODE-0270", "IMPACTS", 0.95,
     {"source": "shop floor observation", "note": "Doubles labor time for >6ft cabinet fab"}),

    # --- Heuristic 2: CNC Grain Rotation ---
    ("EMPLOYEE-CNC-OPERATOR", "HEURISTIC-GRAIN-ROTATION", "APPLIES", 0.80,
     {"source": "operator preference", "note": "Operator independently applies rotation"}),
    ("HEURISTIC-GRAIN-ROTATION", "MATERIAL-BRUSHED-ALUMINUM", "APPLIES_TO", 0.80,
     {"source": "operator preference", "note": "Only for brushed aluminum sheets"}),

    # --- Heuristic 3: 0310 Dead Code ---
    ("HEURISTIC-0310-ZERO-UTIL", "WORK_CODE-0310", "IMPACTS", 1.0,
     {"source": "SignX-Intel analysis", "jobs_analyzed": 2443}),

    # --- Heuristic 4: Supplier X Defect ---
    ("FAILURE-ALUMINUM-OUT-OF-SPEC", "SUPPLIER-X", "CAUSED_BY", 0.90,
     {"source": "welder report", "defect": "extrusion out of spec"}),
    ("FAILURE-ALUMINUM-OUT-OF-SPEC", "JOB-45678", "IMPACTS_JOB", 0.90,
     {"source": "welder report", "rework_hours": 12}),
    ("JOB-45678", "MATERIAL-BRUSHED-ALUMINUM", "USED_MATERIAL", 0.85,
     {"source": "job materials list"}),

    # --- Heuristic 5: Joe's Channel Letter Padding ---
    ("EMPLOYEE-JOE", "HEURISTIC-JOE-CHANNEL-PADDING", "USES", 0.70,
     {"source": "SignX-Intel pattern detection", "confirmed": False}),
    ("HEURISTIC-JOE-CHANNEL-PADDING", "WORK_CODE-0270", "IMPACTS", 0.70,
     {"source": "SignX-Intel pattern detection", "note": "Exact multiplier unknown"}),
]


async def seed():
    """Upsert all 5 tribal-knowledge heuristics into the existing 500IQ graph."""
    await init_db()

    nodes_created = 0
    nodes_merged = 0
    nodes_skipped = 0
    edges_created = 0
    edges_updated = 0
    edges_skipped = 0

    async with get_db() as session:
        # ── Upsert nodes ──────────────────────────────────────────────
        print("\n=== NODES ===")
        for node_id, node_type, label, properties in NODES:
            action = await upsert_node(session, node_id, node_type, label, properties)
            icon = {"created": "+", "merged": "~", "skipped": "!"}[action]
            print(f"  [{icon}] {action:8s}  {node_id:45s}  type={node_type}")
            if action == "created":
                nodes_created += 1
            elif action == "merged":
                nodes_merged += 1
            else:
                nodes_skipped += 1

        await session.flush()

        # ── Upsert edges ──────────────────────────────────────────────
        print("\n=== EDGES ===")
        for src, tgt, rel, conf, evidence in EDGES:
            action = await upsert_edge(session, src, tgt, rel, conf, evidence)
            icon = {"created": "+", "updated": "~", "skipped": "!"}[action]
            print(f"  [{icon}] {action:8s}  {src:45s} --{rel:-<15s}--> {tgt}")
            if action == "created":
                edges_created += 1
            elif action == "updated":
                edges_updated += 1
            else:
                edges_skipped += 1

    # ── Summary ───────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  SEED SUMMARY")
    print(f"{'='*60}")
    print(f"  Nodes created:  {nodes_created}")
    print(f"  Nodes merged:   {nodes_merged}")
    print(f"  Nodes skipped:  {nodes_skipped}")
    print(f"  Edges created:  {edges_created}")
    print(f"  Edges updated:  {edges_updated}")
    print(f"  Edges skipped:  {edges_skipped}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(seed())
