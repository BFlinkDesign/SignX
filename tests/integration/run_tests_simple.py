"""Simple integration test runner (no pytest required)."""

from __future__ import annotations

import sys
import time
from typing import Any

import requests


BASE_URL = "http://localhost:8000"


def test_health():
    """Test /health returns valid envelope."""
    print("Testing /health...", end=" ")
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    assert response.status_code == 200
    
    data = response.json()
    assert "result" in data and data["result"]["status"] == "ok"
    print("[OK] PASSED")
    return True


def test_ready():
    """Test /ready returns dependency checks."""
    print("Testing /ready...", end=" ")
    response = requests.get(f"{BASE_URL}/ready", timeout=10)
    assert response.status_code == 200
    
    data = response.json()
    assert "checks" in data["result"]
    assert data["result"]["status"] in ["ok", "degraded"]
    print("[OK] PASSED")
    return True


def test_cabinets():
    """Test cabinets derive returns valid envelope."""
    print("Testing cabinets derive...", end=" ")
    payload = {
        "cabinets": [
            {"width_ft": 4.0, "height_ft": 6.0, "weight_lbs": 150.0, "x_offset_ft": 0.0, "y_offset_ft": 0.0}
        ],
        "wind_speed_mph": 90.0,
    }
    
    response = requests.post(f"{BASE_URL}/signage/common/cabinets/derive", json=payload, timeout=30)
    if response.status_code != 200:
        print(f"[FAIL] Status {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return False
    
    data = response.json()
    if "result" not in data:
        print("[FAIL] No 'result' in response")
        return False
    if "A_ft2" not in data["result"]:
        print(f"[FAIL] Expected 'A_ft2', got {list(data['result'].keys())}")
        return False
    
    print("[OK] PASSED")
    return True


def test_determinism():
    """Test identical requests produce same results."""
    print("Testing determinism...", end=" ")
    payload = {
        "cabinets": [{"width_ft": 4.0, "height_ft": 6.0, "weight_lbs": 150.0}],
        "wind_speed_mph": 90.0,
    }
    
    r1 = requests.post(f"{BASE_URL}/signage/common/cabinets/derive", json=payload, timeout=30)
    time.sleep(0.1)
    r2 = requests.post(f"{BASE_URL}/signage/common/cabinets/derive", json=payload, timeout=30)
    
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["result"] == r2.json()["result"]
    print("[OK] PASSED")
    return True


def test_poles():
    """Test poles options."""
    print("Testing poles options...", end=" ")
    payload = {"weight_top_klf": 1.0, "height_ft": 20.0, "wind_speed_mph": 90.0, "exposure": "C"}
    
    response = requests.post(f"{BASE_URL}/signage/common/poles/options", json=payload, timeout=30)
    if response.status_code != 200:
        print(f"[FAIL] Status {response.status_code}: {response.text[:200]}")
        return False
    
    data = response.json()
    if "result" not in data or "options" not in data["result"]:
        print(f"[FAIL] Unexpected response structure: {list(data.get('result', {}).keys())}")
        return False
    
    print("[OK] PASSED")
    return True


def test_version():
    """Test version endpoint."""
    print("Testing /version...", end=" ")
    response = requests.get(f"{BASE_URL}/version", timeout=5)
    assert response.status_code == 200
    print("[OK] PASSED")
    return True


def main():
    """Run all tests."""
    print("="*60)
    print("CalcuSign Integration Tests")
    print(f"API: {BASE_URL}")
    print("="*60)
    
    tests = [
        test_health,
        test_ready,
        test_cabinets,
        test_determinism,
        test_poles,
        test_version,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"[FAIL] AssertionError: {e}")
            failed += 1
        except requests.exceptions.RequestException as e:
            print(f"[FAIL] Request failed: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] ERROR: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

