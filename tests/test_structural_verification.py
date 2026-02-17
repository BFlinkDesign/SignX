"""Structural module verification tests — Phase 5B.

Verifies each structural calculation module against known reference values
from published codes (ASCE 7-22, IBC, ACI 318-19, AISC 360-22).

Run with:
    timeout 60 python -m pytest tests/test_structural_verification.py --timeout=30 -v
"""
from __future__ import annotations

import math
import sys

import pytest

sys.path.insert(0, "services/signcalc-service")


# ---------------------------------------------------------------------------
# Wind loads — ASCE 7-22
# ---------------------------------------------------------------------------


class TestWindASCE7:
    """ASCE 7-22 wind load module reference checks."""

    @pytest.fixture(autouse=True)
    def import_wind(self):
        from apex_signcalc.wind_asce7 import (
            ke,
            kz,
            velocity_pressure,
            wind_force_on_sign,
        )

        self.kz = kz
        self.ke = ke
        self.velocity_pressure = velocity_pressure
        self.wind_force_on_sign = wind_force_on_sign

    # --- Table 26.10-1 Kz at 15 ft -------

    def test_kz_15ft_exposure_B(self):
        """Kz at 15 ft, Exposure B = 0.57 per ASCE 7-22 Table 26.10-1."""
        assert self.kz(15.0, "B") == pytest.approx(0.57, abs=1e-6)

    def test_kz_15ft_exposure_C(self):
        """Kz at 15 ft, Exposure C = 0.85 per ASCE 7-22 Table 26.10-1."""
        assert self.kz(15.0, "C") == pytest.approx(0.85, abs=1e-6)

    def test_kz_15ft_exposure_D(self):
        """Kz at 15 ft, Exposure D = 1.03 per ASCE 7-22 Table 26.10-1."""
        assert self.kz(15.0, "D") == pytest.approx(1.03, abs=1e-6)

    def test_kz_below_15ft_clamps_to_15ft(self):
        """Heights below 15 ft use the 15-ft value per code footnote."""
        assert self.kz(5.0, "B") == self.kz(15.0, "B")
        assert self.kz(0.0, "C") == self.kz(15.0, "C")

    def test_kz_invalid_exposure_raises(self):
        """Invalid exposure category raises ValueError."""
        with pytest.raises(ValueError):
            self.kz(15.0, "A")

    # --- Table 26.9-1 Ke -------

    def test_ke_sea_level(self):
        """Ke at sea level (0 ft) = 1.00 per ASCE 7-22 Table 26.9-1."""
        assert self.ke(0.0) == pytest.approx(1.00, abs=1e-6)

    def test_ke_6000ft(self):
        """Ke at 6000 ft elevation = 0.80 per ASCE 7-22 Table 26.9-1."""
        assert self.ke(6000.0) == pytest.approx(0.80, abs=1e-6)

    def test_ke_negative_elevation_clamps_to_zero(self):
        """Negative elevation treated as sea level."""
        assert self.ke(-100.0) == pytest.approx(1.00, abs=1e-6)

    # --- Velocity pressure (ASCE 7-22 Eq. 26.10-1) -------

    def test_velocity_pressure_reference_case(self):
        """qz for V=115 mph, Kz=0.85, Kzt=1.0, Kd=0.85, Ke=1.0 = 24.46 psf.

        Manual: 0.00256 * 0.85 * 1.0 * 0.85 * 1.0 * 115^2 = 24.455 psf
        """
        qz = self.velocity_pressure(V=115.0, Kz=0.85, Kzt=1.0, Kd=0.85, Ke=1.0)
        expected = 0.00256 * 0.85 * 1.0 * 0.85 * 1.0 * 115.0 ** 2
        assert qz == pytest.approx(expected, rel=1e-4)
        assert qz == pytest.approx(24.46, abs=0.02)

    def test_velocity_pressure_proportional_to_v_squared(self):
        """qz scales as V^2 — doubling speed quadruples pressure."""
        qz_100 = self.velocity_pressure(100.0, 1.0, 1.0, 1.0, 1.0)
        qz_200 = self.velocity_pressure(200.0, 1.0, 1.0, 1.0, 1.0)
        assert qz_200 == pytest.approx(4.0 * qz_100, rel=1e-6)

    # --- Full sign calculation -------

    def test_wind_force_reasonable_range(self):
        """10 ft wide x 5 ft tall sign, top at 20 ft, Exp C, V=115 mph.

        Governing force should be in the 1500–2500 lbf range based on
        ASCE 7-22 Chapter 29 sign loads in moderate wind zones.
        Case C governs for B/s >= 2 (B/s = 2.0 here).
        """
        result = self.wind_force_on_sign(
            V_mph=115.0,
            sign_width_ft=10.0,
            sign_height_ft=5.0,
            height_to_top_ft=20.0,
            exposure="C",
        )
        governing_F = result["governing_F_lbf"]
        assert 1500 <= governing_F <= 2500, (
            f"Expected governing force 1500–2500 lbf; got {governing_F} lbf"
        )

    def test_wind_force_case_C_applies(self):
        """Case C is applicable when B/s = 10/5 = 2.0 >= 2."""
        result = self.wind_force_on_sign(115.0, 10.0, 5.0, 20.0, "C")
        assert result["case_C_applicable"] is True

    def test_wind_force_sign_area(self):
        """Face area B*s should be 10 * 5 = 50 sf."""
        result = self.wind_force_on_sign(115.0, 10.0, 5.0, 20.0, "C")
        assert result["A_sf"] == pytest.approx(50.0, abs=0.01)

    def test_wind_force_qz_at_centroid(self):
        """Centroid at 20 - 5/2 = 17.5 ft; Kz for 17.5 ft Exp C interpolates between 15 and 20."""
        result = self.wind_force_on_sign(115.0, 10.0, 5.0, 20.0, "C")
        # Centroid at 17.5 ft → Kz interpolated between Kz(15)=0.85 and Kz(20)=0.90
        assert 0.85 <= result["Kz"] <= 0.90

    def test_wind_force_higher_speed_gives_higher_force(self):
        """Higher wind speed must produce proportionally higher force."""
        r90 = self.wind_force_on_sign(90.0, 10.0, 5.0, 20.0, "C")
        r115 = self.wind_force_on_sign(115.0, 10.0, 5.0, 20.0, "C")
        assert r115["governing_F_lbf"] > r90["governing_F_lbf"]

    def test_wind_force_invalid_inputs_raise(self):
        """Negative width should raise ValueError."""
        with pytest.raises(ValueError):
            self.wind_force_on_sign(115.0, -10.0, 5.0, 20.0, "C")

    def test_wind_force_audit_trail_complete(self):
        """Output dict must contain all required audit keys."""
        result = self.wind_force_on_sign(115.0, 10.0, 5.0, 20.0, "C")
        required_keys = [
            "Kz", "Kzt", "Kd", "Ke", "G", "qz_psf",
            "Cf_A", "F_A_lbf", "M_A_ftlbf",
            "F_B_lbf", "T_B_ftlbf", "M_B_ftlbf",
            "governing_case", "governing_F_lbf", "governing_M_ftlbf",
            "_version", "_reference",
        ]
        for key in required_keys:
            assert key in result, f"Missing audit key: {key}"


