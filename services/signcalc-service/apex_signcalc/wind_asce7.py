"""ASCE 7-22 Section 29.3 Wind Load Module — Freestanding Signs.

PE-stampable implementation of Chapter 26 / Chapter 29.3 for solid freestanding
walls and signs. All intermediate values are preserved in return dicts for
complete audit trail.

Reference: ASCE 7-22, Chapters 26, 29
Module version: ASCE7-22_v1.0
"""

from __future__ import annotations

import math
from typing import Dict, Literal, Optional, Tuple

# ---------------------------------------------------------------------------
# Module version constant
# ---------------------------------------------------------------------------
_version = "ASCE7-22_v1.0"

# ---------------------------------------------------------------------------
# Table 26.10-1 — Velocity Pressure Exposure Coefficients (Kz)
# ASCE 7-22 Table 26.10-1
# Keys are height in feet. Below 15 ft uses the 15-ft value per code note.
# ---------------------------------------------------------------------------
_KZ_TABLE: Dict[str, Dict[float, float]] = {
    "B": {
        15.0: 0.57,
        20.0: 0.62,
        25.0: 0.66,
        30.0: 0.70,
        40.0: 0.76,
        50.0: 0.81,
        60.0: 0.85,
        70.0: 0.89,
        80.0: 0.93,
        90.0: 0.96,
        100.0: 0.99,
        120.0: 1.04,
        140.0: 1.09,
        160.0: 1.13,
        180.0: 1.17,
        200.0: 1.20,
        250.0: 1.28,
        300.0: 1.35,
        350.0: 1.41,
        400.0: 1.47,
        450.0: 1.52,
        500.0: 1.56,
    },
    "C": {
        15.0: 0.85,
        20.0: 0.90,
        25.0: 0.94,
        30.0: 0.98,
        40.0: 1.04,
        50.0: 1.09,
        60.0: 1.13,
        70.0: 1.17,
        80.0: 1.21,
        90.0: 1.24,
        100.0: 1.26,
        120.0: 1.31,
        140.0: 1.36,
        160.0: 1.39,
        180.0: 1.43,
        200.0: 1.46,
        250.0: 1.53,
        300.0: 1.59,
        350.0: 1.64,
        400.0: 1.69,
        450.0: 1.73,
        500.0: 1.77,
    },
    "D": {
        15.0: 1.03,
        20.0: 1.08,
        25.0: 1.12,
        30.0: 1.16,
        40.0: 1.22,
        50.0: 1.27,
        60.0: 1.31,
        70.0: 1.34,
        80.0: 1.38,
        90.0: 1.40,
        100.0: 1.43,
        120.0: 1.48,
        140.0: 1.52,
        160.0: 1.55,
        180.0: 1.58,
        200.0: 1.61,
        250.0: 1.68,
        300.0: 1.73,
        350.0: 1.78,
        400.0: 1.82,
        450.0: 1.86,
        500.0: 1.89,
    },
}

# ---------------------------------------------------------------------------
# Table 26.9-1 — Ground Elevation Factor (Ke)
# ASCE 7-22 Table 26.9-1
# Key: elevation above sea level in feet
# ---------------------------------------------------------------------------
_KE_TABLE: Dict[float, float] = {
    0.0: 1.00,
    1000.0: 0.96,
    2000.0: 0.93,
    3000.0: 0.89,
    4000.0: 0.86,
    5000.0: 0.83,
    6000.0: 0.80,
}

# ---------------------------------------------------------------------------
# Table 26.6-1 — Wind Directionality Factor (Kd)
# ASCE 7-22 Table 26.6-1
# For signs and freestanding walls: Kd = 0.85
# ---------------------------------------------------------------------------
KD_SIGNS: float = 0.85

# ---------------------------------------------------------------------------
# Gust Effect Factor (G)
# ASCE 7-22 Section 26.11
# For rigid structures (natural frequency >= 1 Hz): G = 0.85
# Most freestanding signs qualify as rigid.
# ---------------------------------------------------------------------------
G_RIGID: float = 0.85


# ---------------------------------------------------------------------------
# Case A/B force coefficient table — ASCE 7-22 Figure 29.3-1
# Outer key: B/s ratio (sign width / sign height)
# Inner key: s/h ratio bracket ("le08" = <= 0.8, "10" = 1.0)
# Case B uses the same Cf values as Case A per ASCE 7-22.
# ---------------------------------------------------------------------------
_CF_TABLE_AB: Dict[float, Dict[str, float]] = {
    1.0:  {"le08": 1.30, "10": 1.70},
    2.0:  {"le08": 1.30, "10": 1.70},
    5.0:  {"le08": 1.35, "10": 1.75},
    10.0: {"le08": 1.40, "10": 1.80},
    20.0: {"le08": 1.50, "10": 1.85},
    30.0: {"le08": 1.55, "10": 1.85},
}

