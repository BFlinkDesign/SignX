"""
test_performance.py — Performance benchmark suite for SignX-Takeoff.

Tests critical path latencies against target thresholds.
Each benchmark runs 3 iterations, reports min/avg/max, and grades PASS/WARN/FAIL.

PASS: within target
WARN: within 2x target
FAIL: beyond 2x target
"""

import asyncio
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
import uvicorn

from abc_engine import (
    ConstructionType,
    EstimateResult,
    FontType,
    JobInput,
    SignType,
    estimate,
    estimate_monument,
)
from customer_intel import (
    find_similar_jobs,
    get_customer_profile,
    get_market_intel,
    warehouse_stats,
)
from drawing_search import search_drawings
from project_files import scan_project_files
from app import app

PASS = 0
WARN = 0
FAIL = 0
ERRORS = []
ITERATIONS = 3
BASE = "http://127.0.0.1:18766"


def grade(label, target_s, times):
    """Grade a benchmark: PASS/WARN/FAIL based on avg vs target."""
    global PASS, WARN, FAIL
    mn = min(times)
    mx = max(times)
    avg = sum(times) / len(times)

    tag = ""
    if avg <= target_s:
        tag = "PASS"
        PASS += 1
    elif avg <= target_s * 2:
        tag = "WARN"
        WARN += 1
    else:
        tag = "FAIL"
        FAIL += 1
        ERRORS.append(f"{label} (avg {avg*1000:.0f}ms vs {target_s*1000:.0f}ms target)")

    target_ms = target_s * 1000
    print(f"  {tag}: {label}")
    print(f"        target: {target_ms:.0f}ms | min: {mn*1000:.1f}ms | avg: {avg*1000:.1f}ms | max: {mx*1000:.1f}ms")


def bench(label, target_s, fn, *args, **kwargs):
    """Run fn() ITERATIONS times and grade it."""
    times = []
    for _ in range(ITERATIONS):
        t0 = time.perf_counter()
        fn(*args, **kwargs)
        times.append(time.perf_counter() - t0)
    grade(label, target_s, times)


def run_server():
    uvicorn.run(app, host="127.0.0.1", port=18766, log_level="error")


def run_direct_benchmarks():
    """Benchmarks that call Python functions directly (no HTTP)."""

    # Warm up warehouse data (first call loads CSV)
    print("\n  (warming up warehouse data...)")
    warehouse_stats()

    # 1. Customer profile lookup: < 500ms
    print("\n--- customer_profile(Cat Scale) target < 500ms ---")
    bench("Customer profile lookup", 0.5, get_customer_profile, "Cat Scale")

    # 2. Similar jobs query: < 500ms
    print("\n--- find_similar_jobs(MONUMENT, 6000) target < 500ms ---")
    bench("Similar jobs query", 0.5, find_similar_jobs, "MONUMENT", revenue_estimate=6000)

    # 3. Market intel query: < 200ms
    print("\n--- get_market_intel(PYLON) target < 200ms ---")
    bench("Market intel query", 0.2, get_market_intel, "PYLON")

    # 4. Warehouse stats: < 200ms
    print("\n--- warehouse_stats() target < 200ms ---")
    bench("Warehouse stats", 0.2, warehouse_stats)

    # 5. Project files (cold then cached): cold < 60s, cached < 10ms
    print("\n--- scan_project_files(Cat Scale) COLD target < 60s ---")
    cold_times = []
    for _ in range(1):  # only 1 cold call (it's slow)
        t0 = time.perf_counter()
        scan_project_files("Cat Scale")
        cold_times.append(time.perf_counter() - t0)
    grade("Project files (cold)", 60.0, cold_times)

    # The module may or may not cache internally, but second call should be warm
    print("\n--- scan_project_files(Cat Scale) WARM target < 10s ---")
    warm_times = []
    for _ in range(ITERATIONS):
        t0 = time.perf_counter()
        scan_project_files("Cat Scale")
        warm_times.append(time.perf_counter() - t0)
    grade("Project files (warm)", 10.0, warm_times)

    # 6. Drawing search: < 15s
    print("\n--- search_drawings(Cat Scale) target < 15s ---")
    draw_times = []
    for _ in range(ITERATIONS):
        t0 = time.perf_counter()
        search_drawings(customer_name="Cat Scale")
        draw_times.append(time.perf_counter() - t0)
    grade("Drawing search", 15.0, draw_times)

    # 7. Channel letter estimate: < 100ms
    print("\n--- estimate(channel letter) target < 100ms ---")
    def run_cl_estimate():
        job = JobInput(
            font_type=FontType.BLOCK,
            construction=ConstructionType.FACE_LIT,
            letter_count=10,
            letter_height_inches=18.0,
        )
        estimate(job)
    bench("Channel letter estimate", 0.1, run_cl_estimate)

    # 8. Monument estimate: < 100ms
    print("\n--- estimate_monument() target < 100ms ---")
    def run_mon_estimate():
        job = JobInput(
            sign_type=SignType.MONDF,
            sign_sf_per_face=32.0,
            num_faces=2,
            is_illuminated=False,
            has_vinyl=True,
            install_height_ft=6.0,
            miles_one_way=25.0,
            crew_size=2,
        )
        estimate_monument(job)
    bench("Monument estimate", 0.1, run_mon_estimate)


