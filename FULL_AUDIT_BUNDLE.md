# SignX Engineering Calculation Audit Bundle

## CRITICAL ISSUES SUMMARY

1. **design_anchors() returns SF=0 without raising error** (line ~496-521 in anchors_baseplate.py)
2. **IBC formula unbounded** - 500kip load returns 2941ft depth (foundation_embed.py)
3. **No futa cap** - should limit to min(1.9*fya, 125ksi) per ACI 318-19 17.6.1.2
4. **No LTB/compactness checks** - sections.py returns full plastic moment always

---


## FILE 1: anchors_baseplate.py (ACI 318-19 Chapter 17)

```python
"""
ACI 318-19 Chapter 17 Anchor Design - Complete Implementation

This module implements cast-in-place and post-installed anchor design per ACI 318-19
(Building Code Requirements for Structural Concrete and Commentary).

Key Code Sections Implemented:
- Section 17.4: General Requirements for Strength of Anchors
- Section 17.6: Tensile Strength of Anchors
- Section 17.7: Shear Strength of Anchors
- Section 17.8: Interaction of Tensile and Shear Forces

References:
- ACI 318-19 Equation 17.6.1.2a: Steel strength in tension
- ACI 318-19 Equation 17.6.2.1a: Concrete breakout strength in tension
- ACI 318-19 Equation 17.7.1.2a: Steel strength in shear
- ACI 318-19 Equation 17.7.2.1a: Concrete breakout strength in shear
- ACI 318-19 Equation 17.8.2: Tension-shear interaction

Author: SignX Engineering
Version: 2.0.0 (ACI 318-19 Compliant)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

# ACI 318-19 Strength Reduction Factors (Section 17.5.3)
PHI_STEEL_TENSION = 0.75      # Ductile steel element in tension
PHI_STEEL_SHEAR = 0.65        # Ductile steel element in shear
PHI_CONCRETE_TENSION = 0.70   # Concrete breakout, side-face blowout (Condition B)
PHI_CONCRETE_SHEAR = 0.70     # Concrete breakout, pryout (Condition B)
PHI_PULLOUT = 0.70            # Pullout strength
PHI_BOND = 0.65               # Bond strength (adhesive anchors)


class AnchorType(str, Enum):
    """Anchor types per ACI 318-19 Section 17.3."""
    CAST_IN_HEADED = "cast_in_headed"
    CAST_IN_HOOKED = "cast_in_hooked"
    POST_INSTALLED_EXPANSION = "expansion"
    POST_INSTALLED_UNDERCUT = "undercut"
    POST_INSTALLED_ADHESIVE = "adhesive"
    POST_INSTALLED_SCREW = "screw"


@dataclass
class AnchorMaterial:
    """Anchor material properties."""
    grade: str
    futa_ksi: float
    fya_ksi: float
    is_ductile: bool = True


# Common anchor materials per ASTM specifications
ANCHOR_MATERIALS = {
    "F1554-36": AnchorMaterial("F1554-36", 58.0, 36.0, True),
    "F1554-55": AnchorMaterial("F1554-55", 75.0, 55.0, True),
    "F1554-105": AnchorMaterial("F1554-105", 125.0, 105.0, True),
    "A307": AnchorMaterial("A307", 60.0, 36.0, True),
    "A325": AnchorMaterial("A325", 120.0, 92.0, True),
    "A449": AnchorMaterial("A449", 120.0, 92.0, True),
    "A193-B7": AnchorMaterial("A193-B7", 125.0, 105.0, True),
}

# Standard UNC thread data: diameter -> (threads_per_inch, tensile_stress_area_in2)
UNC_THREAD_DATA = {
    0.500: (13, 0.1419),
    0.625: (11, 0.2260),
    0.750: (10, 0.3340),
    0.875: (9, 0.4617),
    1.000: (8, 0.6057),
    1.125: (7, 0.7633),
    1.250: (7, 0.9691),
    1.375: (6, 1.1549),
    1.500: (6, 1.4053),
    1.750: (5, 1.8998),
    2.000: (4.5, 2.4982),
}

# Standard anchor sizes
STANDARD_DIAMETERS = [0.500, 0.625, 0.750, 0.875, 1.000, 1.125, 1.250, 1.375, 1.500]


def get_anchor_area(diameter_in: float) -> float:
    """
    Get effective tensile stress area for threaded anchor per AISC.

    Ase = π/4 * (d - 0.9743/n)² where n = threads per inch

    Reference: AISC Steel Construction Manual Table 7-17
    """
    if diameter_in in UNC_THREAD_DATA:
        return UNC_THREAD_DATA[diameter_in][1]

    # Linear interpolation for non-standard sizes
    diameters = sorted(UNC_THREAD_DATA.keys())
    for i in range(len(diameters) - 1):
        d1, d2 = diameters[i], diameters[i + 1]
        if d1 <= diameter_in <= d2:
            a1, a2 = UNC_THREAD_DATA[d1][1], UNC_THREAD_DATA[d2][1]
            frac = (diameter_in - d1) / (d2 - d1)
            return a1 + frac * (a2 - a1)

    # Fallback: approximate using gross area * 0.75
    return 0.75 * math.pi * (diameter_in / 2) ** 2


def get_head_bearing_area(diameter_in: float) -> float:
    """
    Get net bearing area of headed anchor (Abrg).

    For standard hex head: Abrg ≈ 2.0 * Ab (gross bolt area)
    For heavy hex head: Abrg ≈ 2.5 * Ab

    Reference: ACI 318-19 Section R17.6.3.2.2
    """
    ab = math.pi * (diameter_in / 2) ** 2
    return 2.0 * ab  # Standard hex head


def calc_steel_tension_strength(
    ase_in2: float,
    futa_ksi: float,
    n_anchors: int = 1,
) -> Tuple[float, str]:
    """
    Calculate steel strength in tension per ACI 318-19 Section 17.6.1.

    Nsa = Ase,N * futa  (Eq. 17.6.1.2)

    Returns:
        (φNsa in kips, code reference)
    """
    nsa_kip = n_anchors * ase_in2 * futa_ksi
    phi_nsa = PHI_STEEL_TENSION * nsa_kip
    return phi_nsa, "ACI 318-19 Eq. 17.6.1.2"


def calc_concrete_breakout_tension(
    hef_in: float,
    fc_psi: float,
    ca_min_in: float,
    s1_in: float,
    s2_in: float,
    n_anchors: int,
    rows: int,
    cols: int,
    lambda_a: float = 1.0,
    is_cracked: bool = True,
) -> Tuple[float, str]:
    """
    Calculate concrete breakout strength in tension per ACI 318-19 Section 17.6.2.

    Ncbg = (ANc/ANco) * ψec,N * ψed,N * ψc,N * ψcp,N * Nb  (Eq. 17.6.2.1a)
    Nb = kc * λa * √f'c * hef^1.5  (Eq. 17.6.2.2a)

    Returns:
        (φNcbg in kips, code reference)
    """
    # kc = 24 for cast-in anchors, 17 for post-installed
    kc = 24.0

    # Basic single anchor breakout strength Nb (Eq. 17.6.2.2a)
    nb_lb = kc * lambda_a * math.sqrt(fc_psi) * (hef_in ** 1.5)
    nb_kip = nb_lb / 1000.0

    # Projected area ANco for single anchor (Eq. 17.6.2.1c)
    anco_in2 = 9.0 * (hef_in ** 2)

    # Projected area ANc for group
    # Width direction: ca_min + (cols-1)*s1 + ca_min, capped at 1.5*hef per side
    w1 = min(ca_min_in, 1.5 * hef_in)
    w2 = min(ca_min_in, 1.5 * hef_in)
    width = w1 + (cols - 1) * s1_in + w2

    h1 = min(ca_min_in, 1.5 * hef_in)
    h2 = min(ca_min_in, 1.5 * hef_in)
    height = h1 + (rows - 1) * s2_in + h2

    anc_in2 = width * height
    area_ratio = min(anc_in2 / anco_in2, float(n_anchors))

    # ψec,N - eccentricity factor (assume concentric loading)
    psi_ec_n = 1.0

    # ψed,N - edge distance factor (Eq. 17.6.2.4.1)
    if ca_min_in >= 1.5 * hef_in:
        psi_ed_n = 1.0
    else:
        psi_ed_n = 0.7 + 0.3 * (ca_min_in / (1.5 * hef_in))

    # ψc,N - cracking factor (Section 17.6.2.5)
    psi_c_n = 1.0 if is_cracked else 1.25

    # ψcp,N - splitting factor for cast-in anchors
    cac_in = 2.5 * hef_in
    if ca_min_in >= cac_in:
        psi_cp_n = 1.0
    else:
        psi_cp_n = max(ca_min_in / cac_in, 1.5 * hef_in / cac_in)

    # Group breakout strength (Eq. 17.6.2.1a)
    ncbg_kip = area_ratio * psi_ec_n * psi_ed_n * psi_c_n * psi_cp_n * nb_kip
    phi_ncbg = PHI_CONCRETE_TENSION * ncbg_kip

    return phi_ncbg, "ACI 318-19 Eq. 17.6.2.1a"


def calc_pullout_strength(
    abrg_in2: float,
    fc_psi: float,
    n_anchors: int,
    is_cracked: bool = True,
) -> Tuple[float, str]:
    """
    Calculate pullout strength in tension per ACI 318-19 Section 17.6.3.

    Npn = ψc,P * Np  (Eq. 17.6.3.1)
    Np = 8 * Abrg * f'c  (Eq. 17.6.3.2.2a)

    Returns:
        (φNpn in kips, code reference)
    """
    psi_c_p = 1.0 if is_cracked else 1.4
    np_lb = 8.0 * abrg_in2 * fc_psi
    npn_kip = psi_c_p * np_lb / 1000.0
    total_npn_kip = n_anchors * npn_kip
    phi_npn = PHI_PULLOUT * total_npn_kip
    return phi_npn, "ACI 318-19 Eq. 17.6.3.2.2a"


def calc_steel_shear_strength(
    ase_in2: float,
    futa_ksi: float,
    fya_ksi: float,
    n_anchors: int = 1,
) -> Tuple[float, str]:
    """
    Calculate steel strength in shear per ACI 318-19 Section 17.7.1.

    Vsa = 0.6 * Ase,V * futa  (Eq. 17.7.1.2b)

    Returns:
        (φVsa in kips, code reference)
    """
    fut_limit = min(futa_ksi, 1.9 * fya_ksi)
    vsa_kip = n_anchors * 0.6 * ase_in2 * fut_limit
    phi_vsa = PHI_STEEL_SHEAR * vsa_kip
    return phi_vsa, "ACI 318-19 Eq. 17.7.1.2b"


def calc_concrete_breakout_shear(
    hef_in: float,
    fc_psi: float,
    ca1_in: float,
    ca2_in: float,
    diameter_in: float,
    n_anchors: int,
    lambda_a: float = 1.0,
    is_cracked: bool = True,
) -> Tuple[float, str]:
    """
    Calculate concrete breakout strength in shear per ACI 318-19 Section 17.7.2.

    Vcbg = (AVc/AVco) * ψec,V * ψed,V * ψc,V * ψh,V * Vb  (Eq. 17.7.2.1a)

    Returns:
        (φVcbg in kips, code reference)
    """
    le_in = min(hef_in, 8.0 * diameter_in)

    # Basic shear breakout (Eq. 17.7.2.2.1a)
    vb_lb = 7.0 * (le_in / diameter_in) ** 0.2 * (diameter_in ** 0.5) * lambda_a * math.sqrt(fc_psi) * (ca1_in ** 1.5)
    vb_kip = vb_lb / 1000.0

    avco_in2 = 4.5 * (ca1_in ** 2)
    avc_in2 = avco_in2 * min(n_anchors, 2.0)
    area_ratio = min(avc_in2 / avco_in2, float(n_anchors))

    psi_ec_v = 1.0
    psi_ed_v = 1.0 if ca2_in >= 1.5 * ca1_in else 0.7 + 0.3 * (ca2_in / (1.5 * ca1_in))
    psi_c_v = 1.0 if is_cracked else 1.4
    psi_h_v = 1.0

    vcbg_kip = area_ratio * psi_ec_v * psi_ed_v * psi_c_v * psi_h_v * vb_kip
    phi_vcbg = PHI_CONCRETE_SHEAR * vcbg_kip
    return phi_vcbg, "ACI 318-19 Eq. 17.7.2.1a"


def calc_concrete_pryout_shear(
    ncbg_kip: float,
    hef_in: float,
) -> Tuple[float, str]:
    """
    Calculate concrete pryout strength in shear per ACI 318-19 Section 17.7.3.

    Vcpg = kcp * Ncbg  (Eq. 17.7.3.1a)

    Returns:
        (φVcpg in kips, code reference)
    """
    kcp = 1.0 if hef_in < 2.5 else 2.0
    vcpg_kip = kcp * ncbg_kip
    phi_vcpg = PHI_CONCRETE_SHEAR * vcpg_kip
    return phi_vcpg, "ACI 318-19 Eq. 17.7.3.1a"


def check_tension_shear_interaction(
    nua_kip: float,
    phi_nn_kip: float,
    vua_kip: float,
    phi_vn_kip: float,
) -> Tuple[bool, float, str]:
    """
    Check tension-shear interaction per ACI 318-19 Section 17.8.

    For Nua/φNn <= 0.2: Full shear strength permitted
    For Vua/φVn <= 0.2: Full tensile strength permitted
    Otherwise: Nua/φNn + Vua/φVn <= 1.2  (Eq. 17.8.3)

    Returns:
        (passes, interaction_ratio, code reference)
    """
    if phi_nn_kip <= 0 or phi_vn_kip <= 0:
        return False, 999.0, "ACI 318-19 Section 17.8"

    tension_ratio = nua_kip / phi_nn_kip
    shear_ratio = vua_kip / phi_vn_kip

    if tension_ratio <= 0.2:
        return shear_ratio <= 1.0, shear_ratio, "ACI 318-19 Section 17.8.1"

    if shear_ratio <= 0.2:
        return tension_ratio <= 1.0, tension_ratio, "ACI 318-19 Section 17.8.2"

    interaction = tension_ratio + shear_ratio
    passes = interaction <= 1.2
    return passes, interaction / 1.2, "ACI 318-19 Eq. 17.8.3"


def design_anchors(
    F_lbf: float,
    M_inlb: float,
    fc_psi: float = 4000.0,
    anchor_grade: str = "F1554-36",
    is_cracked: bool = True,
    min_edge_distance_in: float = 6.0,
    base_plate_width_in: float = 12.0,
    base_plate_length_in: float = 12.0,
) -> Tuple[Dict[str, any], Dict[str, float]]:
    """
    Design anchor system for given loads per ACI 318-19 Chapter 17.

    This function sizes anchors and checks all applicable failure modes:
    - Steel tension (Eq. 17.6.1.2)
    - Concrete breakout tension (Eq. 17.6.2.1a)
    - Pullout (Eq. 17.6.3.2.2a)
    - Steel shear (Eq. 17.7.1.2b)
    - Concrete breakout shear (Eq. 17.7.2.1a)
    - Concrete pryout (Eq. 17.7.3.1a)
    - Tension-shear interaction (Eq. 17.8.3)

    Args:
        F_lbf: Applied shear force (lbs)
        M_inlb: Applied moment (in-lbs)
        fc_psi: Concrete compressive strength (psi), default 4000
        anchor_grade: Anchor material grade per ASTM
        is_cracked: True for cracked concrete assumption (default)
        min_edge_distance_in: Minimum edge distance (in)
        base_plate_width_in: Base plate width (in)
        base_plate_length_in: Base plate length (in)

    Returns:
        Tuple of (design_dict, safety_factors_dict)

    Reference:
        ACI 318-19 Chapter 17: Anchoring to Concrete
    """
    material = ANCHOR_MATERIALS.get(anchor_grade, ANCHOR_MATERIALS["F1554-36"])

    V_kip = F_lbf / 1000.0
    moment_arm_in = 0.8 * base_plate_length_in / 2.0
    T_kip = (M_inlb / moment_arm_in) / 1000.0 if moment_arm_in > 0 else 0.0
    T_kip = max(T_kip, 0.001)  # Minimum for calculation

    target_sf = 2.0
    required_tension_area = (target_sf * T_kip) / (PHI_STEEL_TENSION * material.futa_ksi)

    for n_anchors in [4, 6, 8]:
        required_area_per_anchor = required_tension_area / n_anchors

        selected_dia = STANDARD_DIAMETERS[-1]
        for dia in STANDARD_DIAMETERS:
            if get_anchor_area(dia) >= required_area_per_anchor:
                selected_dia = dia
                break

        ase = get_anchor_area(selected_dia)
        abrg = get_head_bearing_area(selected_dia)

        if n_anchors == 4:
            rows, cols = 2, 2
        elif n_anchors == 6:
            rows, cols = 2, 3
        else:
            rows, cols = 2, 4

        s1 = (base_plate_width_in - 2 * min_edge_distance_in) / max(cols - 1, 1)
        s2 = (base_plate_length_in - 2 * min_edge_distance_in) / max(rows - 1, 1)
        s1 = max(s1, 3.0 * selected_dia)
        s2 = max(s2, 3.0 * selected_dia)

        hef_min = max(8.0 * selected_dia, 4.0)

        for hef_mult in [1.0, 1.25, 1.5, 2.0, 2.5]:
            hef = hef_min * hef_mult

            phi_nsa, _ = calc_steel_tension_strength(ase, material.futa_ksi, n_anchors)
            phi_npn, _ = calc_pullout_strength(abrg, fc_psi, n_anchors, is_cracked)
            phi_ncbg, _ = calc_concrete_breakout_tension(
                hef, fc_psi, min_edge_distance_in, s1, s2, n_anchors, rows, cols, is_cracked=is_cracked
            )

            phi_vsa, _ = calc_steel_shear_strength(ase, material.futa_ksi, material.fya_ksi, n_anchors)
            phi_vcbg, _ = calc_concrete_breakout_shear(
                hef, fc_psi, min_edge_distance_in, min_edge_distance_in,
                selected_dia, n_anchors, is_cracked=is_cracked
            )
            ncbg_unfactored = phi_ncbg / PHI_CONCRETE_TENSION
            phi_vcpg, _ = calc_concrete_pryout_shear(ncbg_unfactored, hef)

            phi_nn = min(phi_nsa, phi_ncbg, phi_npn)
            phi_vn = min(phi_vsa, phi_vcbg, phi_vcpg)

            interaction_passes, interaction_ratio, _ = check_tension_shear_interaction(
                T_kip, phi_nn, V_kip, phi_vn
            )

            sf_tension = phi_nn / T_kip if T_kip > 0 else 999.0
            sf_shear = phi_vn / V_kip if V_kip > 0 else 999.0

            if interaction_passes and sf_tension >= 1.5 and sf_shear >= 1.5:
                plate_t = max(0.5, selected_dia)

                if phi_nsa == phi_nn:
                    gov_t = "steel"
                elif phi_ncbg == phi_nn:
                    gov_t = "breakout"
                else:
                    gov_t = "pullout"

                if phi_vsa == phi_vn:
                    gov_v = "steel"
                elif phi_vcbg == phi_vn:
                    gov_v = "breakout"
                else:
                    gov_v = "pryout"

                design = {
                    "pattern": f"{n_anchors}-bolt ({rows}x{cols})",
                    "dia": f"{selected_dia} in",
                    "diameter_in": selected_dia,
                    "embed_in": round(hef, 1),
                    "grade": anchor_grade,
                    "n_anchors": n_anchors,
                    "rows": rows,
                    "cols": cols,
                    "edge_distance_in": min_edge_distance_in,
                    "spacing_s1_in": round(s1, 2),
                    "spacing_s2_in": round(s2, 2),
                    "plate_t_in": plate_t,
                    "ref": "ACI 318-19 Chapter 17",
                }

                checks = {
                    "T_sf": round(sf_tension, 2),
                    "V_sf": round(sf_shear, 2),
                    "interaction_ratio": round(interaction_ratio, 3),
                    "phi_Nsa_kip": round(phi_nsa, 2),
                    "phi_Ncbg_kip": round(phi_ncbg, 2),
                    "phi_Npn_kip": round(phi_npn, 2),
                    "phi_Vsa_kip": round(phi_vsa, 2),
                    "phi_Vcbg_kip": round(phi_vcbg, 2),
                    "phi_Vcpg_kip": round(phi_vcpg, 2),
                    "governing_tension": gov_t,
                    "governing_shear": gov_v,
                }

                return design, checks

    # Fallback for extreme loads - requires PE review
    design = {
        "pattern": "8-bolt (2x4)",
        "dia": "1.25 in",
        "diameter_in": 1.25,
        "embed_in": 18.0,
        "grade": "F1554-55",
        "n_anchors": 8,
        "rows": 2,
        "cols": 4,
        "edge_distance_in": min_edge_distance_in,
        "spacing_s1_in": 4.0,
        "spacing_s2_in": 6.0,
        "plate_t_in": 1.25,
        "ref": "ACI 318-19 Chapter 17 - REQUIRES PE REVIEW",
        "warning": "Loads exceed standard anchor capacity",
    }

    checks = {
        "T_sf": 0.0,
        "V_sf": 0.0,
        "interaction_ratio": 999.0,
        "requires_pe_review": True,
    }

    return design, checks
```


