"""Tests for signx-takeoff/abc_catalog.py — pure helpers used by abc_engine."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="function")
def enriched(monkeypatch):
    """ABC_CATALOG_ENRICHMENT=on via monkeypatch — call-time helper reads env on each lookup."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    monkeypatch.setenv("ABC_CATALOG_ENRICHMENT", "on")
    import abc_catalog
    return abc_catalog


@pytest.fixture(scope="function")
def disabled(monkeypatch):
    """ABC_CATALOG_ENRICHMENT=off via monkeypatch — see enriched fixture for rationale."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    monkeypatch.setenv("ABC_CATALOG_ENRICHMENT", "off")
    import abc_catalog
    return abc_catalog


# ---- ENRICH off (must be byte-identical to "no catalog at all") ----------

class TestEnrichDisabled:
    def test_lookup_cl_return_returns_none(self, disabled):
        assert disabled.lookup_channel_letter_return(5.0) is None

    def test_lookup_raceway_returns_none(self, disabled):
        assert disabled.lookup_raceway_extrusion() is None

    def test_lookup_retainer_returns_none(self, disabled):
        assert disabled.lookup_retainer("IV", "mill") is None

    def test_lookup_tubing_returns_none(self, disabled):
        assert disabled.lookup_tubing("2.5", "141", "steel", "square") is None

    def test_complexity_multiplier_is_one(self, disabled):
        assert disabled.complexity_multiplier(5, 3, True) == 1.0


# ---- M2: lookup_channel_letter_return ------------------------------------

class TestM2ChannelLetterReturn:
    def test_too_shallow_returns_none(self, enriched):
        assert enriched.lookup_channel_letter_return(2.5) is None
        assert enriched.lookup_channel_letter_return(3.0) is None

    def test_5_inch_picks_channelume_5(self, enriched):
        r = enriched.lookup_channel_letter_return(5.0)
        assert r is not None
        assert r["code"] == "CHANNELUME5"
        assert r["depth_in"] == 5

    def test_5_5_inch_rounds_up_to_8(self, enriched):
        r = enriched.lookup_channel_letter_return(5.5)
        assert r["code"] == "CHANNELUME8"

    def test_above_max_uses_deepest_with_note(self, enriched):
        r = enriched.lookup_channel_letter_return(10.0)
        assert r["code"] == "CHANNELUME8"
        assert "exceeds" in r.get("note", "")

    def test_none_input_returns_none(self, enriched):
        assert enriched.lookup_channel_letter_return(None) is None


# ---- M3: lookup_raceway_extrusion ----------------------------------------

class TestM3RacewayExtrusion:
    def test_default_returns_raceway_bottom(self, enriched):
        r = enriched.lookup_raceway_extrusion()
        assert r is not None
        assert r["vendor"] == "abc"
        assert "Raceway" in r["name"]


# ---- M5: lookup_retainer with ABC type code -----------------------------

class TestM5RetainerLookup:
    def test_type_iv_mill_resolves(self, enriched):
        r = enriched.lookup_retainer("IV", "mill")
        assert r is not None
        assert r["abc_type_code"] == "IV"
        assert r["finish_multiplier"] == 1.0
        assert r["eagle_pn"] == "202-0710"

    def test_type_iv_bronze_applies_multiplier(self, enriched):
        r = enriched.lookup_retainer("IV", "bronze")
        assert r is not None
        assert r["finish_multiplier"] == 1.34
        assert r["eagle_pn"] == "202-0710"

    def test_type_iii_resolves(self, enriched):
        r = enriched.lookup_retainer("III", "bronze")
        assert r is not None
        assert r["abc_type_code"] == "III"

    def test_unknown_type_returns_first_untyped(self, enriched):
        r = enriched.lookup_retainer(None, "mill")
        assert r is not None  # fallback to first untyped/default-finish retainer

    def test_eagle_pn_only_for_type_iv(self, enriched):
        """Only Type IV currently maps to Eagle SKU 202-0710."""
        for type_code in ["I", "II", "III"]:
            r = enriched.lookup_retainer(type_code)
            assert r is None or r.get("eagle_pn") is None

    def test_finish_multipliers_known(self, enriched):
        # Spot-check the canonical multiplier table
        assert enriched.FINISH_MULTIPLIER["mill"] == 1.0
        assert enriched.FINISH_MULTIPLIER["bronze"] == 1.34
        assert enriched.FINISH_MULTIPLIER["black"] == 1.20


# ---- M6: lookup_tubing ---------------------------------------------------

class TestM6Tubing:
    def test_steel_square_2_5_141(self, enriched):
        r = enriched.lookup_tubing("2.5", "141", "steel", "square")
        assert r is not None
        assert r["nominal_size"] == "2.5"
        assert r["wall_thousandths"] == "141"
        assert r["material"] == "steel"
        assert r["shape"] == "square"

    def test_alum_square_3_125(self, enriched):
        r = enriched.lookup_tubing("3", "125", "alum", "square")
        assert r is not None
        assert r["material"] == "alum"

    def test_unknown_size_returns_none(self, enriched):
        r = enriched.lookup_tubing("99", "999", "steel", "square")
        assert r is None


# ---- M7: complexity multiplier -------------------------------------------

class TestM7ComplexityMultiplier:
    def test_baseline_one(self, enriched):
        assert enriched.complexity_multiplier(1, 1, False) == 1.0

    def test_3_materials_2_colors(self, enriched):
        m = enriched.complexity_multiplier(3, 2, False)
        # 1.0 * 1.05 * 1.04 = 1.092
        assert m == pytest.approx(1.092, abs=0.001)

    def test_5_materials_3_colors_radius(self, enriched):
        m = enriched.complexity_multiplier(5, 3, True)
        # 1.0 * 1.10 * 1.08 * 1.05 = 1.2474
        assert m == pytest.approx(1.2474, abs=0.001)

    def test_caps_at_5_plus(self, enriched):
        # 10 materials should not exceed 5-material multiplier (no further increase)
        a = enriched.complexity_multiplier(5, 3, True)
        b = enriched.complexity_multiplier(10, 5, True)
        assert a == b


# ---- Integration with calculate_materials() -----------------------------

class TestCalculateMaterialsCompat:
    """When ENRICH is OFF, calculate_materials should be byte-identical to
    its pre-catalog behavior. We don't import abc_engine here (heavy), but
    verify the helper module has zero side effects on import."""

    def test_import_with_enrich_off_is_safe(self, monkeypatch):
        monkeypatch.setenv("ABC_CATALOG_ENRICHMENT", "off")
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import abc_catalog
        # All helpers callable, all return None when disabled
        assert abc_catalog.lookup_channel_letter_return(5.0) is None
        assert abc_catalog.lookup_raceway_extrusion() is None
        assert abc_catalog.lookup_retainer("IV", "mill") is None
        assert abc_catalog.lookup_tubing("2.5", "141", "steel", "square") is None
        assert abc_catalog.complexity_multiplier(5, 3, True) == 1.0
