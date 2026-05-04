"""Integration tests for M2 + M3 catalog enrichment in calculate_materials().

Verifies:
- ENRICH off → byte-identical legacy BOM (250+ existing tests preserved)
- ENRICH on → BOM lines gain `catalog_*` metadata without changing core dict shape
- Raceway material line appears when raceway_lf > 0 (M3)
- Channel letter return enrichment fires at ≥5" depth (M2)
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

# Add signx-takeoff to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def abc_engine_disabled():
    """Reload abc_engine.py with ABC_CATALOG_ENRICHMENT off (default)."""
    os.environ["ABC_CATALOG_ENRICHMENT"] = "off"
    for mod in ("abc_engine", "abc_catalog"):
        if mod in sys.modules:
            del sys.modules[mod]
    import abc_engine
    importlib.reload(abc_engine)
    yield abc_engine


@pytest.fixture
def abc_engine_enriched():
    """Reload abc_engine.py with ABC_CATALOG_ENRICHMENT on."""
    os.environ["ABC_CATALOG_ENRICHMENT"] = "on"
    for mod in ("abc_engine", "abc_catalog"):
        if mod in sys.modules:
            del sys.modules[mod]
    import abc_engine
    importlib.reload(abc_engine)
    yield abc_engine
    os.environ.pop("ABC_CATALOG_ENRICHMENT", None)


# ---- M2: channel letter return ------------------------------------------

class TestM2EnrichmentDisabled:
    def test_coil_line_unchanged_when_disabled(self, abc_engine_disabled):
        m = abc_engine_disabled
        bom = m.calculate_materials(
            pf=20.0, face_sf=10.0, return_depth_inches=5.0,
            raceway_lf=0.0,
            construction=m.ConstructionType.FACE_LIT,
        )
        coil = next(b for b in bom if "Return Coil" in b["item"])
        assert "catalog_part" not in coil
        assert "catalog_vendor" not in coil
        assert coil["part"] == "205-0111"  # original behavior preserved


class TestM2EnrichmentOn:
    def test_5_inch_depth_enriches_with_channelume_5(self, abc_engine_enriched):
        m = abc_engine_enriched
        bom = m.calculate_materials(
            pf=20.0, face_sf=10.0, return_depth_inches=5.0,
            raceway_lf=0.0,
            construction=m.ConstructionType.FACE_LIT,
        )
        coil = next(b for b in bom if "Return Coil" in b["item"])
        assert coil["part"] == "205-0111"  # base part unchanged
        assert coil.get("catalog_part") == "CHANNELUME5"
        assert coil.get("catalog_vendor") == "abc"
        assert coil.get("catalog_depth_in") == 5

    def test_3_inch_depth_no_enrichment(self, abc_engine_enriched):
        """Below 3.5" → use coil aluminum, no Channelume profile match."""
        m = abc_engine_enriched
        bom = m.calculate_materials(
            pf=20.0, face_sf=10.0, return_depth_inches=3.0,
            raceway_lf=0.0,
            construction=m.ConstructionType.FACE_LIT,
        )
        coil = next(b for b in bom if "Return Coil" in b["item"])
        assert "catalog_part" not in coil

    def test_8_inch_depth_picks_channelume_8(self, abc_engine_enriched):
        m = abc_engine_enriched
        bom = m.calculate_materials(
            pf=20.0, face_sf=10.0, return_depth_inches=8.0,
            raceway_lf=0.0,
            construction=m.ConstructionType.FACE_LIT,
        )
        coil = next(b for b in bom if "Return Coil" in b["item"])
        assert coil.get("catalog_part") == "CHANNELUME8"


# ---- M3: raceway extrusion BOM ------------------------------------------