## FILE 2: foundation_embed.py (IBC 2024 / Broms)

```python
"""
Direct burial (embedment) foundation design per IBC 2024 Section 1807.3 and Broms Method.

Code References:
- IBC 2024 Section 1807.3: Poles embedded in earth
- IBC 2024 Section 1807.3.2.1: Simplified method (Equation 18-1)
- IBC 2024 Section 1807.3.2.2: Nonconstrained conditions
- Broms (1964): Lateral resistance of piles in cohesive/cohesionless soils
- ASCE 7-22: Load factors for foundation design

This module provides:
1. IBC simplified method for round poles (Section 1807.3.2.1)
2. Broms method for short/long pile behavior
3. Combined axial + lateral load design
4. Soil classification and property lookup
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# =============================================================================
# CODE REFERENCE CONSTANTS
# =============================================================================

# IBC 2024 Section 1807.3 Constants
IBC_LATERAL_BEARING_INCREMENT = 1 / 3  # 1/3 increase per foot depth (Section 1806.2)
IBC_MIN_EMBED_DEPTH_FT = 4.0  # Minimum embedment depth
IBC_MAX_LATERAL_BEARING_MULT = 3.0  # Maximum multiplier on lateral bearing

# Broms Method Constants
BROMS_SHORT_PILE_LD_RATIO = 6.0  # L/D ratio threshold for short pile behavior
BROMS_LONG_PILE_LD_RATIO = 20.0  # L/D ratio for fully long pile behavior

# Safety Factors per IBC 2024 / ASCE 7-22
SF_OVERTURNING = 1.5  # Overturning safety factor (IBC 1807.3)
SF_LATERAL_BEARING = 2.0  # Lateral soil bearing
SF_SLIDING = 1.5  # Sliding resistance
SF_UPLIFT = 1.5  # Uplift resistance

# ASCE 7-22 Load Factors
LOAD_FACTOR_DEAD = 1.4  # Dead load only
LOAD_FACTOR_WIND = 1.0  # Wind load (ASD)


# =============================================================================
# SOIL CLASSIFICATION (IBC Table 1806.2)
# =============================================================================

class SoilClass(Enum):
    """Soil classification per IBC 2024 Table 1806.2."""
    ROCK = "rock"
    GRAVEL_GW_GP = "gravel"  # Well/poorly graded gravel
    SAND_SW_SP = "sand"  # Well/poorly graded sand
    SAND_SILTY_SM = "silty_sand"  # Silty sand
    CLAY_STIFF = "clay_stiff"  # Stiff clay, CL/CH
    CLAY_SOFT = "clay_soft"  # Soft clay
    SILT_ML = "silt"  # Silt, ML


@dataclass
class SoilProperties:
    """Soil engineering properties for foundation design."""
    soil_class: SoilClass
    # IBC Table 1806.2 values
    lateral_bearing_psf: float  # Allowable lateral bearing (psf/ft depth)
    vertical_bearing_psf: float  # Allowable vertical bearing (psf)
    friction_coefficient: float  # Base friction coefficient
    # Geotechnical properties
    unit_weight_pcf: float  # Total unit weight (pcf)
    friction_angle_deg: float  # Internal friction angle (degrees)
    cohesion_psf: float  # Cohesion (psf)
    # Derived Rankine coefficients
    Kp: float = field(init=False)  # Passive pressure coefficient
    Ka: float = field(init=False)  # Active pressure coefficient

    def __post_init__(self) -> None:
        """Calculate Rankine pressure coefficients."""
        phi_rad = math.radians(self.friction_angle_deg)
        # Passive: Kp = tan²(45° + φ/2)
        self.Kp = math.tan(math.radians(45) + phi_rad / 2) ** 2
        # Active: Ka = tan²(45° - φ/2)
        self.Ka = math.tan(math.radians(45) - phi_rad / 2) ** 2


# IBC 2024 Table 1806.2 - Presumptive Load-Bearing Values
SOIL_PROPERTIES: Dict[SoilClass, SoilProperties] = {
    SoilClass.ROCK: SoilProperties(
        soil_class=SoilClass.ROCK,
        lateral_bearing_psf=1200,  # psf/ft depth
        vertical_bearing_psf=12000,  # psf
        friction_coefficient=0.70,
        unit_weight_pcf=150,
        friction_angle_deg=45,
        cohesion_psf=0,
    ),
    SoilClass.GRAVEL_GW_GP: SoilProperties(
        soil_class=SoilClass.GRAVEL_GW_GP,
        lateral_bearing_psf=400,
        vertical_bearing_psf=3000,
        friction_coefficient=0.55,
        unit_weight_pcf=125,
        friction_angle_deg=36,
        cohesion_psf=0,
    ),
    SoilClass.SAND_SW_SP: SoilProperties(
        soil_class=SoilClass.SAND_SW_SP,
        lateral_bearing_psf=300,
        vertical_bearing_psf=2000,
        friction_coefficient=0.45,
        unit_weight_pcf=115,
        friction_angle_deg=32,
        cohesion_psf=0,
    ),
    SoilClass.SAND_SILTY_SM: SoilProperties(
        soil_class=SoilClass.SAND_SILTY_SM,
        lateral_bearing_psf=200,
        vertical_bearing_psf=1500,
        friction_coefficient=0.35,
        unit_weight_pcf=110,
        friction_angle_deg=28,
        cohesion_psf=100,
    ),
    SoilClass.CLAY_STIFF: SoilProperties(
        soil_class=SoilClass.CLAY_STIFF,
        lateral_bearing_psf=200,
        vertical_bearing_psf=2000,
        friction_coefficient=0.30,
        unit_weight_pcf=120,
        friction_angle_deg=0,
        cohesion_psf=1000,
    ),
    SoilClass.CLAY_SOFT: SoilProperties(
        soil_class=SoilClass.CLAY_SOFT,
        lateral_bearing_psf=100,
        vertical_bearing_psf=1000,
        friction_coefficient=0.20,
        unit_weight_pcf=110,
        friction_angle_deg=0,
        cohesion_psf=500,
    ),
    SoilClass.SILT_ML: SoilProperties(
        soil_class=SoilClass.SILT_ML,
        lateral_bearing_psf=150,
        vertical_bearing_psf=1500,
        friction_coefficient=0.30,
        unit_weight_pcf=105,
        friction_angle_deg=25,
        cohesion_psf=200,
    ),
}


def get_soil_properties(soil_class: SoilClass | str) -> SoilProperties:
    """Get soil properties by classification."""
    if isinstance(soil_class, str):
        soil_class = SoilClass(soil_class)
    return SOIL_PROPERTIES[soil_class]


# =============================================================================
# IBC 2024 SECTION 1807.3.2.1 - SIMPLIFIED METHOD
# =============================================================================

def calc_ibc_simplified_embedment(
    P_lbf: float,
    h_ft: float,
    b_in: float,
    S1_psf_per_ft: float,
) -> Tuple[float, str]:
    """
    Calculate embedment depth per IBC 2024 Equation 18-1.

    IBC 2024 Section 1807.3.2.1 - Simplified method for round wood poles.

    d = 0.5 * A * (1 + sqrt(1 + 4.36*h/A))

    Where:
        A = 2.34 * P / (S1 * b)
        d = embedment depth (ft)
        h = height above ground to point of lateral load (ft)
        P = applied lateral force (lbf)
        S1 = allowable lateral soil-bearing pressure (psf/ft of depth)
        b = diameter of round pole (ft)

    Args:
        P_lbf: Applied lateral force (lbf)
        h_ft: Height above ground to load application (ft)
        b_in: Pole diameter (in)
        S1_psf_per_ft: Allowable lateral bearing (psf per ft depth)

    Returns:
        Tuple of (embedment_depth_ft, code_reference)

    Reference: IBC 2024 Section 1807.3.2.1, Equation 18-1
    """
    b_ft = b_in / 12.0

    # IBC Equation 18-1 components
    A = 2.34 * P_lbf / (S1_psf_per_ft * b_ft)

    # Prevent division by zero
    if A <= 0:
        A = 0.001

    # IBC Equation 18-1
    d_ft = 0.5 * A * (1 + math.sqrt(1 + 4.36 * h_ft / A))

    # Apply minimum embedment
    d_ft = max(d_ft, IBC_MIN_EMBED_DEPTH_FT)

    code_ref = (
        f"IBC 2024 Eq. 18-1: d = 0.5A(1 + √(1 + 4.36h/A)), "
        f"A = 2.34P/(S₁b) = 2.34({P_lbf})/(({S1_psf_per_ft})({b_ft:.2f})) = {A:.2f} ft, "
        f"d = {d_ft:.2f} ft"
    )

    return d_ft, code_ref


def calc_ibc_nonconstrained_embedment(
    P_lbf: float,
    M_ftlbf: float,
    b_in: float,
    S1_psf_per_ft: float,
    S3_psf: float,
) -> Tuple[float, str]:
    """
    Calculate embedment depth per IBC 2024 Section 1807.3.2.2 (nonconstrained).

    For poles with both lateral force and overturning moment at grade.
    Uses iterative solution for lateral equilibrium.

    Args:
        P_lbf: Applied lateral force at top (lbf)
        M_ftlbf: Overturning moment at grade (ft-lbf)
        b_in: Pole diameter (in)
        S1_psf_per_ft: Allowable lateral bearing at surface (psf/ft)
        S3_psf: Allowable passive pressure below point of rotation (psf)

    Returns:
        Tuple of (embedment_depth_ft, code_reference)

    Reference: IBC 2024 Section 1807.3.2.2
    """
    b_ft = b_in / 12.0

    # Iterative solution for depth
    # The pole rotates about a point at depth 'd_rot' from surface
    # Above rotation point: resisting passive pressure
    # Below rotation point: driving passive pressure

    d_ft = IBC_MIN_EMBED_DEPTH_FT

    for _ in range(100):  # Iterate to find equilibrium
        # Allowable lateral bearing increases with depth (IBC 1806.2)
        # But capped at 3x surface value
        S_avg = S1_psf_per_ft * d_ft / 2  # Average pressure to depth d
        S_avg = min(S_avg, S1_psf_per_ft * d_ft * IBC_MAX_LATERAL_BEARING_MULT)

        # Resisting moment capacity
        M_resist = S_avg * b_ft * (d_ft ** 2) / 3  # Triangular distribution

        # Total applied moment at grade
        M_applied = M_ftlbf + P_lbf * d_ft / 3  # Moment at rotation point

        # Check equilibrium with safety factor
        if M_resist >= M_applied * SF_OVERTURNING:
            break

        d_ft += 0.5  # Increment depth

    d_ft = max(d_ft, IBC_MIN_EMBED_DEPTH_FT)

    code_ref = (
        f"IBC 2024 Section 1807.3.2.2: Nonconstrained embedment, "
        f"M_resist = {M_resist:.0f} ft-lbf ≥ {SF_OVERTURNING} × M_applied = "
        f"{M_applied * SF_OVERTURNING:.0f} ft-lbf, d = {d_ft:.2f} ft"
    )

    return d_ft, code_ref


# =============================================================================
# BROMS METHOD - LATERALLY LOADED PILES
# =============================================================================

def calc_broms_cohesionless(
    P_lbf: float,
    M_ftlbf: float,
    b_in: float,
    L_ft: float,
    soil: SoilProperties,
) -> Tuple[float, float, str]:
    """
    Calculate lateral capacity per Broms (1964) for cohesionless soils.

    For short piles (free-head) in cohesionless soil:
        Hu = 0.5 * γ * b * L² * Kp

    For long piles (free-head) in cohesionless soil:
        Hu = My / (e + 0.67f)
        where f is depth to max moment

    Args:
        P_lbf: Applied lateral force (lbf)
        M_ftlbf: Applied moment at grade (ft-lbf)
        b_in: Pile diameter (in)
        L_ft: Embedment depth (ft)
        soil: Soil properties

    Returns:
        Tuple of (lateral_capacity_lbf, safety_factor, code_reference)

    Reference: Broms (1964) "Lateral Resistance of Piles in Cohesionless Soils"
    """
    b_ft = b_in / 12.0
    gamma = soil.unit_weight_pcf
    Kp = soil.Kp

    # Eccentricity of load
    e_ft = M_ftlbf / P_lbf if P_lbf > 0 else 0

    # Check pile behavior (short vs long)
    LD_ratio = L_ft / b_ft

    if LD_ratio <= BROMS_SHORT_PILE_LD_RATIO:
        # Short pile - soil failure governs
        # Hu = 0.5 * γ * b * L² * Kp (simplified)
        Hu_lbf = 0.5 * gamma * b_ft * (L_ft ** 2) * Kp

        # Apply eccentricity reduction
        if e_ft > 0:
            # Reduced capacity for eccentric loading
            Hu_lbf = Hu_lbf / (1 + 0.67 * e_ft / L_ft)

        behavior = "short pile (soil failure)"

    else:
        # Long pile - plastic hinge in pile may govern
        # Ultimate soil resistance at depth z: pu = 3 * γ * z * Kp * b
        # Depth to maximum moment: f = 0.82 * sqrt(Hu / (γ * b * Kp))

        # For free-head pile:
        # Hu = 0.5 * γ * b * Kp * f² where f = depth to max moment
        # Iterative solution needed

        # Approximate: Hu = γ * b * Kp * L² / (2 * (1 + e_ft/L_ft))
        Hu_lbf = gamma * b_ft * Kp * (L_ft ** 2) / (2 * (1 + e_ft / L_ft if L_ft > 0 else 1))
        behavior = "long pile (pile/soil interaction)"

    sf = Hu_lbf / P_lbf if P_lbf > 0 else float('inf')

    code_ref = (
        f"Broms (1964) - Cohesionless soil, {behavior}, "
        f"L/D = {LD_ratio:.1f}, Kp = {Kp:.2f}, "
        f"Hu = {Hu_lbf:.0f} lbf, SF = {sf:.2f}"
    )

    return Hu_lbf, sf, code_ref


def calc_broms_cohesive(
    P_lbf: float,
    M_ftlbf: float,
    b_in: float,
    L_ft: float,
    soil: SoilProperties,
) -> Tuple[float, float, str]:
    """
    Calculate lateral capacity per Broms (1964) for cohesive soils.

    For short piles (free-head) in cohesive soil:
        Hu = 9 * cu * b * (L - 1.5b)

    For long piles (free-head) in cohesive soil:
        Hu = 2 * My / (e + 1.5b + 0.5f)

    Args:
        P_lbf: Applied lateral force (lbf)
        M_ftlbf: Applied moment at grade (ft-lbf)
        b_in: Pile diameter (in)
        L_ft: Embedment depth (ft)
        soil: Soil properties

    Returns:
        Tuple of (lateral_capacity_lbf, safety_factor, code_reference)

    Reference: Broms (1964) "Lateral Resistance of Piles in Cohesive Soils"
    """
    b_ft = b_in / 12.0
    cu_psf = soil.cohesion_psf  # Undrained shear strength

    # Eccentricity of load
    e_ft = M_ftlbf / P_lbf if P_lbf > 0 else 0

    # Effective length (soil near surface assumed ineffective)
    L_eff = max(0, L_ft - 1.5 * b_ft)

    # Check pile behavior
    LD_ratio = L_ft / b_ft

    if LD_ratio <= BROMS_SHORT_PILE_LD_RATIO:
        # Short pile - soil failure governs
        # Ultimate lateral resistance: 9 * cu per unit length (Broms)
        Hu_lbf = 9 * cu_psf * b_ft * L_eff

        # Apply eccentricity reduction
        if e_ft > 0:
            Hu_lbf = Hu_lbf / (1 + 1.5 * e_ft / L_ft)

        behavior = "short pile (soil failure)"

    else:
        # Long pile - plastic hinge may form
        # Hu = 9 * cu * b * (L - 1.5b - f)
        # where f = (Hu - 9 * cu * b * 1.5b) / (9 * cu * b)

        # Simplified: ultimate capacity limited by soil bearing
        Hu_lbf = 9 * cu_psf * b_ft * L_eff / (1 + e_ft / L_ft if L_ft > 0 else 1)
        behavior = "long pile (plastic hinge)"

    sf = Hu_lbf / P_lbf if P_lbf > 0 else float('inf')

    code_ref = (
        f"Broms (1964) - Cohesive soil, {behavior}, "
        f"L/D = {LD_ratio:.1f}, cu = {cu_psf} psf, "
        f"Hu = {Hu_lbf:.0f} lbf, SF = {sf:.2f}"
    )

    return Hu_lbf, sf, code_ref


def calc_broms_lateral_capacity(
    P_lbf: float,
    M_ftlbf: float,
    b_in: float,
    L_ft: float,
    soil: SoilProperties,
) -> Tuple[float, float, str]:
    """
    Calculate lateral capacity using appropriate Broms method.

    Automatically selects cohesive or cohesionless method based on soil properties.

    Args:
        P_lbf: Applied lateral force (lbf)
        M_ftlbf: Applied moment at grade (ft-lbf)
        b_in: Pile diameter (in)
        L_ft: Embedment depth (ft)
        soil: Soil properties

    Returns:
        Tuple of (lateral_capacity_lbf, safety_factor, code_reference)
    """
    # Cohesive soil: friction angle ≈ 0, cohesion > 0
    # Cohesionless soil: friction angle > 0, cohesion ≈ 0

    if soil.cohesion_psf > 0 and soil.friction_angle_deg < 5:
        # Cohesive soil (clay)
        return calc_broms_cohesive(P_lbf, M_ftlbf, b_in, L_ft, soil)
    elif soil.friction_angle_deg > 0 and soil.cohesion_psf < 100:
        # Cohesionless soil (sand/gravel)
        return calc_broms_cohesionless(P_lbf, M_ftlbf, b_in, L_ft, soil)
    else:
        # c-φ soil - use combined approach (conservative: lesser of both)
        Hu_c, sf_c, ref_c = calc_broms_cohesive(P_lbf, M_ftlbf, b_in, L_ft, soil)
        Hu_nc, sf_nc, ref_nc = calc_broms_cohesionless(P_lbf, M_ftlbf, b_in, L_ft, soil)

        # Conservative: use lower capacity
        if Hu_c <= Hu_nc:
            return Hu_c, sf_c, f"{ref_c} (c-φ soil, cohesive governs)"
        else:
            return Hu_nc, sf_nc, f"{ref_nc} (c-φ soil, cohesionless governs)"


# =============================================================================
# OVERTURNING AND STABILITY CHECKS
# =============================================================================

def check_overturning_stability(
    M_ftlbf: float,
    b_in: float,
    L_ft: float,
    soil: SoilProperties,
) -> Tuple[bool, float, str]:
    """
    Check overturning stability per IBC 2024 Section 1807.3.

    Resisting moment from passive soil pressure must exceed
    overturning moment by required safety factor.

    Args:
        M_ftlbf: Applied overturning moment at grade (ft-lbf)
        b_in: Foundation diameter (in)
        L_ft: Embedment depth (ft)
        soil: Soil properties

    Returns:
        Tuple of (is_adequate, safety_factor, code_reference)
    """
    b_ft = b_in / 12.0

    # Passive pressure resistance (triangular distribution)
    # σp = γ * z * Kp for cohesionless
    # σp = 2 * cu + γ * z for cohesive

    if soil.friction_angle_deg > 5:
        # Cohesionless: passive pressure = 0.5 * γ * L² * Kp
        sigma_p_total = 0.5 * soil.unit_weight_pcf * (L_ft ** 2) * soil.Kp
        # Resultant at L/3 from bottom
        moment_arm = L_ft / 3
    else:
        # Cohesive: passive pressure = 9 * cu * (L - 1.5b)
        L_eff = max(0.1, L_ft - 1.5 * b_ft)
        sigma_p_total = 9 * soil.cohesion_psf * L_eff
        moment_arm = L_eff / 2

    # Resisting moment (about base)
    M_resist = sigma_p_total * b_ft * moment_arm

    # Safety factor
    sf = M_resist / M_ftlbf if M_ftlbf > 0 else float('inf')
    is_adequate = sf >= SF_OVERTURNING

    code_ref = (
        f"IBC 2024 Section 1807.3 Overturning: "
        f"M_resist = {M_resist:.0f} ft-lbf, M_applied = {M_ftlbf:.0f} ft-lbf, "
        f"SF = {sf:.2f} {'≥' if is_adequate else '<'} {SF_OVERTURNING} required"
    )

    return is_adequate, sf, code_ref


def check_sliding_resistance(
    P_lbf: float,
    W_lbf: float,
    b_in: float,
    L_ft: float,
    soil: SoilProperties,
) -> Tuple[bool, float, str]:
    """
    Check sliding resistance at base of foundation.

    Resistance = base friction + passive pressure on embedment face.

    Args:
        P_lbf: Applied lateral force (lbf)
        W_lbf: Total vertical load including foundation weight (lbf)
        b_in: Foundation diameter (in)
        L_ft: Embedment depth (ft)
        soil: Soil properties

    Returns:
        Tuple of (is_adequate, safety_factor, code_reference)
    """
    b_ft = b_in / 12.0

    # Base friction resistance
    F_friction = W_lbf * soil.friction_coefficient

    # Passive pressure on foundation face (at base level)
    if soil.friction_angle_deg > 5:
        # Cohesionless: Pp = 0.5 * γ * L² * Kp * b
        Pp = 0.5 * soil.unit_weight_pcf * (L_ft ** 2) * soil.Kp * b_ft
    else:
        # Cohesive: Pp = (2*cu + γ*L) * L * b
        Pp = (2 * soil.cohesion_psf + soil.unit_weight_pcf * L_ft) * L_ft * b_ft

    # Total sliding resistance
    R_total = F_friction + Pp

    sf = R_total / P_lbf if P_lbf > 0 else float('inf')
    is_adequate = sf >= SF_SLIDING

    code_ref = (
        f"Sliding resistance: F_friction = {F_friction:.0f} lbf, "
        f"P_passive = {Pp:.0f} lbf, R_total = {R_total:.0f} lbf, "
        f"SF = {sf:.2f} {'≥' if is_adequate else '<'} {SF_SLIDING} required"
    )

    return is_adequate, sf, code_ref


def check_bearing_capacity(
    W_lbf: float,
    M_ftlbf: float,
    b_in: float,
    soil: SoilProperties,
) -> Tuple[bool, float, str]:
    """
    Check vertical bearing capacity at foundation base.

    Accounts for moment-induced eccentric loading using effective area method.

    Args:
        W_lbf: Total vertical load (lbf)
        M_ftlbf: Moment at base (ft-lbf)
        b_in: Foundation diameter (in)
        soil: Soil properties

    Returns:
        Tuple of (is_adequate, safety_factor, code_reference)
    """
    b_ft = b_in / 12.0

    # Eccentricity
    e_ft = M_ftlbf / W_lbf if W_lbf > 0 else 0

    # Check if load is within kern (e < D/6 for circle)
    kern_limit = b_ft / 6

    if e_ft <= kern_limit:
        # Load within kern - full base in compression
        A_base = math.pi * (b_ft / 2) ** 2
        q_max = W_lbf / A_base * (1 + 6 * e_ft / b_ft)  # Maximum edge pressure
    else:
        # Load outside kern - partial base in compression
        # Effective width: b' = b - 2e
        b_eff = b_ft - 2 * e_ft
        if b_eff <= 0:
            # Complete overturning
            return False, 0.0, "Bearing FAILS: eccentricity exceeds foundation radius"
        A_eff = math.pi * (b_eff / 2) ** 2 * 0.5  # Approximate effective area
        q_max = W_lbf / A_eff

    # Allowable bearing
    q_allow = soil.vertical_bearing_psf

    sf = q_allow / q_max if q_max > 0 else float('inf')
    is_adequate = sf >= SF_LATERAL_BEARING

    code_ref = (
        f"IBC 2024 Table 1806.2 Bearing: "
        f"q_max = {q_max:.0f} psf, q_allow = {q_allow} psf, "
        f"e = {e_ft:.2f} ft {'(within kern)' if e_ft <= kern_limit else '(outside kern)'}, "
        f"SF = {sf:.2f}"
    )

    return is_adequate, sf, code_ref


# =============================================================================
# MAIN DESIGN FUNCTIONS
# =============================================================================

@dataclass
class EmbedmentDesignResult:
    """Complete embedment foundation design result."""
    # Geometry
    diameter_in: float
    depth_in: float
    shape: str

    # Loads
    lateral_force_lbf: float
    moment_ftlbf: float
    vertical_load_lbf: float

    # Soil
    soil_class: str

    # Capacity checks
    lateral_capacity_lbf: float
    lateral_sf: float
    overturning_sf: float
    sliding_sf: float
    bearing_sf: float

    # Status
    is_adequate: bool
    governing_check: str

    # Code references
    code_refs: List[str]
    design_method: str


def design_embed(
    F_lbf: float,
    M_inlb: float,
    constraints: Dict[str, float] | None = None,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Design direct-burial foundation per IBC 2024 Section 1807.3.

    This is the main entry point for foundation design, compatible with
    the existing API interface.

    Args:
        F_lbf: Applied lateral force (lbf)
        M_inlb: Applied moment (in-lbf)
        constraints: Optional design constraints:
            - max_foundation_dia_in: Maximum diameter (in)
            - max_embed_in: Maximum embedment depth (in)
            - soil_class: Soil classification (default: "sand")
            - h_ft: Height above ground to load (ft, default: 10)

    Returns:
        Tuple of (geometry_dict, safety_factors_dict)

    Reference: IBC 2024 Section 1807.3
    """
    # Parse constraints
    constraints = constraints or {}
    max_dia_in = constraints.get("max_foundation_dia_in", 60.0)
    max_embed_in = constraints.get("max_embed_in", 180.0)  # 15 ft default max
    soil_class_str = constraints.get("soil_class", "sand")
    h_ft = constraints.get("h_ft", 10.0)  # Height to load application

    # Get soil properties
    soil_class_map = {
        "rock": SoilClass.ROCK,
        "gravel": SoilClass.GRAVEL_GW_GP,
        "sand": SoilClass.SAND_SW_SP,
        "silty_sand": SoilClass.SAND_SILTY_SM,
        "clay_stiff": SoilClass.CLAY_STIFF,
        "clay_soft": SoilClass.CLAY_SOFT,
        "silt": SoilClass.SILT_ML,
    }
    soil_class = soil_class_map.get(soil_class_str, SoilClass.SAND_SW_SP)
    soil = get_soil_properties(soil_class)

    # Convert moment to ft-lbf
    M_ftlbf = M_inlb / 12.0

    # Initial sizing using IBC simplified method
    # Start with minimum diameter based on lateral force
    min_dia_in = max(18.0, 0.5 * math.sqrt(F_lbf))  # Empirical starting point

    # Calculate required embedment using IBC method
    d_ft, _ = calc_ibc_simplified_embedment(
        P_lbf=F_lbf,
        h_ft=h_ft,
        b_in=min_dia_in,
        S1_psf_per_ft=soil.lateral_bearing_psf,
    )

    depth_in = d_ft * 12.0
    dia_in = min_dia_in

    # Iterate to find adequate design
    max_iterations = 50
    for _ in range(max_iterations):
        L_ft = depth_in / 12.0

        # Check lateral capacity (Broms method)
        Hu_lbf, lat_sf, _ = calc_broms_lateral_capacity(
            P_lbf=F_lbf,
            M_ftlbf=M_ftlbf,
            b_in=dia_in,
            L_ft=L_ft,
            soil=soil,
        )

        # Check overturning
        ot_ok, ot_sf, _ = check_overturning_stability(
            M_ftlbf=M_ftlbf,
            b_in=dia_in,
            L_ft=L_ft,
            soil=soil,
        )

        # Estimate foundation weight
        concrete_pcf = 150.0
        vol_cf = math.pi * (dia_in / 24.0) ** 2 * L_ft
        W_fdn = vol_cf * concrete_pcf

        # Check sliding
        slide_ok, slide_sf, _ = check_sliding_resistance(
            P_lbf=F_lbf,
            W_lbf=W_fdn,
            b_in=dia_in,
            L_ft=L_ft,
            soil=soil,
        )

        # Check bearing
        brg_ok, brg_sf, _ = check_bearing_capacity(
            W_lbf=W_fdn,
            M_ftlbf=M_ftlbf,
            b_in=dia_in,
            soil=soil,
        )

        # All checks must pass
        if lat_sf >= SF_OVERTURNING and ot_ok and slide_ok and brg_ok:
            break

        # Increase size if checks fail
        if lat_sf < SF_OVERTURNING or not ot_ok:
            # Need more depth for lateral/overturning
            depth_in += 6.0
        if not slide_ok or not brg_ok:
            # Need more diameter for bearing/sliding
            dia_in += 3.0

        # Apply constraints
        if dia_in > max_dia_in:
            dia_in = max_dia_in
            depth_in *= 1.1  # Compensate with more depth
        if depth_in > max_embed_in:
            depth_in = max_embed_in

    # Final safety factors
    L_ft = depth_in / 12.0
    _, ot_sf, _ = check_overturning_stability(M_ftlbf, dia_in, L_ft, soil)

    vol_cf = math.pi * (dia_in / 24.0) ** 2 * L_ft
    W_fdn = vol_cf * 150.0
    _, slide_sf, _ = check_sliding_resistance(F_lbf, W_fdn, dia_in, L_ft, soil)
    _, brg_sf, _ = check_bearing_capacity(W_fdn, M_ftlbf, dia_in, soil)

    return (
        {
            "shape": "cyl",
            "dia_in": round(dia_in, 1),
            "depth_in": round(depth_in, 1),
            "soil_class": soil_class_str,
            "code_ref": "IBC 2024 Section 1807.3",
        },
        {
            "OT_sf": round(ot_sf, 2),
            "BRG_sf": round(brg_sf, 2),
            "SLIDE_sf": round(slide_sf, 2),
            "UPLIFT_sf": round(ot_sf, 2),  # Uplift similar to overturning for embedded
        },
    )


def solve_footing_interactive(
    diameter_ft: float,
    M_pole_kipft: float,
    soil_psf: float,
    num_poles: int = 1,
) -> float:
    """
    Compute minimum depth for given diameter (interactive mode).

    Uses IBC 2024 simplified method.

    Monotonic property: diameter↓ ⇒ depth↑

    Args:
        diameter_ft: Foundation diameter (ft)
        M_pole_kipft: Applied moment per pole (kip-ft)
        soil_psf: Allowable lateral soil bearing (psf per ft depth)
        num_poles: Number of poles (for load sharing)

    Returns:
        Required embedment depth (in)

    Reference: IBC 2024 Section 1807.3.2.1, Equation 18-1
    """
    # Convert moment to lateral force equivalent at 10 ft height
    # M = P * h, so P = M / h
    h_ft = 10.0  # Assumed height to load
    P_lbf = (M_pole_kipft * 1000.0) / h_ft  # Convert kip-ft to lbf at height

    if num_poles > 1:
        P_lbf = P_lbf / num_poles  # Distribute among poles

    diameter_in = diameter_ft * 12.0

    # Use IBC simplified method
    d_ft, _ = calc_ibc_simplified_embedment(
        P_lbf=P_lbf,
        h_ft=h_ft,
        b_in=diameter_in,
        S1_psf_per_ft=soil_psf,
    )

    depth_in = max(36.0, d_ft * 12.0)

    return round(depth_in, 1)


def design_embedment_complete(
    lateral_force_lbf: float,
    moment_ftlbf: float,
    vertical_load_lbf: float,
    height_to_load_ft: float,
    soil_class: SoilClass | str = SoilClass.SAND_SW_SP,
    min_diameter_in: float = 18.0,
    max_diameter_in: float = 60.0,
    min_depth_in: float = 48.0,
    max_depth_in: float = 180.0,
) -> EmbedmentDesignResult:
    """
    Complete embedment foundation design with all checks.

    Performs iterative design to find minimum foundation size that
    satisfies all IBC 2024 requirements.

    Args:
        lateral_force_lbf: Applied lateral force (lbf)
        moment_ftlbf: Applied moment at grade (ft-lbf)
        vertical_load_lbf: Applied vertical load (lbf, positive = compression)
        height_to_load_ft: Height above grade to load application (ft)
        soil_class: Soil classification
        min_diameter_in: Minimum foundation diameter (in)
        max_diameter_in: Maximum foundation diameter (in)
        min_depth_in: Minimum embedment depth (in)
        max_depth_in: Maximum embedment depth (in)

    Returns:
        EmbedmentDesignResult with complete design information

    Reference: IBC 2024 Section 1807.3, Broms (1964)
    """
    # Get soil properties
    if isinstance(soil_class, str):
        soil_class = SoilClass(soil_class)
    soil = get_soil_properties(soil_class)

    # Initialize design
    dia_in = min_diameter_in
    depth_in = min_depth_in
    code_refs: List[str] = []

    # Iterative design
    is_adequate = False
    governing_check = ""

    for iteration in range(100):
        L_ft = depth_in / 12.0

        # Foundation weight
        vol_cf = math.pi * (dia_in / 24.0) ** 2 * L_ft
        W_fdn = vol_cf * 150.0
        W_total = W_fdn + vertical_load_lbf

        # Lateral capacity check
        Hu_lbf, lat_sf, lat_ref = calc_broms_lateral_capacity(
            lateral_force_lbf, moment_ftlbf, dia_in, L_ft, soil
        )

        # Overturning check
        ot_ok, ot_sf, ot_ref = check_overturning_stability(
            moment_ftlbf, dia_in, L_ft, soil
        )

        # Sliding check
        slide_ok, slide_sf, slide_ref = check_sliding_resistance(
            lateral_force_lbf, W_total, dia_in, L_ft, soil
        )

        # Bearing check
        brg_ok, brg_sf, brg_ref = check_bearing_capacity(
            W_total, moment_ftlbf, dia_in, soil
        )

        # Determine if adequate
        checks = [
            (lat_sf >= SF_OVERTURNING, lat_sf, "lateral"),
            (ot_ok, ot_sf, "overturning"),
            (slide_ok, slide_sf, "sliding"),
            (brg_ok, brg_sf, "bearing"),
        ]

        all_ok = all(check[0] for check in checks)

        if all_ok:
            is_adequate = True
            min_sf = min(check[1] for check in checks)
            governing_check = [check[2] for check in checks if check[1] == min_sf][0]
            code_refs = [lat_ref, ot_ref, slide_ref, brg_ref]
            break

        # Find governing failure and increase size
        failing_checks = [check for check in checks if not check[0]]
        min_sf_check = min(failing_checks, key=lambda x: x[1])
        governing_check = min_sf_check[2]

        if governing_check in ["lateral", "overturning"]:
            depth_in = min(depth_in + 6.0, max_depth_in)
        else:
            dia_in = min(dia_in + 3.0, max_diameter_in)

        # If at limits, try the other dimension
        if depth_in >= max_depth_in and dia_in < max_diameter_in:
            dia_in = min(dia_in + 3.0, max_diameter_in)
        elif dia_in >= max_diameter_in and depth_in < max_depth_in:
            depth_in = min(depth_in + 6.0, max_depth_in)
        elif depth_in >= max_depth_in and dia_in >= max_diameter_in:
            # At maximum limits
            code_refs = [lat_ref, ot_ref, slide_ref, brg_ref]
            break

    return EmbedmentDesignResult(
        diameter_in=round(dia_in, 1),
        depth_in=round(depth_in, 1),
        shape="cylindrical",
        lateral_force_lbf=lateral_force_lbf,
        moment_ftlbf=moment_ftlbf,
        vertical_load_lbf=vertical_load_lbf,
        soil_class=soil_class.value,
        lateral_capacity_lbf=round(Hu_lbf, 0),
        lateral_sf=round(lat_sf, 2),
        overturning_sf=round(ot_sf, 2),
        sliding_sf=round(slide_sf, 2),
        bearing_sf=round(brg_sf, 2),
        is_adequate=is_adequate,
        governing_check=governing_check,
        code_refs=code_refs,
        design_method="IBC 2024 Section 1807.3 + Broms (1964)",
    )
```