# ---------------------------------------------------------------------------
# Case C force coefficient table — ASCE 7-22 Figure 29.3-1
# Only applicable when B/s >= 2.
# Two zones: "near" (windward free-edge half) and "far" (other half).
# ---------------------------------------------------------------------------
_CF_TABLE_C: Dict[float, Dict[str, float]] = {
    2.0:  {"near": 2.40, "far": 1.20},
    5.0:  {"near": 2.50, "far": 1.10},
    10.0: {"near": 2.55, "far": 1.05},
    20.0: {"near": 2.58, "far": 1.02},
    30.0: {"near": 2.60, "far": 1.00},
}


# ---------------------------------------------------------------------------
# Low-level interpolation utility
# ---------------------------------------------------------------------------

def _linear_interp(table: Dict[float, float], x: float) -> float:
    """Linearly interpolate within a monotonically keyed float→float table.

    Returns the clamped endpoint value when x is outside the table range.
    """
    xs = sorted(table.keys())
    ys = [table[k] for k in xs]

    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]

    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + t * (ys[i + 1] - ys[i])

    return ys[-1]  # unreachable but satisfies type checkers


# ---------------------------------------------------------------------------
# Kz — Velocity Pressure Exposure Coefficient
# ---------------------------------------------------------------------------

def kz(z_ft: float, exposure: str) -> float:
    """Return Kz for height z_ft and exposure category.

    Reference: ASCE 7-22 Table 26.10-1
    Heights below 15 ft are treated as 15 ft per code footnote.

    Parameters
    ----------
    z_ft : float
        Height above grade in feet.
    exposure : str
        Exposure category: "B", "C", or "D".

    Returns
    -------
    float
        Kz value (dimensionless).
    """
    exposure = exposure.upper()
    if exposure not in _KZ_TABLE:
        raise ValueError(f"Exposure must be 'B', 'C', or 'D'; got '{exposure}'")

    # Minimum height 15 ft per Table 26.10-1 footnote
    z_eff = max(z_ft, 15.0)
    return _linear_interp(_KZ_TABLE[exposure], z_eff)


def ke(elevation_ft: float) -> float:
    """Return ground elevation factor Ke.

    Reference: ASCE 7-22 Table 26.9-1
    Reduces velocity pressure at high elevation sites (thinner air).

    Parameters
    ----------
    elevation_ft : float
        Ground elevation above sea level in feet.

    Returns
    -------
    float
        Ke value (dimensionless, between 0.80 and 1.00).
    """
    return _linear_interp(_KE_TABLE, max(elevation_ft, 0.0))


# ---------------------------------------------------------------------------
# Velocity Pressure
# ---------------------------------------------------------------------------

def velocity_pressure(
    V: float,
    Kz: float,
    Kzt: float,
    Kd: float,
    Ke: float,
) -> float:
    """Compute velocity pressure qz at height z.

    Reference: ASCE 7-22 Eq. 26.10-1
        qz = 0.00256 * Kz * Kzt * Kd * Ke * V^2  (psf)

    IMPORTANT: G (gust effect factor) is NOT part of this equation.
    G multiplies the resulting force, not the velocity pressure.

    Parameters
    ----------
    V : float
        Basic wind speed in mph.
    Kz : float
        Velocity pressure exposure coefficient (Table 26.10-1).
    Kzt : float
        Topographic factor (Section 26.8; = 1.0 for flat terrain).
    Kd : float
        Wind directionality factor (Table 26.6-1; = 0.85 for signs).
    Ke : float
        Ground elevation factor (Table 26.9-1).

    Returns
    -------
    float
        qz in pounds per square foot (psf).
    """
    return 0.00256 * Kz * Kzt * Kd * Ke * (V ** 2)


# ---------------------------------------------------------------------------
# Force Coefficients — Case A / B
# ---------------------------------------------------------------------------