class TestM3RacewayBOM:
    def test_raceway_line_absent_when_lf_zero(self, abc_engine_enriched):
        m = abc_engine_enriched
        bom = m.calculate_materials(
            pf=20.0, face_sf=10.0, return_depth_inches=5.0,
            raceway_lf=0.0,
            construction=m.ConstructionType.FACE_LIT,
        )
        raceway_lines = [b for b in bom if "Raceway extrusion" in b["item"]]
        assert len(raceway_lines) == 0

    def test_raceway_line_present_when_lf_positive(self, abc_engine_enriched):
        m = abc_engine_enriched
        bom = m.calculate_materials(
            pf=20.0, face_sf=10.0, return_depth_inches=5.0,
            raceway_lf=12.0,
            construction=m.ConstructionType.FACE_LIT,
        )
        raceway_lines = [b for b in bom if "Raceway extrusion" in b["item"]]
        assert len(raceway_lines) == 1
        line = raceway_lines[0]
        assert line["part"] == "202-1265"  # Excellart 7" CLRW (Eagle SKU)
        assert line["unit"] == "LF"

    def test_raceway_qty_includes_5pct_waste(self, abc_engine_enriched):
        m = abc_engine_enriched
        bom = m.calculate_materials(
            pf=20.0, face_sf=10.0, return_depth_inches=5.0,
            raceway_lf=10.0,
            construction=m.ConstructionType.FACE_LIT,
        )
        raceway = next(b for b in bom if "Raceway extrusion" in b["item"])
        assert raceway["qty"] == pytest.approx(10.5)  # 10 * 1.05

    def test_raceway_has_excellart_cross_reference(self, abc_engine_enriched):
        m = abc_engine_enriched
        bom = m.calculate_materials(
            pf=20.0, face_sf=10.0, return_depth_inches=5.0,
            raceway_lf=12.0,
            construction=m.ConstructionType.FACE_LIT,
        )
        raceway = next(b for b in bom if "Raceway extrusion" in b["item"])
        assert raceway.get("catalog_excellart_product_number") == "1401015"
        assert raceway.get("catalog_eagle_pn") == "202-1265"


class TestM3RacewayDisabled:
    def test_raceway_line_absent_when_disabled(self, abc_engine_disabled):
        """When ENRICH is off (default), the raceway material line is NOT
        added — the BOM keeps its byte-identical legacy shape. Production
        callers always pass raceway_lf > 0, so an unconditional add would
        silently change the output of every channel-letter quote."""
        m = abc_engine_disabled
        bom = m.calculate_materials(
            pf=20.0, face_sf=10.0, return_depth_inches=5.0,
            raceway_lf=12.0,
            construction=m.ConstructionType.FACE_LIT,
        )
        raceway_lines = [b for b in bom if "Raceway extrusion" in b["item"]]
        assert len(raceway_lines) == 0  # gated behind ABC_CATALOG_ENRICHMENT


# ---- Task 3: Trim Cap real fix ------------------------------------------

class TestTrimCapEnabled:
    """When ENRICH=on, the trim cap line is rewritten with the real
    Jewelite part number from the warehouse (208-0xxx)."""

    def test_trim_cap_uses_real_jewelite_sku(self, abc_engine_enriched):
        m = abc_engine_enriched
        bom = m.calculate_materials(
            pf=20.0, face_sf=10.0, return_depth_inches=5.0,
            raceway_lf=0.0,
            construction=m.ConstructionType.FACE_LIT,
        )
        trim = next(b for b in bom if "Trim Cap" in b["item"])
        # Real Jewelite SKU starts with 208-, not 202-0710.
        assert trim["part"].startswith("208-"), (
            f"expected 208-* Jewelite SKU, got {trim['part']}"
        )
        assert trim.get("catalog_vendor") == "jewelite"
        assert trim.get("catalog_color")  # color resolved


class TestTrimCapDisabled:
    """When ENRICH=off, the trim cap line keeps the legacy 202-0710 part
    for byte-identical output, but emits a DeprecationWarning."""

    def test_trim_cap_keeps_legacy_part_when_disabled(self, abc_engine_disabled):
        import warnings
        m = abc_engine_disabled
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            bom = m.calculate_materials(
                pf=20.0, face_sf=10.0, return_depth_inches=5.0,
                raceway_lf=0.0,
                construction=m.ConstructionType.FACE_LIT,
            )
        trim = next(b for b in bom if "Trim Cap" in b["item"])
        assert trim["part"] == "202-0710"  # legacy preserved
        assert trim["item"] == "Trim Cap 1\""
        # No catalog_* fields when disabled
        assert "catalog_vendor" not in trim
        # DeprecationWarning was emitted
        deprecations = [w for w in captured if issubclass(w.category, DeprecationWarning)
                        and "202-0710" in str(w.message)]
        assert len(deprecations) >= 1, (
            f"expected DeprecationWarning about 202-0710; got "
            f"{[str(w.message) for w in captured]}"
        )