# ---------------------------------------------------------------------------
# Foundation — Broms / IBC
# ---------------------------------------------------------------------------


class TestFoundationEmbed:
    """Foundation design module reference checks."""

    @pytest.fixture(autouse=True)
    def import_foundation(self):
        from apex_signcalc.foundation_embed import design_embed, design_foundation

        self.design_embed = design_embed
        self.design_foundation = design_foundation

    def test_design_embed_returns_geometry_and_checks(self):
        """design_embed must return (geometry_dict, checks_dict) tuple."""
        result = self.design_embed(2000.0, 20000.0)
        assert isinstance(result, tuple)
        assert len(result) == 2
        geom, checks = result
        assert "depth_in" in geom
        assert "dia_in" in geom

    def test_design_embed_reasonable_depth_range(self):
        """24-in diameter pier, 2000 lbf lateral, 20000 in-lb moment.

        Embedment depth must be in a reasonable engineering range.
        The design_embed legacy function uses medium_sand and default diameter.
        For 24-in dia with these loads, expect depth between 18 and 360 inches.
        """
        geom, checks = self.design_embed(2000.0, 20000.0, {"max_foundation_dia_in": 24})
        depth_in = geom["depth_in"]
        assert 18.0 <= depth_in <= 360.0, (
            f"Embedment depth {depth_in} in is outside realistic range 18–360 in"
        )

    def test_design_embed_diameter_respects_constraint(self):
        """Diameter should not exceed max_foundation_dia_in constraint."""
        geom, _ = self.design_embed(2000.0, 20000.0, {"max_foundation_dia_in": 24})
        assert geom["dia_in"] <= 24.0

    def test_design_foundation_broms_cohesive_medium_clay(self):
        """Broms cohesive method with custom medium clay (cu=1000 psf).

        Known case: 24-in dia pier, 2000 lbf lateral, 20000 in-lb moment,
        medium clay (qu=2000 psf → cu = qu/2 = 1000 psf).
        Expected embedment: 4–8 ft range for sign foundations.
        """
        D_ft = 2.0
        P_lbf = 2000.0
        M_ftlb = 20000.0 / 12.0
        h_eff = M_ftlb / P_lbf  # effective height above grade

        custom_soil = {
            "cu_psf": 1000.0,
            "gamma_pcf": 115.0,
            "phi_deg": 0.0,
            "S1_psf_per_ft": 200.0,
        }
        result = self.design_foundation(
            lateral_force_lbf=P_lbf,
            moment_at_grade_ftlb=M_ftlb,
            height_to_force_ft=h_eff,
            shaft_diameter_ft=D_ft,
            custom_soil=custom_soil,
            method="broms",
        )
        embed_ft = result["embedment_ft"]
        sf = result["safety_factor"]

        assert 1.0 <= embed_ft <= 10.0, (
            f"Broms embedment {embed_ft} ft outside 1–10 ft range for these loads"
        )
        assert sf is not None
        assert sf >= 2.0, f"Safety factor {sf} < 2.0 target"

    def test_design_foundation_ibc_method_runs(self):
        """IBC 1807.3.1 method produces a positive embedment depth."""
        result = self.design_foundation(
            lateral_force_lbf=2000.0,
            moment_at_grade_ftlb=20000.0 / 12.0,
            height_to_force_ft=0.833,
            shaft_diameter_ft=2.0,
            soil_type="medium_clay",
            method="ibc",
        )
        assert result["embedment_ft"] > 0.0

    def test_design_foundation_governing_is_maximum(self):
        """When running all methods, governing depth is the maximum."""
        result = self.design_foundation(
            lateral_force_lbf=3000.0,
            moment_at_grade_ftlb=30000.0 / 12.0,
            height_to_force_ft=1.0,
            shaft_diameter_ft=2.0,
            soil_type="medium_sand",
            method="all",
        )
        gov_depth = result["embedment_ft"]
        for method_name, audit in result["all_results"].items():
            if "L_design_ft" in audit:
                assert gov_depth >= audit["L_design_ft"] - 0.1, (
                    f"Governing depth {gov_depth} < {method_name} depth {audit['L_design_ft']}"
                )

    def test_design_foundation_invalid_soil_raises(self):
        """Unknown soil type must raise ValueError."""
        with pytest.raises(ValueError):
            self.design_foundation(
                2000.0, 1000.0, 10.0,
                soil_type="moon_dust",
                shaft_diameter_ft=2.0,
            )

    def test_design_foundation_audit_trail_present(self):
        """Output must include calibration_version for PE audit trail."""
        result = self.design_foundation(
            2000.0, 1000.0, 10.0,
            soil_type="medium_sand",
            shaft_diameter_ft=2.0,
        )
        assert "calibration_version" in result
        assert "input_echo" in result


