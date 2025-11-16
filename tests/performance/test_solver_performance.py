"""Performance tests: Solver performance validation."""

from __future__ import annotations

import time

import pytest


@pytest.mark.performance
@pytest.mark.asyncio
async def test_derive_performance_p95(client):
    """Test cabinet derive performance: p95 <100ms."""
    
    runs = []
    
    for i in range(50):
        start = time.time()
        
        resp = await client.post(
            "/cabinets/derive",
            json={
                "sign": {"height_ft": 10.0, "width_ft": 8.0},
                "board": {"layers": []},
            },
        )
        
        elapsed = (time.time() - start) * 1000  # ms
        runs.append(elapsed)
        
        assert resp.status_code in (200, 422)
    
    # Calculate p95
    runs.sort()
    p95_index = int(0.95 * len(runs))
    p95 = runs[p95_index]
    
    # Should meet SLO: p95 <100ms
    assert p95 < 100, f"p95 latency {p95}ms exceeds 100ms SLO"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_pole_filtering_performance(client):
    """Test pole filtering performance: p95 <50ms."""
    
    runs = []
    
    for i in range(50):
        start = time.time()
        
        resp = await client.post(
            "/poles/options",
            json={"loads": {"moment_kips_ft": 100}, "preferences": {}},
        )
        
        elapsed = (time.time() - start) * 1000
        runs.append(elapsed)
        
        assert resp.status_code in (200, 422)
    
    runs.sort()
    p95_index = int(0.95 * len(runs))
    p95 = runs[p95_index]
    
    assert p95 < 50, f"p95 latency {p95}ms exceeds 50ms SLO"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_footing_solve_performance(client):
    """Test footing solve performance: p95 <50ms."""
    
    runs = []
    
    for i in range(50):
        start = time.time()
        
        resp = await client.post(
            "/footing/design",
            json={
                "module": "signage.direct_burial_2pole",
                "loads": {"force_kips": 50},
            },
        )
        
        elapsed = (time.time() - start) * 1000
        runs.append(elapsed)
        
        assert resp.status_code in (200, 422)
    
    runs.sort()
    p95_index = int(0.95 * len(runs))
    p95 = runs[p95_index]
    
    assert p95 < 50, f"p95 latency {p95}ms exceeds 50ms SLO"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_report_generation_performance(client, sample_payload):
    """Test report generation performance: p95 <1s."""
    
    runs = []
    
    for i in range(20):  # Fewer runs due to longer operation
        start = time.time()
        
        resp = await client.post(
            "/projects/test_report/report",
            json=sample_payload,
        )
        
        elapsed = (time.time() - start) * 1000
        runs.append(elapsed)
        
        assert resp.status_code in (200, 202)
    
    runs.sort()
    p95_index = int(0.95 * len(runs))
    p95 = runs[p95_index]
    
    assert p95 < 1000, f"p95 latency {p95}ms exceeds 1s SLO"


@pytest.mark.performance
@pytest.mark.benchmark
async def test_benchmark_create_project(client):
    """Benchmark project creation performance."""
    
    import asyncio
    
    start = time.time()
    
    # Create 100 projects
    tasks = []
    for i in range(100):
        tasks.append(client.post(
            "/projects/",
            json={
                "account_id": f"perf_test_{i}",
                "name": f"Performance Test {i}",
                "created_by": "perf_user",
            },
        ))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.time() - start
    
    # Should complete in reasonable time
    assert elapsed < 30, f"Created 100 projects in {elapsed}s, exceeds 30s threshold"
    
    # Calculate throughput
    throughput = 100 / elapsed
    print(f"Throughput: {throughput:.2f} projects/second")


@pytest.mark.performance
@pytest.mark.asyncio
async def test_memory_usage_derives(client):
    """Test memory usage during derive operations."""
    
    import tracemalloc
    
    # Start memory tracking
    tracemalloc.start()
    snapshot_start = tracemalloc.take_snapshot()
    
    # Perform derives
    for i in range(100):
        resp = await client.post(
            "/cabinets/derive",
            json={
                "sign": {"height_ft": 10.0, "width_ft": 8.0},
                "board": {"layers": []},
            },
        )
        assert resp.status_code in (200, 422)
    
    snapshot_end = tracemalloc.take_snapshot()
    tracemalloc.stop()
    
    # Calculate memory increase
    top_stats = snapshot_end.compare_to(snapshot_start, 'lineno')
    total_mb = sum(stat.size_diff / 1024 / 1024 for stat in top_stats[:10])
    
    # Should not exceed 50MB increase for 100 derives
    assert total_mb < 50, f"Memory increase {total_mb}MB exceeds 50MB threshold"

