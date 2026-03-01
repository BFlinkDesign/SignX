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

        section("1. Seed from real warehouse data")

        from seed_from_warehouse import seed  # noqa: E402
        asyncio.run(seed())

        r = client.get("/stats")
        data = r.json()["result"]
        check("After seed: >= 100 nodes", data["total_nodes"] >= 100)
        check("After seed: >= 300 edges", data["total_edges"] >= 300)

        seed_nodes = data["total_nodes"]
        seed_edges = data["total_edges"]

        # Verify real node types exist
        types_present = {x["type"] for x in data["nodes_by_type"]}
        check("SIGN_TYPE nodes exist", "SIGN_TYPE" in types_present)
        check("WORK_CODE nodes exist", "WORK_CODE" in types_present)
        check("EMPLOYEE nodes exist", "EMPLOYEE" in types_present)
        check("HEURISTIC nodes exist", "HEURISTIC" in types_present)

        # ── 2) Heuristic — real warehouse query ─────────────────────── #

        section("2. Heuristic query (CLLIT + 0270 — real underestimate)")

        r = client.post("/heuristic", json={
            "sign_type": "SIGN_TYPE-CLLIT",
            "work_code": "WORK_CODE-0270",
        })
        check("POST /heuristic returns 200", r.status_code == 200)
        result = r.json()["result"]
        check(
            ">= 1 adjustment found for CLLIT 0270",
            len(result["adjustments"]) >= 1,
            f"got {len(result['adjustments'])}",
        )
        # The CLLIT 0270 underestimate has factor ~10.294
        cllit_adj = result["adjustments"][0]
        check(
            "Adjustment factor > 5.0 (massive underestimate)",
            cllit_adj["adjustment_factor"] is not None
            and cllit_adj["adjustment_factor"] > 5.0,
            f"got {cllit_adj['adjustment_factor']}",
        )
        check(
            "Confidence > 0.9 (n=228)",
            cllit_adj["confidence"] > 0.9,
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

        # Verify total edge count hasn't changed (seed_edges + 1 batch edge)
        r = client.get("/stats")
        data = r.json()["result"]
        check(
            f"Total edges = {seed_edges + 1} (seed + 1 batch, no duplicates)",
            data["total_edges"] == seed_edges + 1,
            f"got {data['total_edges']}",
        )

        # ── 5) Safety gating — proposed edges excluded from /heuristic ── #

        section("5. Safety gating — proposed edge NOT in /heuristic")

        # Count validated adjustments BEFORE adding proposed edges
        r = client.post("/heuristic", json={
            "sign_type": "SIGN_TYPE-CLLIT",
            "work_code": "WORK_CODE-0270",
        })
        baseline_adj = r.json()["result"]
        baseline_count = len(baseline_adj["adjustments"])
        baseline_factor = baseline_adj["combined_factor"]

        # Add proposed edges: Chad Nelson USES alu heuristic, alu heuristic IMPACTS 0270
        batch2 = {
            "nodes": [],
            "edges": [
                {
                    "source_id": "EMPLOYEE-CHAD-NELSON",
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

        # Query heuristic WITHOUT include_proposed — should be unchanged
        r = client.post("/heuristic", json={
            "sign_type": "SIGN_TYPE-CLLIT",
            "work_code": "WORK_CODE-0270",
        })
        result = r.json()["result"]
        check(
            f"Without include_proposed: still {baseline_count} adjustment(s)",
            len(result["adjustments"]) == baseline_count,
            f"got {len(result['adjustments'])} adjustments",
        )
        check(
            f"Combined factor unchanged at {baseline_factor}",
            result["combined_factor"] == baseline_factor,
            f"got {result['combined_factor']}",
        )

        # Query WITH include_proposed — should include the new one
        r = client.post("/heuristic?include_proposed=true", json={
            "employee_id": "EMPLOYEE-CHAD-NELSON",
            "work_code": "WORK_CODE-0270",
        })
        result = r.json()["result"]
        check(
            "With include_proposed: >= 1 adjustment for Chad + 0270",
            len(result["adjustments"]) >= 1,
            f"got {len(result['adjustments'])} adjustments",
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

        # Find edges to validate
        uses_edge = None
        impacts_edge = None
        for e in proposed_edges:
            if (e["source_id"] == "EMPLOYEE-CHAD-NELSON"
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
                    "id": "EMPLOYEE-CHAD-NELSON",
                    "type": "MATERIAL",  # Wrong type — Chad is EMPLOYEE not MATERIAL
                    "label": "Chad (wrong type)",
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
        expected_nodes = seed_nodes + 2   # +2 from batch ingest (MATERIAL + HEURISTIC)
        expected_edges = seed_edges + 3   # +3 from batch ingest (ADJUSTS + USES + IMPACTS)
        check(
            f"{expected_nodes} total nodes ({seed_nodes} seed + 2 batch)",
            data["total_nodes"] == expected_nodes,
            f"got {data['total_nodes']}",
        )
        check(
            f"{expected_edges} total edges ({seed_edges} seed + 3 batch)",
            data["total_edges"] == expected_edges,
            f"got {data['total_edges']}",
        )

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