# ---------------------------------------------------------------------------
# Sections — AISC catalog
# ---------------------------------------------------------------------------


class TestSections:
    """Section catalog reference checks."""

    @pytest.fixture(autouse=True)
    def import_sections(self):
        from apex_signcalc.sections import get_section, load_catalog

        self.load_catalog = load_catalog
        self.get_section = get_section

    def test_w14x22_properties(self):
        """W14X22: d=13.74, Ix=199, Sx=29.0, Zx=33.2 per AISC SCM 16th Ed."""
        sec = self.get_section("W14X22")
        assert sec is not None, "W14X22 not found in catalog"
        assert sec.d_in == pytest.approx(13.74, abs=0.01)
        assert sec.Ix_in4 == pytest.approx(199.0, abs=0.5)
        assert sec.Sx_in3 == pytest.approx(29.0, abs=0.1)
        assert sec.Zx_in3 == pytest.approx(33.2, abs=0.1)

    def test_w14x22_material(self):
        """W14X22 should be A992 steel: Fy=50 ksi, Fu=65 ksi."""
        sec = self.get_section("W14X22")
        assert sec.Fy_ksi == pytest.approx(50.0, abs=0.1)
        assert sec.Fu_ksi == pytest.approx(65.0, abs=0.1)

    def test_pipe4std_dimensions(self):
        """Pipe4STD: OD=4.500, t_w=0.237 per AISC SCM Table 1-14."""
        sec = self.get_section("Pipe4STD")
        assert sec is not None, "Pipe4STD not found in catalog"
        assert sec.d_in == pytest.approx(4.500, abs=0.001)
        assert sec.tw_in == pytest.approx(0.237, abs=0.001)

    def test_pipe4std_material(self):
        """Pipe4STD should be A53 Gr B: Fy=35 ksi."""
        sec = self.get_section("Pipe4STD")
        assert sec.Fy_ksi == pytest.approx(35.0, abs=0.1)

    def test_hss6x6x025_loads(self):
        """HSS6x6x1/4 should be retrievable from catalog."""
        sec = self.get_section("HSS6x6x1/4")
        assert sec is not None, "HSS6x6x1/4 not found in catalog"
        assert sec.family.lower() == "hss_square"
        assert sec.d_in == pytest.approx(6.0, abs=0.01)

    def test_catalog_loads_without_error(self):
        """load_catalog must not raise and must return sections."""
        catalog = self.load_catalog()
        assert isinstance(catalog, list)
        assert len(catalog) > 0, "Catalog returned empty list"

    def test_catalog_has_all_three_families(self):
        """Catalog must contain pipe, W-shape, and HSS_square sections."""
        catalog = self.load_catalog()
        families = {s.family.lower() for s in catalog}
        assert "pipe" in families, "No pipe sections in catalog"
        assert "w" in families, "No W-shape sections in catalog"
        assert "hss_square" in families, "No HSS sections in catalog"

    def test_catalog_minimum_section_count(self):
        """Hardcoded catalog must have at least 15 sections covering key shapes."""
        catalog = self.load_catalog()
        # Hardcoded fallback has 19 sections; JSON file (if present) has 2000+.
        # We verify the minimum that must always be available.
        assert len(catalog) >= 15, (
            f"Expected at least 15 sections in catalog, got {len(catalog)}"
        )

    def test_get_section_case_insensitive(self):
        """get_section lookup should be case-insensitive."""
        sec_upper = self.get_section("W14X22")
        sec_lower = self.get_section("w14x22")
        assert sec_upper is not None
        assert sec_lower is not None
        assert sec_upper.designation.lower() == sec_lower.designation.lower()

    def test_get_section_missing_returns_none(self):
        """Non-existent designation returns None."""
        sec = self.get_section("W99X9999")
        assert sec is None