## FILE 3: rebar_schedules.py (ACI 318-19 Reinforcement)

```python
"""
ACI 318-19 Reinforced Concrete Design - Rebar Schedule Generation

This module implements reinforcement design for circular pier foundations per ACI 318-19
(Building Code Requirements for Structural Concrete and Commentary).

Key Code Sections Implemented:
- Section 9.6: Reinforcement Limits
- Section 9.7: Reinforcement Detailing
- Section 22.5: One-way Shear Strength
- Section 22.6: Two-way Shear Strength
- Section 25.4: Development of Reinforcement

References:
- ACI 318-19 Table 25.4.2.2: Development length factors
- ACI 318-19 Section 9.6.1.2: Minimum reinforcement
- ACI 318-19 Section 9.6.1.3: Maximum reinforcement
- ACI 318-19 Section 25.2.1: Concrete cover

Author: SignX Engineering
Version: 2.0.0 (ACI 318-19 Compliant)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

# Standard rebar sizes per ASTM A615/A706
# Size designation: (bar_num, diameter_in, area_in2, weight_lbf_per_ft)
REBAR_SIZES = {
    "#3": (3, 0.375, 0.11, 0.376),
    "#4": (4, 0.500, 0.20, 0.668),
    "#5": (5, 0.625, 0.31, 1.043),
    "#6": (6, 0.750, 0.44, 1.502),
    "#7": (7, 0.875, 0.60, 2.044),
    "#8": (8, 1.000, 0.79, 2.670),
    "#9": (9, 1.128, 1.00, 3.400),
    "#10": (10, 1.270, 1.27, 4.303),
    "#11": (11, 1.410, 1.56, 5.313),
    "#14": (14, 1.693, 2.25, 7.650),
    "#18": (18, 2.257, 4.00, 13.600),
}

# Standard rebar grades per ASTM A615/A706
REBAR_GRADES = {
    "Grade 40": 40.0,   # fy = 40 ksi (legacy)
    "Grade 60": 60.0,   # fy = 60 ksi (most common)
    "Grade 75": 75.0,   # fy = 75 ksi
    "Grade 80": 80.0,   # fy = 80 ksi
    "Grade 100": 100.0, # fy = 100 ksi (per ACI 318-19)
}


class RebarGrade(str, Enum):
    """Rebar grade per ASTM A615/A706."""
    GRADE_40 = "Grade 40"
    GRADE_60 = "Grade 60"
    GRADE_75 = "Grade 75"
    GRADE_80 = "Grade 80"
    GRADE_100 = "Grade 100"


@dataclass
class RebarDesignResult:
    """Complete rebar schedule design result."""
    # Vertical bars
    vertical_bar_size: str
    vertical_bar_count: int
    vertical_bar_spacing_in: float
    vertical_bar_length_ft: float

    # Ties/hoops
    tie_bar_size: str
    tie_spacing_in: float
    first_tie_from_top_in: float

    # Areas
    as_provided_in2: float
    as_required_in2: float
    rho_provided: float
    rho_min: float
    rho_max: float

    # Development
    ld_required_in: float
    ld_provided_in: float

    # Code reference
    schedule_id: str
    code_refs: List[str]
    assumptions: List[str]


def get_rebar_area(size: str) -> float:
    """Get cross-sectional area of rebar size in in²."""
    if size in REBAR_SIZES:
        return REBAR_SIZES[size][2]
    raise ValueError(f"Unknown rebar size: {size}")


def get_rebar_diameter(size: str) -> float:
    """Get diameter of rebar size in inches."""
    if size in REBAR_SIZES:
        return REBAR_SIZES[size][1]
    raise ValueError(f"Unknown rebar size: {size}")


def calc_min_reinforcement_ratio(fc_psi: float, fy_ksi: float) -> float:
    """
    Calculate minimum reinforcement ratio per ACI 318-19 Section 9.6.1.2.

    For columns and piers: ρ_min = 0.01 (1% of gross area)

    For flexural members (beams):
    As,min = max(3*√f'c/fy * bw*d, 200/fy * bw*d)

    Reference: ACI 318-19 Section 9.6.1.2
    """
    # For pier foundations (compression members): 1% minimum
    return 0.01


def calc_max_reinforcement_ratio(fc_psi: float, fy_ksi: float) -> float:
    """
    Calculate maximum reinforcement ratio per ACI 318-19 Section 9.6.1.3.

    For columns: ρ_max = 0.08 (8% of gross area)
    For special seismic: ρ_max = 0.06

    Reference: ACI 318-19 Section 9.6.1.3
    """
    # For pier foundations: 8% maximum (4% for lap splice regions)
    return 0.08


def calc_development_length(
    bar_size: str,
    fc_psi: float,
    fy_ksi: float,
    cover_in: float,
    is_top_bar: bool = False,
    is_epoxy_coated: bool = False,
    is_lightweight: bool = False,
) -> float:
    """
    Calculate development length for deformed bars in tension per ACI 318-19 Section 25.4.2.

    ld = (fy * ψt * ψe * ψs * ψg / (25 * λ * √f'c)) * db  (Eq. 25.4.2.4a simplified)

    But not less than 12 inches.

    Args:
        bar_size: Rebar size designation (e.g., "#5")
        fc_psi: Concrete compressive strength (psi)
        fy_ksi: Rebar yield strength (ksi)
        cover_in: Clear cover to bar (in)
        is_top_bar: True for top bars with >12" concrete below
        is_epoxy_coated: True for epoxy-coated bars
        is_lightweight: True for lightweight concrete

    Returns:
        Required development length ld (inches)

    Reference: ACI 318-19 Section 25.4.2
    """
    db = get_rebar_diameter(bar_size)
    fy_psi = fy_ksi * 1000.0

    # Modification factors per Table 25.4.2.5
    psi_t = 1.3 if is_top_bar else 1.0  # Casting position factor
    psi_e = 1.5 if is_epoxy_coated else 1.0  # Coating factor
    psi_s = 0.8 if db <= 0.75 else 1.0  # Bar size factor (#6 and smaller)
    psi_g = 1.0  # Grade factor (1.0 for Grade 60)
    lambda_factor = 0.75 if is_lightweight else 1.0

    # Combined factor limit per 25.4.2.5
    psi_t_e = min(psi_t * psi_e, 1.7)

    # Simplified formula per Eq. 25.4.2.4a
    # ld/db = (fy * ψt * ψe)/(25 * λ * √f'c) for bars with clear spacing >= db and cover >= db
    # ld/db = (fy * ψt * ψe)/(20 * λ * √f'c) otherwise

    if cover_in >= db:
        ld = (fy_psi * psi_t_e * psi_s * psi_g) / (25.0 * lambda_factor * math.sqrt(fc_psi)) * db
    else:
        ld = (fy_psi * psi_t_e * psi_s * psi_g) / (20.0 * lambda_factor * math.sqrt(fc_psi)) * db

    # Minimum development length per 25.4.2.1
    ld = max(ld, 12.0)

    return ld


def calc_tie_spacing(
    vertical_bar_size: str,
    tie_bar_size: str,
    pier_diameter_in: float,
) -> float:
    """
    Calculate tie/hoop spacing per ACI 318-19 Section 25.7.2.

    Tie spacing shall not exceed the least of:
    (a) 16 * longitudinal bar diameter
    (b) 48 * tie bar diameter
    (c) Least dimension of compression member

    Reference: ACI 318-19 Section 25.7.2.1
    """
    db_long = get_rebar_diameter(vertical_bar_size)
    db_tie = get_rebar_diameter(tie_bar_size)

    spacing_a = 16.0 * db_long
    spacing_b = 48.0 * db_tie
    spacing_c = pier_diameter_in

    max_spacing = min(spacing_a, spacing_b, spacing_c)

    # Round down to nearest inch
    return math.floor(max_spacing)


def calc_concrete_cover(
    exposure: str = "earth",
    bar_size: str = "#5",
) -> float:
    """
    Determine minimum concrete cover per ACI 318-19 Section 20.5.1.3.

    For cast-against-earth: 3 inches minimum
    For exposed to weather (#6-#18): 2 inches
    For exposed to weather (#5 and smaller): 1.5 inches
    For not exposed: 1.5 inches

    Reference: ACI 318-19 Table 20.5.1.3.1
    """
    bar_num = REBAR_SIZES[bar_size][0] if bar_size in REBAR_SIZES else 5

    if exposure == "earth":
        return 3.0
    elif exposure == "weather":
        return 2.0 if bar_num >= 6 else 1.5
    else:
        return 1.5


def design_pier_reinforcement(
    pier_diameter_in: float,
    pier_depth_in: float,
    mu_kipft: float,
    pu_kip: float = 0.0,
    fc_psi: float = 4000.0,
    fy_ksi: float = 60.0,
    exposure: str = "earth",
) -> RebarDesignResult:
    """
    Design reinforcement for circular pier foundation per ACI 318-19.

    This function designs:
    1. Longitudinal (vertical) reinforcement for flexure and axial
    2. Transverse reinforcement (ties/spirals) for confinement
    3. Development length verification

    Args:
        pier_diameter_in: Pier diameter (inches)
        pier_depth_in: Pier embedment depth (inches)
        mu_kipft: Factored moment demand (kip-ft)
        pu_kip: Factored axial load (kip), positive = compression
        fc_psi: Concrete compressive strength (psi)
        fy_ksi: Rebar yield strength (ksi)
        exposure: Exposure condition ("earth", "weather", "interior")

    Returns:
        RebarDesignResult with complete reinforcement schedule

    Reference: ACI 318-19 Chapters 9, 22, 25
    """
    assumptions = []
    code_refs = []

    # Concrete cover per ACI 318-19 Table 20.5.1.3.1
    cover_in = calc_concrete_cover(exposure, "#5")
    assumptions.append(f"Concrete cover = {cover_in} in per ACI 318-19 Table 20.5.1.3.1")
    code_refs.append("ACI 318-19 Table 20.5.1.3.1")

    # Gross area of pier
    ag_in2 = math.pi * (pier_diameter_in / 2.0) ** 2

    # Minimum and maximum reinforcement ratios
    rho_min = calc_min_reinforcement_ratio(fc_psi, fy_ksi)
    rho_max = calc_max_reinforcement_ratio(fc_psi, fy_ksi)
    code_refs.append("ACI 318-19 Section 9.6.1.2 (ρ_min = 0.01)")
    code_refs.append("ACI 318-19 Section 9.6.1.3 (ρ_max = 0.08)")

    # Minimum steel area
    as_min_in2 = rho_min * ag_in2

    # Calculate required steel from moment (simplified interaction)
    # For circular section: effective depth d ≈ 0.8 * diameter
    d_in = 0.8 * pier_diameter_in
    mu_kipin = mu_kipft * 12.0

    # φMn = φ * As * fy * (d - a/2) where a = As*fy / (0.85*f'c*b)
    # For circular section, use equivalent rectangular width b ≈ 0.8 * D
    b_eq_in = 0.8 * pier_diameter_in

    # Solve for As using quadratic (simplified for small a/d)
    # As ≈ Mu / (φ * fy * 0.9d) for initial estimate
    phi_b = 0.9  # Flexure
    as_moment_in2 = mu_kipin / (phi_b * fy_ksi * 0.9 * d_in) if d_in > 0 else 0.0

    # Required steel (larger of minimum and moment requirement)
    as_required_in2 = max(as_min_in2, as_moment_in2)

    # Select bar size and count
    # Start with #5 bars and increase if needed
    bar_sizes_to_try = ["#5", "#6", "#7", "#8", "#9", "#10"]

    selected_bar = "#5"
    selected_count = 6  # Minimum 6 bars for circular arrangement

    for bar_size in bar_sizes_to_try:
        bar_area = get_rebar_area(bar_size)
        bar_dia = get_rebar_diameter(bar_size)

        # Minimum number of bars: 6 for circular piers
        # Maximum bar spacing around circumference: 6" per ACI 318-19
        core_diameter = pier_diameter_in - 2 * cover_in - bar_dia
        circumference = math.pi * core_diameter
        max_bars_by_spacing = int(circumference / 6.0)
        min_bars = max(6, int(as_required_in2 / bar_area) + 1)

        # Select number of bars
        n_bars = max(min_bars, 6)
        n_bars = min(n_bars, max_bars_by_spacing)

        # Round to even number for symmetry
        if n_bars % 2 != 0:
            n_bars += 1

        as_provided = n_bars * bar_area

        if as_provided >= as_required_in2:
            selected_bar = bar_size
            selected_count = n_bars
            break

    # Final steel area provided
    as_provided_in2 = selected_count * get_rebar_area(selected_bar)
    rho_provided = as_provided_in2 / ag_in2

    # Bar spacing around circumference
    bar_dia = get_rebar_diameter(selected_bar)
    core_dia = pier_diameter_in - 2 * cover_in - bar_dia
    bar_spacing = (math.pi * core_dia) / selected_count

    # Vertical bar length (embedment + development + extension)
    ld_required = calc_development_length(selected_bar, fc_psi, fy_ksi, cover_in)
    ld_provided = pier_depth_in - cover_in  # Available embedment

    # Bar length = depth + 12" hook at bottom + 24" extension at top
    bar_length_in = pier_depth_in + 12.0 + 24.0
    bar_length_ft = bar_length_in / 12.0

    # Tie design per ACI 318-19 Section 25.7.2
    # Minimum tie size: #3 for #10 and smaller longitudinal bars
    #                   #4 for #11, #14, #18 longitudinal bars
    bar_num = REBAR_SIZES[selected_bar][0]
    tie_size = "#3" if bar_num <= 10 else "#4"

    tie_spacing = calc_tie_spacing(selected_bar, tie_size, pier_diameter_in)
    code_refs.append("ACI 318-19 Section 25.7.2.1 (tie spacing)")

    # First tie within 1/2 tie spacing from top
    first_tie_from_top = tie_spacing / 2.0

    # Generate schedule ID
    schedule_id = f"SCH-{int(pier_diameter_in)}-{int(pier_depth_in)}-{selected_bar}@{selected_count}-{tie_size}@{int(tie_spacing)}"

    return RebarDesignResult(
        vertical_bar_size=selected_bar,
        vertical_bar_count=selected_count,
        vertical_bar_spacing_in=round(bar_spacing, 2),
        vertical_bar_length_ft=round(bar_length_ft, 1),
        tie_bar_size=tie_size,
        tie_spacing_in=tie_spacing,
        first_tie_from_top_in=first_tie_from_top,
        as_provided_in2=round(as_provided_in2, 2),
        as_required_in2=round(as_required_in2, 2),
        rho_provided=round(rho_provided, 4),
        rho_min=rho_min,
        rho_max=rho_max,
        ld_required_in=round(ld_required, 1),
        ld_provided_in=round(ld_provided, 1),
        schedule_id=schedule_id,
        code_refs=code_refs,
        assumptions=assumptions,
    )


def schedule_for(dia_in: float, depth_in: float, mu_kipft: float = 0.0) -> str:
    """
    Generate rebar schedule designation for pier foundation.

    This is a simplified interface that returns a schedule ID string.
    For full design details, use design_pier_reinforcement().

    Args:
        dia_in: Pier diameter (inches)
        depth_in: Pier depth (inches)
        mu_kipft: Factored moment (kip-ft), optional

    Returns:
        Schedule designation string

    Reference: ACI 318-19 Chapters 9, 25
    """
    # Use default moment if not provided (conservative sizing)
    if mu_kipft <= 0:
        # Estimate moment from typical wind load on sign
        # Assume 30 psf wind on 100 sqft at 20 ft height = 30*100*20/12 = 5000 kip-in = 417 kip-ft
        # Scale by pier size
        mu_kipft = max(10.0, 0.5 * dia_in * depth_in / 12.0)

    result = design_pier_reinforcement(
        pier_diameter_in=dia_in,
        pier_depth_in=depth_in,
        mu_kipft=mu_kipft,
    )

    return result.schedule_id
```