async def run_http_benchmarks():
    """Benchmarks that hit HTTP endpoints."""

    async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as c:

        # 9. Dossier endpoint (HTTP, includes all aggregation): < 3s
        # Warm up first
        await c.get("/api/dossier", params={"customer": "Cat Scale", "sign_type": "PYLON"})

        print("\n--- GET /api/dossier (HTTP) target < 3s ---")
        times = []
        for _ in range(ITERATIONS):
            t0 = time.perf_counter()
            r = await c.get("/api/dossier", params={"customer": "Cat Scale", "sign_type": "PYLON"})
            times.append(time.perf_counter() - t0)
            assert r.status_code == 200, f"Dossier returned {r.status_code}"
        grade("Dossier endpoint (HTTP)", 3.0, times)

        # 10. Estimate endpoint (HTTP round-trip): < 500ms
        print("\n--- POST /api/estimate (HTTP) target < 500ms ---")
        times = []
        for _ in range(ITERATIONS):
            t0 = time.perf_counter()
            r = await c.post("/api/estimate", json={
                "pf_source": "chart",
                "letter_count": 10,
                "height_inches": 18,
                "font_type": "block",
                "construction": "face_lit",
            })
            times.append(time.perf_counter() - t0)
            assert r.status_code == 200, f"Estimate returned {r.status_code}"
        grade("Estimate endpoint (HTTP)", 0.5, times)


def main():
    # Start server for HTTP benchmarks
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(3)

    print("=" * 70)
    print("SIGNX PERFORMANCE BENCHMARKS")
    print(f"  Iterations per benchmark: {ITERATIONS}")
    print(f"  Grading: PASS (<=target) | WARN (<=2x) | FAIL (>2x)")
    print("=" * 70)

    # Direct function benchmarks
    print("\n[DIRECT FUNCTION BENCHMARKS]")
    run_direct_benchmarks()

    # HTTP endpoint benchmarks
    print("\n[HTTP ENDPOINT BENCHMARKS]")
    asyncio.run(run_http_benchmarks())

    # Summary
    total = PASS + WARN + FAIL
    print("\n" + "=" * 70)
    print(f"RESULTS: {PASS} PASS, {WARN} WARN, {FAIL} FAIL out of {total} benchmarks")
    if FAIL == 0 and WARN == 0:
        print("ALL BENCHMARKS WITHIN TARGET")
    elif FAIL == 0:
        print(f"ALL PASS (with {WARN} warnings)")
    else:
        print(f"!!! {FAIL} BENCHMARKS EXCEEDED 2x TARGET !!!")
        for e in ERRORS:
            print(f"  - {e}")
    print("=" * 70)

    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
