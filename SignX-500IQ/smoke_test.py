"""
smoke_test.py — End-to-end smoke test for 500IQ Phase 4.

Starts the 500IQ app via TestClient (no live server needed),
then exercises batch ingest, idempotency, safety gating, and review workflow.

Run:
    cd SignX-500IQ
    python smoke_test.py
"""
from __future__ import annotations

import asyncio
import os
import sys

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Delete existing DB so we start clean
DB_PATH = "./signx_500iq.db"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

# Create tables before anything else
from database import init_db  # noqa: E402
asyncio.run(init_db())

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}  — {detail}")


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def run_tests():
    global PASS, FAIL

    with TestClient(app) as client:

        # ── 0) Health + empty stats ──────────────────────────────────── #

        section("0. Health & empty stats")

        r = client.get("/healthz")
        check("GET /healthz returns 200", r.status_code == 200)
        check("Status is 'ok'", r.json()["status"] == "ok")

        r = client.get("/stats")
        check("GET /stats returns 200", r.status_code == 200)
        check("Total nodes = 0 (empty DB)", r.json()["result"]["total_nodes"] == 0)
        check("Total edges = 0 (empty DB)", r.json()["result"]["total_edges"] == 0)

        # ── 1) Seed via script ───────────────────────────────────────── #

        section("1. Re-seed the Jeff Factor")

        from seed_initial_knowledge import seed  # noqa: E402
        asyncio.run(seed())

        r = client.get("/stats")
        data = r.json()["result"]
        check("After seed: 6 nodes", data["total_nodes"] == 6)
        check("After seed: 6 edges", data["total_edges"] == 6)

        # ── 2) Heuristic — validated edges only ──────────────────────── #

        section("2. Heuristic query (validated edges only)")

        r = client.post("/heuristic", json={
            "employee_id": "EMPLOYEE-JEFF",
            "work_code": "WORK_CODE-0270",
        })
        check("POST /heuristic returns 200", r.status_code == 200)
        result = r.json()["result"]
        check("1 adjustment found", len(result["adjustments"]) == 1)
        check(
            "Adjustment factor = 1.15",
            result["adjustments"][0]["adjustment_factor"] == 1.15,
        )
        check("Combined factor = 1.15", result["combined_factor"] == 1.15)
        check(
            "Confidence = 0.94",
            result["adjustments"][0]["confidence"] == 0.94,
        )

        # ── 3) Batch ingest (new nodes + proposed edge) ──────────────── #

        section("3. Batch ingest — new material + proposed edge")

        batch_payload = {
            "nodes": [
                {
                    "id": "MATERIAL-ALUMINUM-5052",
                    "type": "MATERIAL",
                    "label": "Aluminum 5052-H32",
                    "properties": {
                        "alloy": "5052",
                        "temper": "H32",
                        "yield_mpa": 193,
                        "common_use": "sign cabinets",
                    },
                },
                {
                    "id": "HEURISTIC-ALU-THICKNESS",
                    "type": "HEURISTIC",
                    "label": "Alu 5052 minimum 0.080\" for cabinets",
                    "properties": {
                        "description": "Use min 0.080\" 5052 for outdoor cabinets",
                        "adjustment_factor": 1.05,
                        "confidence": 0.80,
                        "note": "Extracted from shop foreman tribal knowledge",
                    },
                },
            ],
            "edges": [
                {
                    "source_id": "MATERIAL-ALUMINUM-5052",
                    "target_id": "HEURISTIC-ALU-THICKNESS",
                    "relationship_type": "ADJUSTS",
                    "confidence": 0.75,
                    "evidence": {"source": "shop foreman interview 2025-08"},
                },
            ],
            "source": "knowex-test",
        }

        r = client.post("/nodes/batch", json=batch_payload)
        check("POST /nodes/batch returns 200", r.status_code == 200)
        result = r.json()["result"]
        check("2 nodes created", result["nodes_created"] == 2)
        check("0 nodes updated", result["nodes_updated"] == 0)
        check("1 edge created", result["edges_created"] == 1)
        check("0 errors", len(result["errors"]) == 0)

        # Verify nodes exist
        r = client.get("/nodes/MATERIAL-ALUMINUM-5052")
        check("New node accessible via GET", r.status_code == 200)

        # Verify edge is proposed (not validated)
        r = client.get("/review/edges?status=proposed")
        check("Review list returns proposed edges", r.status_code == 200)
        proposed = r.json()
        check("1 proposed edge in review queue", proposed["count"] == 1)
        check(
            "Edge status is 'proposed'",
            proposed["edges"][0]["status"] == "proposed",
        )

        # ── 4) Idempotency — re-ingest same batch ───────────────────── #

        section("4. Idempotency — re-ingest same batch")

        r = client.post("/nodes/batch", json=batch_payload)
        check("Second POST /nodes/batch returns 200", r.status_code == 200)
        result = r.json()["result"]
        check("0 nodes created (upsert)", result["nodes_created"] == 0)
        check("2 nodes updated (merged)", result["nodes_updated"] == 2)
        check("0 edges created (dedup)", result["edges_created"] == 0)
        check("1 edge updated (confidence)", result["edges_updated"] == 1)

        # Verify total edge count hasn't changed
        r = client.get("/stats")
        data = r.json()["result"]
        check(
            "Total edges = 7 (6 seed + 1 batch, no duplicates)",
            data["total_edges"] == 7,
            f"got {data['total_edges']}",
        )

        # ── 5) Safety gating — proposed edges excluded from /heuristic ── #

        section("5. Safety gating — proposed edge NOT in /heuristic")

        # Add proposed edges: Jeff USES alu heuristic, alu heuristic IMPACTS 0270
        batch2 = {
            "nodes": [],
            "edges": [
                {
                    "source_id": "EMPLOYEE-JEFF",
                    "target_id": "HEURISTIC-ALU-THICKNESS",
                    "relationship_type": "USES",
                    "confidence": 0.60,
                    "evidence": {"source": "auto-extracted from meeting notes"},
                },
                {
                    "source_id": "HEURISTIC-ALU-THICKNESS",
                    "target_id": "WORK_CODE-0270",
                    "relationship_type": "IMPACTS",
                    "confidence": 0.55,
                    "evidence": {"source": "inferred correlation"},
                },
            ],
        }
        r = client.post("/nodes/batch", json=batch2)
        check("Batch with proposed edges succeeds", r.status_code == 200)

        # Query heuristic WITHOUT include_proposed
        r = client.post("/heuristic", json={
            "employee_id": "EMPLOYEE-JEFF",
            "work_code": "WORK_CODE-0270",
        })
        result = r.json()["result"]
        check(
            "Without include_proposed: still 1 adjustment (Jeff cabinet padding)",
            len(result["adjustments"]) == 1,
            f"got {len(result['adjustments'])} adjustments",
        )
        check(
            "Combined factor unchanged at 1.15",
            result["combined_factor"] == 1.15,
            f"got {result['combined_factor']}",
        )

        # Query WITH include_proposed
        r = client.post("/heuristic?include_proposed=true", json={
            "employee_id": "EMPLOYEE-JEFF",
            "work_code": "WORK_CODE-0270",
        })
        result = r.json()["result"]
        check(
            "With include_proposed: 2 adjustments",
            len(result["adjustments"]) == 2,
            f"got {len(result['adjustments'])} adjustments",
        )
        # Confidence-weighted average: (1.15×0.94 + 1.05×0.80) / (0.94+0.80)
        expected_cwa = round((1.15 * 0.94 + 1.05 * 0.80) / (0.94 + 0.80), 6)
        check(
            f"Combined factor (CWA) = {expected_cwa}",
            result["combined_factor"] == expected_cwa,
            f"got {result['combined_factor']}",
        )

        # ── 6) Review workflow — validate then re-check ──────────────── #

        section("6. Review workflow — validate proposed edge, re-check")

        r = client.get("/review/edges?status=proposed")
        proposed_edges = r.json()["edges"]
        check(
            "3 proposed edges in queue",
            len(proposed_edges) == 3,
            f"got {len(proposed_edges)}",
        )

        # Find the edges to validate
        uses_edge = None
        impacts_edge = None
        for e in proposed_edges:
            if (e["source_id"] == "EMPLOYEE-JEFF"
                    and e["relationship_type"] == "USES"):
                uses_edge = e
            if (e["relationship_type"] == "IMPACTS"
                    and e["target_id"] == "WORK_CODE-0270"
                    and e["source_id"] == "HEURISTIC-ALU-THICKNESS"):
                impacts_edge = e

        check("Found USES proposed edge", uses_edge is not None)
        check("Found IMPACTS proposed edge", impacts_edge is not None)

        if uses_edge and impacts_edge:
            r1 = client.post(f"/review/edges/{uses_edge['id']}/validate")
            r2 = client.post(f"/review/edges/{impacts_edge['id']}/validate")
            check("Validate USES edge returns 200", r1.status_code == 200)
            check("Validate IMPACTS edge returns 200", r2.status_code == 200)
            check(
                "USES edge now validated",
                r1.json()["result"]["status"] == "validated",
            )

            # Now /heuristic should return 2 adjustments without include_proposed
            r = client.post("/heuristic", json={
                "employee_id": "EMPLOYEE-JEFF",
                "work_code": "WORK_CODE-0270",
            })
            result = r.json()["result"]
            check(
                "After validation: 2 adjustments in default query",
                len(result["adjustments"]) == 2,
                f"got {len(result['adjustments'])}",
            )
            # Same CWA after validation
            check(
                f"Combined factor (CWA) = {expected_cwa}",
                result["combined_factor"] == expected_cwa,
                f"got {result['combined_factor']}",
            )

        # ── 7) Reject an edge ────────────────────────────────────────── #

        section("7. Reject workflow")

        r = client.get("/review/edges?status=proposed")
        remaining = r.json()["edges"]
        check(
            "1 proposed edge remaining",
            len(remaining) == 1,
            f"got {len(remaining)}",
        )

        if remaining:
            r = client.post(f"/review/edges/{remaining[0]['id']}/reject")
            check("Reject returns 200", r.status_code == 200)
            check(
                "Edge status is 'rejected'",
                r.json()["result"]["status"] == "rejected",
            )

            r = client.get("/review/edges?status=proposed")
            check("Proposed queue now empty", r.json()["count"] == 0)

        # ── 8) Strict mode error handling ─────────────────────────────── #

        section("8. Strict mode — type mismatch error")

        bad_batch = {
            "nodes": [
                {
                    "id": "EMPLOYEE-JEFF",
                    "type": "MATERIAL",  # Wrong type
                    "label": "Jeff (wrong type)",
                },
            ],
            "edges": [],
        }

        r = client.post("/nodes/batch?mode=strict", json=bad_batch)
        check("Type mismatch in strict mode returns 400", r.status_code == 400)
        check(
            "Error mentions 'type mismatch'",
            "type mismatch" in r.json()["detail"].lower(),
            r.json()["detail"],
        )

        # Same in best_effort mode
        r = client.post("/nodes/batch?mode=best_effort", json=bad_batch)
        check("Type mismatch in best_effort returns 200", r.status_code == 200)
        check(
            "Error recorded in response",
            len(r.json()["result"]["errors"]) == 1,
            str(r.json()["result"].get("errors", [])),
        )

        # ── 9) Final stats ────────────────────────────────────────────── #

        section("9. Final graph stats")

        r = client.get("/stats")
        data = r.json()["result"]
        node_summary = ", ".join(
            f"{x['type']}={x['count']}" for x in data["nodes_by_type"]
        )
        edge_summary = ", ".join(
            f"{x['type']}={x['count']}" for x in data["edges_by_type"]
        )
        print(f"  Nodes: {data['total_nodes']} ({node_summary})")
        print(f"  Edges: {data['total_edges']} ({edge_summary})")
        check("8 total nodes (6 seed + 2 batch)", data["total_nodes"] == 8)
        check("9 total edges (6 seed + 3 batch)", data["total_edges"] == 9)

    # ── Summary ──────────────────────────────────────────────────────── #

    print(f"\n{'='*60}")
    print(f"  RESULTS: {PASS} passed, {FAIL} failed out of {PASS + FAIL} checks")
    print(f"{'='*60}")

    if FAIL > 0:
        print("\n  SOME CHECKS FAILED — review output above.\n")
        sys.exit(1)
    else:
        print("\n  ALL CHECKS PASSED — 500IQ Phase 4 is solid.\n")
        sys.exit(0)


if __name__ == "__main__":
    run_tests()