## FILE 4: sections.py (AISC 360-22 / Shapes Database v16.0)

```python
"""
AISC Steel Section Database per AISC Steel Construction Manual 16th Edition.

This module provides comprehensive steel section properties for structural
design calculations. All data sourced from AISC Shapes Database v16.0.

Code References:
- AISC 360-22: Specification for Structural Steel Buildings
- AISC Steel Construction Manual, 16th Edition
- ASTM A500 Grade C: HSS sections (Fy = 50 ksi, Fu = 62 ksi)
- ASTM A53 Grade B: Standard Pipe (Fy = 35 ksi, Fu = 60 ksi)
- ASTM A992: W-shapes (Fy = 50 ksi, Fu = 65 ksi)
- ASTM A572 Grade 50: Plates and shapes (Fy = 50 ksi, Fu = 65 ksi)

Units:
- Dimensions: inches
- Area: square inches
- Section modulus: cubic inches (in³)
- Moment of inertia: in⁴
- Weight: lb/ft
- Stress: psi
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import pandas as pd
except ImportError:
    pd = None


# =============================================================================
# MATERIAL SPECIFICATIONS
# =============================================================================

class SteelGrade(Enum):
    """ASTM steel grades with yield and tensile strengths."""
    A36 = ("A36", 36000, 58000)  # General purpose
    A53_B = ("A53 Grade B", 35000, 60000)  # Standard pipe
    A500_C = ("A500 Grade C", 50000, 62000)  # HSS
    A572_50 = ("A572 Grade 50", 50000, 65000)  # High-strength shapes
    A588 = ("A588", 50000, 70000)  # Weathering steel
    A992 = ("A992", 50000, 65000)  # W-shapes (preferred)
    A1085 = ("A1085", 50000, 65000)  # HSS (preferred)

    def __init__(self, designation: str, fy_psi: int, fu_psi: int):
        self.designation = designation
        self.fy_psi = fy_psi
        self.fu_psi = fu_psi


# Default material specifications per shape type
DEFAULT_MATERIALS: Dict[str, SteelGrade] = {
    "W": SteelGrade.A992,
    "pipe": SteelGrade.A53_B,
    "tube": SteelGrade.A500_C,
    "HSS_round": SteelGrade.A500_C,
    "HSS_rect": SteelGrade.A500_C,
    "C": SteelGrade.A36,
    "MC": SteelGrade.A36,
    "L": SteelGrade.A36,
    "HP": SteelGrade.A572_50,
    "WT": SteelGrade.A992,
    "MT": SteelGrade.A992,
    "ST": SteelGrade.A36,
}


# =============================================================================
# SECTION DATA CLASSES
# =============================================================================

@dataclass
class Section:
    """Basic steel section properties for design calculations."""
    family: str
    designation: str
    weight_lbf: float  # lb/ft
    Sx_in3: float  # Elastic section modulus (strong axis), in³
    Ix_in4: float  # Moment of inertia (strong axis), in⁴
    fy_psi: float  # Yield strength, psi

    @property
    def Mn_inlb(self) -> float:
        """Nominal moment capacity (yield), in-lb."""
        return self.Sx_in3 * self.fy_psi

    @property
    def phi_Mn_inlb(self) -> float:
        """Design moment capacity (LRFD φ=0.9), in-lb."""
        return 0.9 * self.Mn_inlb


@dataclass
class SectionFull:
    """Complete steel section properties per AISC database."""
    family: str
    designation: str
    weight_lbf: float  # lb/ft

    # Cross-section geometry
    A_in2: float  # Area, in²
    d_in: float  # Depth, in
    bf_in: float  # Flange width (or OD for round), in
    tw_in: float  # Web thickness (or wall for round), in
    tf_in: float  # Flange thickness, in

    # Strong axis (x-x)
    Ix_in4: float  # Moment of inertia, in⁴
    Sx_in3: float  # Elastic section modulus, in³
    Zx_in3: float  # Plastic section modulus, in³
    rx_in: float  # Radius of gyration, in

    # Weak axis (y-y)
    Iy_in4: float  # Moment of inertia, in⁴
    Sy_in3: float  # Elastic section modulus, in³
    Zy_in3: float  # Plastic section modulus, in³
    ry_in: float  # Radius of gyration, in

    # Torsion
    J_in4: float  # Torsional constant, in⁴
    Cw_in6: float  # Warping constant, in⁶

    # Material
    fy_psi: float = 50000.0
    fu_psi: float = 65000.0

    # AISC slenderness ratios (for compact/noncompact checks)
    bf_2tf: float = field(default=0.0)  # Flange slenderness
    h_tw: float = field(default=0.0)  # Web slenderness

    def to_basic(self) -> Section:
        """Convert to basic Section for compatibility."""
        return Section(
            family=self.family,
            designation=self.designation,
            weight_lbf=self.weight_lbf,
            Sx_in3=self.Sx_in3,
            Ix_in4=self.Ix_in4,
            fy_psi=self.fy_psi,
        )


# =============================================================================
# STANDARD PIPE SECTIONS - AISC Database v16.0
# ASTM A53 Grade B: Fy = 35 ksi
# =============================================================================

# Standard Weight Pipe (Schedule 40 for sizes ≤10", Schedule 30 for larger)
PIPE_STANDARD: List[Tuple[str, float, float, float, float, float, float, float]] = [
    # (designation, OD_in, t_in, A_in2, W_lb/ft, Ix_in4, Sx_in3, rx_in)
    ("Pipe 2 Std", 2.375, 0.154, 1.07, 3.65, 0.666, 0.561, 0.787),
    ("Pipe 2-1/2 Std", 2.875, 0.203, 1.70, 5.79, 1.53, 1.06, 0.947),
    ("Pipe 3 Std", 3.500, 0.216, 2.23, 7.58, 3.02, 1.72, 1.16),
    ("Pipe 3-1/2 Std", 4.000, 0.226, 2.68, 9.11, 4.79, 2.39, 1.34),
    ("Pipe 4 Std", 4.500, 0.237, 3.17, 10.79, 7.23, 3.21, 1.51),
    ("Pipe 5 Std", 5.563, 0.258, 4.30, 14.62, 15.2, 5.45, 1.88),
    ("Pipe 6 Std", 6.625, 0.280, 5.58, 18.97, 28.1, 8.50, 2.25),
    ("Pipe 8 Std", 8.625, 0.322, 8.40, 28.55, 72.5, 16.8, 2.94),
    ("Pipe 10 Std", 10.750, 0.365, 11.9, 40.48, 161, 29.9, 3.67),
    ("Pipe 12 Std", 12.750, 0.375, 14.6, 49.56, 279, 43.8, 4.38),
    ("Pipe 14 Std", 14.000, 0.375, 16.1, 54.57, 373, 53.3, 4.82),
    ("Pipe 16 Std", 16.000, 0.375, 18.4, 62.58, 562, 70.3, 5.53),
    ("Pipe 18 Std", 18.000, 0.375, 20.8, 70.59, 807, 89.6, 6.23),
    ("Pipe 20 Std", 20.000, 0.375, 23.1, 78.60, 1114, 111, 6.94),
    ("Pipe 24 Std", 24.000, 0.375, 27.8, 94.62, 1943, 162, 8.35),
]

# Extra Strong Pipe (Schedule 80 for sizes ≤8", Schedule 60 for larger)
PIPE_XS: List[Tuple[str, float, float, float, float, float, float, float]] = [
    ("Pipe 2 XS", 2.375, 0.218, 1.48, 5.02, 0.868, 0.731, 0.766),
    ("Pipe 2-1/2 XS", 2.875, 0.276, 2.25, 7.66, 1.92, 1.34, 0.924),
    ("Pipe 3 XS", 3.500, 0.300, 3.02, 10.25, 3.89, 2.23, 1.14),
    ("Pipe 3-1/2 XS", 4.000, 0.318, 3.68, 12.51, 6.28, 3.14, 1.31),
    ("Pipe 4 XS", 4.500, 0.337, 4.41, 14.98, 9.61, 4.27, 1.48),
    ("Pipe 5 XS", 5.563, 0.375, 6.11, 20.78, 20.7, 7.43, 1.84),
    ("Pipe 6 XS", 6.625, 0.432, 8.40, 28.57, 40.5, 12.2, 2.19),
    ("Pipe 8 XS", 8.625, 0.500, 12.8, 43.39, 106, 24.5, 2.88),
    ("Pipe 10 XS", 10.750, 0.500, 16.1, 54.74, 212, 39.4, 3.63),
    ("Pipe 12 XS", 12.750, 0.500, 19.2, 65.42, 362, 56.7, 4.33),
    ("Pipe 14 XS", 14.000, 0.500, 21.2, 72.09, 484, 69.1, 4.78),
    ("Pipe 16 XS", 16.000, 0.500, 24.3, 82.77, 732, 91.5, 5.49),
    ("Pipe 18 XS", 18.000, 0.500, 27.5, 93.45, 1053, 117, 6.19),
    ("Pipe 20 XS", 20.000, 0.500, 30.6, 104.1, 1457, 146, 6.90),
    ("Pipe 24 XS", 24.000, 0.500, 36.9, 125.5, 2550, 213, 8.31),
]

# Double Extra Strong Pipe
PIPE_XXS: List[Tuple[str, float, float, float, float, float, float, float]] = [
    ("Pipe 2 XXS", 2.375, 0.436, 2.66, 9.03, 1.31, 1.10, 0.703),
    ("Pipe 2-1/2 XXS", 2.875, 0.552, 4.03, 13.69, 2.87, 2.00, 0.844),
    ("Pipe 3 XXS", 3.500, 0.600, 5.47, 18.58, 5.99, 3.42, 1.05),
    ("Pipe 4 XXS", 4.500, 0.674, 8.10, 27.54, 15.3, 6.79, 1.37),
    ("Pipe 5 XXS", 5.563, 0.750, 11.3, 38.55, 33.6, 12.1, 1.72),
    ("Pipe 6 XXS", 6.625, 0.864, 15.6, 53.16, 66.3, 20.0, 2.06),
    ("Pipe 8 XXS", 8.625, 0.875, 21.3, 72.42, 162, 37.6, 2.76),
]


def load_pipe_catalog() -> List[Section]:
    """
    Load all standard pipe sections per AISC database.

    Returns list of Section objects for pipe shapes commonly used
    in sign structure posts and supports.

    Material: ASTM A53 Grade B (Fy = 35 ksi)
    """
    sections: List[Section] = []
    fy = SteelGrade.A53_B.fy_psi  # 35,000 psi

    # Standard weight pipes
    for data in PIPE_STANDARD:
        designation, od, t, a, w, ix, sx, rx = data
        sections.append(Section(
            family="pipe",
            designation=designation,
            weight_lbf=w,
            Sx_in3=sx,
            Ix_in4=ix,
            fy_psi=fy,
        ))

    # Extra strong pipes
    for data in PIPE_XS:
        designation, od, t, a, w, ix, sx, rx = data
        sections.append(Section(
            family="pipe",
            designation=designation,
            weight_lbf=w,
            Sx_in3=sx,
            Ix_in4=ix,
            fy_psi=fy,
        ))

    # Double extra strong (for heavily loaded posts)
    for data in PIPE_XXS:
        designation, od, t, a, w, ix, sx, rx = data
        sections.append(Section(
            family="pipe",
            designation=designation,
            weight_lbf=w,
            Sx_in3=sx,
            Ix_in4=ix,
            fy_psi=fy,
        ))

    return sections


# =============================================================================
# W-SHAPES (WIDE FLANGE) - AISC Database v16.0
# ASTM A992: Fy = 50 ksi, Fu = 65 ksi
# =============================================================================

# Common W-shapes used in sign structures (cantilevers, trusses)
# (designation, W_lb/ft, A_in2, d_in, bf_in, tf_in, tw_in, Ix_in4, Sx_in3, Zx_in3, rx_in, Iy_in4, Sy_in3, ry_in)
W_SHAPES: List[Tuple] = [
    # W6 series
    ("W6x8.5", 8.5, 2.52, 5.83, 3.94, 0.195, 0.170, 14.9, 5.10, 5.73, 2.43, 1.99, 1.01, 0.890),
    ("W6x9", 9.0, 2.68, 5.90, 3.94, 0.215, 0.170, 16.4, 5.56, 6.23, 2.47, 2.19, 1.11, 0.905),
    ("W6x12", 12.0, 3.55, 6.03, 4.00, 0.280, 0.230, 22.1, 7.31, 8.30, 2.49, 2.99, 1.50, 0.918),
    ("W6x15", 15.0, 4.43, 5.99, 5.99, 0.260, 0.230, 29.1, 9.72, 10.8, 2.56, 9.32, 3.11, 1.45),
    ("W6x16", 16.0, 4.74, 6.28, 4.03, 0.405, 0.260, 32.1, 10.2, 11.7, 2.60, 4.43, 2.20, 0.966),
    ("W6x20", 20.0, 5.87, 6.20, 6.02, 0.365, 0.260, 41.4, 13.4, 14.9, 2.66, 13.3, 4.41, 1.50),
    ("W6x25", 25.0, 7.34, 6.38, 6.08, 0.455, 0.320, 53.4, 16.7, 18.9, 2.70, 17.1, 5.61, 1.52),

    # W8 series
    ("W8x10", 10.0, 2.96, 7.89, 3.94, 0.205, 0.170, 30.8, 7.81, 8.87, 3.22, 2.09, 1.06, 0.841),
    ("W8x13", 13.0, 3.84, 7.99, 4.00, 0.255, 0.230, 39.6, 9.91, 11.4, 3.21, 2.73, 1.37, 0.843),
    ("W8x15", 15.0, 4.44, 8.11, 4.01, 0.315, 0.245, 48.0, 11.8, 13.6, 3.29, 3.41, 1.70, 0.876),
    ("W8x18", 18.0, 5.26, 8.14, 5.25, 0.330, 0.230, 61.9, 15.2, 17.0, 3.43, 7.97, 3.04, 1.23),
    ("W8x21", 21.0, 6.16, 8.28, 5.27, 0.400, 0.250, 75.3, 18.2, 20.4, 3.49, 9.77, 3.71, 1.26),
    ("W8x24", 24.0, 7.08, 7.93, 6.50, 0.400, 0.245, 82.7, 20.9, 23.1, 3.42, 18.3, 5.63, 1.61),
    ("W8x28", 28.0, 8.24, 8.06, 6.54, 0.465, 0.285, 98.0, 24.3, 27.2, 3.45, 21.7, 6.63, 1.62),
    ("W8x31", 31.0, 9.12, 8.00, 8.00, 0.435, 0.285, 110, 27.5, 30.4, 3.47, 37.1, 9.27, 2.02),
    ("W8x35", 35.0, 10.3, 8.12, 8.02, 0.495, 0.310, 127, 31.2, 34.7, 3.51, 42.6, 10.6, 2.03),
    ("W8x40", 40.0, 11.7, 8.25, 8.07, 0.560, 0.360, 146, 35.5, 39.8, 3.53, 49.1, 12.2, 2.04),
    ("W8x48", 48.0, 14.1, 8.50, 8.11, 0.685, 0.400, 184, 43.2, 49.0, 3.61, 60.9, 15.0, 2.08),
    ("W8x58", 58.0, 17.1, 8.75, 8.22, 0.810, 0.510, 228, 52.0, 59.8, 3.65, 75.1, 18.3, 2.10),
    ("W8x67", 67.0, 19.7, 9.00, 8.28, 0.935, 0.570, 272, 60.4, 70.1, 3.72, 88.6, 21.4, 2.12),

    # W10 series
    ("W10x12", 12.0, 3.54, 9.87, 3.96, 0.210, 0.190, 53.8, 10.9, 12.6, 3.90, 2.18, 1.10, 0.785),
    ("W10x15", 15.0, 4.41, 9.99, 4.00, 0.270, 0.230, 68.9, 13.8, 16.0, 3.95, 2.89, 1.45, 0.810),
    ("W10x17", 17.0, 4.99, 10.1, 4.01, 0.330, 0.240, 81.9, 16.2, 18.7, 4.05, 3.56, 1.78, 0.845),
    ("W10x19", 19.0, 5.62, 10.2, 4.02, 0.395, 0.250, 96.3, 18.8, 21.6, 4.14, 4.29, 2.14, 0.874),
    ("W10x22", 22.0, 6.49, 10.2, 5.75, 0.360, 0.240, 118, 23.2, 26.0, 4.27, 11.4, 3.97, 1.33),
    ("W10x26", 26.0, 7.61, 10.3, 5.77, 0.440, 0.260, 144, 27.9, 31.3, 4.35, 14.1, 4.89, 1.36),
    ("W10x30", 30.0, 8.84, 10.5, 5.81, 0.510, 0.300, 170, 32.4, 36.6, 4.38, 16.7, 5.75, 1.37),
    ("W10x33", 33.0, 9.71, 9.73, 7.96, 0.435, 0.290, 171, 35.0, 38.8, 4.19, 36.6, 9.20, 1.94),
    ("W10x39", 39.0, 11.5, 9.92, 7.99, 0.530, 0.315, 209, 42.1, 46.8, 4.27, 45.0, 11.3, 1.98),
    ("W10x45", 45.0, 13.3, 10.1, 8.02, 0.620, 0.350, 248, 49.1, 54.9, 4.32, 53.4, 13.3, 2.01),
    ("W10x49", 49.0, 14.4, 10.0, 10.0, 0.560, 0.340, 272, 54.6, 60.4, 4.35, 93.4, 18.7, 2.54),
    ("W10x54", 54.0, 15.8, 10.1, 10.0, 0.615, 0.370, 303, 60.0, 66.6, 4.37, 103, 20.6, 2.56),
    ("W10x60", 60.0, 17.6, 10.2, 10.1, 0.680, 0.420, 341, 66.7, 74.6, 4.39, 116, 23.0, 2.57),
    ("W10x68", 68.0, 20.0, 10.4, 10.1, 0.770, 0.470, 394, 75.7, 85.3, 4.44, 134, 26.4, 2.59),
    ("W10x77", 77.0, 22.6, 10.6, 10.2, 0.870, 0.530, 455, 85.9, 97.6, 4.49, 154, 30.1, 2.60),
    ("W10x88", 88.0, 26.0, 10.8, 10.3, 0.990, 0.605, 534, 98.5, 113, 4.54, 179, 34.8, 2.63),
    ("W10x100", 100.0, 29.4, 11.1, 10.3, 1.12, 0.680, 623, 112, 130, 4.60, 207, 40.0, 2.65),
    ("W10x112", 112.0, 32.9, 11.4, 10.4, 1.25, 0.755, 716, 126, 147, 4.66, 236, 45.3, 2.68),

    # W12 series
    ("W12x14", 14.0, 4.16, 11.9, 3.97, 0.225, 0.200, 88.6, 14.9, 17.4, 4.62, 2.36, 1.19, 0.753),
    ("W12x16", 16.0, 4.71, 12.0, 3.99, 0.265, 0.220, 103, 17.1, 20.1, 4.67, 2.82, 1.41, 0.773),
    ("W12x19", 19.0, 5.57, 12.2, 4.01, 0.350, 0.235, 130, 21.3, 24.7, 4.82, 3.76, 1.88, 0.822),
    ("W12x22", 22.0, 6.48, 12.3, 4.03, 0.425, 0.260, 156, 25.4, 29.3, 4.91, 4.66, 2.31, 0.848),
    ("W12x26", 26.0, 7.65, 12.2, 6.49, 0.380, 0.230, 204, 33.4, 37.2, 5.17, 17.3, 5.34, 1.51),
    ("W12x30", 30.0, 8.79, 12.3, 6.52, 0.440, 0.260, 238, 38.6, 43.1, 5.21, 20.3, 6.24, 1.52),
    ("W12x35", 35.0, 10.3, 12.5, 6.56, 0.520, 0.300, 285, 45.6, 51.2, 5.25, 24.5, 7.47, 1.54),
    ("W12x40", 40.0, 11.7, 11.9, 8.01, 0.515, 0.295, 307, 51.5, 57.0, 5.13, 44.1, 11.0, 1.94),
    ("W12x45", 45.0, 13.1, 12.1, 8.05, 0.575, 0.335, 348, 57.7, 64.2, 5.15, 50.0, 12.4, 1.95),
    ("W12x50", 50.0, 14.6, 12.2, 8.08, 0.640, 0.370, 391, 64.2, 71.9, 5.18, 56.3, 13.9, 1.96),
    ("W12x53", 53.0, 15.6, 12.1, 10.0, 0.575, 0.345, 425, 70.6, 77.9, 5.23, 95.8, 19.2, 2.48),
    ("W12x58", 58.0, 17.0, 12.2, 10.0, 0.640, 0.360, 475, 78.0, 86.4, 5.28, 107, 21.4, 2.51),
    ("W12x65", 65.0, 19.1, 12.1, 12.0, 0.605, 0.390, 533, 87.9, 96.8, 5.28, 174, 29.1, 3.02),
    ("W12x72", 72.0, 21.1, 12.3, 12.0, 0.670, 0.430, 597, 97.4, 108, 5.31, 195, 32.4, 3.04),
    ("W12x79", 79.0, 23.2, 12.4, 12.1, 0.735, 0.470, 662, 107, 119, 5.34, 216, 35.8, 3.05),
    ("W12x87", 87.0, 25.6, 12.5, 12.1, 0.810, 0.515, 740, 118, 132, 5.38, 241, 39.7, 3.07),
    ("W12x96", 96.0, 28.2, 12.7, 12.2, 0.900, 0.550, 833, 131, 147, 5.44, 270, 44.4, 3.09),
    ("W12x106", 106.0, 31.2, 12.9, 12.2, 0.990, 0.610, 933, 145, 164, 5.47, 301, 49.3, 3.11),
    ("W12x120", 120.0, 35.2, 13.1, 12.3, 1.11, 0.710, 1070, 163, 186, 5.51, 345, 56.0, 3.13),
    ("W12x136", 136.0, 39.9, 13.4, 12.4, 1.25, 0.790, 1240, 186, 214, 5.58, 398, 64.2, 3.16),
    ("W12x152", 152.0, 44.7, 13.7, 12.5, 1.40, 0.870, 1430, 209, 243, 5.66, 454, 72.8, 3.19),

    # W14 series (very common for cantilevers)
    ("W14x22", 22.0, 6.49, 13.7, 5.00, 0.335, 0.230, 199, 29.0, 33.2, 5.54, 7.00, 2.80, 1.04),
    ("W14x26", 26.0, 7.69, 13.9, 5.03, 0.420, 0.255, 245, 35.3, 40.2, 5.65, 8.91, 3.54, 1.08),
    ("W14x30", 30.0, 8.85, 13.8, 6.73, 0.385, 0.270, 291, 42.0, 47.3, 5.73, 19.6, 5.82, 1.49),
    ("W14x34", 34.0, 10.0, 14.0, 6.75, 0.455, 0.285, 340, 48.6, 54.6, 5.83, 23.3, 6.91, 1.53),
    ("W14x38", 38.0, 11.2, 14.1, 6.77, 0.515, 0.310, 385, 54.6, 61.5, 5.87, 26.7, 7.88, 1.55),
    ("W14x43", 43.0, 12.6, 13.7, 8.00, 0.530, 0.305, 428, 62.6, 69.6, 5.82, 45.2, 11.3, 1.89),
    ("W14x48", 48.0, 14.1, 13.8, 8.03, 0.595, 0.340, 484, 70.2, 78.4, 5.85, 51.4, 12.8, 1.91),
    ("W14x53", 53.0, 15.6, 13.9, 8.06, 0.660, 0.370, 541, 77.8, 87.1, 5.89, 57.7, 14.3, 1.92),
    ("W14x61", 61.0, 17.9, 13.9, 10.0, 0.645, 0.375, 640, 92.1, 102, 5.98, 107, 21.5, 2.45),
    ("W14x68", 68.0, 20.0, 14.0, 10.0, 0.720, 0.415, 722, 103, 115, 6.01, 121, 24.2, 2.46),
    ("W14x74", 74.0, 21.8, 14.2, 10.1, 0.785, 0.450, 795, 112, 126, 6.04, 134, 26.6, 2.48),
    ("W14x82", 82.0, 24.0, 14.3, 10.1, 0.855, 0.510, 881, 123, 139, 6.05, 148, 29.3, 2.48),
    ("W14x90", 90.0, 26.5, 14.0, 14.5, 0.710, 0.440, 999, 143, 157, 6.14, 362, 49.9, 3.70),
    ("W14x99", 99.0, 29.1, 14.2, 14.6, 0.780, 0.485, 1110, 157, 173, 6.17, 402, 55.2, 3.71),
    ("W14x109", 109.0, 32.0, 14.3, 14.6, 0.860, 0.525, 1240, 173, 192, 6.22, 447, 61.2, 3.73),
    ("W14x120", 120.0, 35.3, 14.5, 14.7, 0.940, 0.590, 1380, 190, 212, 6.24, 495, 67.5, 3.74),
    ("W14x132", 132.0, 38.8, 14.7, 14.7, 1.03, 0.645, 1530, 209, 234, 6.28, 548, 74.5, 3.76),
    ("W14x145", 145.0, 42.7, 14.8, 15.5, 1.09, 0.680, 1710, 232, 260, 6.33, 677, 87.3, 3.98),
    ("W14x159", 159.0, 46.7, 15.0, 15.6, 1.19, 0.745, 1900, 254, 287, 6.38, 748, 96.2, 4.00),

    # W16 series
    ("W16x26", 26.0, 7.68, 15.7, 5.50, 0.345, 0.250, 301, 38.4, 44.2, 6.26, 9.59, 3.49, 1.12),
    ("W16x31", 31.0, 9.13, 15.9, 5.53, 0.440, 0.275, 375, 47.2, 54.0, 6.41, 12.4, 4.49, 1.17),
    ("W16x36", 36.0, 10.6, 15.9, 6.99, 0.430, 0.295, 448, 56.5, 64.0, 6.51, 24.5, 7.00, 1.52),
    ("W16x40", 40.0, 11.8, 16.0, 7.00, 0.505, 0.305, 518, 64.7, 73.0, 6.63, 28.9, 8.25, 1.57),
    ("W16x45", 45.0, 13.3, 16.1, 7.04, 0.565, 0.345, 586, 72.7, 82.3, 6.65, 32.8, 9.34, 1.57),
    ("W16x50", 50.0, 14.7, 16.3, 7.07, 0.630, 0.380, 659, 81.0, 92.0, 6.68, 37.2, 10.5, 1.59),
    ("W16x57", 57.0, 16.8, 16.4, 7.12, 0.715, 0.430, 758, 92.2, 105, 6.72, 43.1, 12.1, 1.60),
    ("W16x67", 67.0, 19.7, 16.3, 10.2, 0.665, 0.395, 954, 117, 130, 6.96, 119, 23.2, 2.46),
    ("W16x77", 77.0, 22.6, 16.5, 10.3, 0.760, 0.455, 1110, 134, 150, 7.00, 138, 26.9, 2.47),
    ("W16x89", 89.0, 26.2, 16.8, 10.4, 0.875, 0.525, 1300, 155, 175, 7.05, 163, 31.4, 2.49),
    ("W16x100", 100.0, 29.4, 17.0, 10.4, 0.985, 0.585, 1490, 175, 198, 7.10, 186, 35.7, 2.52),

    # W18 series
    ("W18x35", 35.0, 10.3, 17.7, 6.00, 0.425, 0.300, 510, 57.6, 66.5, 7.04, 15.3, 5.12, 1.22),
    ("W18x40", 40.0, 11.8, 17.9, 6.02, 0.525, 0.315, 612, 68.4, 78.4, 7.21, 19.1, 6.35, 1.27),
    ("W18x46", 46.0, 13.5, 18.1, 6.06, 0.605, 0.360, 712, 78.8, 90.7, 7.25, 22.5, 7.43, 1.29),
    ("W18x50", 50.0, 14.7, 18.0, 7.50, 0.570, 0.355, 800, 88.9, 101, 7.38, 40.1, 10.7, 1.65),
    ("W18x55", 55.0, 16.2, 18.1, 7.53, 0.630, 0.390, 890, 98.3, 112, 7.41, 44.9, 11.9, 1.67),
    ("W18x60", 60.0, 17.6, 18.2, 7.56, 0.695, 0.415, 984, 108, 123, 7.47, 50.1, 13.3, 1.69),
    ("W18x65", 65.0, 19.1, 18.4, 7.59, 0.750, 0.450, 1070, 117, 133, 7.49, 54.8, 14.4, 1.69),
    ("W18x71", 71.0, 20.8, 18.5, 7.64, 0.810, 0.495, 1170, 127, 146, 7.50, 60.3, 15.8, 1.70),
    ("W18x76", 76.0, 22.3, 18.2, 11.0, 0.680, 0.425, 1330, 146, 163, 7.73, 152, 27.6, 2.61),
    ("W18x86", 86.0, 25.3, 18.4, 11.1, 0.770, 0.480, 1530, 166, 186, 7.77, 175, 31.6, 2.63),
    ("W18x97", 97.0, 28.5, 18.6, 11.1, 0.870, 0.535, 1750, 188, 211, 7.82, 201, 36.1, 2.65),
    ("W18x106", 106.0, 31.1, 18.7, 11.2, 0.940, 0.590, 1910, 204, 230, 7.84, 220, 39.4, 2.66),
    ("W18x119", 119.0, 35.1, 19.0, 11.3, 1.06, 0.655, 2190, 231, 262, 7.90, 253, 44.9, 2.69),

    # W21 series
    ("W21x44", 44.0, 13.0, 20.7, 6.50, 0.450, 0.350, 843, 81.6, 95.4, 8.06, 20.7, 6.36, 1.26),
    ("W21x50", 50.0, 14.7, 20.8, 6.53, 0.535, 0.380, 984, 94.5, 110, 8.18, 24.9, 7.64, 1.30),
    ("W21x57", 57.0, 16.7, 21.1, 6.56, 0.650, 0.405, 1170, 111, 129, 8.36, 30.6, 9.35, 1.35),
    ("W21x62", 62.0, 18.3, 21.0, 8.24, 0.615, 0.400, 1330, 127, 144, 8.54, 57.5, 13.9, 1.77),
    ("W21x68", 68.0, 20.0, 21.1, 8.27, 0.685, 0.430, 1480, 140, 160, 8.60, 64.7, 15.7, 1.80),
    ("W21x73", 73.0, 21.5, 21.2, 8.30, 0.740, 0.455, 1600, 151, 172, 8.64, 70.6, 17.0, 1.81),
    ("W21x83", 83.0, 24.4, 21.4, 8.36, 0.835, 0.515, 1830, 171, 196, 8.67, 81.4, 19.5, 1.83),
    ("W21x93", 93.0, 27.3, 21.6, 8.42, 0.930, 0.580, 2070, 192, 221, 8.70, 92.9, 22.1, 1.84),
    ("W21x101", 101.0, 29.8, 21.4, 12.3, 0.800, 0.500, 2420, 227, 253, 9.02, 248, 40.3, 2.89),
    ("W21x111", 111.0, 32.7, 21.5, 12.3, 0.875, 0.550, 2670, 249, 279, 9.05, 274, 44.5, 2.90),
    ("W21x122", 122.0, 35.9, 21.7, 12.4, 0.960, 0.600, 2960, 273, 307, 9.09, 305, 49.2, 2.92),
    ("W21x132", 132.0, 38.8, 21.8, 12.4, 1.04, 0.650, 3220, 295, 333, 9.12, 333, 53.5, 2.93),

    # W24 series
    ("W24x55", 55.0, 16.2, 23.6, 7.01, 0.505, 0.395, 1350, 114, 134, 9.11, 29.1, 8.30, 1.34),
    ("W24x62", 62.0, 18.2, 23.7, 7.04, 0.590, 0.430, 1550, 131, 153, 9.23, 34.5, 9.80, 1.38),
    ("W24x68", 68.0, 20.1, 23.7, 8.97, 0.585, 0.415, 1830, 154, 177, 9.55, 70.4, 15.7, 1.87),
    ("W24x76", 76.0, 22.4, 23.9, 8.99, 0.680, 0.440, 2100, 176, 200, 9.69, 82.5, 18.4, 1.92),
    ("W24x84", 84.0, 24.7, 24.1, 9.02, 0.770, 0.470, 2370, 196, 224, 9.79, 94.4, 20.9, 1.95),
    ("W24x94", 94.0, 27.7, 24.3, 9.07, 0.875, 0.515, 2700, 222, 254, 9.87, 109, 24.0, 1.98),
    ("W24x104", 104.0, 30.6, 24.1, 12.8, 0.750, 0.500, 3100, 258, 289, 10.1, 259, 40.7, 2.91),
    ("W24x117", 117.0, 34.4, 24.3, 12.8, 0.850, 0.550, 3540, 291, 327, 10.1, 297, 46.5, 2.94),
    ("W24x131", 131.0, 38.5, 24.5, 12.9, 0.960, 0.605, 4020, 329, 370, 10.2, 340, 52.6, 2.97),
    ("W24x146", 146.0, 43.0, 24.7, 12.9, 1.09, 0.650, 4580, 371, 418, 10.3, 391, 60.5, 3.01),
    ("W24x162", 162.0, 47.7, 25.0, 13.0, 1.22, 0.705, 5170, 414, 468, 10.4, 443, 68.4, 3.05),
]


def load_w_catalog() -> List[Section]:
    """
    Load W-shape catalog per AISC Steel Construction Manual.

    Returns comprehensive list of wide flange shapes commonly used
    in sign structure cantilevers and support beams.

    Material: ASTM A992 (Fy = 50 ksi)
    """
    sections: List[Section] = []
    fy = SteelGrade.A992.fy_psi  # 50,000 psi

    for data in W_SHAPES:
        designation = data[0]
        weight = data[1]
        ix = data[7]  # Ix is at index 7
        sx = data[8]  # Sx is at index 8

        sections.append(Section(
            family="W",
            designation=designation,
            weight_lbf=weight,
            Sx_in3=sx,
            Ix_in4=ix,
            fy_psi=fy,
        ))

    return sections


# =============================================================================
# HSS SECTIONS - AISC Database v16.0
# ASTM A500 Grade C: Fy = 50 ksi (Round), Fy = 50 ksi (Square/Rect)
# =============================================================================

# Round HSS (Hollow Structural Sections)
# (designation, OD_in, t_in, A_in2, W_lb/ft, I_in4, S_in3, r_in, Z_in3, J_in4, C_in3)
HSS_ROUND: List[Tuple] = [
    ("HSS2.375x0.154", 2.375, 0.154, 1.07, 3.65, 0.627, 0.528, 0.765, 0.717, 1.25, 1.06),
    ("HSS2.875x0.203", 2.875, 0.203, 1.70, 5.79, 1.45, 1.01, 0.922, 1.37, 2.90, 2.01),
    ("HSS3.000x0.216", 3.000, 0.216, 1.89, 6.43, 1.77, 1.18, 0.968, 1.60, 3.53, 2.36),
    ("HSS3.500x0.216", 3.500, 0.216, 2.23, 7.58, 2.91, 1.67, 1.14, 2.24, 5.83, 3.33),
    ("HSS3.500x0.250", 3.500, 0.250, 2.55, 8.68, 3.26, 1.86, 1.13, 2.52, 6.52, 3.73),
    ("HSS3.500x0.300", 3.500, 0.300, 3.02, 10.26, 3.74, 2.14, 1.11, 2.92, 7.48, 4.27),
    ("HSS4.000x0.226", 4.000, 0.226, 2.68, 9.11, 4.58, 2.29, 1.31, 3.06, 9.16, 4.58),
    ("HSS4.000x0.250", 4.000, 0.250, 2.95, 10.01, 4.99, 2.49, 1.30, 3.34, 9.97, 4.99),
    ("HSS4.000x0.313", 4.000, 0.313, 3.63, 12.33, 5.95, 2.97, 1.28, 4.02, 11.9, 5.95),
    ("HSS4.500x0.237", 4.500, 0.237, 3.17, 10.79, 6.86, 3.05, 1.47, 4.06, 13.7, 6.10),
    ("HSS4.500x0.250", 4.500, 0.250, 3.34, 11.36, 7.19, 3.20, 1.47, 4.26, 14.4, 6.39),
    ("HSS4.500x0.337", 4.500, 0.337, 4.41, 14.98, 9.12, 4.05, 1.44, 5.48, 18.2, 8.10),
    ("HSS5.000x0.258", 5.000, 0.258, 3.85, 13.09, 10.4, 4.14, 1.64, 5.49, 20.7, 8.29),
    ("HSS5.000x0.312", 5.000, 0.312, 4.59, 15.62, 12.1, 4.85, 1.63, 6.44, 24.3, 9.70),
    ("HSS5.000x0.375", 5.000, 0.375, 5.45, 18.52, 14.0, 5.59, 1.60, 7.49, 27.9, 11.2),
    ("HSS5.563x0.258", 5.563, 0.258, 4.30, 14.62, 14.5, 5.21, 1.84, 6.89, 29.0, 10.4),
    ("HSS5.563x0.375", 5.563, 0.375, 6.11, 20.78, 19.8, 7.11, 1.80, 9.52, 39.5, 14.2),
    ("HSS5.563x0.500", 5.563, 0.500, 7.95, 27.04, 24.6, 8.85, 1.76, 11.9, 49.2, 17.7),
    ("HSS6.000x0.280", 6.000, 0.280, 5.03, 17.12, 19.4, 6.48, 1.97, 8.54, 38.9, 13.0),
    ("HSS6.000x0.375", 6.000, 0.375, 6.62, 22.51, 24.8, 8.26, 1.93, 11.0, 49.5, 16.5),
    ("HSS6.000x0.500", 6.000, 0.500, 8.64, 29.35, 31.2, 10.4, 1.90, 14.0, 62.4, 20.8),
    ("HSS6.625x0.280", 6.625, 0.280, 5.58, 18.97, 26.4, 7.98, 2.18, 10.5, 52.9, 15.9),
    ("HSS6.625x0.375", 6.625, 0.375, 7.36, 25.03, 33.8, 10.2, 2.14, 13.5, 67.7, 20.4),
    ("HSS6.625x0.432", 6.625, 0.432, 8.40, 28.57, 38.0, 11.5, 2.13, 15.3, 76.0, 22.9),
    ("HSS6.625x0.500", 6.625, 0.500, 9.62, 32.71, 42.8, 12.9, 2.11, 17.3, 85.5, 25.8),
    ("HSS7.000x0.375", 7.000, 0.375, 7.80, 26.52, 40.2, 11.5, 2.27, 15.2, 80.4, 22.9),
    ("HSS7.000x0.500", 7.000, 0.500, 10.21, 34.71, 51.0, 14.6, 2.23, 19.5, 102, 29.2),
    ("HSS7.500x0.375", 7.500, 0.375, 8.38, 28.51, 50.0, 13.3, 2.44, 17.6, 100, 26.6),
    ("HSS7.500x0.500", 7.500, 0.500, 11.00, 37.40, 63.8, 17.0, 2.41, 22.7, 128, 34.0),
    ("HSS8.625x0.250", 8.625, 0.250, 6.58, 22.36, 57.7, 13.4, 2.96, 17.5, 115, 26.8),
    ("HSS8.625x0.322", 8.625, 0.322, 8.40, 28.55, 71.8, 16.7, 2.92, 21.9, 144, 33.3),
    ("HSS8.625x0.375", 8.625, 0.375, 9.72, 33.04, 82.2, 19.1, 2.91, 25.1, 164, 38.1),
    ("HSS8.625x0.500", 8.625, 0.500, 12.76, 43.39, 105, 24.3, 2.86, 32.2, 210, 48.6),
    ("HSS8.625x0.625", 8.625, 0.625, 15.69, 53.35, 126, 29.1, 2.83, 38.8, 251, 58.3),
    ("HSS10.000x0.375", 10.000, 0.375, 11.3, 38.55, 130, 26.0, 3.39, 34.1, 260, 52.1),
    ("HSS10.000x0.500", 10.000, 0.500, 14.9, 50.87, 168, 33.5, 3.35, 44.3, 335, 67.1),
    ("HSS10.750x0.250", 10.750, 0.250, 8.24, 28.03, 117, 21.8, 3.77, 28.3, 234, 43.6),
    ("HSS10.750x0.375", 10.750, 0.375, 12.2, 41.59, 170, 31.6, 3.73, 41.4, 339, 63.2),
    ("HSS10.750x0.500", 10.750, 0.500, 16.1, 54.74, 220, 40.8, 3.69, 53.9, 439, 81.6),
    ("HSS12.750x0.375", 12.750, 0.375, 14.6, 49.56, 289, 45.4, 4.45, 59.2, 579, 90.8),
    ("HSS12.750x0.500", 12.750, 0.500, 19.2, 65.42, 375, 58.8, 4.41, 77.1, 750, 118),
    ("HSS14.000x0.375", 14.000, 0.375, 16.1, 54.57, 385, 55.0, 4.89, 71.6, 770, 110),
    ("HSS14.000x0.500", 14.000, 0.500, 21.2, 72.09, 501, 71.5, 4.86, 93.5, 1000, 143),
    ("HSS16.000x0.375", 16.000, 0.375, 18.4, 62.58, 581, 72.6, 5.62, 94.2, 1160, 145),
    ("HSS16.000x0.500", 16.000, 0.500, 24.3, 82.77, 757, 94.7, 5.58, 123, 1510, 189),
]

# Square HSS
# (designation, B_in, t_in, A_in2, W_lb/ft, Ix_in4, Sx_in3, rx_in, Zx_in3)
HSS_SQUARE: List[Tuple] = [
    ("HSS2x2x1/8", 2.0, 0.116, 0.840, 2.86, 0.486, 0.486, 0.761, 0.593),
    ("HSS2x2x3/16", 2.0, 0.174, 1.19, 4.07, 0.641, 0.641, 0.733, 0.802),
    ("HSS2x2x1/4", 2.0, 0.233, 1.51, 5.14, 0.747, 0.747, 0.704, 0.963),
    ("HSS2-1/2x2-1/2x1/8", 2.5, 0.116, 1.07, 3.63, 1.01, 0.805, 0.973, 0.960),
    ("HSS2-1/2x2-1/2x3/16", 2.5, 0.174, 1.53, 5.21, 1.37, 1.10, 0.945, 1.33),
    ("HSS2-1/2x2-1/2x1/4", 2.5, 0.233, 1.95, 6.64, 1.65, 1.32, 0.918, 1.64),
    ("HSS3x3x1/8", 3.0, 0.116, 1.30, 4.40, 1.82, 1.22, 1.19, 1.43),
    ("HSS3x3x3/16", 3.0, 0.174, 1.87, 6.36, 2.52, 1.68, 1.16, 2.00),
    ("HSS3x3x1/4", 3.0, 0.233, 2.40, 8.15, 3.10, 2.06, 1.14, 2.51),
    ("HSS3x3x5/16", 3.0, 0.291, 2.89, 9.82, 3.58, 2.39, 1.11, 2.95),
    ("HSS3x3x3/8", 3.0, 0.349, 3.34, 11.4, 3.96, 2.64, 1.09, 3.34),
    ("HSS3-1/2x3-1/2x1/8", 3.5, 0.116, 1.52, 5.18, 2.98, 1.70, 1.40, 1.98),
    ("HSS3-1/2x3-1/2x3/16", 3.5, 0.174, 2.21, 7.51, 4.16, 2.38, 1.37, 2.79),
    ("HSS3-1/2x3-1/2x1/4", 3.5, 0.233, 2.85, 9.70, 5.19, 2.96, 1.35, 3.52),
    ("HSS3-1/2x3-1/2x5/16", 3.5, 0.291, 3.45, 11.7, 6.06, 3.46, 1.33, 4.18),
    ("HSS3-1/2x3-1/2x3/8", 3.5, 0.349, 4.00, 13.6, 6.79, 3.88, 1.30, 4.77),
    ("HSS4x4x1/8", 4.0, 0.116, 1.75, 5.95, 4.52, 2.26, 1.61, 2.62),
    ("HSS4x4x3/16", 4.0, 0.174, 2.55, 8.66, 6.36, 3.18, 1.58, 3.71),
    ("HSS4x4x1/4", 4.0, 0.233, 3.31, 11.3, 8.00, 4.00, 1.56, 4.70),
    ("HSS4x4x5/16", 4.0, 0.291, 4.02, 13.7, 9.42, 4.71, 1.53, 5.59),
    ("HSS4x4x3/8", 4.0, 0.349, 4.69, 15.9, 10.7, 5.32, 1.51, 6.41),
    ("HSS4x4x1/2", 4.0, 0.465, 5.96, 20.3, 12.8, 6.39, 1.46, 7.82),
    ("HSS4-1/2x4-1/2x3/16", 4.5, 0.174, 2.89, 9.82, 9.26, 4.12, 1.79, 4.79),
    ("HSS4-1/2x4-1/2x1/4", 4.5, 0.233, 3.76, 12.8, 11.8, 5.23, 1.77, 6.13),
    ("HSS4-1/2x4-1/2x5/16", 4.5, 0.291, 4.58, 15.6, 13.9, 6.18, 1.74, 7.33),
    ("HSS4-1/2x4-1/2x3/8", 4.5, 0.349, 5.36, 18.2, 15.9, 7.05, 1.72, 8.44),
    ("HSS4-1/2x4-1/2x1/2", 4.5, 0.465, 6.85, 23.3, 19.3, 8.57, 1.68, 10.4),
    ("HSS5x5x3/16", 5.0, 0.174, 3.23, 11.0, 13.0, 5.20, 2.01, 6.00),
    ("HSS5x5x1/4", 5.0, 0.233, 4.21, 14.3, 16.6, 6.65, 1.99, 7.71),
    ("HSS5x5x5/16", 5.0, 0.291, 5.15, 17.5, 19.8, 7.92, 1.96, 9.27),
    ("HSS5x5x3/8", 5.0, 0.349, 6.03, 20.5, 22.7, 9.07, 1.94, 10.7),
    ("HSS5x5x1/2", 5.0, 0.465, 7.75, 26.4, 28.0, 11.2, 1.90, 13.4),
    ("HSS6x6x3/16", 6.0, 0.174, 3.91, 13.3, 23.2, 7.75, 2.44, 8.86),
    ("HSS6x6x1/4", 6.0, 0.233, 5.11, 17.4, 29.9, 9.99, 2.42, 11.5),
    ("HSS6x6x5/16", 6.0, 0.291, 6.26, 21.3, 35.9, 12.0, 2.39, 13.9),
    ("HSS6x6x3/8", 6.0, 0.349, 7.36, 25.0, 41.4, 13.8, 2.37, 16.1),
    ("HSS6x6x1/2", 6.0, 0.465, 9.53, 32.4, 51.8, 17.3, 2.33, 20.4),
    ("HSS6x6x5/8", 6.0, 0.581, 11.5, 39.2, 60.3, 20.1, 2.29, 24.1),
    ("HSS7x7x3/16", 7.0, 0.174, 4.59, 15.6, 37.4, 10.7, 2.85, 12.2),
    ("HSS7x7x1/4", 7.0, 0.233, 6.01, 20.4, 48.5, 13.9, 2.84, 15.8),
    ("HSS7x7x5/16", 7.0, 0.291, 7.38, 25.1, 58.5, 16.7, 2.82, 19.2),
    ("HSS7x7x3/8", 7.0, 0.349, 8.69, 29.5, 67.7, 19.4, 2.79, 22.4),
    ("HSS7x7x1/2", 7.0, 0.465, 11.3, 38.5, 85.8, 24.5, 2.75, 28.6),
    ("HSS7x7x5/8", 7.0, 0.581, 13.8, 46.8, 101, 28.9, 2.71, 34.1),
    ("HSS8x8x3/16", 8.0, 0.174, 5.26, 17.9, 56.4, 14.1, 3.27, 16.0),
    ("HSS8x8x1/4", 8.0, 0.233, 6.91, 23.5, 73.3, 18.3, 3.26, 20.8),
    ("HSS8x8x5/16", 8.0, 0.291, 8.49, 28.9, 88.8, 22.2, 3.23, 25.4),
    ("HSS8x8x3/8", 8.0, 0.349, 10.0, 34.1, 103, 25.7, 3.21, 29.6),
    ("HSS8x8x1/2", 8.0, 0.465, 13.1, 44.6, 131, 32.7, 3.16, 38.0),
    ("HSS8x8x5/8", 8.0, 0.581, 16.0, 54.4, 156, 38.9, 3.12, 45.6),
    ("HSS9x9x3/8", 9.0, 0.349, 11.4, 38.6, 150, 33.3, 3.63, 38.1),
    ("HSS9x9x1/2", 9.0, 0.465, 14.9, 50.7, 192, 42.6, 3.59, 49.2),
    ("HSS9x9x5/8", 9.0, 0.581, 18.2, 62.0, 230, 51.1, 3.55, 59.4),
    ("HSS10x10x3/8", 10.0, 0.349, 12.7, 43.1, 210, 42.0, 4.07, 47.8),
    ("HSS10x10x1/2", 10.0, 0.465, 16.7, 56.8, 271, 54.1, 4.03, 62.1),
    ("HSS10x10x5/8", 10.0, 0.581, 20.5, 69.6, 326, 65.1, 3.99, 75.3),
    ("HSS12x12x3/8", 12.0, 0.349, 15.3, 52.2, 375, 62.5, 4.94, 70.6),
    ("HSS12x12x1/2", 12.0, 0.465, 20.3, 69.0, 487, 81.2, 4.90, 92.1),
    ("HSS12x12x5/8", 12.0, 0.581, 24.9, 84.8, 591, 98.5, 4.87, 113),
]


def load_tube_catalog() -> List[Section]:
    """
    Load HSS (tube) sections from AISC database.

    Includes both round and square HSS sections commonly used
    in sign structure posts and chords.

    Material: ASTM A500 Grade C (Fy = 50 ksi)
    """
    sections: List[Section] = []
    fy = SteelGrade.A500_C.fy_psi  # 50,000 psi

    # Round HSS
    for data in HSS_ROUND:
        designation, od, t, a, w, ix, sx, rx, zx, j, c = data
        sections.append(Section(
            family="tube",
            designation=designation,
            weight_lbf=w,
            Sx_in3=sx,
            Ix_in4=ix,
            fy_psi=fy,
        ))

    # Square HSS
    for data in HSS_SQUARE:
        designation, b, t, a, w, ix, sx, rx, zx = data
        sections.append(Section(
            family="tube",
            designation=designation,
            weight_lbf=w,
            Sx_in3=sx,
            Ix_in4=ix,
            fy_psi=fy,
        ))

    return sections


# =============================================================================
# CHANNEL SECTIONS - For framing and secondary members
# =============================================================================

# C-shapes (American Standard Channels)
# (designation, W_lb/ft, A_in2, d_in, bf_in, tf_in, tw_in, Ix_in4, Sx_in3, rx_in)
C_SHAPES: List[Tuple] = [
    ("C3x4.1", 4.1, 1.21, 3.00, 1.41, 0.273, 0.170, 1.66, 1.10, 1.17),
    ("C3x5", 5.0, 1.47, 3.00, 1.50, 0.273, 0.258, 1.85, 1.24, 1.12),
    ("C3x6", 6.0, 1.76, 3.00, 1.60, 0.273, 0.356, 2.07, 1.38, 1.08),
    ("C4x5.4", 5.4, 1.59, 4.00, 1.58, 0.296, 0.184, 3.85, 1.93, 1.56),
    ("C4x7.25", 7.25, 2.13, 4.00, 1.72, 0.296, 0.321, 4.59, 2.29, 1.47),
    ("C5x6.7", 6.7, 1.97, 5.00, 1.75, 0.320, 0.190, 7.49, 3.00, 1.95),
    ("C5x9", 9.0, 2.64, 5.00, 1.89, 0.320, 0.325, 8.90, 3.56, 1.83),
    ("C6x8.2", 8.2, 2.40, 6.00, 1.92, 0.343, 0.200, 13.1, 4.38, 2.34),
    ("C6x10.5", 10.5, 3.09, 6.00, 2.03, 0.343, 0.314, 15.2, 5.06, 2.22),
    ("C6x13", 13.0, 3.83, 6.00, 2.16, 0.343, 0.437, 17.4, 5.80, 2.13),
    ("C7x9.8", 9.8, 2.87, 7.00, 2.09, 0.366, 0.210, 21.3, 6.08, 2.72),
    ("C7x12.25", 12.25, 3.60, 7.00, 2.19, 0.366, 0.314, 24.2, 6.93, 2.60),
    ("C7x14.75", 14.75, 4.33, 7.00, 2.30, 0.366, 0.419, 27.2, 7.78, 2.51),
    ("C8x11.5", 11.5, 3.38, 8.00, 2.26, 0.390, 0.220, 32.6, 8.14, 3.11),
    ("C8x13.75", 13.75, 4.04, 8.00, 2.34, 0.390, 0.303, 36.1, 9.03, 2.99),
    ("C8x18.75", 18.75, 5.51, 8.00, 2.53, 0.390, 0.487, 44.0, 11.0, 2.82),
    ("C9x13.4", 13.4, 3.94, 9.00, 2.43, 0.413, 0.233, 47.9, 10.6, 3.48),
    ("C9x15", 15.0, 4.41, 9.00, 2.49, 0.413, 0.285, 51.0, 11.3, 3.40),
    ("C9x20", 20.0, 5.88, 9.00, 2.65, 0.413, 0.448, 60.9, 13.5, 3.22),
    ("C10x15.3", 15.3, 4.49, 10.00, 2.60, 0.436, 0.240, 67.4, 13.5, 3.87),
    ("C10x20", 20.0, 5.88, 10.00, 2.74, 0.436, 0.379, 78.9, 15.8, 3.66),
    ("C10x25", 25.0, 7.35, 10.00, 2.89, 0.436, 0.526, 91.2, 18.2, 3.52),
    ("C10x30", 30.0, 8.82, 10.00, 3.03, 0.436, 0.673, 103, 20.7, 3.42),
    ("C12x20.7", 20.7, 6.09, 12.00, 2.94, 0.501, 0.282, 129, 21.5, 4.61),
    ("C12x25", 25.0, 7.35, 12.00, 3.05, 0.501, 0.387, 144, 24.1, 4.43),
    ("C12x30", 30.0, 8.82, 12.00, 3.17, 0.501, 0.510, 162, 27.0, 4.29),
    ("C15x33.9", 33.9, 9.96, 15.00, 3.40, 0.650, 0.400, 315, 42.0, 5.62),
    ("C15x40", 40.0, 11.8, 15.00, 3.52, 0.650, 0.520, 348, 46.5, 5.44),
    ("C15x50", 50.0, 14.7, 15.00, 3.72, 0.650, 0.716, 404, 53.8, 5.24),
]


def load_channel_catalog() -> List[Section]:
    """
    Load C-shape (channel) sections from AISC database.

    Material: ASTM A36 (Fy = 36 ksi)
    """
    sections: List[Section] = []
    fy = SteelGrade.A36.fy_psi  # 36,000 psi

    for data in C_SHAPES:
        designation, w, a, d, bf, tf, tw, ix, sx, rx = data
        sections.append(Section(
            family="C",
            designation=designation,
            weight_lbf=w,
            Sx_in3=sx,
            Ix_in4=ix,
            fy_psi=fy,
        ))

    return sections


# =============================================================================
# ANGLE SECTIONS - For bracing and connections
# =============================================================================

# L-shapes (Equal leg angles)
# (designation, W_lb/ft, A_in2, Ix_in4, Sx_in3, rx_in)
L_SHAPES: List[Tuple] = [
    ("L2x2x1/8", 0.81, 0.241, 0.190, 0.131, 0.889),
    ("L2x2x3/16", 1.19, 0.355, 0.272, 0.190, 0.875),
    ("L2x2x1/4", 1.55, 0.463, 0.348, 0.247, 0.866),
    ("L2x2x5/16", 1.90, 0.566, 0.416, 0.300, 0.857),
    ("L2x2x3/8", 2.23, 0.666, 0.479, 0.351, 0.849),
    ("L2-1/2x2-1/2x3/16", 1.52, 0.451, 0.547, 0.303, 1.10),
    ("L2-1/2x2-1/2x1/4", 2.00, 0.590, 0.703, 0.394, 1.09),
    ("L2-1/2x2-1/2x5/16", 2.46, 0.725, 0.849, 0.482, 1.08),
    ("L2-1/2x2-1/2x3/8", 2.91, 0.856, 0.984, 0.566, 1.07),
    ("L3x3x3/16", 1.85, 0.547, 0.984, 0.458, 1.34),
    ("L3x3x1/4", 2.43, 0.717, 1.27, 0.596, 1.33),
    ("L3x3x5/16", 3.00, 0.883, 1.53, 0.728, 1.32),
    ("L3x3x3/8", 3.55, 1.05, 1.78, 0.854, 1.30),
    ("L3x3x1/2", 4.60, 1.37, 2.22, 1.07, 1.27),
    ("L3-1/2x3-1/2x1/4", 2.87, 0.844, 2.08, 0.831, 1.57),
    ("L3-1/2x3-1/2x5/16", 3.54, 1.04, 2.52, 1.02, 1.56),
    ("L3-1/2x3-1/2x3/8", 4.21, 1.24, 2.95, 1.20, 1.54),
    ("L3-1/2x3-1/2x1/2", 5.49, 1.62, 3.72, 1.52, 1.52),
    ("L4x4x1/4", 3.30, 0.971, 3.17, 1.11, 1.81),
    ("L4x4x5/16", 4.08, 1.20, 3.87, 1.36, 1.80),
    ("L4x4x3/8", 4.86, 1.43, 4.52, 1.60, 1.78),
    ("L4x4x1/2", 6.37, 1.88, 5.72, 2.04, 1.75),
    ("L4x4x5/8", 7.84, 2.31, 6.81, 2.44, 1.72),
    ("L4x4x3/4", 9.25, 2.73, 7.78, 2.81, 1.69),
    ("L5x5x5/16", 5.16, 1.52, 7.78, 2.17, 2.26),
    ("L5x5x3/8", 6.16, 1.81, 9.18, 2.58, 2.25),
    ("L5x5x1/2", 8.12, 2.39, 11.8, 3.33, 2.22),
    ("L5x5x5/8", 10.0, 2.96, 14.2, 4.03, 2.19),
    ("L5x5x3/4", 11.9, 3.50, 16.4, 4.68, 2.16),
    ("L6x6x3/8", 7.45, 2.19, 16.2, 3.75, 2.72),
    ("L6x6x1/2", 9.87, 2.91, 21.1, 4.90, 2.69),
    ("L6x6x5/8", 12.2, 3.61, 25.6, 5.97, 2.66),
    ("L6x6x3/4", 14.5, 4.28, 29.8, 6.97, 2.64),
    ("L6x6x1", 19.0, 5.59, 37.2, 8.75, 2.58),
    ("L8x8x1/2", 13.3, 3.93, 51.7, 8.94, 3.63),
    ("L8x8x5/8", 16.5, 4.87, 63.5, 11.0, 3.61),
    ("L8x8x3/4", 19.7, 5.80, 74.7, 13.0, 3.58),
    ("L8x8x1", 26.0, 7.62, 95.5, 16.7, 3.54),
]


def load_angle_catalog() -> List[Section]:
    """
    Load L-shape (angle) sections from AISC database.

    Material: ASTM A36 (Fy = 36 ksi)
    """
    sections: List[Section] = []
    fy = SteelGrade.A36.fy_psi  # 36,000 psi

    for data in L_SHAPES:
        designation, w, a, ix, sx, rx = data
        sections.append(Section(
            family="L",
            designation=designation,
            weight_lbf=w,
            Sx_in3=sx,
            Ix_in4=ix,
            fy_psi=fy,
        ))

    return sections


# =============================================================================
# CATALOG AGGREGATION
# =============================================================================

def catalogs_for_order(order: Iterable[str]) -> List[Section]:
    """
    Get combined section catalog for specified shape families.

    Args:
        order: Iterable of shape family names ("pipe", "W", "tube", "C", "L")

    Returns:
        Combined list of Section objects, sorted by weight (ascending)
    """
    order_list = list(order)
    cat: List[Section] = []

    for fam in order_list:
        fam_lower = fam.lower()
        if fam_lower == "pipe":
            cat.extend(load_pipe_catalog())
        elif fam_lower == "w":
            cat.extend(load_w_catalog())
        elif fam_lower in ("tube", "hss"):
            cat.extend(load_tube_catalog())
        elif fam_lower == "c":
            cat.extend(load_channel_catalog())
        elif fam_lower == "l":
            cat.extend(load_angle_catalog())

    # Sort ascending by weight for optimization
    return sorted(cat, key=lambda s: s.weight_lbf)


def get_all_sections() -> List[Section]:
    """
    Get complete catalog of all section types.

    Returns all available sections sorted by weight.
    """
    return catalogs_for_order(["pipe", "W", "tube", "C", "L"])


def find_section(designation: str) -> Optional[Section]:
    """
    Find a specific section by designation.

    Args:
        designation: Section designation (e.g., "W10x26", "HSS6x6x1/4")

    Returns:
        Section if found, None otherwise
    """
    all_sections = get_all_sections()
    for section in all_sections:
        if section.designation.lower() == designation.lower():
            return section
    return None


def select_section_for_moment(
    Mu_inlb: float,
    family: str = "W",
    phi: float = 0.9,
) -> Optional[Section]:
    """
    Select the lightest section that satisfies moment demand.

    Uses AISC 360-22 LRFD design:
        φMn ≥ Mu
        φMn = φ × Fy × Sx (yield limit state)

    Args:
        Mu_inlb: Required moment capacity (in-lb)
        family: Shape family to select from
        phi: Resistance factor (default 0.9 for flexure)

    Returns:
        Lightest adequate Section, or None if none found
    """
    sections = catalogs_for_order([family])

    for section in sections:
        phi_Mn = phi * section.fy_psi * section.Sx_in3
        if phi_Mn >= Mu_inlb:
            return section

    return None


def select_section_for_deflection(
    M_inlb: float,
    L_in: float,
    delta_max_in: float,
    E_psi: float = 29_000_000,
    family: str = "W",
) -> Optional[Section]:
    """
    Select the lightest section that satisfies deflection limit.

    For simply-supported beam with uniform moment:
        δ = M × L² / (8 × E × I)

    Args:
        M_inlb: Applied moment (in-lb)
        L_in: Span length (in)
        delta_max_in: Maximum allowable deflection (in)
        E_psi: Modulus of elasticity (psi), default 29,000 ksi
        family: Shape family to select from

    Returns:
        Lightest adequate Section, or None if none found
    """
    # Required Ix for deflection limit
    Ix_required = M_inlb * (L_in ** 2) / (8 * E_psi * delta_max_in)

    sections = catalogs_for_order([family])

    for section in sections:
        if section.Ix_in4 >= Ix_required:
            return section

    return None
```