def _interp_cf_ab_by_bs(bs_ratio: float, sh_ratio: float) -> float:
    """Interpolate Cf (Cases A and B) from Figure 29.3-1.

    Clamps B/s to [1, 30]. Interpolates between the two s/h brackets
    (<=0.8 and 1.0) and between tabulated B/s values.
    """
    # Clamp B/s
    bs = max(1.0, min(bs_ratio, 30.0))

    # Sorted B/s breakpoints
    bs_keys = sorted(_CF_TABLE_AB.keys())

    # Interpolate the two s/h brackets separately, then blend
    def cf_at_bs(b: float, bracket: str) -> float:
        lo_key = max(k for k in bs_keys if k <= b) if any(k <= b for k in bs_keys) else bs_keys[0]
        hi_key = min(k for k in bs_keys if k >= b) if any(k >= b for k in bs_keys) else bs_keys[-1]
        if lo_key == hi_key:
            return _CF_TABLE_AB[lo_key][bracket]
        t = (b - lo_key) / (hi_key - lo_key)
        return _CF_TABLE_AB[lo_key][bracket] + t * (_CF_TABLE_AB[hi_key][bracket] - _CF_TABLE_AB[lo_key][bracket])

    cf_le08 = cf_at_bs(bs, "le08")
    cf_10 = cf_at_bs(bs, "10")

    # s/h bracket: clamp to [0, 1.0]
    sh = max(0.0, min(sh_ratio, 1.0))

    if sh <= 0.8:
        return cf_le08
    # Linearly interpolate between s/h=0.8 and s/h=1.0
    t = (sh - 0.8) / (1.0 - 0.8)
    return cf_le08 + t * (cf_10 - cf_le08)


def _interp_cf_c(bs_ratio: float) -> Tuple[float, float]:
    """Interpolate Case C force coefficients (near-edge and far zones).

    Returns (Cf_near, Cf_far).
    Only valid for B/s >= 2; caller must enforce applicability.
    """
    bs = max(2.0, min(bs_ratio, 30.0))
    c_keys = sorted(_CF_TABLE_C.keys())

    lo_key = max(k for k in c_keys if k <= bs) if any(k <= bs for k in c_keys) else c_keys[0]
    hi_key = min(k for k in c_keys if k >= bs) if any(k >= bs for k in c_keys) else c_keys[-1]

    if lo_key == hi_key:
        return _CF_TABLE_C[lo_key]["near"], _CF_TABLE_C[lo_key]["far"]

    t = (bs - lo_key) / (hi_key - lo_key)
    cf_near = _CF_TABLE_C[lo_key]["near"] + t * (_CF_TABLE_C[hi_key]["near"] - _CF_TABLE_C[lo_key]["near"])
    cf_far = _CF_TABLE_C[lo_key]["far"] + t * (_CF_TABLE_C[hi_key]["far"] - _CF_TABLE_C[lo_key]["far"])
    return cf_near, cf_far


# ---------------------------------------------------------------------------
# Main wind load function
# ---------------------------------------------------------------------------

