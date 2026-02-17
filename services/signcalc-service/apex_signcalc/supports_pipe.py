"""
AISC 360-22 LRFD member design — production-grade checks for sign support structures.

Covers:
  Chapter E  — Compression members (buckling, slenderness)
  Chapter F  — Flexure (yielding, LTB, local buckling, pipe/HSS/W-shape provisions)
  Chapter G  — Shear
  Chapter H  — Combined loading interaction equations H1-1a / H1-1b
  Serviceability — Deflection checks (L/120 for sign supports)

All forces / moments in US customary:
  forces  : lbf
  moments : in-lb
  lengths : in
  stresses: psi (internally converted from ksi section properties)

Reference:
  AISC 360-22 "Specification for Structural Steel Buildings", 2022 edition
  AISC Steel Construction Manual, 16th Edition

PE-reviewable: every intermediate quantity is returned in the audit dict
with key names that directly match AISC equation numbers.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from .sections import Section, load_catalog

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------
E_PSI: float = 29_000_000.0          # Modulus of elasticity, psi  (AISC Sec. A3.1a)
E_KSI: float = 29_000.0              # Same value in ksi
G_PSI: float = 11_200_000.0          # Shear modulus, psi
PHI_B: float = 0.90                   # Flexure  LRFD resistance factor (AISC F1)
PHI_V: float = 1.00                   # Shear    LRFD resistance factor (AISC G2.1, rolled I)
PHI_C: float = 0.90                   # Compression LRFD resistance factor (AISC E1)
DEF_LIMIT: float = 1.0 / 120.0       # L/120 serviceability limit for sign supports

# Slenderness limits (AISC E2 note / B7)
KLR_MAX_COMPRESSION: float = 200.0
LR_MAX_TENSION: float = 300.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe(x: float, fallback: float = 1e-9) -> float:
    """Guard against zero denominators."""
    return x if abs(x) > 1e-12 else fallback


# ---------------------------------------------------------------------------
# Chapter F — Flexure
# ---------------------------------------------------------------------------

def _classify_flange_local_buckling(sec: Section, Fy_psi: float) -> str:
    """
    Classify flange for local buckling per AISC Table B4.1b (W-shapes).
    Returns 'compact', 'noncompact', or 'slender'.
    """
    if sec.tf_in <= 0 or sec.bf_in <= 0:
        return "compact"
    lam = (sec.bf_in / 2.0) / _safe(sec.tf_in)
    lam_pf = 0.38 * math.sqrt(E_PSI / _safe(Fy_psi))        # Table B4.1b Case 10
    lam_rf = 1.00 * math.sqrt(E_PSI / _safe(Fy_psi))        # Table B4.1b Case 10
    if lam <= lam_pf:
        return "compact"
    if lam <= lam_rf:
        return "noncompact"
    return "slender"


def _classify_web_local_buckling(sec: Section, Fy_psi: float) -> str:
    """
    Classify web for local buckling per AISC Table B4.1b (W-shapes).
    Returns 'compact', 'noncompact', or 'slender'.
    """
    if sec.tw_in <= 0 or sec.d_in <= 0:
        return "compact"
    h_tw = (sec.d_in - 2.0 * sec.tf_in) / _safe(sec.tw_in)
    lam_pw = 3.76 * math.sqrt(E_PSI / _safe(Fy_psi))        # Table B4.1b Case 15 (pure bending)
    lam_rw = 5.70 * math.sqrt(E_PSI / _safe(Fy_psi))        # Table B4.1b Case 15
    if h_tw <= lam_pw:
        return "compact"
    if h_tw <= lam_rw:
        return "noncompact"
    return "slender"


def _Lp_Lr_W(sec: Section, Fy_psi: float) -> Tuple[float, float]:
    """
    Limiting unbraced lengths Lp and Lr for W-shapes.
    AISC 360-22 Eq. F2-5 and F2-6.

    Returns (Lp_in, Lr_in).
    """
    ry = _safe(sec.ry_in)
    # Eq. F2-5:  Lp = 1.76 * ry * sqrt(E/Fy)
    Lp = 1.76 * ry * math.sqrt(E_PSI / _safe(Fy_psi))

    # Eq. F2-6:  Lr = 1.95 * rts * (E/(0.7*Fy)) * sqrt(J*c/(Sx*ho) + sqrt((J*c/(Sx*ho))^2 + 6.76*(0.7*Fy/E)^2))
    # rts^2 = sqrt(Iy * Cw) / Sx   (AISC Commentary F2, also Eq. F2-7)
    Iy = _safe(sec.Iy_in4)
    Cw = max(sec.Cw_in6, 0.0)
    Sx = _safe(sec.Sx_in3)
    J  = _safe(sec.J_in4)
    # c = 1.0 for doubly symmetric I-shapes (AISC F2)
    c  = 1.0
    # approximate ho as d - tf (distance between flange centroids)
    ho = max(sec.d_in - sec.tf_in, sec.d_in * 0.9)

    if Cw > 0:
        rts2 = math.sqrt(Iy * Cw) / Sx
    else:
        # Degenerate: use ry
        rts2 = ry

    rts = math.sqrt(rts2) if rts2 > 0 else ry

    term = (J * c) / (_safe(Sx * ho))
    inner = term + math.sqrt(term ** 2 + 6.76 * (0.7 * Fy_psi / _safe(E_PSI)) ** 2)
    inner = max(inner, 0.0)
    Lr = 1.95 * rts * (E_PSI / (0.7 * _safe(Fy_psi))) * math.sqrt(inner)

    return Lp, Lr


def _Mn_W_shape(
    sec: Section,
    Fy_psi: float,
    Lb_in: float,
    Cb: float,
) -> Tuple[float, Dict[str, object]]:
    """
    Nominal flexural strength for doubly symmetric W-shapes.
    AISC 360-22 Chapter F2 (yielding + LTB) and F3 (flange local buckling).

    Returns (Mn_inlb, audit_dict).
    """
    Zx = _safe(sec.Zx_in3)
    Sx = _safe(sec.Sx_in3)
    Mp = Fy_psi * Zx                                         # Eq. F2-1

    flange_class = _classify_flange_local_buckling(sec, Fy_psi)
    web_class    = _classify_web_local_buckling(sec, Fy_psi)
    Lp, Lr       = _Lp_Lr_W(sec, Fy_psi)

    # --- LTB limit state ---
    if Lb_in <= Lp:
        Mn_ltb = Mp
        ltb_state = "no_LTB"
    elif Lb_in <= Lr:
        # Eq. F2-2: inelastic LTB
        Mn_ltb = Cb * (Mp - (Mp - 0.7 * Fy_psi * Sx) * (Lb_in - Lp) / _safe(Lr - Lp))
        Mn_ltb = min(Mn_ltb, Mp)
        ltb_state = "inelastic_LTB"
    else:
        # Eq. F2-3: elastic LTB
        J  = _safe(sec.J_in4)
        c  = 1.0
        Iy = _safe(sec.Iy_in4)
        Cw = max(sec.Cw_in6, 0.0)
        Sx_  = _safe(sec.Sx_in3)
        ry   = _safe(sec.ry_in)
        ho   = max(sec.d_in - sec.tf_in, sec.d_in * 0.9)
        # rts from Eq. F2-7
        if Cw > 0:
            rts2 = math.sqrt(Iy * Cw) / Sx_
        else:
            rts2 = ry
        rts = math.sqrt(rts2) if rts2 > 0 else ry
        Fcr = (
            (Cb * math.pi ** 2 * E_PSI) / ((Lb_in / _safe(rts)) ** 2)
            * math.sqrt(1.0 + 0.078 * (J * c / _safe(Sx_ * ho)) * (Lb_in / _safe(rts)) ** 2)
        )
        Mn_ltb = Fcr * Sx_
        Mn_ltb = min(Mn_ltb, Mp)
        ltb_state = "elastic_LTB"

    # --- Flange local buckling (AISC F3) ---
    if flange_class == "compact":
        Mn_flb = Mp
        flb_state = "compact_flange"
    elif flange_class == "noncompact":
        lam    = (sec.bf_in / 2.0) / _safe(sec.tf_in)
        lam_pf = 0.38 * math.sqrt(E_PSI / _safe(Fy_psi))
        lam_rf = 1.00 * math.sqrt(E_PSI / _safe(Fy_psi))
        # Eq. F3-1
        Mn_flb = Mp - (Mp - 0.7 * Fy_psi * Sx) * (lam - lam_pf) / _safe(lam_rf - lam_pf)
        flb_state = "noncompact_flange_FLB"
    else:
        # slender flange — Eq. F3-2
        kc  = 4.0 / math.sqrt(max((sec.d_in - 2.0 * sec.tf_in) / _safe(sec.tw_in), 0.35))
        kc  = max(0.35, min(kc, 0.76))
        Mn_flb = (0.9 * E_PSI * kc * Sx) / ((sec.bf_in / 2.0) / _safe(sec.tf_in)) ** 2
        flb_state = "slender_flange_FLB"

    Mn = min(Mn_ltb, Mn_flb)

    audit = {
        "Mp_inlb": Mp,
        "Lp_in": Lp,
        "Lr_in": Lr,
        "ltb_state": ltb_state,
        "Mn_LTB_inlb": Mn_ltb,
        "flange_class": flange_class,
        "web_class": web_class,
        "flb_state": flb_state,
        "Mn_FLB_inlb": Mn_flb,
        "Mn_inlb": Mn,
    }
    return Mn, audit


def _Mn_pipe_hss_round(
    sec: Section,
    Fy_psi: float,
) -> Tuple[float, Dict[str, object]]:
    """
    Nominal flexural strength for round pipe / HSS.
    AISC 360-22 Section F8.

    D/t limits per Table B4.1b Case 20:
      compact     : D/t <= 0.07 * E/Fy
      noncompact  : D/t <= 0.31 * E/Fy
      slender     : D/t >  0.31 * E/Fy

    Returns (Mn_inlb, audit_dict).
    """
    D  = _safe(sec.d_in)          # outer diameter (OD stored in d_in)
    t  = _safe(sec.tw_in)         # wall thickness
    Fy = Fy_psi
    Zx = _safe(sec.Zx_in3)
    Sx = _safe(sec.Sx_in3)
    Mp = Fy * Zx                  # Eq. F8-1 (upper bound)

    ratio     = D / t
    lam_p     = 0.07  * E_PSI / Fy                           # Table B4.1b compact limit
    lam_r     = 0.31  * E_PSI / Fy                           # Table B4.1b noncompact limit

    if ratio <= lam_p:
        Mn        = Mp
        sect_class = "compact"
    elif ratio <= lam_r:
        # Eq. F8-2: Mn = (0.021*E/( D/t) + Fy) * Sx
        Mn        = (0.021 * E_PSI / ratio + Fy) * Sx        # Eq. F8-2
        Mn        = min(Mn, Mp)
        sect_class = "noncompact"
    else:
        # Slender — Eq. F8-3: Fcr = 0.33*E / (D/t)
        Fcr       = 0.33 * E_PSI / ratio                      # Eq. F8-3
        Mn        = Fcr * Sx
        sect_class = "slender"

    audit = {
        "D_in": D,
        "t_in": t,
        "D_over_t": ratio,
        "lam_p_F8": lam_p,
        "lam_r_F8": lam_r,
        "section_class": sect_class,
        "Mp_inlb": Mp,
        "Mn_inlb": Mn,
    }
    return Mn, audit


def _Mn_hss_square(
    sec: Section,
    Fy_psi: float,
) -> Tuple[float, Dict[str, object]]:
    """
    Nominal flexural strength for square / rectangular HSS.
    AISC 360-22 Section F7.

    Flange (compression) D/t limits per Table B4.1b Case 17:
      compact    : b/t <= 1.12 * sqrt(E/Fy)
      noncompact : b/t <= 1.40 * sqrt(E/Fy)
      slender    : b/t >  1.40 * sqrt(E/Fy)

    Returns (Mn_inlb, audit_dict).
    """
    b  = sec.bf_in - 3.0 * sec.tw_in          # flat width of compression flange
    t  = _safe(sec.tw_in)
    Fy = Fy_psi
    Zx = _safe(sec.Zx_in3)
    Sx = _safe(sec.Sx_in3)
    Mp = Fy * Zx                               # Eq. F7-1

    b_t       = max(b, 0.0) / t
    lam_p     = 1.12 * math.sqrt(E_PSI / Fy)  # Table B4.1b Case 17
    lam_r     = 1.40 * math.sqrt(E_PSI / Fy)  # Table B4.1b Case 17

    if b_t <= lam_p:
        Mn        = Mp
        sect_class = "compact"
    elif b_t <= lam_r:
        # Eq. F7-2
        Mn        = Mp - (Mp - Fy * Sx) * (3.57 * b_t * math.sqrt(Fy / _safe(E_PSI)) - 4.0)
        Mn        = min(max(Mn, 0.0), Mp)
        sect_class = "noncompact"
    else:
        # Slender — Eq. F7-3 / effective section
        be   = 1.92 * t * math.sqrt(E_PSI / Fy) * (1.0 - 0.38 / (b_t * math.sqrt(Fy / _safe(E_PSI))))
        be   = min(be, b)
        # Approximate effective Sx reduction (b_eff/b ratio applied to Sx)
        Seff = Sx * (be / max(b, t))
        Mn   = Fy * Seff
        sect_class = "slender"

    audit = {
        "b_t_F7": b_t,
        "lam_p_F7": lam_p,
        "lam_r_F7": lam_r,
        "section_class": sect_class,
        "Mp_inlb": Mp,
        "Mn_inlb": Mn,
    }
    return Mn, audit


# ---------------------------------------------------------------------------
# Chapter G — Shear
# ---------------------------------------------------------------------------

def _phi_Vn(sec: Section, Fy_psi: float) -> Tuple[float, Dict[str, object]]:
    """
    Design shear strength phi*Vn.
    AISC 360-22 Section G2.1 (I-shapes) or G4 (round HSS/pipe) or G5 (rect HSS).

    Returns (phiVn_lbf, audit_dict).
    """
    family = sec.family.lower()
    Fy = Fy_psi

    if family == "w":
        # AISC G2.1 — rolled I-shapes
        Aw = sec.d_in * sec.tw_in                             # Eq. G2-2 (approx; web area = d*tw)
        # Cv1 check: h/tw <= 2.24*sqrt(E/Fy)
        h_tw = (sec.d_in - 2.0 * sec.tf_in) / _safe(sec.tw_in)
        limit = 2.24 * math.sqrt(E_PSI / _safe(Fy))
        if h_tw <= limit:
            Cv1    = 1.0                                       # Eq. G2-2 condition
            phi_v  = 1.00
        else:
            # kv = 5.34 (no transverse stiffeners)
            kv    = 5.34
            h_tw_ = h_tw
            lim1  = 1.10 * math.sqrt(kv * E_PSI / _safe(Fy))
            if h_tw_ <= lim1:
                Cv1  = 1.0
            elif h_tw_ <= 1.37 * math.sqrt(kv * E_PSI / _safe(Fy)):
                Cv1  = 1.10 * math.sqrt(kv * E_PSI / _safe(Fy)) / _safe(h_tw_)
            else:
                Cv1  = 1.51 * E_PSI * kv / (_safe(h_tw_ ** 2) * Fy)
            phi_v  = 0.90

        Vn     = 0.6 * Fy * Aw * Cv1                          # Eq. G2-1
        phiVn  = phi_v * Vn
        audit  = {
            "Aw_in2": Aw,
            "h_over_tw": h_tw,
            "Cv1": Cv1,
            "phi_v": phi_v,
            "Vn_G2_lbf": Vn,
        }

    elif family == "pipe":
        # AISC G4 — round HSS/pipe
        # Vn = 0.6 * Fy * Ag / 2   (approximate; exact uses Fcr per G4)
        Ag    = _safe(sec.A_in2)
        D     = _safe(sec.d_in)
        t     = _safe(sec.tw_in)
        Lv    = 1.0   # effective length ratio (conservative = 1)
        # Fcr from G4-1 (elastic shear buckling) or G4-2 (inelastic)
        kv    = 1.60 / (Lv / (D / t) ** 0.5)  # simplified, conservative
        kv    = max(kv, 0.5)
        Fcr_g4_1 = 0.78 * E_PSI / ((D / t) ** 1.5)           # Eq. G4-1
        Fcr_g4_2 = 1.60 * E_PSI / (math.sqrt(Lv / D) * (D / t) ** 1.25)  # Eq. G4-2
        Fcr_max  = 0.6 * Fy
        Fcr      = min(max(Fcr_g4_1, Fcr_g4_2), Fcr_max)
        Vn    = Fcr * Ag / 2.0                                 # Eq. G4-3 (Aw = Ag/2 for round)
        phiVn = 0.90 * Vn
        audit = {
            "Ag_in2": Ag,
            "D_over_t": D / t,
            "Fcr_G4_psi": Fcr,
            "phi_v": 0.90,
            "Vn_G4_lbf": Vn,
        }

    else:
        # AISC G5 — rectangular HSS / square HSS
        # 2h*t shear area (both webs)
        Aw    = 2.0 * (sec.d_in - 2.0 * sec.tw_in) * sec.tw_in
        Aw    = max(Aw, sec.A_in2 * 0.5)
        Cv2   = 1.0                                            # conservative; kv = 5 for unstiffened
        Vn    = 0.6 * Fy * Aw * Cv2                           # Eq. G5-1
        phiVn = 0.90 * Vn
        audit = {
            "Aw_in2": Aw,
            "Cv2": Cv2,
            "phi_v": 0.90,
            "Vn_G5_lbf": Vn,
        }

    return phiVn, audit


# ---------------------------------------------------------------------------
# Chapter E — Compression
# ---------------------------------------------------------------------------

def _phi_Pn(
    sec: Section,
    Fy_psi: float,
    K: float,
    L_in: float,
) -> Tuple[float, Dict[str, object]]:
    """
    Design compressive strength phi*Pn.
    AISC 360-22 Section E3 (flexural buckling).

    Parameters
    ----------
    K     : effective length factor
    L_in  : unbraced length, in

    Returns (phiPn_lbf, audit_dict).
    """
    Ag   = _safe(sec.A_in2)
    r    = _safe(min(sec.rx_in, sec.ry_in))  # governing (minimum) radius of gyration
    Fy   = Fy_psi

    KL_r = K * L_in / r                      # governing slenderness ratio

    # Slenderness warning flag
    slender_flag = KL_r > KLR_MAX_COMPRESSION

    Fe = math.pi ** 2 * E_PSI / _safe(KL_r ** 2)              # Eq. E3-4

    limit = 4.71 * math.sqrt(E_PSI / _safe(Fy))               # Eq. E3-2 breakpoint
    if KL_r <= limit:
        Fcr = (0.658 ** (Fy / _safe(Fe))) * Fy                 # Eq. E3-2
        buckling_mode = "inelastic"
    else:
        Fcr = 0.877 * Fe                                        # Eq. E3-3
        buckling_mode = "elastic"

    Pn    = Fcr * Ag                                            # Eq. E3-1
    phiPn = PHI_C * Pn

    audit = {
        "KL_over_r": KL_r,
        "KLr_limit_200": KLR_MAX_COMPRESSION,
        "slenderness_exceeded": slender_flag,
        "Fe_psi": Fe,
        "Fcr_psi": Fcr,
        "buckling_mode": buckling_mode,
        "Pn_lbf": Pn,
        "phiPn_lbf": phiPn,
    }
    return phiPn, audit


# ---------------------------------------------------------------------------
# Deflection
# ---------------------------------------------------------------------------

def _deflection(
    V_lbf: float,
    L_in: float,
    Ix_in4: float,
    load_type: str,
    w_lbpin: float = 0.0,
) -> Tuple[float, str]:
    """
    Compute maximum elastic deflection.

    load_type options:
      'cantilever'       — tip point load:  delta = P*L^3 / (3*E*I)
      'cantilever_udl'   — cantilever UDL:  delta = w*L^4 / (8*E*I)
      'simple_point'     — midspan point:   delta = P*L^3 / (48*E*I)
      'simple_udl'       — simple UDL:      delta = 5*w*L^4 / (384*E*I)
      'fixed_point'      — fixed-fixed pt:  delta = P*L^3 / (192*E*I)

    Returns (delta_in, formula_label).
    """
    EI = E_PSI * _safe(Ix_in4)
    lt = load_type.lower()

    if lt == "cantilever":
        delta = V_lbf * L_in ** 3 / (3.0 * EI)
        label = "P*L^3/(3EI)"
    elif lt == "cantilever_udl":
        delta = w_lbpin * L_in ** 4 / (8.0 * EI)
        label = "w*L^4/(8EI)"
    elif lt == "simple_point":
        delta = V_lbf * L_in ** 3 / (48.0 * EI)
        label = "P*L^3/(48EI)"
    elif lt == "simple_udl":
        delta = 5.0 * w_lbpin * L_in ** 4 / (384.0 * EI)
        label = "5wL^4/(384EI)"
    elif lt == "fixed_point":
        delta = V_lbf * L_in ** 3 / (192.0 * EI)
        label = "P*L^3/(192EI)"
    else:
        # Default: cantilever (conservative for sign supports)
        delta = V_lbf * L_in ** 3 / (3.0 * EI)
        label = "P*L^3/(3EI) [default]"

    return delta, label


# ---------------------------------------------------------------------------
# Primary public API
# ---------------------------------------------------------------------------

def check_section(
    sec: Section,
    M_inlb: float,
    V_lbf: float,
    L_in: float,
    P_lbf: float = 0.0,
    K: float = 1.0,
    Cb: float = 1.0,
    load_type: str = "cantilever",
    My_inlb: float = 0.0,
    w_lbpin: float = 0.0,
) -> Tuple[bool, Dict]:
    """
    Full AISC 360-22 LRFD member check for sign support structures.

    Parameters
    ----------
    sec       : Section dataclass from sections.py
    M_inlb    : Required flexural strength (strong axis), in-lb
    V_lbf     : Required shear force, lbf
    L_in      : Member length (also used as unbraced length Lb), in
    P_lbf     : Required axial compressive force, lbf (default 0)
    K         : Effective length factor for compression (default 1.0)
    Cb        : Moment gradient factor (default 1.0, conservative)
    load_type : Deflection formula key — 'cantilever', 'simple_point',
                'simple_udl', 'cantilever_udl', 'fixed_point'
    My_inlb   : Required weak-axis moment, in-lb (for biaxial interaction)
    w_lbpin   : Distributed load intensity for UDL deflection, lbf/in

    Returns
    -------
    (pass: bool, audit: dict)
        pass  — True if all limit-state checks pass
        audit — Complete intermediate-value dictionary (PE-reviewable)

    Limit states checked
    --------------------
    F2 / F7 / F8  Flexure (yielding, LTB, local buckling)
    G2.1 / G4 / G5  Shear
    E3            Compression (flexural buckling)
    H1-1a / H1-1b  Combined loading interaction
    Serviceability  Deflection <= L/120
    """
    Fy_psi = sec.Fy_ksi * 1_000.0
    Lb_in  = L_in       # unbraced length = full member length (conservative)

    result: Dict = {
        "section": sec.designation,
        "family": sec.family,
        "Fy_ksi": sec.Fy_ksi,
        "weight_plf": sec.weight_plf,
    }

    # ----------------------------------------------------------------
    # 1. Flexure — Chapter F
    # ----------------------------------------------------------------
    family = sec.family.lower()
    if family == "w":
        Mn, flex_audit = _Mn_W_shape(sec, Fy_psi, Lb_in, Cb)
    elif family == "pipe":
        Mn, flex_audit = _Mn_pipe_hss_round(sec, Fy_psi)
    elif family in ("hss_square", "hss_rect"):
        Mn, flex_audit = _Mn_hss_square(sec, Fy_psi)
    else:
        # Generic fallback: yielding only, phi*Mp
        Mn = Fy_psi * _safe(sec.Zx_in3)
        flex_audit = {"Mn_inlb": Mn, "note": "generic_yielding_only"}

    phiMnx   = PHI_B * Mn
    IR_flex  = M_inlb / _safe(phiMnx)
    result.update(flex_audit)
    result.update({
        "Mn_inlb": Mn,
        "phiMnx_inlb": phiMnx,
        "Mr_x_inlb": M_inlb,
        "IR_flexure": IR_flex,
        "phi_b": PHI_B,
    })

    # Weak-axis flexure (simplified yielding-only for biaxial check)
    Mny   = Fy_psi * _safe(sec.Zy_in3)
    phiMny = PHI_B * Mny
    result["Mny_inlb"] = Mny
    result["phiMny_inlb"] = phiMny
    result["Mr_y_inlb"] = My_inlb

    # ----------------------------------------------------------------
    # 2. Shear — Chapter G
    # ----------------------------------------------------------------
    phiVn, shear_audit = _phi_Vn(sec, Fy_psi)
    IR_shear = V_lbf / _safe(phiVn)
    result.update(shear_audit)
    result.update({
        "phiVn_lbf": phiVn,
        "Vr_lbf": V_lbf,
        "IR_shear": IR_shear,
    })

    # ----------------------------------------------------------------
    # 3. Compression — Chapter E
    # ----------------------------------------------------------------
    phiPn, comp_audit = _phi_Pn(sec, Fy_psi, K, L_in)
    result.update(comp_audit)
    result["phiPn_lbf"] = phiPn
    result["Pr_lbf"]    = P_lbf

    # ----------------------------------------------------------------
    # 4. Combined loading — Chapter H
    # ----------------------------------------------------------------
    # Convert to kip-in for interaction equations (ratios are unitless)
    Pr_Pc = P_lbf / _safe(phiPn)
    Mr_x  = M_inlb / _safe(phiMnx)
    Mr_y  = My_inlb / _safe(phiMny)

    if Pr_Pc >= 0.2:
        # Eq. H1-1a
        interaction = Pr_Pc + (8.0 / 9.0) * (Mr_x + Mr_y)
        h1_eq       = "H1-1a"
    else:
        # Eq. H1-1b
        interaction = Pr_Pc / 2.0 + (Mr_x + Mr_y)
        h1_eq       = "H1-1b"

    result.update({
        "Pr_over_Pc": Pr_Pc,
        "Mrx_over_Mcx": Mr_x,
        "Mry_over_Mcy": Mr_y,
        "H1_equation": h1_eq,
        "IR_combined": interaction,
    })

    # ----------------------------------------------------------------
    # 5. Deflection — Serviceability
    # ----------------------------------------------------------------
    delta_in, def_formula = _deflection(V_lbf, L_in, sec.Ix_in4, load_type, w_lbpin)
    def_limit_in = L_in * DEF_LIMIT
    IR_def       = delta_in / _safe(def_limit_in)
    result.update({
        "delta_in": delta_in,
        "def_limit_in": def_limit_in,
        "def_formula": def_formula,
        "IR_deflection": IR_def,
        "load_type": load_type,
    })

    # ----------------------------------------------------------------
    # 6. Slenderness flags
    # ----------------------------------------------------------------
    KL_r = K * L_in / _safe(min(sec.rx_in, sec.ry_in))
    result["KL_over_r"]            = KL_r
    result["slenderness_flag_200"] = KL_r > KLR_MAX_COMPRESSION

    # ----------------------------------------------------------------
    # 7. Governing limit state + overall pass/fail
    # ----------------------------------------------------------------
    checks = {
        "flexure":    IR_flex,
        "shear":      IR_shear,
        "combined":   interaction,
        "deflection": IR_def,
    }
    governing = max(checks, key=lambda k: checks[k])
    result["governing_limit_state"] = governing
    result["governing_IR"]          = checks[governing]

    # All interaction ratios <= 1.0 required for pass
    all_pass = all(v <= 1.0 for v in checks.values())

    # Additional slenderness check (warning, not hard fail per AISC, but noted)
    if result["slenderness_flag_200"]:
        result["slenderness_warning"] = (
            f"KL/r = {KL_r:.1f} exceeds AISC recommended limit of {KLR_MAX_COMPRESSION}"
        )

    result["pass"] = all_pass
    return all_pass, result


# ---------------------------------------------------------------------------
# Member selection
# ---------------------------------------------------------------------------

def select_member(
    M_inlb: float,
    V_lbf: float,
    L_in: float,
    P_lbf: float = 0.0,
    K: float = 1.0,
    Cb: float = 1.0,
    load_type: str = "cantilever",
    My_inlb: float = 0.0,
    w_lbpin: float = 0.0,
    families: Optional[List[str]] = None,
    max_weight_plf: Optional[float] = None,
) -> Tuple[Optional[Section], Dict]:
    """
    Lightest-weight member from the section catalog that satisfies all
    AISC 360-22 LRFD checks for the given demand.

    Parameters
    ----------
    M_inlb        : Required strong-axis moment, in-lb
    V_lbf         : Required shear, lbf
    L_in          : Member length, in
    P_lbf         : Required axial compression, lbf (default 0)
    K             : Effective length factor (default 1.0)
    Cb            : Moment gradient factor (default 1.0)
    load_type     : Deflection model (see check_section)
    My_inlb       : Required weak-axis moment, in-lb
    w_lbpin       : Distributed load for UDL deflection, lbf/in
    families      : List of section families to consider
                    (e.g. ['HSS_square', 'pipe', 'W']).
                    None = defaults to ['HSS_square', 'pipe', 'W']
                    (HSS preferred per Eagle standard practice).
    max_weight_plf: Optional upper weight filter, lb/ft

    Returns
    -------
    (best_section, audit_for_best_section)
    Returns (None, {}) if no section passes.
    """
    # Default: HSS preferred over pipe per Eagle standard practice
    if families is None:
        families = ["HSS_square", "pipe", "W"]
    catalog = load_catalog(families=families)

    # Sort by family preference then lightest-first within each family
    _fam_order = {f.lower(): i for i, f in enumerate(families)}
    catalog_sorted = sorted(
        catalog,
        key=lambda s: (_fam_order.get(s.family.lower(), 99), s.weight_plf),
    )

    if max_weight_plf is not None:
        catalog_sorted = [s for s in catalog_sorted if s.weight_plf <= max_weight_plf]

    best_section: Optional[Section] = None
    best_audit:   Dict              = {}

    for sec in catalog_sorted:
        passed, audit = check_section(
            sec,
            M_inlb=M_inlb,
            V_lbf=V_lbf,
            L_in=L_in,
            P_lbf=P_lbf,
            K=K,
            Cb=Cb,
            load_type=load_type,
            My_inlb=My_inlb,
            w_lbpin=w_lbpin,
        )
        if passed:
            best_section = sec
            best_audit   = audit
            break

    return best_section, best_audit


# ---------------------------------------------------------------------------
# Backward-compatible convenience re-exports
# ---------------------------------------------------------------------------

__all__ = [
    "check_section",
    "select_member",
    "PHI_B",
    "PHI_V",
    "PHI_C",
    "E_PSI",
    "DEF_LIMIT",
]
