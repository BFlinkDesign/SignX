from __future__ import annotations

import copy
import pytest


@pytest.mark.asyncio
async def test_zero_weights_rejected(client, fixture_payload):
    fx = copy.deepcopy(fixture_payload)
    fx["weights"] = {"yield_strength": 0, "density": 0, "cost": 0, "corrosion": 0, "fatigue": 0}
    r = await client.post("/pick", json=fx)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_missing_weights_normalize_warns(client, fixture_payload):
    fx = copy.deepcopy(fixture_payload)
    # Leave only two non-zero weights; sum != 1, should normalize and warn
    fx["weights"]["yield_strength"] = 0.7
    fx["weights"]["corrosion"] = 0.0
    fx["weights"]["density"] = 0.3
    fx["weights"]["cost"] = 0.0
    fx["weights"]["fatigue"] = 0.0
    r = await client.post("/pick", json=fx)
    assert r.status_code == 200
    data = r.json()
    assert any("Normalized weights" in a for a in data.get("assumptions", []))


@pytest.mark.asyncio
async def test_tie_break_stable(client, fixture_payload):
    fx = copy.deepcopy(fixture_payload)
    # Craft tie by setting only density weight and making two densities equal
    fx["weights"] = {"yield_strength": 0, "density": 1.0, "cost": 0, "corrosion": 0, "fatigue": 0}
    # Make A and B same density
    fx["materials"][1]["properties"]["density"] = fx["materials"][0]["properties"]["density"]
    r1 = (await client.post("/pick", json=fx)).json()
    r2 = (await client.post("/pick", json=fx)).json()
    ids1 = [x["id"] for x in r1["result"]["ranked"]]
    ids2 = [x["id"] for x in r2["result"]["ranked"]]
    assert ids1 == ids2


@pytest.mark.asyncio
@pytest.mark.parametrize("label", ["marine", "salt-spray", "CRES"])
async def test_synonyms_map_adds_assumption(client, fixture_payload, label):
    fx = copy.deepcopy(fixture_payload)
    fx.setdefault("constraints", {})["environment"] = f"outdoor-{label}"
    r = await client.post("/pick", json=fx)
    assert r.status_code == 200
    data = r.json()
    assert any("mapped" in a for a in data.get("assumptions", []))


@pytest.mark.asyncio
async def test_out_of_range_negative_property_rejected(client, fixture_payload):
    fx = copy.deepcopy(fixture_payload)
    fx["materials"][0]["properties"]["yield_strength"] = -10
    r = await client.post("/pick", json=fx)
    assert r.status_code == 422
    assert "materials[0].properties.yield_strength" in r.text


@pytest.mark.asyncio
async def test_impute_neutral_corrosion_and_assumption(client, fixture_payload):
    fx = copy.deepcopy(fixture_payload)
    # Remove corrosion from first material
    fx["materials"][0]["qualities"].pop("corrosion", None)
    r = await client.post("/pick", json=fx)
    assert r.status_code == 200
    data = r.json()
    assert any("Imputed 'corrosion=neutral'" in a for a in data.get("assumptions", []))


@pytest.mark.asyncio
async def test_confidence_capped_for_single_candidate(client, fixture_payload):
    fx = copy.deepcopy(fixture_payload)
    fx["materials"] = [fx["materials"][0]]
    r = await client.post("/pick", json=fx)
    assert r.status_code == 200
    conf = r.json()["confidence"]
    assert conf <= 0.55