def wind_force_on_sign(
    V_mph: float,
    sign_width_ft: float,
    sign_height_ft: float,
    height_to_top_ft: float,
    exposure: str,
    Kzt: float = 1.0,
    elevation_ft: float = 0.0,
    risk_category: str = "II",
) -> dict:
    """Complete ASCE 7-22 Section 29.3 wind load analysis for a freestanding sign.

    Computes velocity pressure, gust factor, force coefficients, resultant
    forces, overturning moments, and eccentricities for all three loading
    cases defined in ASCE 7-22 Figure 29.3-1. The governing case (maximum
    base overturning moment) is identified automatically.

    Reference: ASCE 7-22 Sections 26.6, 26.8, 26.9, 26.10, 26.11, 29.3

    Parameters
    ----------
    V_mph : float
        Basic wind speed in mph (ASCE 7-22 Figure 26.5-1 or 26.5-2).
    sign_width_ft : float
        Horizontal dimension of sign face (B) in feet.
    sign_height_ft : float
        Vertical dimension of sign face (s) in feet.
    height_to_top_ft : float
        Height from ground to TOP of sign (h) in feet.
    exposure : str
        Exposure category: "B", "C", or "D".
    Kzt : float, optional
        Topographic factor per Section 26.8. Default 1.0 (flat terrain).
    elevation_ft : float, optional
        Ground elevation above sea level in feet. Default 0.0.
    risk_category : str, optional
        Risk category per Table 1.5-1. Used for documentation; does not
        affect Cf or qz (wind speed already risk-adjusted). Default "II".

    Returns
    -------
    dict
        Complete audit-trail dict with keys:

        Geometry
        --------
        B_ft, s_ft, h_ft : sign dimensions and top-of-sign height
        h_bottom_ft       : height from ground to BOTTOM of sign
        h_centroid_ft     : height to sign centroid above grade
        A_sf              : sign face area (sf)
        Bs_ratio          : B/s
        sh_ratio          : s/h

        Pressure parameters
        -------------------
        V_mph, exposure, risk_category
        Kz, Kzt, Kd, Ke, G
        qz_psf            : velocity pressure at sign centroid (psf)

        Case A
        ------
        Cf_A              : force coefficient (center resultant)
        F_A_lbf           : resultant force, lbf
        e_A_ft            : eccentricity from centerline (= 0)
        arm_A_ft          : moment arm from grade to centroid
        M_A_ftlbf         : overturning moment at base, ft-lbf

        Case B
        ------
        Cf_B              : force coefficient (same as Cf_A)
        F_B_lbf           : resultant force, lbf (= F_A)
        e_B_ft            : eccentricity = 0.2 * B from sign center
        arm_B_ft          : moment arm from grade to centroid (= arm_A)
        M_B_ftlbf         : overturning moment at base (torsional case), ft-lbf
                            NOTE: For lateral base moment M_B = M_A.
                            The eccentricity creates a TORSIONAL demand on
                            the foundation, reported as T_B_ftlbf.
        T_B_ftlbf         : torsional moment = F_B * e_B (ft-lbf)

        Case C
        ------
        case_C_applicable : bool — True only when B/s >= 2
        Cf_C_near         : Cf in windward free-edge zone
        Cf_C_far          : Cf in far zone
        F_C_near_lbf      : force on near-edge zone half
        F_C_far_lbf       : force on far zone half
        F_C_total_lbf     : total Case C resultant
        e_C_ft            : eccentricity of resultant from sign center
        arm_C_ft          : same vertical arm as A/B
        M_C_ftlbf         : lateral overturning moment at base

        Governing
        ---------
        governing_case    : "A", "B", or "C"
        governing_F_lbf   : governing lateral force (lbf)
        governing_M_ftlbf : governing base overturning moment (ft-lbf)

        Meta
        ----
        _version          : module version string
        _reference        : code reference string
    """
    # ------------------------------------------------------------------
    # 0. Input validation
    # ------------------------------------------------------------------
    exposure = exposure.upper()
    if exposure not in ("B", "C", "D"):
        raise ValueError(f"exposure must be 'B', 'C', or 'D'; got '{exposure}'")
    if sign_width_ft <= 0 or sign_height_ft <= 0:
        raise ValueError("sign_width_ft and sign_height_ft must be positive")
    if height_to_top_ft <= 0:
        raise ValueError("height_to_top_ft must be positive")
    if V_mph <= 0:
        raise ValueError("V_mph must be positive")

    B = sign_width_ft
    s = sign_height_ft
    h = height_to_top_ft

    # ------------------------------------------------------------------
    # 1. Geometry
    # ------------------------------------------------------------------
    h_bottom = h - s                              # height to bottom of sign (ft)
    h_centroid = h - s / 2.0                     # height to sign centroid (ft)
    A = B * s                                     # face area (sf)
    Bs_ratio = B / s
    sh_ratio = s / h

    # ------------------------------------------------------------------
    # 2. Pressure coefficients at sign centroid
    # ------------------------------------------------------------------
    Kz_val = kz(h_centroid, exposure)
    Ke_val = ke(elevation_ft)
    Kd_val = KD_SIGNS
    G_val = G_RIGID

    qz_val = velocity_pressure(V_mph, Kz_val, Kzt, Kd_val, Ke_val)

    # ------------------------------------------------------------------
    # 3. Force Coefficients — Case A
    # Reference: ASCE 7-22 Figure 29.3-1
    # ------------------------------------------------------------------
    Cf_A = _interp_cf_ab_by_bs(Bs_ratio, sh_ratio)

    # ------------------------------------------------------------------
    # 4. Case A — Resultant at geometric center (e = 0)
    # F = qz * G * Cf * A  (ASCE 7-22 Eq. 29.3-1)
    # M_base = F * h_centroid
    # ------------------------------------------------------------------
    F_A = qz_val * G_val * Cf_A * A
    e_A = 0.0
    arm_A = h_centroid
    M_A = F_A * arm_A

    # ------------------------------------------------------------------
    
    # 5. Case B — Resultant offset 0.2*B from geometric center
    # Reference: ASCE 7-22 Figure 29.3-1, Note 4 (Case B not req if B/s > 2)
    # ------------------------------------------------------------------
    case_B_applicable = Bs_ratio <= 2.0
    
    if case_B_applicable:
        Cf_B = Cf_A
        F_B = F_A
        e_B = 0.2 * B
        arm_B = arm_A
        M_B = F_B * arm_B
        T_B = F_B * e_B
    else:
        Cf_B = 0.0
        F_B = 0.0
        e_B = 0.0
        arm_B = 0.0
        M_B = 0.0
        T_B = 0.0
              # torsional moment at foundation (ft-lbf)

    # ------------------------------------------------------------------
    # 6. Case C — Two-zone loading (only when B/s >= 2)
    # Reference: ASCE 7-22 Figure 29.3-1, Case C
    # Near-edge zone: from windward free edge to B/2 from that edge
    # Far zone: remaining B/2
    # ------------------------------------------------------------------
    case_C_applicable = Bs_ratio >= 2.0

    if case_C_applicable:
        Cf_C_near, Cf_C_far = _interp_cf_c(Bs_ratio)

        # Each zone covers B/2 in width, full sign height s
        A_zone = (B / 2.0) * s

        F_C_near = qz_val * G_val * Cf_C_near * A_zone
        F_C_far = qz_val * G_val * Cf_C_far * A_zone
        F_C_total = F_C_near + F_C_far

        # Resultant location from windward end:
        #   x_near = B/4  (centroid of near-edge zone)
        #   x_far  = 3B/4 (centroid of far zone)
        # Resultant from windward end:
        x_resultant = (F_C_near * (B / 4.0) + F_C_far * (3.0 * B / 4.0)) / F_C_total
        # Eccentricity from sign geometric center (B/2):
        e_C = abs(x_resultant - B / 2.0)

        arm_C = arm_A   # same vertical arm
        M_C = F_C_total * arm_C

        Cf_C_near_out = round(Cf_C_near, 2)
        Cf_C_far_out = round(Cf_C_far, 2)
        F_C_near_out = round(F_C_near, 1)
        F_C_far_out = round(F_C_far, 1)
        F_C_total_out = round(F_C_total, 1)
        e_C_out = round(e_C, 3)
        M_C_out = round(M_C, 1)
    else:
        Cf_C_near_out = None
        Cf_C_far_out = None
        F_C_near_out = None
        F_C_far_out = None
        F_C_total_out = None
        e_C_out = None
        M_C_out = None
        F_C_total = None
        M_C = None

    # ------------------------------------------------------------------
    # 7. Governing case (maximum base overturning moment)
    # ------------------------------------------------------------------
    candidates: Dict[str, float] = {"A": M_A, "B": M_B}
    if case_C_applicable and M_C is not None:
        candidates["C"] = M_C

    governing_case = max(candidates, key=lambda k: candidates[k])
    governing_F_map = {
        "A": F_A,
        "B": F_B,
        "C": F_C_total if F_C_total is not None else 0.0,
    }
    governing_M = candidates[governing_case]
    governing_F = governing_F_map[governing_case]

    # ------------------------------------------------------------------
    # 8. Assemble output dict
    # ------------------------------------------------------------------
    return {
        # --- Geometry ---
        "B_ft": round(B, 3),
        "s_ft": round(s, 3),
        "h_ft": round(h, 3),
        "h_bottom_ft": round(h_bottom, 3),
        "h_centroid_ft": round(h_centroid, 3),
        "A_sf": round(A, 2),
        "Bs_ratio": round(Bs_ratio, 3),
        "sh_ratio": round(sh_ratio, 3),

        # --- Site & Wind Parameters ---
        "V_mph": V_mph,
        "exposure": exposure,
        "risk_category": risk_category,
        "elevation_ft": elevation_ft,

        # --- Pressure Coefficients ---
        "Kz": round(Kz_val, 3),
        "Kzt": round(Kzt, 3),
        "Kd": round(Kd_val, 2),
        "Ke": round(Ke_val, 3),
        "G": round(G_val, 2),
        "qz_psf": round(qz_val, 2),

        # --- Case A ---
        "Cf_A": round(Cf_A, 2),
        "F_A_lbf": round(F_A, 1),
        "e_A_ft": round(e_A, 3),
        "arm_A_ft": round(arm_A, 3),
        "M_A_ftlbf": round(M_A, 1),

        # --- Case B ---
        "Cf_B": round(Cf_B, 2),
        "F_B_lbf": round(F_B, 1),
        "e_B_ft": round(e_B, 3),
        "T_B_ftlbf": round(T_B, 1),
        "arm_B_ft": round(arm_B, 3),
        "case_B_applicable": case_B_applicable,
          "M_B_ftlbf": round(M_B, 1),

        # --- Case C ---
        "case_C_applicable": case_C_applicable,
        "Cf_C_near": Cf_C_near_out,
        "Cf_C_far": Cf_C_far_out,
        "F_C_near_lbf": F_C_near_out,
        "F_C_far_lbf": F_C_far_out,
        "F_C_total_lbf": F_C_total_out,
        "e_C_ft": e_C_out,
        "arm_C_ft": round(arm_A, 3),
        "M_C_ftlbf": M_C_out,

        # --- Governing ---
        "governing_case": governing_case,
        "governing_F_lbf": round(governing_F, 1),
        "governing_M_ftlbf": round(governing_M, 1),

        # --- Meta ---
        "_version": _version,
        "_reference": "ASCE 7-22 Sections 26.6, 26.8, 26.9, 26.10, 26.11, 29.3",
    }


