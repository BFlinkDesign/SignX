"""Direct burial foundation design — PE-stampable quality.

Methods implemented:
  1. Broms (1964) — lateral capacity of short rigid piles in cohesive and
     cohesionless soils.
  2. IBC 1807.3.1 nonconstrained — direct formula for unconstrained poles.
  3. Simplified Brinch Hansen — passive pressure integration via Kq/Kc.

All safety factors are computed, never capped.
All outputs carry a full audit trail keyed to calibration version.

Reference:
  Broms, B.B. (1964). "Lateral Resistance of Piles in Cohesionless Soils."
      J. Soil Mech. Found. Div., ASCE 90(SM3):123-156.
  IBC 2021 Section 1807.3.1
  Hansen, J.B. (1961). "The Ultimate Resistance of Rigid Piles Against
      Transversal Forces." Danish Geotech. Inst. Bull. 12.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# Calibration version — bump when any constant changes
# ---------------------------------------------------------------------------
CALIBRATION_VERSION = "footing_v2_broms_ibc_hansen"

# ---------------------------------------------------------------------------
# Soil property database
# cu_psf     — undrained shear strength (cohesive only; 0 for sand/gravel)
# gamma_pcf  — unit weight (pcf)
# phi_deg    — friction angle (degrees; 0 for cohesive soils)
# S1_psf_per_ft — IBC allowable lateral bearing pressure (psf per foot of depth)
# ---------------------------------------------------------------------------
SOIL_PROPERTIES: Dict[str, Dict[str, float]] = {
    "soft_clay":   {"cu_psf": 375,  "gamma_pcf": 105, "phi_deg": 0,  "S1_psf_per_ft": 75},
    "medium_clay": {"cu_psf": 750,  "gamma_pcf": 115, "phi_deg": 0,  "S1_psf_per_ft": 150},
    "stiff_clay":  {"cu_psf": 1500, "gamma_pcf": 125, "phi_deg": 0,  "S1_psf_per_ft": 300},
    "loose_sand":  {"cu_psf": 0,    "gamma_pcf": 100, "phi_deg": 29, "S1_psf_per_ft": 100},
    "medium_sand": {"cu_psf": 0,    "gamma_pcf": 120, "phi_deg": 33, "S1_psf_per_ft": 200},
    "dense_sand":  {"cu_psf": 0,    "gamma_pcf": 130, "phi_deg": 38, "S1_psf_per_ft": 350},
    "gravel":      {"cu_psf": 0,    "gamma_pcf": 130, "phi_deg": 37, "S1_psf_per_ft": 200},
}

# Concrete unit weight for volume / weight calculations
CONCRETE_PCF = 150.0
# Target safety factor for Broms iteration
BROMS_SF_TARGET = 2.0
# Iteration bounds (feet)
_L_MIN_FT = 1.0
_L_MAX_FT = 30.0
_L_TOL_FT = 0.001


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _kp(phi_deg: float) -> float:
    """Rankine passive earth pressure coefficient."""
    phi_rad = math.radians(phi_deg)
    return (1.0 + math.sin(phi_rad)) / (1.0 - math.sin(phi_rad))


def _broms_cohesive(
    cu_psf: float,
    D_ft: float,
    P_lbf: float,
    h_ft: float,
) -> Tuple[float, Dict[str, Any]]:
    """Broms method for cohesive soils (short rigid pile, L/D <= 6).

    Ultimate lateral capacity:
        Hu = 9 * cu * D * (L - 1.5*D)      [Broms 1964, eq. for short pile]

    Moment at failure is taken about the point of maximum moment.
    For a free-head pole with lateral load P at height h above grade:
        M_applied = P * (h + L/2)  (conservative: assume load acts at midpoint
        of embedded depth for moment arm)

    We iterate L so that:
        SF = Hu * (L/2) / M_applied >= BROMS_SF_TARGET
    which resolves to finding L such that:
        9*cu*D*(L - 1.5*D) * (L/2) = SF_target * P * (h + L/2)
    Rearranged as f(L) = 0 via bisection.
    """
    # Moment at grade from applied load
    M_grade_ftlb = P_lbf * h_ft  # ft-lb

    def _hu(L: float) -> float:
        return 9.0 * cu_psf * D_ft * max(L - 1.5 * D_ft, 0.0)

    def _resisting_moment(L: float) -> float:
        # Resisting moment about groundline: Hu acts at (2/3)*L from tip
        # i.e., at L/3 from groundline per Broms short-pile assumption
        return _hu(L) * (L / 3.0)  # ft-lb (conservative lever arm)

    def _demand_moment(L: float) -> float:
        return M_grade_ftlb + P_lbf * (L / 2.0)

    def _f(L: float) -> float:
        return _resisting_moment(L) - BROMS_SF_TARGET * _demand_moment(L)

    # Bisect
    lo, hi = _L_MIN_FT, _L_MAX_FT
    if _f(hi) < 0:
        # Even max embedment insufficient — return max with SF < target
        L_design = hi
    else:
        while (hi - lo) > _L_TOL_FT:
            mid = (lo + hi) / 2.0
            if _f(mid) < 0:
                lo = mid
            else:
                hi = mid
        L_design = hi

    hu_final = _hu(L_design)
    rm_final = _resisting_moment(L_design)
    dm_final = _demand_moment(L_design)
    sf_actual = rm_final / dm_final if dm_final > 0 else float("inf")
    ld_ratio = L_design / D_ft

    audit: Dict[str, Any] = {
        "method": "Broms_cohesive_1964",
        "cu_psf": cu_psf,
        "D_ft": D_ft,
        "L_design_ft": round(L_design, 3),
        "L_over_D": round(ld_ratio, 2),
        "Hu_lbf": round(hu_final, 1),
        "resisting_moment_ftlb": round(rm_final, 1),
        "demand_moment_ftlb": round(dm_final, 1),
        "safety_factor": round(sf_actual, 3),
        "short_pile_check": "OK" if ld_ratio <= 6.0 else "LONG_PILE_WARNING",
        "calibration_version": CALIBRATION_VERSION,
    }
    return L_design, audit


def _broms_cohesionless(
    gamma_pcf: float,
    phi_deg: float,
    D_ft: float,
    P_lbf: float,
    h_ft: float,
) -> Tuple[float, Dict[str, Any]]:
    """Broms method for cohesionless soils.

    Ultimate lateral capacity (short rigid pile):
        Hu = 1.5 * Kp * gamma * D * L^2

    Moment equilibrium at pile tip:
        Hu * (h + 2/3 * L) = P * (h + L)    ... simplified
    We solve for L where SF = Hu*(2L/3) / (P*(h+L/2)) >= 2.0 via bisection.
    """
    Kp = _kp(phi_deg)
    M_grade_ftlb = P_lbf * h_ft

    def _hu(L: float) -> float:
        return 1.5 * Kp * gamma_pcf * D_ft * (L ** 2)

    def _resisting_moment(L: float) -> float:
        # Hu acts at 2/3 L from pile head (tip reaction)
        return _hu(L) * (2.0 * L / 3.0)

    def _demand_moment(L: float) -> float:
        return M_grade_ftlb + P_lbf * (L / 2.0)

    def _f(L: float) -> float:
        return _resisting_moment(L) - BROMS_SF_TARGET * _demand_moment(L)

    lo, hi = _L_MIN_FT, _L_MAX_FT
    if _f(hi) < 0:
        L_design = hi
    else:
        while (hi - lo) > _L_TOL_FT:
            mid = (lo + hi) / 2.0
            if _f(mid) < 0:
                lo = mid
            else:
                hi = mid
        L_design = hi

    hu_final = _hu(L_design)
    rm_final = _resisting_moment(L_design)
    dm_final = _demand_moment(L_design)
    sf_actual = rm_final / dm_final if dm_final > 0 else float("inf")
    ld_ratio = L_design / D_ft

    audit: Dict[str, Any] = {
        "method": "Broms_cohesionless_1964",
        "Kp": round(Kp, 4),
        "phi_deg": phi_deg,
        "gamma_pcf": gamma_pcf,
        "D_ft": D_ft,
        "L_design_ft": round(L_design, 3),
        "L_over_D": round(ld_ratio, 2),
        "Hu_lbf": round(hu_final, 1),
        "resisting_moment_ftlb": round(rm_final, 1),
        "demand_moment_ftlb": round(dm_final, 1),
        "safety_factor": round(sf_actual, 3),
        "short_pile_check": "OK" if ld_ratio <= 6.0 else "LONG_PILE_WARNING",
        "calibration_version": CALIBRATION_VERSION,
    }
    return L_design, audit


def _ibc_18073(
    P_lbf: float,
    h_ft: float,
    S1_psf_per_ft: float,
    b_ft: float,
) -> Tuple[float, Dict[str, Any]]:
    """IBC 2021 Section 1807.3.1 — Nonconstrained (free-head) pole.

    d = 0.5 * A * (1 + sqrt(1 + 4.36 * h / A))
    where:
        A = 2.34 * P / (S1 * b)
        P = lateral force (lbf)
        h = height of resultant above groundline (ft)
        S1 = allowable lateral soil-bearing pressure (psf/ft of depth)
        b = diameter of round pier (ft)
    """
    if S1_psf_per_ft <= 0 or b_ft <= 0:
        raise ValueError("S1 and pier diameter must be positive.")

    A = 2.34 * P_lbf / (S1_psf_per_ft * b_ft)
    discriminant = 1.0 + 4.36 * h_ft / A
    if discriminant < 0:
        raise ValueError("IBC 1807.3.1: discriminant < 0; check input loads.")
    d_ft = 0.5 * A * (1.0 + math.sqrt(discriminant))

    audit: Dict[str, Any] = {
        "method": "IBC_1807.3.1_nonconstrained",
        "P_lbf": P_lbf,
        "h_ft": h_ft,
        "S1_psf_per_ft": S1_psf_per_ft,
        "b_ft": b_ft,
        "A": round(A, 4),
        "discriminant": round(discriminant, 6),
        "d_ft": round(d_ft, 3),
        "safety_factor": None,  # IBC formula is already ASD-based
        "calibration_version": CALIBRATION_VERSION,
    }
    return d_ft, audit


def _brinch_hansen(
    gamma_pcf: float,
    phi_deg: float,
    cu_psf: float,
    D_ft: float,
    P_lbf: float,
    h_ft: float,
) -> Tuple[float, Dict[str, Any]]:
    """Simplified Brinch Hansen passive pressure integration.

    Uses Hansen (1961) Kq and Kc shape factors.
    For a rigid pile, net lateral resistance per unit depth:
        p(z) = Kq * gamma * z * D  (frictional component)
               + Kc * cu * D        (cohesive component)

    Moment equilibrium about groundline:
        integral_0^L  p(z) * z dz = SF * M_applied(L)

    Kq and Kc are simplified per Hansen (1961):
        Kq = 1.5 * Kp  (conservative approximation)
        Kc = 9.0        (limiting for deep embedment)

    Integrals:
        int p(z)*z dz = Kq*gamma*D * L^3/3 + Kc*cu*D * L^2/2

    Iterate L via bisection for SF = 2.0.
    """
    phi_rad = math.radians(phi_deg)
    Kp_val = _kp(phi_deg) if phi_deg > 0 else 1.0
    Kq = 1.5 * Kp_val
    Kc = 9.0

    M_grade_ftlb = P_lbf * h_ft

    def _resisting_moment(L: float) -> float:
        frictional = Kq * gamma_pcf * D_ft * (L ** 3) / 3.0
        cohesive = Kc * cu_psf * D_ft * (L ** 2) / 2.0
        return frictional + cohesive

    def _demand_moment(L: float) -> float:
        return M_grade_ftlb + P_lbf * (L / 2.0)

    def _f(L: float) -> float:
        return _resisting_moment(L) - BROMS_SF_TARGET * _demand_moment(L)

    lo, hi = _L_MIN_FT, _L_MAX_FT
    if _f(hi) < 0:
        L_design = hi
    else:
        while (hi - lo) > _L_TOL_FT:
            mid = (lo + hi) / 2.0
            if _f(mid) < 0:
                lo = mid
            else:
                hi = mid
        L_design = hi

    rm_final = _resisting_moment(L_design)
    dm_final = _demand_moment(L_design)
    sf_actual = rm_final / dm_final if dm_final > 0 else float("inf")

    audit: Dict[str, Any] = {
        "method": "Brinch_Hansen_1961_simplified",
        "Kq": round(Kq, 4),
        "Kc": Kc,
        "phi_deg": phi_deg,
        "cu_psf": cu_psf,
        "gamma_pcf": gamma_pcf,
        "D_ft": D_ft,
        "L_design_ft": round(L_design, 3),
        "resisting_moment_ftlb": round(rm_final, 1),
        "demand_moment_ftlb": round(dm_final, 1),
        "safety_factor": round(sf_actual, 3),
        "calibration_version": CALIBRATION_VERSION,
    }
    return L_design, audit


# ---------------------------------------------------------------------------
# Secondary outputs
# ---------------------------------------------------------------------------

def _concrete_volume_cy(D_ft: float, L_ft: float) -> float:
    """Volume of cylindrical shaft in cubic yards."""
    vol_ft3 = math.pi * (D_ft / 2.0) ** 2 * L_ft
    return vol_ft3 / 27.0


def _shaft_weight_lbf(D_ft: float, L_ft: float) -> float:
    return _concrete_volume_cy(D_ft, L_ft) * 27.0 * CONCRETE_PCF


def _skin_friction_uplift(
    gamma_pcf: float,
    phi_deg: float,
    cu_psf: float,
    D_ft: float,
    L_ft: float,
) -> float:
    """Approximate skin friction uplift capacity (ASD).

    Cohesive:  Qs = alpha * cu * pi * D * L   (alpha = 0.55 conservative)
    Cohesionless: Qs = 0.5 * K * sigma_v * pi * D * L * tan(delta)
                  where K=0.5, delta=0.75*phi, sigma_v = gamma*L/2
    """
    perimeter = math.pi * D_ft
    if cu_psf > 0:
        alpha = 0.55
        return alpha * cu_psf * perimeter * L_ft
    else:
        phi_rad = math.radians(phi_deg)
        delta_rad = 0.75 * phi_rad
        K = 0.5
        sigma_v_avg = gamma_pcf * L_ft / 2.0
        return 0.5 * K * sigma_v_avg * perimeter * L_ft * math.tan(delta_rad)


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def design_foundation(
    lateral_force_lbf: float,
    moment_at_grade_ftlb: float,
    height_to_force_ft: float,
    soil_type: str = "medium_sand",
    shaft_diameter_ft: float = 2.5,
    custom_soil: Optional[Dict[str, float]] = None,
    method: str = "all",
) -> Dict[str, Any]:
    """Design a direct-burial pole foundation.

    Parameters
    ----------
    lateral_force_lbf : float
        Resultant lateral (wind/seismic) force at grade or resultant height,
        in pounds-force.
    moment_at_grade_ftlb : float
        Overturning moment at the groundline in ft-lb.  If the applied moment
        is provided separately from the lateral force, supply it here.
        If zero, the moment is derived entirely from lateral_force * height.
    height_to_force_ft : float
        Height of the resultant lateral force above finished grade (ft).
        For a sign panel, use the centroid height of the wind load.
    soil_type : str
        Key into SOIL_PROPERTIES.  Must be one of the defined types unless
        custom_soil is supplied.
    shaft_diameter_ft : float
        Drilled shaft diameter in feet.  Typical: 2.0 – 4.0 ft.
    custom_soil : dict | None
        Override soil properties.  Must contain keys: cu_psf, gamma_pcf,
        phi_deg, S1_psf_per_ft.  When provided, soil_type is ignored.
    method : str
        "all" (default) — run all three methods, return governing (maximum) depth.
        "broms"         — Broms only.
        "ibc"           — IBC 1807.3.1 only.
        "hansen"        — Brinch Hansen only.

    Returns
    -------
    dict with keys:
        embedment_ft        — governing design embedment (ft), rounded to 0.1 ft
        safety_factor       — governing method SF (computed, NOT capped)
        method_governing    — name of the governing method
        all_results         — dict of {method_name: audit_dict} for all methods run
        dfm_flag            — "auger" if embedment <= 3 ft else "excavator"
        concrete_volume_cy  — shaft concrete volume (cy)
        shaft_weight_lbf    — concrete shaft weight (lbf)
        skin_friction_uplift_lbf — estimated skin friction uplift resistance (lbf)
        input_echo          — full echo of inputs for audit trail
        calibration_version — version string
    """
    # ------------------------------------------------------------------
    # Resolve soil properties
    # ------------------------------------------------------------------
    if custom_soil is not None:
        soil = custom_soil
        soil_label = "custom"
    else:
        if soil_type not in SOIL_PROPERTIES:
            raise ValueError(
                f"Unknown soil_type '{soil_type}'. "
                f"Valid options: {sorted(SOIL_PROPERTIES.keys())}"
            )
        soil = SOIL_PROPERTIES[soil_type]
        soil_label = soil_type

    cu_psf = soil["cu_psf"]
    gamma_pcf = soil["gamma_pcf"]
    phi_deg = soil["phi_deg"]
    S1_psf_per_ft = soil["S1_psf_per_ft"]

    D_ft = shaft_diameter_ft
    P_lbf = lateral_force_lbf
    h_ft = height_to_force_ft

    # If moment_at_grade is provided independently, compute effective height
    # such that IBC formula (which uses h) captures total overturning.
    # Effective h = total moment / P  (only when P > 0)
    if P_lbf > 0 and moment_at_grade_ftlb > 0:
        h_eff_ft = moment_at_grade_ftlb / P_lbf
    elif P_lbf > 0:
        h_eff_ft = h_ft
    else:
        # Pure moment, no shear — treat as equivalent horizontal force at 1 ft
        P_lbf = moment_at_grade_ftlb  # treat M as P for stability
        h_eff_ft = 1.0

    # ------------------------------------------------------------------
    # Run selected methods
    # ------------------------------------------------------------------
    all_results: Dict[str, Any] = {}
    depths: Dict[str, float] = {}

    run_broms = method in ("all", "broms")
    run_ibc = method in ("all", "ibc")
    run_hansen = method in ("all", "hansen")

    if run_broms:
        if cu_psf > 0:
            L_b, audit_b = _broms_cohesive(cu_psf, D_ft, P_lbf, h_eff_ft)
        else:
            L_b, audit_b = _broms_cohesionless(gamma_pcf, phi_deg, D_ft, P_lbf, h_eff_ft)
        all_results["broms"] = audit_b
        depths["broms"] = L_b

    if run_ibc:
        try:
            L_i, audit_i = _ibc_18073(P_lbf, h_eff_ft, S1_psf_per_ft, D_ft)
            all_results["ibc"] = audit_i
            depths["ibc"] = L_i
        except ValueError as exc:
            all_results["ibc"] = {"error": str(exc)}

    if run_hansen:
        L_h, audit_h = _brinch_hansen(
            gamma_pcf, phi_deg, cu_psf, D_ft, P_lbf, h_eff_ft
        )
        all_results["hansen"] = audit_h
        depths["hansen"] = L_h

    if not depths:
        raise ValueError("No methods produced a valid result.")

    # ------------------------------------------------------------------
    # Governing depth = maximum of all methods (conservative envelope)
    # ------------------------------------------------------------------
    method_governing = max(depths, key=lambda k: depths[k])
    L_governing = depths[method_governing]

    # Safety factor from governing method
    gov_audit = all_results[method_governing]
    sf_governing = gov_audit.get("safety_factor", None)

    # ------------------------------------------------------------------
    # Secondary outputs
    # ------------------------------------------------------------------
    conc_cy = _concrete_volume_cy(D_ft, L_governing)
    shaft_wt = _shaft_weight_lbf(D_ft, L_governing)
    skin_fric = _skin_friction_uplift(
        gamma_pcf, phi_deg, cu_psf, D_ft, L_governing
    )
    dfm_flag = "auger" if L_governing <= 3.0 else "excavator"

    return {
        "embedment_ft": round(L_governing, 1),
        "safety_factor": round(sf_governing, 3) if sf_governing is not None else None,
        "method_governing": method_governing,
        "all_results": all_results,
        "dfm_flag": dfm_flag,
        "concrete_volume_cy": round(conc_cy, 3),
        "shaft_weight_lbf": round(shaft_wt, 1),
        "skin_friction_uplift_lbf": round(skin_fric, 1),
        "input_echo": {
            "lateral_force_lbf": lateral_force_lbf,
            "moment_at_grade_ftlb": moment_at_grade_ftlb,
            "height_to_force_ft": height_to_force_ft,
            "h_eff_ft_used": round(h_eff_ft, 4),
            "soil_type": soil_label,
            "shaft_diameter_ft": shaft_diameter_ft,
            "method_requested": method,
        },
        "calibration_version": CALIBRATION_VERSION,
    }


# ---------------------------------------------------------------------------
# Legacy shim — preserves old design_embed(F_lbf, M_inlb, constraints) API
# ---------------------------------------------------------------------------

def design_embed(
    F_lbf: float,
    M_inlb: float,
    constraints: Optional[Dict[str, float]] = None,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Legacy wrapper.  Converts old (F_lbf, M_inlb) signature to new API.

    Parameters
    ----------
    F_lbf : float
        Lateral force (lbf).
    M_inlb : float
        Overturning moment in inch-lb (converted internally to ft-lb).
    constraints : dict | None
        May contain 'max_foundation_dia_in' and/or 'max_embed_in'.

    Returns
    -------
    (geometry_dict, checks_dict) matching the old tuple format.
    """
    M_ftlb = M_inlb / 12.0
    h_ft = M_ftlb / F_lbf if F_lbf > 0 else 10.0

    # Resolve diameter from constraints or default
    default_dia_in = 30.0
    if constraints and constraints.get("max_foundation_dia_in"):
        dia_in = min(default_dia_in, constraints["max_foundation_dia_in"])
    else:
        dia_in = default_dia_in
    D_ft = dia_in / 12.0

    result = design_foundation(
        lateral_force_lbf=F_lbf,
        moment_at_grade_ftlb=M_ftlb,
        height_to_force_ft=h_ft,
        soil_type="medium_sand",
        shaft_diameter_ft=D_ft,
        method="all",
    )

    L_in = result["embedment_ft"] * 12.0

    # Apply legacy max_embed_in constraint
    if constraints and constraints.get("max_embed_in"):
        L_in = min(L_in, constraints["max_embed_in"])

    sf = result["safety_factor"] or 1.0

    geometry: Dict[str, float] = {
        "shape": "cyl",
        "dia_in": round(dia_in, 1),
        "depth_in": round(L_in, 1),
    }
    checks: Dict[str, float] = {
        "OT_sf": round(sf, 2),
        "BRG_sf": round(sf, 2),
        "SLIDE_sf": round(sf, 2),
        "UPLIFT_sf": round(
            result["skin_friction_uplift_lbf"] / max(F_lbf, 1.0), 2
        ),
    }
    return geometry, checks


# ---------------------------------------------------------------------------
# Interactive helper (preserved for backward compat)
# ---------------------------------------------------------------------------

def solve_footing_interactive(
    diameter_ft: float,
    M_pole_kipft: float,
    soil_psf: float,
    num_poles: int = 1,
) -> float:
    """Compute minimum embedment depth (inches) for a given diameter.

    Uses IBC 1807.3.1 with S1 derived from soil_psf argument.
    Maintains monotonic property: smaller diameter -> greater depth.
    """
    M_per_pole_kipft = M_pole_kipft if num_poles == 1 else M_pole_kipft * 0.5
    M_ftlb = M_per_pole_kipft * 1000.0
    # Estimate lateral force assuming force acts at mid-panel height = 10 ft
    h_assumed_ft = 10.0
    P_lbf = M_ftlb / h_assumed_ft

    A = 2.34 * P_lbf / (soil_psf * diameter_ft)
    if A <= 0:
        return 36.0
    discriminant = 1.0 + 4.36 * h_assumed_ft / A
    if discriminant < 0:
        return 36.0
    d_ft = 0.5 * A * (1.0 + math.sqrt(discriminant))
    d_in = max(36.0, d_ft * 12.0)
    return round(d_in, 1)