# ---------------------------------------------------------------------------
# Anchors / base plate — ACI 318-19
# ---------------------------------------------------------------------------


class TestAnchorsBaseplate:
    """Anchor bolt and base plate design reference checks."""

    @pytest.fixture(autouse=True)
    def import_anchors(self):
        from apex_signcalc.anchors_baseplate import design_anchors

        self.design_anchors = design_anchors

    def test_light_load_returns_geometry_and_checks(self):
        """design_anchors must return (geometry_dict, checks_dict) tuple."""
        result = self.design_anchors(F_lbf=500.0, M_inlb=5000.0)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_light_load_small_bolts(self):
        """Light load (F=500 lbf, M=5000 in-lb) should select 1/2-in or 5/8-in bolts."""
        geom, checks = self.design_anchors(F_lbf=500.0, M_inlb=5000.0)
        dia_in = geom["dia_in"]
        assert dia_in <= 0.750, (
            f"Light load selected oversized {dia_in:.3f}-in bolts"
        )

    def test_light_load_passes_all_checks(self):
        """Light load: all DCR values must be < 1.0."""
        geom, checks = self.design_anchors(F_lbf=500.0, M_inlb=5000.0)
        dcr_keys = [k for k in checks if k.endswith("_dcr")]
        assert len(dcr_keys) > 0, "No DCR keys in checks dict"
        for key in dcr_keys:
            assert checks[key] < 1.0, f"{key} = {checks[key]:.4f} >= 1.0"

    def test_light_load_interaction_dcr(self):
        """Interaction DCR for light load must be well below 1.0."""
        _, checks = self.design_anchors(F_lbf=500.0, M_inlb=5000.0)
        assert checks["interaction_dcr"] < 1.0

    def test_heavy_load_larger_bolts(self):
        """Heavy load (F=5000 lbf, M=100000 in-lb) must select larger bolts than light."""
        geom_light, _ = self.design_anchors(F_lbf=500.0, M_inlb=5000.0)
        geom_heavy, _ = self.design_anchors(F_lbf=5000.0, M_inlb=100000.0)
        assert geom_heavy["dia_in"] >= geom_light["dia_in"], (
            "Heavy load should require bolts at least as large as light load"
        )

    def test_heavy_load_passes_all_checks(self):
        """Heavy load: all DCR values must be < 1.0."""
        geom, checks = self.design_anchors(F_lbf=5000.0, M_inlb=100000.0)
        dcr_keys = [k for k in checks if k.endswith("_dcr")]
        for key in dcr_keys:
            assert checks[key] < 1.0, (
                f"Heavy load check failed: {key} = {checks[key]:.4f} >= 1.0"
            )

    def test_heavy_load_interaction_dcr(self):
        """Heavy load interaction DCR must be < 1.0."""
        _, checks = self.design_anchors(F_lbf=5000.0, M_inlb=100000.0)
        assert checks["interaction_dcr"] < 1.0

    def test_impossible_load_raises_value_error(self):
        """Loads beyond all bolt sizes in the table must raise ValueError."""
        with pytest.raises(ValueError):
            self.design_anchors(F_lbf=50000.0, M_inlb=10_000_000.0)

    def test_geometry_has_required_keys(self):
        """geometry dict must contain all required design keys."""
        geom, _ = self.design_anchors(F_lbf=500.0, M_inlb=5000.0)
        required = [
            "dia_in", "n_bolts", "embed_in",
            "plate_N_in", "plate_B_in", "plate_t_in",
            "bolt_grade", "futa_psi",
        ]
        for key in required:
            assert key in geom, f"Missing geometry key: {key}"

    def test_invalid_bolt_grade_raises(self):
        """Unknown bolt grade must raise ValueError."""
        with pytest.raises(ValueError):
            self.design_anchors(F_lbf=500.0, M_inlb=5000.0, bolt_grade="UNKNOWN")