# ---------------------------------------------------------------------------
# Load Combinations
# ---------------------------------------------------------------------------

def load_combinations(
    D_lbf: float,
    W_lbf: float,
    L_lbf: float = 0.0,
    *,
    return_all: bool = False,
) -> dict:
    """Evaluate ASCE 7-22 load combinations for freestanding sign forces.

    Only the combinations relevant to lateral / overturning demand on signs
    are included. Signs carry no live load in the conventional sense, but
    the interface supports it for future extension.

    Reference: ASCE 7-22 Section 2.3 (LRFD) / Section 2.4 (ASD)

    ASD Combinations (Section 2.4):
        ASD6: D + W                          — lateral + gravity
        ASD7: D + 0.75*W + 0.75*L           — combined
        ASD8: 0.6*D + W                      — uplift / overturning check

    Parameters
    ----------
    D_lbf : float
        Dead load force (lbf). Typically weight of sign + structure.
    W_lbf : float
        Wind load force (lbf). Use governing_F_lbf from wind_force_on_sign.
    L_lbf : float, optional
        Live load force (lbf). Default 0.0.
    return_all : bool, optional
        If True, return all combinations. If False, return only the
        governing (maximum) combination. Default False.

    Returns
    -------
    dict
        Keys: combination name → result value (lbf).
        Includes "governing_combination" and "governing_value" keys always.
    """
    combos = {
        "ASD6_D+W": D_lbf + W_lbf,
        "ASD7_D+0.75W+0.75L": D_lbf + 0.75 * W_lbf + 0.75 * L_lbf,
        "ASD8_0.6D+W": 0.6 * D_lbf + W_lbf,
    }

    governing_combo = max(combos, key=lambda k: combos[k])
    governing_val = combos[governing_combo]

    if return_all:
        result = {k: round(v, 1) for k, v in combos.items()}
    else:
        result = {}

    result["governing_combination"] = governing_combo
    result["governing_value_lbf"] = round(governing_val, 1)
    result["_reference"] = "ASCE 7-22 Sections 2.4 (ASD load combinations)"
    return result


