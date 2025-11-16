"""
Performance benchmarks for APEX signage engineering solvers.

Target: <100ms p95 latency for real-time derives.
"""

from __future__ import annotations

import time
from statistics import mean, stdev

import pytest

from apex.domains.signage.models import Cabinet, SiteLoads
from apex.domains.signage.solvers import derive_loads, filter_poles, footing_solve


@pytest.mark.benchmark
def benchmark_derive_loads():
    """Benchmark derive_loads for <100ms target."""
    site = SiteLoads(wind_speed_mph=115.0, exposure="C")
    cabinets = [Cabinet(width_ft=14.0, height_ft=8.0, weight_psf=10.0) for _ in range(5)]
    
    times = []
    for _ in range(1000):
        start = time.perf_counter()
        result = derive_loads(site, cabinets, height_ft=25.0)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)
    
    avg = mean(times)
    p95 = sorted(times)[int(0.95 * len(times))]
    p99 = sorted(times)[int(0.99 * len(times))]
    
    print(f"\nderive_loads benchmark (1000 iterations):")
    print(f"  Mean: {avg:.2f}ms")
    print(f"  P95: {p95:.2f}ms")
    print(f"  P99: {p99:.2f}ms")
    print(f"  StdDev: {stdev(times):.2f}ms")
    
    assert p95 < 100.0, f"P95 latency {p95:.2f}ms exceeds 100ms target"


@pytest.mark.benchmark
def benchmark_filter_poles_vectorized():
    """Benchmark vectorized filter_poles (should be 10x faster)."""
    sections = [
        {"type": "HSS", "shape": f"HSS {i}x{i}x1/4", "sx_in3": i * 5.0, "w_lbs_per_ft": i * 10.0}
        for i in range(4, 20)
    ]
    prefs = {"family": "HSS", "steel_grade": "A500B", "sort_by": "Sx"}
    
    times = []
    for _ in range(100):
        start = time.perf_counter()
        result, _ = filter_poles(50.0, sections, prefs, seed=42, return_warnings=True)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    
    avg = mean(times)
    print(f"\nfilter_poles benchmark (100 iterations):")
    print(f"  Mean: {avg:.2f}ms")
    print(f"  Vectorized implementation")


@pytest.mark.benchmark
def benchmark_footing_solve_cached():
    """Benchmark footing_solve with memoization."""
    times = []
    for _ in range(100):
        start = time.perf_counter()
        depth, req_eng, warnings = footing_solve(10.0, 3.0, 3000.0, seed=42)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    
    avg = mean(times)
    print(f"\nfooting_solve benchmark (100 iterations, memoized):")
    print(f"  Mean: {avg:.2f}ms")
    print(f"  First call populates cache, subsequent calls are fast")


if __name__ == "__main__":
    benchmark_derive_loads()
    benchmark_filter_poles_vectorized()
    benchmark_footing_solve_cached()