# ---------------------------------------------------------------------------
# Member design — AISC 360-22
# ---------------------------------------------------------------------------


class TestMemberDesign:
    """AISC 360-22 member strength check verification."""

    @pytest.fixture(autouse=True)
    def import_checks(self):
        from apex_signcalc.sections import get_section
        from apex_signcalc.supports_pipe import check_section

        self.check_section = check_section
        self.get_section = get_section

    def test_pipe4std_flexure_ir_reasonable(self):
        """Pipe4STD with M=50000 in-lb: flexure IR should be < 1.0.

        Pipe4STD Zx=4.31 in^3, Fy=35 ksi → phiMn = 0.9*35000*4.31 = 135,765 in-lb
        IR_flexure = 50000 / 135765 ≈ 0.37 (well below 1.0)
        """
        sec = self.get_section("Pipe4STD")
        _, audit = self.check_section(sec, M_inlb=50000.0, V_lbf=1000.0, L_in=240.0)
        assert "IR_flexure" in audit
        assert audit["IR_flexure"] == pytest.approx(0.37, abs=0.02)
        assert audit["IR_flexure"] < 1.0

    def test_pipe4std_shear_ir_reasonable(self):
        """Pipe4STD shear IR for V=1000 lbf should be well below 1.0."""
        sec = self.get_section("Pipe4STD")
        _, audit = self.check_section(sec, M_inlb=50000.0, V_lbf=1000.0, L_in=240.0)
        assert "IR_shear" in audit
        assert audit["IR_shear"] < 1.0

    def test_pipe4std_deflection_check_present(self):
        """Audit dict must include a deflection interaction ratio key."""
        sec = self.get_section("Pipe4STD")
        _, audit = self.check_section(sec, M_inlb=50000.0, V_lbf=1000.0, L_in=240.0)
        assert "IR_deflection" in audit, "Deflection check missing from audit"
        assert "delta_in" in audit, "delta_in missing from audit"
        assert "def_limit_in" in audit, "def_limit_in missing from audit"

    def test_pipe4std_deflection_exceeds_for_long_cantilever(self):
        """240-in cantilever with M=50000 in-lb should fail deflection for Pipe4STD.

        Delta = M*L^2 / (2*E*I) = 50000 * 240^2 / (2 * 29e6 * 7.23) ≈ 13.8 in
        Limit = L/120 = 240/120 = 2.0 in → IR > 1.0 is expected.
        """
        sec = self.get_section("Pipe4STD")
        ok, audit = self.check_section(sec, M_inlb=50000.0, V_lbf=1000.0, L_in=240.0)
        assert audit["IR_deflection"] > 1.0, (
            "Expected deflection failure for 20-ft cantilever with Pipe4STD"
        )
        assert ok is False, "Member should fail due to deflection"

    def test_pipe4std_section_family(self):
        """check_section audit must identify Pipe4STD as pipe family."""
        sec = self.get_section("Pipe4STD")
        _, audit = self.check_section(sec, M_inlb=50000.0, V_lbf=1000.0, L_in=240.0)
        assert audit["family"].lower() == "pipe"

    def test_w14x22_handles_w_shape(self):
        """check_section must process W14X22 (W family) without error."""
        sec = self.get_section("W14X22")
        assert sec is not None
        ok, audit = self.check_section(sec, M_inlb=200000.0, V_lbf=5000.0, L_in=240.0)
        assert "IR_flexure" in audit
        assert audit["family"].lower() == "w"

    def test_w14x22_flexure_ir_reasonable(self):
        """W14X22 with M=200000 in-lb: flexure IR should be < 1.0.

        W14X22 Zx=33.2 in^3, Fy=50 ksi → phiMn = 0.9*50000*33.2 = 1,494,000 in-lb
        IR_flexure = 200000 / 1,494,000 ≈ 0.134 (compact section, likely yielding governs)
        """
        sec = self.get_section("W14X22")
        _, audit = self.check_section(sec, M_inlb=200000.0, V_lbf=5000.0, L_in=240.0)
        assert audit["IR_flexure"] < 1.0, (
            f"W14X22 IR_flexure {audit['IR_flexure']:.4f} unexpectedly >= 1.0"
        )

    def test_check_section_returns_pass_bool_and_audit(self):
        """check_section must return (bool, dict) tuple."""
        sec = self.get_section("Pipe4STD")
        result = self.check_section(sec, M_inlb=50000.0, V_lbf=1000.0, L_in=240.0)
        assert isinstance(result, tuple)
        assert len(result) == 2
        ok, audit = result
        assert isinstance(ok, bool)
        assert isinstance(audit, dict)

    def test_check_section_audit_has_governing_state(self):
        """Audit dict must include governing_limit_state key."""
        sec = self.get_section("Pipe4STD")
        _, audit = self.check_section(sec, M_inlb=50000.0, V_lbf=1000.0, L_in=240.0)
        assert "governing_limit_state" in audit
        assert "governing_IR" in audit

    def test_pipe4std_passes_with_short_member(self):
        """Pipe4STD should pass all checks for short 24-in cantilever with low load."""
        sec = self.get_section("Pipe4STD")
        ok, audit = self.check_section(sec, M_inlb=2000.0, V_lbf=100.0, L_in=24.0)
        assert ok is True, (
            f"Pipe4STD should pass for short member; governing state: "
            f"{audit.get('governing_limit_state')}, IR: {audit.get('governing_IR'):.4f}"
        )