# ---------------------------------------------------------------------------
# Legacy shim — keeps existing call-sites working
# ---------------------------------------------------------------------------

def interpolate_kz(
    kz_table: Dict[str, Dict[float, float]],
    exposure: str,
    z_ft: float,
) -> float:
    """Legacy shim: interpolate Kz from an arbitrary table dict.

    Prefer calling kz(z_ft, exposure) directly, which uses the embedded
    ASCE 7-22 Table 26.10-1.
    """
    rows = sorted(kz_table.get(exposure.upper(), {}).items())
    if not rows:
        return 1.0
    xs = [h for h, _ in rows]
    ys = [v for _, v in rows]
    if z_ft <= xs[0]:
        return ys[0]
    if z_ft >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= z_ft <= xs[i + 1]:
            x0, x1 = xs[i], xs[i + 1]
            y0, y1 = ys[i], ys[i + 1]
            t = (z_ft - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return ys[-1]


def qz_psf(V_basic: float, kz_val: float, kzt: float, kd: float) -> float:
    """Legacy shim: velocity pressure WITHOUT G.

    The old signature incorrectly accepted G as a parameter and baked it
    into qz. G must multiply the force (F = qz * G * Cf * A), not the
    pressure. Ke defaults to 1.0 (sea level) for backward compatibility.

    Reference: ASCE 7-22 Eq. 26.10-1
    """
    return velocity_pressure(V_basic, kz_val, kzt, kd, Ke=1.0)
