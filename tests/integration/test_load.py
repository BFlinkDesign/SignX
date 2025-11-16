"""Load tests for CalcuSign API endpoints."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import requests


BASE_URL = "http://localhost:8000"


def test_health_concurrent():
    """Test health endpoint under concurrent load."""
    def get_health():
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        return resp.status_code == 200
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(get_health) for _ in range(100)]
        results = [f.result() for f in futures]
    
    success_rate = sum(results) / len(results)
    print(f"Concurrent health checks: {success_rate*100:.1f}% success")
    assert success_rate >= 0.95, f"Only {success_rate*100:.1f}% success rate"


def test_cabinets_concurrent():
    """Test cabinets derive under concurrent load."""
    payload = {
        "cabinets": [{"width_ft": 4.0, "height_ft": 6.0, "weight_lbs": 150.0}],
        "wind_speed_mph": 90.0,
    }
    
    def derive_cabinets():
        resp = requests.post(f"{BASE_URL}/signage/common/cabinets/derive", json=payload, timeout=30)
        return resp.status_code == 200
    
    start = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(derive_cabinets) for _ in range(50)]
        results = [f.result() for f in futures]
    
    elapsed = time.time() - start
    success_rate = sum(results) / len(results)
    
    print(f"Concurrent derives: {success_rate*100:.1f}% success, {elapsed:.2f}s")
    assert success_rate >= 0.95, f"Only {success_rate*100:.1f}% success rate"


def test_response_times():
    """Test response times meet SLOs."""
    payload = {
        "cabinets": [{"width_ft": 4.0, "height_ft": 6.0, "weight_lbs": 150.0}],
        "wind_speed_mph": 90.0,
    }
    
    times = []
    for _ in range(10):
        start = time.time()
        resp = requests.post(f"{BASE_URL}/signage/common/cabinets/derive", json=payload, timeout=30)
        elapsed = (time.time() - start) * 1000  # ms
        assert resp.status_code == 200
        times.append(elapsed)
    
    p95 = sorted(times)[int(len(times) * 0.95)]
    p99 = sorted(times)[int(len(times) * 0.99)]
    avg = sum(times) / len(times)
    
    print(f"Response times: avg={avg:.0f}ms, p95={p95:.0f}ms, p99={p99:.0f}ms")
    assert p95 < 200, f"p95 {p95:.0f}ms exceeds 200ms target"
    assert p99 < 1000, f"p99 {p99:.0f}ms exceeds 1s target"


if __name__ == "__main__":
    import sys
    
    print("="*60)
    print("CalcuSign Load Tests")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for name, test in [
        ("health_concurrent", test_health_concurrent),
        ("cabinets_concurrent", test_cabinets_concurrent),
        ("response_times", test_response_times),
    ]:
        try:
            print(f"\nRunning {name}...")
            test()
            print(f"[OK] PASSED")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    sys.exit(0 if failed == 0 else 1)

