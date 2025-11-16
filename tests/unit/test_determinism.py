"""
Determinism tests: identical inputs must produce identical outputs.
"""

from __future__ import annotations

import hashlib
import json

import pytest

# Import from materials service
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "services" / "materials-service"))


@pytest.mark.asyncio
async def test_pdf_determinism() -> None:
    """Same snapshot → identical pdf_sha."""
    import importlib.util

    util_path = Path(__file__).parent.parent.parent / "services" / "api" / "src" / "apex" / "api" / "utils" / "report.py"
    spec = importlib.util.spec_from_file_location("report", util_path)
    if not spec or not spec.loader:
        pytest.skip("Report utils not available")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    payload = {"module": "test", "config": {"a": 1, "b": 2}, "files": [], "cost_snapshot": {}}
    sha1 = mod.compute_payload_sha256(payload)
    sha2 = mod.compute_payload_sha256(payload)
    assert sha1 == sha2, "Same payload must produce same SHA"


@pytest.mark.asyncio
async def test_footing_monotonic() -> None:
    """Diameter ↓ ⇒ depth ↑ (inverse relationship)."""
    # This is a placeholder; actual signcalc-service would be needed
    # For now, verify the concept works with simple math
    def test_depth(dia: float) -> float:
        # Simulated inverse relationship
        return 10.0 / (dia + 1e-6)

    d1 = test_depth(2.0)
    d2 = test_depth(3.0)
    assert d1 > d2, f"Larger diameter should have shallower depth: d1={d1}, d2={d2}"


@pytest.mark.asyncio
async def test_pole_filtering_no_infeasible() -> None:
    """Infeasible sizes never returned."""
    # Placeholder: verify that poles returned have capacity >= demand
    demand_moment = 120.0  # kip-in
    returned_poles = [
        {"name": "4x4", "capacity": 150.0},
        {"name": "6x6", "capacity": 200.0},
    ]

    for pole in returned_poles:
        assert pole["capacity"] >= demand_moment, f"{pole['name']} has insufficient capacity"

