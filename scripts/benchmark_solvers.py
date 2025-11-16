#!/usr/bin/env python3
"""
Solver Performance Benchmark Suite

Measures latency and throughput for all solver endpoints via API.
"""

import statistics
import sys
import time

import requests
import logging

logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000"


def benchmark_endpoint(endpoint, payload, n=100):
    """Benchmark an endpoint for latency and throughput."""
    latencies = []
    errors = 0
    
    start = time.time()
    for i in range(n):
        try:
            t0 = time.time()
            response = requests.post(f"{API_BASE}{endpoint}", json=payload, timeout=10)
            response.raise_for_status()
            elapsed = (time.time() - t0) * 1000  # Convert to ms
            latencies.append(elapsed)
        except requests.exceptions.RequestException:
            errors += 1
    
    total = time.time() - start
    
    if not latencies:
        logger.error(f"{endpoint}: [FAIL] All requests failed")
        return False
    
    # Calculate percentiles
    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    
    # Calculate throughput (successful requests only)
    successful = len(latencies)
    throughput = successful / total
    
    # Calculate statistics
    mean_latency = statistics.mean(latencies)
    median_latency = statistics.median(latencies)
    
    logger.info(f"{endpoint}:")
    throughput_status = "[PASS]" if throughput > 10 else "[FAIL]"
    p95_status = "[PASS]" if p95 < 100 else "[FAIL]"
    p99_status = "[PASS]" if p99 < 500 else "[FAIL]"
    logger.info(f"  Throughput: {throughput:.1f} req/s {throughput_status} (target: >10 req/s)")
    logger.info(f"  Latency p50: {p50:.1f} ms")
    logger.info(f"  Latency p95: {p95:.1f} ms {p95_status} (target: <100 ms)")
    logger.info(f"  Latency p99: {p99:.1f} ms {p99_status} (target: <500 ms)")
    logger.info(f"  Mean: {mean_latency:.1f} ms, Median: {median_latency:.1f} ms")
    if errors > 0:
        logger.error(f"  Errors: {errors}/{n}")
    logger.info()
    
    return throughput > 10 and p95 < 100


def main():
    """Run performance benchmarks."""
    logger.info("Performance Benchmarks\n")
    logger.info("=" * 60)
    
    # Test 1: Cabinet Derivation
    cabinet_payload = {
        "site": {"wind_speed_mph": 115.0, "exposure": "C"},
        "cabinets": [{"width_ft": 14.0, "height_ft": 8.0, "weight_psf": 10.0}],
        "height_ft": 25.0,
    }
    result1 = benchmark_endpoint("/signage/common/cabinets/derive", cabinet_payload)
    
    # Test 2: Pole Selection
    pole_payload = {
        "mu_required_kipin": 50.0,
        "prefs": {"family": "HSS", "steel_grade": "A500B"},
    }
    result2 = benchmark_endpoint("/signage/common/poles/options", pole_payload)
    
    # Test 3: Footing Solve
    footing_payload = {
        "footing": {"diameter_ft": 3.0},
        "soil_psf": 3000.0,
        "M_pole_kipft": 10.0,
        "num_poles": 1,
    }
    result3 = benchmark_endpoint("/signage/direct_burial/footing/solve", footing_payload)
    
    logger.info("=" * 60)
    results = [result1, result2, result3]
    passed = sum(results)
    total = len(results)
    
    logger.info(f"Summary: {passed}/{total} endpoints meeting targets")
    if all(results):
        logger.info("[PASS] All endpoints meeting performance targets")
    else:
        logger.error("[FAIL] Some endpoints not meeting performance targets")
    
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
