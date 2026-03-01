"""
seed_from_warehouse.py — Seed 500IQ from REAL Eagle Sign warehouse data.

Reads pre-computed calibration JSONs (sourced from signx.duckdb):
  - sign_type_classifier.json  → SIGN_TYPE nodes
  - work_code_profiles.json    → WORK_CODE nodes + estimation variance edges
  - workforce_intelligence.json → EMPLOYEE nodes + employee<->work_code edges
  - blind_spots_analysis.json  → HEURISTIC nodes (OT blind spots, underestimates)
  - calibration.json           → install floors, OT factors

ZERO fabricated data. Every node and edge traces to a real DuckDB query result.

Run:
    cd SignX-500IQ
    python seed_from_warehouse.py
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from database import get_db, init_db
from models import Edge, Node

# ── Data paths ──────────────────────────────────────────────────────────── #

DATA_DIR = Path(__file__).parent.parent / "signx-takeoff" / "data"

SIGN_TYPE_FILE = DATA_DIR / "sign_type_classifier.json"
WORK_CODE_FILE = DATA_DIR / "work_code_profiles.json"
WORKFORCE_FILE = DATA_DIR / "workforce_intelligence.json"
BLIND_SPOTS_FILE = DATA_DIR / "blind_spots_analysis.json"
CALIBRATION_FILE = DATA_DIR / "calibration.json"

# ── Thresholds for what gets seeded ─────────────────────────────────────── #

# Only seed employees with >= this many jobs on a work code
MIN_EMPLOYEE_JOBS = 50

# Only seed work code profiles with >= this many observations
MIN_WORK_CODE_N = 10

# Only seed sign types from the top N by revenue
TOP_SIGN_TYPES = 15

# Variance threshold to create a HEURISTIC: |variance| >= this many hours
UNDERESTIMATE_THRESHOLD = 3.0  # hours — systematic underestimate
OVERESTIMATE_THRESHOLD = -3.0  # hours — systematic overestimate

# OT blind spot: only create heuristic if OT appears in >= this % of jobs
OT_FREQUENCY_THRESHOLD = 25.0  # percent


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _make_id(prefix: str, key: str) -> str:
    """Create a node ID: PREFIX-KEY, uppercased, spaces→hyphens."""
    clean = key.strip().upper().replace(" ", "-").replace(".", "-")
    return f"{prefix}-{clean}"


# ── Node/Edge builders ─────────────────────────────────────────────────── #

def build_sign_type_nodes(data: dict) -> list[Node]:
    """Create SIGN_TYPE nodes from sign_type_classifier.json."""
    nodes = []
    types_ranked = data.get("types_by_revenue_rank", [])
    for entry in types_ranked[:TOP_SIGN_TYPES]:
        code = entry["code"]
        nodes.append(Node(
            id=_make_id("SIGN_TYPE", code),
            type="SIGN_TYPE",
            label=f'{code} — {entry["label"]}',
            properties={
                "code": code,
                "label": entry["label"],
                "revenue_rank": entry["rank"],
                "total_jobs": entry["jobs"],
                "total_revenue": entry["total_revenue"],
                "avg_revenue": entry["avg_revenue"],
                "avg_gm_pct": entry["avg_gm_pct"],
            },
            source="warehouse",
        ))
    return nodes


def build_work_code_nodes(profiles: dict) -> list[Node]:
    """Create WORK_CODE nodes from work_code_profiles.json (all unique codes)."""
    seen: set[str] = set()
    nodes = []
    for sign_type, info in profiles.items():
        if sign_type.startswith("_"):
            continue
        for wc in info.get("work_codes", []):
            code = wc["code"]
            if code in seen:
                continue
            seen.add(code)
            nodes.append(Node(
                id=_make_id("WORK_CODE", code),
                type="WORK_CODE",
                label=f'{code} — {wc["desc"]}',
                properties={
                    "code": code,
                    "description": wc["desc"],
                },
                source="warehouse",
            ))
    return nodes


def build_employee_nodes(workforce: dict) -> list[Node]:
    """Create EMPLOYEE nodes from workforce_intelligence.json.

    Only includes employees with at least MIN_EMPLOYEE_JOBS on any single work code.
    """
    # Aggregate: find each employee's max job count across all work codes
    emp_max_jobs: dict[str, int] = {}
    emp_work_codes: dict[str, list[dict]] = {}

    for rec in workforce.get("F1_employee_profiles", {}).get("data", []):
        name = rec["employee"]
        jobs = rec["jobs"]
        emp_max_jobs[name] = max(emp_max_jobs.get(name, 0), jobs)
        if name not in emp_work_codes:
            emp_work_codes[name] = []
        emp_work_codes[name].append(rec)

    nodes = []
    for name, max_jobs in sorted(emp_max_jobs.items()):
        if max_jobs < MIN_EMPLOYEE_JOBS:
            continue
        # Find their top work code
        recs = emp_work_codes[name]
        top = max(recs, key=lambda r: r["jobs"])
        total_jobs = sum(r["jobs"] for r in recs)
        nodes.append(Node(
            id=_make_id("EMPLOYEE", name),
            type="EMPLOYEE",
            label=name,
            properties={
                "name": name,
                "total_job_entries": total_jobs,
                "top_work_code": top["work_code"],
                "top_work_code_desc": top["description"],
                "top_work_code_jobs": top["jobs"],
                "work_codes_count": len(recs),
            },
            source="warehouse",
        ))
    return nodes


def build_employee_work_code_edges(workforce: dict) -> list[Edge]:
    """Create EMPLOYEE --WORKS_ON--> WORK_CODE edges.

    Only for employees that pass the MIN_EMPLOYEE_JOBS filter,
    and only for work codes where they have >= MIN_EMPLOYEE_JOBS.
    """
    edges = []
    emp_max_jobs: dict[str, int] = {}
    for rec in workforce.get("F1_employee_profiles", {}).get("data", []):
        emp_max_jobs[rec["employee"]] = max(
            emp_max_jobs.get(rec["employee"], 0), rec["jobs"]
        )

    for rec in workforce.get("F1_employee_profiles", {}).get("data", []):
        name = rec["employee"]
        if emp_max_jobs.get(name, 0) < MIN_EMPLOYEE_JOBS:
            continue
        if rec["jobs"] < MIN_EMPLOYEE_JOBS:
            continue

        edges.append(Edge(
            source_id=_make_id("EMPLOYEE", name),
            target_id=_make_id("WORK_CODE", rec["work_code"]),
            relationship_type="USES",
            confidence=min(rec["jobs"] / 500.0, 1.0),  # Scale confidence by volume
            status="validated",
            evidence={
                "jobs": rec["jobs"],
                "avg_hours": rec["avg_hours"],
                "stddev": rec["stddev"],
                "fastest": rec["fastest"],
                "slowest": rec["slowest"],
                "source": "workforce_intelligence.json",
            },
        ))
    return edges


def build_variance_heuristics(profiles: dict) -> tuple[list[Node], list[Edge]]:
    """Create HEURISTIC nodes for systematic estimation errors.

    Only for variances that exceed UNDERESTIMATE_THRESHOLD or OVERESTIMATE_THRESHOLD.
    """
    nodes = []
    edges = []
    seen_heuristics: set[str] = set()

    for sign_type, info in profiles.items():
        if sign_type.startswith("_"):
            continue
        for wc in info.get("work_codes", []):
            code = wc["code"]
            n = wc.get("n", 0)
            if n < MIN_WORK_CODE_N:
                continue

            variance_str = wc.get("variance", "0")
            variance = float(variance_str)

            # Check thresholds
            if variance >= UNDERESTIMATE_THRESHOLD:
                direction = "underestimate"
                severity = "critical" if variance >= 10.0 else "significant"
            elif variance <= OVERESTIMATE_THRESHOLD:
                direction = "overestimate"
                severity = "critical" if variance <= -10.0 else "significant"
            else:
                continue

            heuristic_id = _make_id(
                "HEURISTIC", f"{sign_type}-{code}-{direction.upper()}"
            )
            if heuristic_id in seen_heuristics:
                continue
            seen_heuristics.add(heuristic_id)

            est = wc.get("est", 0)
            mean = wc.get("mean", 0)

            # adjustment_factor: ratio of actual to estimated
            # >1.0 = underestimate (actual exceeds estimate)
            # <1.0 = overestimate (estimate exceeds actual)
            if est and est > 0:
                factor = round(mean / est, 3)
            else:
                factor = None  # Can't compute ratio if est is 0

            nodes.append(Node(
                id=heuristic_id,
                type="HEURISTIC",
                label=(
                    f'{sign_type} {code} ({wc["desc"]}): '
                    f'{direction} by {abs(variance):.1f}h'
                ),
                properties={
                    "sign_type": sign_type,
                    "work_code": code,
                    "work_code_desc": wc["desc"],
                    "direction": direction,
                    "severity": severity,
                    "variance_hours": variance,
                    "est_hours": est,
                    "actual_mean_hours": mean,
                    "adjustment_factor": factor,
                    "sample_size": n,
                    "confidence": min(n / 100.0, 0.99),
                    "source": "work_code_profiles.json (DuckDB warehouse)",
                },
                source="warehouse",
            ))

            # HEURISTIC --IMPACTS--> WORK_CODE
            edges.append(Edge(
                source_id=heuristic_id,
                target_id=_make_id("WORK_CODE", code),
                relationship_type="IMPACTS",
                confidence=min(n / 100.0, 0.99),
                status="validated",
                evidence={
                    "variance_hours": variance,
                    "sample_size": n,
                    "source": "DuckDB warehouse query",
                },
            ))

            # SIGN_TYPE --ADJUSTS--> HEURISTIC
            edges.append(Edge(
                source_id=_make_id("SIGN_TYPE", sign_type),
                target_id=heuristic_id,
                relationship_type="ADJUSTS",
                confidence=min(n / 100.0, 0.99),
                status="validated",
                evidence={
                    "sign_type": sign_type,
                    "applies_to_code": code,
                },
            ))

    return nodes, edges


def build_ot_blind_spot_heuristics(
    blind_spots: dict, calibration: dict,
) -> tuple[list[Node], list[Edge]]:
    """Create HEURISTIC nodes for overtime blind spots.

    These are work codes (9200, 9600, 9400, 9800) that appear frequently
    in jobs but are NEVER included in estimates (est=0.00).
    """
    nodes = []
    edges = []

    ot_factors = calibration.get("ot_factors", {})

    for entry in blind_spots.get("E1_overtime", {}).get("data", []):
        sign_type = entry.get("sign_type")
        if sign_type is None:
            continue  # Skip global aggregates
        wc = entry["work_code"]
        jobs = entry["jobs"]
        avg_ot = entry["avg_ot_per_job"]
        total_ot = entry["total_ot_hours"]

        # Check if this sign type has calibrated OT factors
        ot_info = ot_factors.get(sign_type, {})
        total_jobs = ot_info.get("total_jobs", 0)
        if total_jobs == 0:
            continue

        freq_pct = (jobs / total_jobs) * 100.0
        if freq_pct < OT_FREQUENCY_THRESHOLD:
            continue

        # OT code descriptions
        ot_desc = {
            "9200": "FABRICATION OVERTIME",
            "9400": "PAINT DEPT OVERTIME",
            "9600": "INSTALL OVERTIME 1 MAN",
            "9800": "OVERTIME TRAVEL",
        }.get(wc, f"OVERTIME ({wc})")

        heuristic_id = _make_id("HEURISTIC", f"{sign_type}-{wc}-OT-BLIND-SPOT")

        nodes.append(Node(
            id=heuristic_id,
            type="HEURISTIC",
            label=(
                f'{sign_type} {wc} ({ot_desc}): '
                f'OT in {freq_pct:.0f}% of jobs, avg {avg_ot:.1f}h, '
                f'always estimated at 0.00h'
            ),
            properties={
                "sign_type": sign_type,
                "work_code": wc,
                "work_code_desc": ot_desc,
                "direction": "underestimate",
                "severity": "critical",
                "variance_hours": avg_ot,
                "est_hours": 0.0,
                "actual_mean_hours": avg_ot,
                "frequency_pct": round(freq_pct, 1),
                "jobs_with_ot": jobs,
                "total_ot_hours": total_ot,
                "adjustment_factor": None,  # Can't ratio against 0 estimate
                "confidence": min(jobs / 200.0, 0.99),
                "source": "blind_spots_analysis.json (DuckDB warehouse)",
            },
            source="warehouse",
        ))

        # HEURISTIC --IMPACTS--> WORK_CODE
        wc_node_id = _make_id("WORK_CODE", wc)
        edges.append(Edge(
            source_id=heuristic_id,
            target_id=wc_node_id,
            relationship_type="IMPACTS",
            confidence=min(jobs / 200.0, 0.99),
            status="validated",
            evidence={
                "frequency_pct": round(freq_pct, 1),
                "avg_ot_hours": avg_ot,
                "source": "DuckDB warehouse blind spot analysis",
            },
        ))

        # SIGN_TYPE --ADJUSTS--> HEURISTIC
        edges.append(Edge(
            source_id=_make_id("SIGN_TYPE", sign_type),
            target_id=heuristic_id,
            relationship_type="ADJUSTS",
            confidence=min(jobs / 200.0, 0.99),
            status="validated",
            evidence={
                "sign_type": sign_type,
                "ot_code": wc,
            },
        ))

    return nodes, edges


def build_ot_work_code_nodes() -> list[Node]:
    """Ensure OT work code nodes exist (they might not be in profiles)."""
    ot_codes = [
        ("9200", "FABRICATION OVERTIME"),
        ("9400", "PAINT DEPT OVERTIME"),
        ("9600", "INSTALL OVERTIME 1 MAN"),
        ("9800", "OVERTIME TRAVEL"),
    ]
    return [
        Node(
            id=_make_id("WORK_CODE", code),
            type="WORK_CODE",
            label=f"{code} — {desc}",
            properties={"code": code, "description": desc},
            source="warehouse",
        )
        for code, desc in ot_codes
    ]


# ── Main seed function ─────────────────────────────────────────────────── #

async def seed():
    """Load all real warehouse data into 500IQ."""
    await init_db()

    # Load source data
    sign_types = _load_json(SIGN_TYPE_FILE)
    profiles = _load_json(WORK_CODE_FILE)
    workforce = _load_json(WORKFORCE_FILE)
    blind_spots = _load_json(BLIND_SPOTS_FILE)
    calibration = _load_json(CALIBRATION_FILE)

    # Build all nodes and edges
    all_nodes: list[Node] = []
    all_edges: list[Edge] = []

    # 1. Sign types
    st_nodes = build_sign_type_nodes(sign_types)
    all_nodes.extend(st_nodes)
    print(f"  SIGN_TYPE nodes: {len(st_nodes)}")

    # 2. Work codes (from profiles + OT codes)
    wc_nodes = build_work_code_nodes(profiles)
    ot_nodes = build_ot_work_code_nodes()
    # Merge: OT codes might duplicate, dedup by ID
    wc_ids = {n.id for n in wc_nodes}
    for otn in ot_nodes:
        if otn.id not in wc_ids:
            wc_nodes.append(otn)
    all_nodes.extend(wc_nodes)
    print(f"  WORK_CODE nodes: {len(wc_nodes)}")

    # 3. Employees
    emp_nodes = build_employee_nodes(workforce)
    all_nodes.extend(emp_nodes)
    print(f"  EMPLOYEE nodes:  {len(emp_nodes)}")

    # 4. Employee -> Work Code edges
    emp_edges = build_employee_work_code_edges(workforce)
    all_edges.extend(emp_edges)
    print(f"  EMPLOYEE->WORK_CODE edges: {len(emp_edges)}")

    # 5. Variance heuristics (systematic underestimates/overestimates)
    var_nodes, var_edges = build_variance_heuristics(profiles)
    all_nodes.extend(var_nodes)
    all_edges.extend(var_edges)
    print(f"  VARIANCE HEURISTIC nodes: {len(var_nodes)}")
    print(f"  VARIANCE edges: {len(var_edges)}")

    # 6. OT blind spot heuristics
    ot_h_nodes, ot_h_edges = build_ot_blind_spot_heuristics(blind_spots, calibration)
    all_nodes.extend(ot_h_nodes)
    all_edges.extend(ot_h_edges)
    print(f"  OT BLIND SPOT HEURISTIC nodes: {len(ot_h_nodes)}")
    print(f"  OT BLIND SPOT edges: {len(ot_h_edges)}")

    # ── Insert into DB ────────────────────────────────────────────────────
    print(f"\n  TOTAL: {len(all_nodes)} nodes, {len(all_edges)} edges")
    print("  Inserting...")

    # Dedup nodes by ID (first wins)
    seen_ids: set[str] = set()
    deduped_nodes: list[Node] = []
    for n in all_nodes:
        if n.id not in seen_ids:
            seen_ids.add(n.id)
            deduped_nodes.append(n)

    async with get_db() as session:
        created = 0
        merged = 0
        for node in deduped_nodes:
            existing = await session.get(Node, node.id)
            if existing is None:
                session.add(node)
                created += 1
            else:
                # Merge properties
                if existing.type == node.type:
                    base = existing.properties or {}
                    incoming = node.properties or {}
                    existing.properties = {**base, **incoming}
                    if node.label:
                        existing.label = node.label
                    merged += 1

        await session.flush()
        print(f"  Nodes: {created} created, {merged} merged")

        # Dedup edges by (source, target, rel_type)
        edge_created = 0
        edge_skipped = 0
        for edge in all_edges:
            # Check endpoints exist
            if await session.get(Node, edge.source_id) is None:
                edge_skipped += 1
                continue
            if await session.get(Node, edge.target_id) is None:
                edge_skipped += 1
                continue

            from sqlalchemy import select as sel
            stmt = sel(Edge).where(
                Edge.source_id == edge.source_id,
                Edge.target_id == edge.target_id,
                Edge.relationship_type == edge.relationship_type,
            )
            result = await session.execute(stmt)
            if result.scalars().first() is None:
                session.add(edge)
                edge_created += 1
            else:
                edge_skipped += 1

        await session.flush()
        print(f"  Edges: {edge_created} created, {edge_skipped} skipped/existing")

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  500IQ SEEDED FROM REAL WAREHOUSE DATA")
    print(f"{'='*60}")
    print(f"  Source: signx-takeoff/data/ (from signx.duckdb)")
    print(f"  Calibration date: {calibration.get('metadata', {}).get('calibration_date', 'unknown')}")
    print(f"  Nodes created: {created}")
    print(f"  Nodes merged:  {merged}")
    print(f"  Edges created: {edge_created}")
    print(f"  Edges skipped: {edge_skipped}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(seed())
