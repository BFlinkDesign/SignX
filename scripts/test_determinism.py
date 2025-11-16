#!/usr/bin/env python3
"""
Determinism Verification Test Suite

Tests that solvers produce identical outputs for identical inputs via API.
"""

import hashlib
import json
import sys

import requests

API_BASE = "http://localhost:8000"


def test_cabinet_led():
    """Test cabinet derivation determinism."""
    payload = {
        "site": {"wind_speed_mph": 90.0, "exposure": "C"},
        "cabinets": [
            {
                "width_ft": 4.0,
                "height_ft": 6.0,
                "weight_psf": 10.0,
            }
        ],
        "height_ft": 20.0,
    }
    results = []
    
    try:
        for i in range(10):
            response = requests.post(f"{API_BASE}/signage/common/cabinets/derive", json=payload, timeout=5)
            response.raise_for_status()
            result_data = response.json().get("result", {})
            result_hash = hashlib.sha256(
                json.dumps(result_data, sort_keys=True).encode()
            ).hexdigest()
            results.append(result_hash)
        
        if len(set(results)) == 1:
            print(f"[PASS] cabinet-led: PASS")
            return True
        else:
            print(f"[FAIL] cabinet-led: FAIL ({len(set(results))} unique results)")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] cabinet-led: ERROR - {e}")
        return False


def test_monument_structural():
    """Test monument structural determinism."""
    payload = {
        "site": {"wind_speed_mph": 115.0, "exposure": "C"},
        "cabinets": [{"width_ft": 14.0, "height_ft": 8.0, "weight_psf": 10.0}],
        "height_ft": 25.0,
    }
    results = []
    
    try:
        for i in range(10):
            response = requests.post(
                f"{API_BASE}/signage/common/cabinets/derive", json=payload, timeout=5
            )
            response.raise_for_status()
            result_data = response.json().get("result", {})
            result_hash = hashlib.sha256(
                json.dumps(result_data, sort_keys=True).encode()
            ).hexdigest()
            results.append(result_hash)
        
        if len(set(results)) == 1:
            print(f"[PASS] monument-structural: PASS")
            return True
        else:
            print(f"[FAIL] monument-structural: FAIL ({len(set(results))} unique results)")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] monument-structural: ERROR - {e}")
        return False


def test_pole_selection():
    """Test pole selection determinism."""
    payload = {
        "mu_required_kipin": 50.0,
        "prefs": {"family": "HSS", "steel_grade": "A500B", "sort_by": "Sx"},
    }
    results = []
    
    try:
        for i in range(10):
            response = requests.post(
                f"{API_BASE}/signage/common/poles/options", json=payload, timeout=5
            )
            response.raise_for_status()
            result_data = response.json().get("result", {})
            result_hash = hashlib.sha256(
                json.dumps(result_data, sort_keys=True).encode()
            ).hexdigest()
            results.append(result_hash)
        
        if len(set(results)) == 1:
            print(f"[PASS] pole-selection: PASS")
            return True
        else:
            print(f"[FAIL] pole-selection: FAIL ({len(set(results))} unique results)")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] pole-selection: ERROR - {e}")
        return False


if __name__ == "__main__":
    print("Determinism Tests\n")
    
    results = [
        test_cabinet_led(),
        test_monument_structural(),
        test_pole_selection(),
    ]
    
    passed = sum(results)
    total = len(results)
    print(f"\nResults: {passed}/{total} passed")
    
    sys.exit(0 if all(results) else 1)
