"""
Anchor bolt and base plate design module.

Implements ACI 318-19 Chapter 17 (anchor design) and
AISC Design Guide 1 (base plate sizing) for sign structure
column base connections.

All intermediate values are preserved for PE stamp audit trails.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Anchor bolt material database
# ---------------------------------------------------------------------------

# Each entry: (futa_psi, Fy_psi, description)
BOLT_GRADES: Dict[str, Tuple[float, float, str]] = {
    "A307":       (60_000,  36_000, "ASTM A307 Grade A/B"),
    "F1554-36":   (58_000,  36_000, "ASTM F1554 Grade 36"),
    "F1554-55":   (75_000,  55_000, "ASTM F1554 Grade 55"),
    "F1554-105":  (125_000, 105_000, "ASTM F1554 Grade 105"),
    "A36":        (58_000,  36_000, "ASTM A36 rod (headed)"),
}

# Anchor bolt section properties keyed by nominal diameter (inches).
# Ase_in2: effective tensile stress area (ASME B1.1)
# Abrg_in2: head bearing area (hex head) = head_area - bolt_area
# Rows: (nominal_in, Ase_in2, Abrg_in2)
BOLT_SIZES: List[Tuple[float, float, float]] = [
    (0.500, 0.1419, 0.291),
    (0.625, 0.2260, 0.454),
    (0.750, 0.3340, 0.656),
    (0.875, 0.4620, 0.893),
    (1.000, 0.6060, 1.159),
    (1.250, 0.9690, 1.813),
    (1.500, 1.4050, 2.612),
]

# Standard available plate thicknesses (inches)
STANDARD_PLATE_THICKNESSES: List[float] = [
    0.25, 0.3125, 0.375, 0.4375, 0.50,
    0.625, 0.75, 0.875, 1.00, 1.25, 1.50,
    1.75, 2.00, 2.25, 2.50,
]

# ---------------------------------------------------------------------------
# ACI 318-19 strength reduction factors (Table 17.5.3)
# ---------------------------------------------------------------------------
PHI_STEEL_DUCTILE    = 0.75   # Sec 17.5.3(a) — steel, ductile
PHI_CONCRETE_TENSION = 0.70   # Sec 17.5.3(b) — concrete breakout, pullout
PHI_CONCRETE_SHEAR   = 0.70   # Sec 17.5.3(b) — concrete breakout in shear
PHI_PRYOUT           = 0.70   # Sec 17.5.3(c) — pryout

# Interaction exponent per ACI 318-19 Sec 17.8.3
INTERACTION_EXPONENT = 5.0 / 3.0

# Minimum edge distance multiplier (ACI 318-19 Sec 17.9.1)
MIN_EDGE_DIST_MULT = 6.0      # c_min >= 6 * d_a for cast-in headed anchors


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _round_up_plate_thickness(t_req: float) -> float:
    """Return next standard plate thickness >= t_req (inches)."""
    for t in STANDARD_PLATE_THICKNESSES:
        if t >= t_req - 1e-6:
            return t
    return t_req  # fallback: use exact value if beyond table


def _bolt_label(dia_in: float) -> str:
    """Return fractional-inch label for bolt diameter."""
    fracs = {
        0.500: "1/2",
        0.625: "5/8",
        0.750: "3/4",
        0.875: "7/8",
        1.000: "1",
        1.250: "1-1/4",
        1.500: "1-1/2",
    }
    return fracs.get(dia_in, f"{dia_in:.4f}") + " in"


def _concrete_breakout_area(hef: float, c_a1: Optional[float] = None) -> Tuple[float, float]:
    """
    Compute projected concrete failure areas for tension breakout.
    ACI 318-19 Sec 17.6.2.1

    Parameters
    ----------
    hef   : effective embedment depth (inches)
    c_a1  : nearest edge distance (inches); None = unconfined (no edge effects)

    Returns
    -------
    ANco : single-anchor projected area (in^2)
    ANc  : group/modified projected area (in^2) — same as ANco when unconfined
    """
    # Basic projected cone area for single anchor
    ANco = 9.0 * hef ** 2  # ACI 318-19 Eq. 17.6.2.1.3

    # Without edge influence, ANc = ANco
    if c_a1 is None:
        ANc = ANco
    else:
        # Edge-limited: clip projected width to actual edge distance (Sec 17.6.2.1.4)
        s_proj = min(3.0 * hef, c_a1)
        ANc = (s_proj + 3.0 * hef) * min(3.0 * hef, c_a1 + 3.0 * hef)
        ANc = min(ANc, ANco)

    return ANco, ANc


# ---------------------------------------------------------------------------
# ACI 318-19 Capacity Calculations
# ---------------------------------------------------------------------------

def _steel_tension_capacity(Ase: float, futa: float, n: int) -> Dict[str, float]:
    """
    ACI 318-19 Sec 17.6.1 — Steel strength in tension.

    phi_Nsa = phi * n * Ase * futa

    Parameters
    ----------
    Ase  : effective tensile stress area per bolt (in^2)
    futa : specified tensile strength (psi)
    n    : number of bolts in tension

    Returns intermediate values for audit.
    """
    Nsa_per = Ase * futa                    # Per-bolt nominal (lbf)
    phi_Nsa = PHI_STEEL_DUCTILE * n * Nsa_per
    return {
        "Nsa_per_lbf": Nsa_per,
        "phi_Nsa_total_lbf": phi_Nsa,
        "phi_steel_tension": PHI_STEEL_DUCTILE,
        "n_tension_bolts": n,
    }


def _concrete_breakout_tension(
    n: int,
    hef: float,
    f_c: float,
    ANco: float,
    ANc: float,
    psi_ed: float = 1.0,
    psi_c: float = 1.0,
    psi_cp: float = 1.0,
) -> Dict[str, float]:
    """
    ACI 318-19 Sec 17.6.2 — Concrete breakout strength in tension.

    Ncbg = (ANc/ANco) * psi_ed * psi_c * psi_cp * Nb

    where Nb = kc * lambda * sqrt(f'c) * hef^1.5  (Eq. 17.6.2.2a)
    kc = 24 for cast-in anchors.
    lambda = 1.0 (normal-weight concrete).
    """
    kc = 24.0        # ACI 318-19 Sec 17.6.2.2 — cast-in headed anchor
    lam = 1.0        # normal-weight concrete

    Nb = kc * lam * math.sqrt(f_c) * hef ** 1.5      # Eq. 17.6.2.2a (lbf)
    Ncbg = (ANc / ANco) * psi_ed * psi_c * psi_cp * Nb   # Sec 17.6.2.1
    phi_Ncbg = PHI_CONCRETE_TENSION * Ncbg

    return {
        "Nb_lbf": Nb,
        "kc": kc,
        "lambda": lam,
        "ANco_in2": ANco,
        "ANc_in2": ANc,
        "psi_ed_N": psi_ed,
        "psi_c_N": psi_c,
        "psi_cp_N": psi_cp,
        "Ncbg_lbf": Ncbg,
        "phi_Ncbg_lbf": phi_Ncbg,
        "phi_concrete_tension": PHI_CONCRETE_TENSION,
    }


def _pullout_tension(
    n: int,
    Abrg: float,
    f_c: float,
    psi_c: float = 1.0,
) -> Dict[str, float]:
    """
    ACI 318-19 Sec 17.6.3 — Pullout strength in tension.

    Npn = psi_c * 8 * Abrg * f'c   (headed cast-in anchor, Eq. 17.6.3.2.2)
    """
    Np_per = 8.0 * Abrg * f_c              # Single anchor (lbf)
    Npn_per = psi_c * Np_per
    phi_Npn = PHI_CONCRETE_TENSION * n * Npn_per

    return {
        "Np_per_lbf": Np_per,
        "Npn_per_lbf": Npn_per,
        "phi_Npn_total_lbf": phi_Npn,
        "psi_c_pullout": psi_c,
        "n_tension_bolts": n,
    }


def _steel_shear_capacity(Ase: float, futa: float, n: int) -> Dict[str, float]:
    """
    ACI 318-19 Sec 17.7.1 — Steel strength in shear.

    phi_Vsa = phi * n * 0.6 * Ase * futa
    """
    Vsa_per = 0.6 * Ase * futa
    phi_Vsa = PHI_STEEL_DUCTILE * n * Vsa_per

    return {
        "Vsa_per_lbf": Vsa_per,
        "phi_Vsa_total_lbf": phi_Vsa,
        "phi_steel_shear": PHI_STEEL_DUCTILE,
        "n_shear_bolts": n,
    }


def _concrete_breakout_shear(
    n: int,
    dia: float,
    hef: float,
    f_c: float,
    c_a1: float,
) -> Dict[str, float]:
    """
    ACI 318-19 Sec 17.7.2 — Concrete breakout strength in shear.

    Vb = min(7*(le/da)^0.2 * sqrt(da) * lambda * sqrt(f'c) * c_a1^1.5,
              9 * lambda * sqrt(f'c) * c_a1^1.5)
    AVco = 4.5 * c_a1^2  (single anchor)
    Vcbg = (AVc/AVco) * psi_ed_V * psi_c_V * psi_h_V * Vb

    Simplified here for interior anchor group (AVc = n * AVco).
    le = min(8*da, hef)  effective anchor shear length.
    """
    lam = 1.0
    le = min(8.0 * dia, hef)

    Vb1 = 7.0 * (le / dia) ** 0.2 * math.sqrt(dia) * lam * math.sqrt(f_c) * c_a1 ** 1.5
    Vb2 = 9.0 * lam * math.sqrt(f_c) * c_a1 ** 1.5
    Vb = min(Vb1, Vb2)

    AVco = 4.5 * c_a1 ** 2
    # For a group of n bolts in a row perpendicular to shear, multiply
    AVc = min(n * AVco, n * AVco)  # simplified: full group, no edge reduction

    psi_ed_V = 1.0   # no parallel edge effect assumed
    psi_c_V  = 1.0   # no supplemental reinforcement
    psi_h_V  = 1.0   # ha >= 1.5*c_a1 assumed

    Vcbg = (AVc / AVco) * psi_ed_V * psi_c_V * psi_h_V * Vb
    phi_Vcbg = PHI_CONCRETE_SHEAR * Vcbg

    return {
        "le_in": le,
        "Vb_lbf": Vb,
        "AVco_in2": AVco,
        "AVc_in2": AVc,
        "psi_ed_V": psi_ed_V,
        "psi_c_V": psi_c_V,
        "psi_h_V": psi_h_V,
        "Vcbg_lbf": Vcbg,
        "phi_Vcbg_lbf": phi_Vcbg,
        "phi_concrete_shear": PHI_CONCRETE_SHEAR,
    }


def _pryout_shear(
    phi_Ncbg: float,
    hef: float,
) -> Dict[str, float]:
    """
    ACI 318-19 Sec 17.7.3 — Concrete pryout strength in shear.

    phi_Vcp = phi * kcp * Ncbg
    kcp = 1.0 for hef < 2.5 in, else 2.0  (Sec 17.7.3.1)
    """
    kcp = 1.0 if hef < 2.5 else 2.0
    Ncbg_nom = phi_Ncbg / PHI_CONCRETE_TENSION  # recover nominal
    Vcp = kcp * Ncbg_nom
    phi_Vcp = PHI_PRYOUT * Vcp

    return {
        "kcp": kcp,
        "phi_Vcp_lbf": phi_Vcp,
        "phi_pryout": PHI_PRYOUT,
    }


# ---------------------------------------------------------------------------
# Base plate sizing  — AISC Design Guide 1
# ---------------------------------------------------------------------------

def _design_base_plate(
    P_lbf: float,
    M_inlb: float,
    F_lbf: float,
    col_d_in: float,
    col_bf_in: float,
    n_bolts: int,
    bolt_spacing_in: float,
    bolt_edge_in: float,
    f_c_psi: float,
    Fy_plate_psi: float,
) -> Dict[str, Any]:
    """
    AISC Design Guide 1 — Rectangular base plate sizing.

    Steps
    -----
    1. Required bearing area from axial load (compression governs).
    2. Set trial plate dimensions N x B considering bolt pattern.
    3. Compute cantilever projections m, n for plate bending.
    4. Required plate thickness from bending.

    Parameters
    ----------
    P_lbf          : axial compressive load (lbf; positive = compression)
    M_inlb         : overturning moment (in·lbf)
    F_lbf          : base shear (lbf)
    col_d_in       : column depth (in) — assumed HSS or W-shape depth
    col_bf_in      : column flange width (in)
    n_bolts        : total number of anchor bolts
    bolt_spacing_in: bolt pattern spacing (in) — bolts on square pattern
    bolt_edge_in   : bolt edge distance (in)
    f_c_psi        : concrete compressive strength (psi)
    Fy_plate_psi   : plate yield strength (psi)

    Returns
    -------
    dict of geometry + thickness results
    """
    phi_bearing = 0.65  # ACI 318-19 Sec 22.8

    # Minimum bearing area to resist axial load
    if P_lbf > 0:
        A1_req = P_lbf / (phi_bearing * 0.85 * f_c_psi)
    else:
        A1_req = 0.0  # uplift governs anchor design, not bearing

    # Minimum plate dimensions driven by bolt pattern
    # Bolt group occupies: bolt_spacing_in + 2*bolt_edge_in
    bp_size = bolt_spacing_in + 2.0 * bolt_edge_in

    # Minimum N and B: envelope of column size + overhang and bolt pattern
    N_min = max(col_d_in + 2.0 * 3.0, bp_size)   # 3-in min overhang each side
    B_min = max(col_bf_in + 2.0 * 3.0, bp_size)

    # Expand to satisfy bearing area
    if A1_req > N_min * B_min:
        scale = math.sqrt(A1_req / (N_min * B_min))
        N_min *= scale
        B_min *= scale

    # Round up to nearest 0.25-inch increment
    N = math.ceil(N_min / 0.25) * 0.25
    B = math.ceil(B_min / 0.25) * 0.25
    A1_prov = N * B

    # Bearing pressure under axial load
    fp = P_lbf / A1_prov if A1_prov > 0 else 0.0
    phi_fp_max = phi_bearing * 0.85 * f_c_psi

    # Cantilever projections (AISC DG1 Section 3.1)
    m = (N - 0.95 * col_d_in) / 2.0
    n = (B - 0.80 * col_bf_in) / 2.0
    lam_n_prime = 0.25 * math.sqrt(col_d_in * col_bf_in)  # DG1 Eq. 3.2
    ell = max(m, n, lam_n_prime)

    # Required plate thickness (AISC DG1 Eq. 3.3.4)
    # tp_req = ell * sqrt(2 * fp / (phi_plate * Fy))
    phi_plate = 0.90
    if fp > 0:
        tp_req = ell * math.sqrt(2.0 * fp / (phi_plate * Fy_plate_psi))
    else:
        # Uplift case: size from tension in bolts
        # Use simplified approach: tp from moment due to bolt tension
        T_per_bolt = abs(M_inlb) / (bolt_spacing_in * (n_bolts // 2)) if n_bolts >= 2 else 0
        moment_plate = T_per_bolt * bolt_edge_in
        tp_req = math.sqrt(4.0 * moment_plate / (phi_plate * Fy_plate_psi * B))

    tp = _round_up_plate_thickness(max(tp_req, 0.25))

    bearing_dcr = fp / phi_fp_max if phi_fp_max > 0 else 0.0

    return {
        "A1_req_in2": A1_req,
        "A1_prov_in2": A1_prov,
        "N_in": N,
        "B_in": B,
        "m_in": m,
        "n_in": n,
        "lambda_n_prime_in": lam_n_prime,
        "ell_in": ell,
        "fp_psi": fp,
        "phi_fp_max_psi": phi_fp_max,
        "tp_req_in": tp_req,
        "tp_in": tp,
        "bearing_dcr": bearing_dcr,
        "phi_bearing": phi_bearing,
        "phi_plate_bending": phi_plate,
        "Fy_plate_psi": Fy_plate_psi,
    }


# ---------------------------------------------------------------------------
# Main design function
# ---------------------------------------------------------------------------

def design_anchors(
    F_lbf: float,
    M_inlb: float,
    P_lbf: float = 0.0,
    f_c_psi: float = 3000.0,
    Fy_plate_psi: float = 36_000.0,
    bolt_grade: str = "F1554-36",
    n_bolts: int = 4,
    hef_in: Optional[float] = None,
    col_d_in: float = 8.0,
    col_bf_in: float = 8.0,
    edge_dist_in: Optional[float] = None,
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """
    Design anchor bolts and base plate per ACI 318-19 Ch. 17 and AISC DG1.

    The function iterates over bolt sizes (smallest first) and bolt counts
    until all strength checks pass. If no configuration passes, raises
    ValueError.

    Parameters
    ----------
    F_lbf       : horizontal base shear (lbf)
    M_inlb      : overturning moment at base (in·lbf)
    P_lbf       : axial load at base, positive=compression, negative=uplift (lbf)
    f_c_psi     : concrete compressive strength (psi)  [default 3000]
    Fy_plate_psi: plate steel yield strength (psi)     [default 36 ksi]
    bolt_grade  : anchor bolt material grade key       [default "F1554-36"]
    n_bolts     : starting number of bolts (4, 6, 8)   [default 4]
    hef_in      : effective embedment depth (in); if None, auto-sized as 12*dia
    col_d_in    : column depth (in) for base plate sizing [default 8 in]
    col_bf_in   : column flange/tube width (in)          [default 8 in]
    edge_dist_in: bolt edge distance (in); if None, 6*dia

    Returns
    -------
    geometry : dict
        "pattern"         — bolt pattern label
        "dia"             — bolt diameter label
        "dia_in"          — bolt diameter (float, in)
        "n_bolts"         — number of anchor bolts
        "embed_in"        — effective embedment depth (in)
        "bolt_spacing_in" — center-to-center bolt spacing (in)
        "edge_dist_in"    — edge distance (in)
        "plate_N_in"      — base plate length N (in)
        "plate_B_in"      — base plate width B (in)
        "plate_t_in"      — base plate thickness (in)
        "bolt_grade"      — material designation
        "futa_psi"        — anchor tensile strength (psi)
        "Ase_in2"         — effective stress area (in^2)
        "ref"             — compact design reference string
        "governing_mode"  — controlling failure mode label
        "audit"           — nested dict of ALL intermediate values

    checks : dict
        Demand/capacity ratios for each limit state (< 1.0 = pass):
        "steel_tension_dcr"
        "breakout_tension_dcr"
        "pullout_tension_dcr"
        "steel_shear_dcr"
        "breakout_shear_dcr"
        "pryout_shear_dcr"
        "interaction_dcr"
        "bearing_dcr"

    Raises
    ------
    ValueError
        If bolt_grade is not in the database, or if no bolt size/count
        combination satisfies all limit states within the available range.
    """
    if bolt_grade not in BOLT_GRADES:
        raise ValueError(
            f"Unknown bolt_grade '{bolt_grade}'. "
            f"Valid options: {sorted(BOLT_GRADES)}"
        )

    futa_psi, fy_bolt_psi, grade_desc = BOLT_GRADES[bolt_grade]

    # Demand decomposition
    # Treat bolt group as two rows: tension side / compression side
    # Bolts in tension resist M - P*e (net uplift side)
    # For simplicity use n/2 bolts in tension for 4-bolt pattern
    # (conservative: all bolts share shear)
    n_tension = n_bolts // 2  # bolts on tension side
    n_shear   = n_bolts       # all bolts share shear

    # Try each bolt size until all checks pass
    for dia, Ase, Abrg in BOLT_SIZES:
        # Embedment depth — default 12*dia per ACI 318-19 commentary
        hef = hef_in if hef_in is not None else max(12.0 * dia, 6.0)
        # Edge distance — minimum 6*dia per ACI 318-19 Sec 17.9.1
        c_min = MIN_EDGE_DIST_MULT * dia
        c_a1 = edge_dist_in if edge_dist_in is not None else max(c_min, 3.0 * hef / 2.0)

        # Bolt spacing: for 4-bolt square pattern, spacing governs plate width
        bolt_spacing = max(3.0 * dia, 4.0)   # minimum per ACI / practical minimum 4 in

        # ---- Tension demand on anchors ----
        # Max bolt tension from moment + axial (lbf)
        # Simple lever arm model: T_max = M / (lever_arm) + P_uplift / n_tension
        lever_arm = bolt_spacing    # distance between tension/compression bolt rows
        if lever_arm < 1e-6:
            lever_arm = bolt_spacing + 1e-3

        T_demand = M_inlb / lever_arm + max(-P_lbf, 0.0) / n_tension

        # ---- Shear demand ----
        V_demand = F_lbf  # all bolts share shear

        # ---- ACI 318-19 capacity calculations ----
        # Tension: steel
        st = _steel_tension_capacity(Ase, futa_psi, n_tension)
        phi_Nsa = st["phi_Nsa_total_lbf"]

        # Tension: concrete breakout (ACI 318-19 Sec 17.6.2)
        ANco, ANc = _concrete_breakout_area(hef, c_a1)
        # psi_ed_N: edge distance modification (Sec 17.6.2.4)
        if c_a1 >= 1.5 * hef:
            psi_ed_N = 1.0
        else:
            psi_ed_N = 0.7 + 0.3 * c_a1 / (1.5 * hef)   # Eq. 17.6.2.4.1b

        cb = _concrete_breakout_tension(
            n_tension, hef, f_c_psi, ANco, ANc, psi_ed=psi_ed_N
        )
        phi_Ncbg = cb["phi_Ncbg_lbf"]

        # Tension: pullout (ACI 318-19 Sec 17.6.3)
        pu = _pullout_tension(n_tension, Abrg, f_c_psi)
        phi_Npn = pu["phi_Npn_total_lbf"]

        # Governing tension capacity
        phi_Tn = min(phi_Nsa, phi_Ncbg, phi_Npn)
        if phi_Nsa == phi_Tn:
            tension_mode = "steel_tension"
        elif phi_Ncbg == phi_Tn:
            tension_mode = "concrete_breakout_tension"
        else:
            tension_mode = "pullout"

        # Shear: steel (ACI 318-19 Sec 17.7.1)
        sv = _steel_shear_capacity(Ase, futa_psi, n_shear)
        phi_Vsa = sv["phi_Vsa_total_lbf"]

        # Shear: concrete breakout (ACI 318-19 Sec 17.7.2)
        sbv = _concrete_breakout_shear(n_shear, dia, hef, f_c_psi, c_a1)
        phi_Vcbg = sbv["phi_Vcbg_lbf"]

        # Shear: pryout (ACI 318-19 Sec 17.7.3)
        pv = _pryout_shear(phi_Ncbg, hef)
        phi_Vcp = pv["phi_Vcp_lbf"]

        # Governing shear capacity
        phi_Vn = min(phi_Vsa, phi_Vcbg, phi_Vcp)
        if phi_Vsa == phi_Vn:
            shear_mode = "steel_shear"
        elif phi_Vcbg == phi_Vn:
            shear_mode = "concrete_breakout_shear"
        else:
            shear_mode = "pryout"

        # ---- Demand/capacity ratios ----
        st_dcr  = T_demand / phi_Nsa  if phi_Nsa  > 0 else float("inf")
        cbt_dcr = T_demand / phi_Ncbg if phi_Ncbg > 0 else float("inf")
        pu_dcr  = T_demand / phi_Npn  if phi_Npn  > 0 else float("inf")
        ssv_dcr = V_demand / phi_Vsa  if phi_Vsa  > 0 else float("inf")
        cbv_dcr = V_demand / phi_Vcbg if phi_Vcbg > 0 else float("inf")
        pry_dcr = V_demand / phi_Vcp  if phi_Vcp  > 0 else float("inf")

        # ---- Combined tension + shear interaction (ACI 318-19 Sec 17.8) ----
        # Full-strength zone: skip interaction if either demand is small
        tu_ratio = T_demand / phi_Tn if phi_Tn > 0 else float("inf")
        vu_ratio = V_demand / phi_Vn if phi_Vn > 0 else float("inf")

        if tu_ratio <= 0.2:
            interaction_dcr = vu_ratio  # tension insignificant
        elif vu_ratio <= 0.2:
            interaction_dcr = tu_ratio  # shear insignificant
        else:
            interaction_dcr = tu_ratio ** INTERACTION_EXPONENT + vu_ratio ** INTERACTION_EXPONENT

        # ---- Base plate ----
        bp = _design_base_plate(
            P_lbf, M_inlb, F_lbf,
            col_d_in, col_bf_in,
            n_bolts, bolt_spacing, c_a1,
            f_c_psi, Fy_plate_psi,
        )
        bearing_dcr = bp["bearing_dcr"]

        # ---- All-pass check ----
        all_dcrs = [st_dcr, cbt_dcr, pu_dcr, ssv_dcr, cbv_dcr, pry_dcr, interaction_dcr, bearing_dcr]
        if all(d <= 1.0 for d in all_dcrs):
            # Design passes — build result dicts
            governing_mode_t = tension_mode
            governing_mode_v = shear_mode
            max_dcr = max(all_dcrs)
            dcr_labels = [
                "steel_tension", "concrete_breakout_tension", "pullout",
                "steel_shear", "concrete_breakout_shear", "pryout",
                "interaction", "bearing",
            ]
            governing_mode = dcr_labels[all_dcrs.index(max_dcr)]

            ref = (
                f"{n_bolts}-bolts-{_bolt_label(dia)}-"
                f"e{hef:.2f}in-N{bp['N_in']:.2f}xB{bp['B_in']:.2f}x"
                f"t{bp['tp_in']:.4f}in-{bolt_grade}"
            )

            geometry: Dict[str, Any] = {
                "pattern": f"{n_bolts}-bolt-square",
                "dia": _bolt_label(dia),
                "dia_in": dia,
                "n_bolts": n_bolts,
                "embed_in": hef,
                "bolt_spacing_in": bolt_spacing,
                "edge_dist_in": c_a1,
                "c_a1_in": c_a1,
                "plate_N_in": bp["N_in"],
                "plate_B_in": bp["B_in"],
                "plate_t_in": bp["tp_in"],
                "plate_t_req_in": bp["tp_req_in"],
                "bolt_grade": bolt_grade,
                "bolt_grade_desc": grade_desc,
                "futa_psi": futa_psi,
                "fy_bolt_psi": fy_bolt_psi,
                "Ase_in2": Ase,
                "Abrg_in2": Abrg,
                "hef_in": hef,
                "f_c_psi": f_c_psi,
                "Fy_plate_psi": Fy_plate_psi,
                "ref": ref,
                "governing_mode": governing_mode,
                "code_refs": {
                    "steel_tension":  "ACI 318-19 Sec 17.6.1",
                    "breakout_tension": "ACI 318-19 Sec 17.6.2",
                    "pullout":        "ACI 318-19 Sec 17.6.3",
                    "steel_shear":    "ACI 318-19 Sec 17.7.1",
                    "breakout_shear": "ACI 318-19 Sec 17.7.2",
                    "pryout":         "ACI 318-19 Sec 17.7.3",
                    "interaction":    "ACI 318-19 Sec 17.8.3",
                    "base_plate":     "AISC DG1 Sec 3.1",
                },
                "audit": {
                    "demands": {
                        "T_demand_lbf": T_demand,
                        "V_demand_lbf": V_demand,
                        "P_lbf": P_lbf,
                        "M_inlb": M_inlb,
                        "F_lbf": F_lbf,
                        "lever_arm_in": lever_arm,
                        "n_tension": n_tension,
                        "n_shear": n_shear,
                    },
                    "steel_tension":  st,
                    "breakout_tension": cb,
                    "pullout":        pu,
                    "steel_shear":    sv,
                    "breakout_shear": sbv,
                    "pryout":         pv,
                    "base_plate":     bp,
                    "capacities": {
                        "phi_Nsa_lbf":  phi_Nsa,
                        "phi_Ncbg_lbf": phi_Ncbg,
                        "phi_Npn_lbf":  phi_Npn,
                        "phi_Tn_gov_lbf": phi_Tn,
                        "tension_governing_mode": governing_mode_t,
                        "phi_Vsa_lbf":  phi_Vsa,
                        "phi_Vcbg_lbf": phi_Vcbg,
                        "phi_Vcp_lbf":  phi_Vcp,
                        "phi_Vn_gov_lbf": phi_Vn,
                        "shear_governing_mode": governing_mode_v,
                    },
                    "interaction": {
                        "tu_ratio": tu_ratio,
                        "vu_ratio": vu_ratio,
                        "interaction_dcr": interaction_dcr,
                        "exponent": INTERACTION_EXPONENT,
                        "ref": "ACI 318-19 Sec 17.8.3",
                    },
                },
            }

            checks: Dict[str, float] = {
                "steel_tension_dcr":    round(st_dcr, 4),
                "breakout_tension_dcr": round(cbt_dcr, 4),
                "pullout_tension_dcr":  round(pu_dcr, 4),
                "steel_shear_dcr":      round(ssv_dcr, 4),
                "breakout_shear_dcr":   round(cbv_dcr, 4),
                "pryout_shear_dcr":     round(pry_dcr, 4),
                "interaction_dcr":      round(interaction_dcr, 4),
                "bearing_dcr":          round(bearing_dcr, 4),
                # Legacy keys for backward compatibility
                "T_sf":  round(1.0 / st_dcr, 3)  if st_dcr  > 0 else float("inf"),
                "V_sf":  round(1.0 / ssv_dcr, 3) if ssv_dcr > 0 else float("inf"),
            }

            return geometry, checks

    # If we exhaust all bolt sizes without passing, raise
    raise ValueError(
        f"No bolt configuration in the available size range "
        f"({BOLT_SIZES[0][0]:.3f} – {BOLT_SIZES[-1][0]:.3f} in) "
        f"satisfies all ACI 318-19 Ch. 17 limit states for the given loads:\n"
        f"  F={F_lbf:.1f} lbf  M={M_inlb:.1f} in·lbf  P={P_lbf:.1f} lbf\n"
        f"Consider increasing n_bolts, embedment depth, or concrete strength."
    )
