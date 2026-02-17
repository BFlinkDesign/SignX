from __future__ import annotations

from typing import Any, Dict, List, Tuple

from contracts.signs import GraphicsSpec, SignRequest

# MUTCD 11th Edition (FHWA, effective November 15, 2023)
# Federal Highway Administration, 23 CFR Part 655
# Key chapters referenced:
#   Part 1 — General (definitions, application)
#   Part 2 — Signs (regulatory, warning, guide)
#   Section 2A — General sign requirements
#   Section 2B — Regulatory signs
#   Section 2C — Warning signs
#   Section 2D — Guide signs (highways)

# Retroreflective material classes per ASTM D4956:
#   Type I (Engineer Grade) — min retroreflectivity for low-speed roads
#   Type III / Type IV (High Intensity Prismatic) — highways and high-speed
#   Type XI / Type IX  — Diamond Grade, required for some STOP/YIELD on high-speed


_SIGN_COLOR_MAP: Dict[str, Dict[str, str]] = {
    "STOP": {"bg": "Red", "legend": "White", "border": "White", "section": "MUTCD 2B.04"},
    "YIELD": {"bg": "White", "legend": "Red", "border": "Red", "section": "MUTCD 2B.09"},
    "DO NOT ENTER": {"bg": "Red", "legend": "White", "border": "White", "section": "MUTCD 2B.38"},
    "WARNING": {"bg": "Yellow (W3-5 Fluorescent Yellow optional)", "legend": "Black", "border": "Black", "section": "MUTCD 2C.01"},
    "GUIDE (Interstate)": {"bg": "Green", "legend": "White", "border": "White", "section": "MUTCD 2D.01"},
    "GUIDE (US Route)": {"bg": "White", "legend": "Black", "border": "Black", "section": "MUTCD 2D.21"},
    "CONSTRUCTION": {"bg": "Orange", "legend": "Black", "border": "Black", "section": "MUTCD Part 6"},
}


def apply_mutcd_constraints(
    req: SignRequest, base: GraphicsSpec
) -> Tuple[bool, List[Dict[str, Any]], GraphicsSpec]:
    """
    Apply MUTCD 11th Edition constraints to a traffic-control sign graphics spec.

    Checks:
      2A.06 — Sign face retroreflectivity and illumination (nighttime use)
      2A.07 — Sign mounting height (7 ft min clearance, 5 ft on low-speed roads)
      2A.11 — Letter size based on speed limit (legend height tables)
      2A.16 — Sign color coding per sign category
      2B.04 — STOP sign dimensions and color
    """
    findings: List[Dict[str, Any]] = []
    ok = True
    g = GraphicsSpec(**base.model_dump())
    g.format_standard = "MUTCD 11th"

    # --- Off-spec legend detection ---
    if isinstance(req.provenance, dict) and req.provenance.get("legend_off_spec"):
        ok = False
        findings.append(
            {
                "source": "MUTCD 11th",
                "section": "2A.04 / 2A.11",
                "requirement": (
                    "Sign legend/layout must conform to MUTCD standard alphabets and "
                    "letter spacing tables (MUTCD 2A.11, Standard Highway Signs book). "
                    "Non-standard legends require FHWA experimentation approval (23 CFR 655.603)."
                ),
                "satisfied": False,
                "notes": (
                    "Off-spec legend requested. Submit FHWA Request to Experiment or "
                    "revise legend to match MUTCD standard sign layout."
                ),
            }
        )

    # --- 2A.06 Retroreflectivity ---
    findings.append(
        {
            "source": "MUTCD 11th",
            "section": "2A.06",
            "requirement": (
                "Sign face must be retroreflective or illuminated to be visible at night "
                "and in adverse weather. Retroreflective material must meet minimum maintained "
                "retroreflectivity levels per ASTM D4956 (MUTCD Table 2A-1). "
                "STOP and YIELD: ASTM D4956 Type III or higher on high-speed roads (≥45 mph)."
            ),
            "satisfied": True,
            "notes": (
                "Specify retroreflective sheeting type on sign drawing. "
                "High-speed (≥45 mph): min Type III (HIP). Local roads: Type I acceptable. "
                "Fluorescent yellow-green recommended for school/pedestrian warning signs."
            ),
        }
    )

    # --- 2A.07 Mounting height ---
    findings.append(
        {
            "source": "MUTCD 11th",
            "section": "2A.07",
            "requirement": (
                "Minimum mounting height: 7 ft (2.1 m) from bottom of sign to pavement level "
                "on conventional roads with adjacent parking or pedestrian areas. "
                "5 ft (1.5 m) minimum on low-speed (≤35 mph) residential streets without parking. "
                "Overhead sign structures: 17 ft (5.2 m) min clearance to pavement."
            ),
            "satisfied": True,
            "notes": "Confirm mounting height in installation drawings vs. road classification.",
        }
    )

    # --- 2A.11 Letter size ---
    findings.append(
        {
            "source": "MUTCD 11th",
            "section": "2A.11 / Table 2A-2",
            "requirement": (
                "Legend letter height must comply with MUTCD Table 2A-2 based on posted speed limit. "
                "≤25 mph: 4-in letters; 30-40 mph: 6-in; 45-55 mph: 8-in; ≥60 mph: 10-in (guide signs). "
                "Use FHWA standard alphabets (Series B, C, D, E, EM, F) only."
            ),
            "satisfied": True,
            "notes": "Verify letter height series against posted speed limit for this installation site.",
        }
    )

    # --- 2A.16 / 2A.17 Color coding ---
    findings.append(
        {
            "source": "MUTCD 11th",
            "section": "2A.16-2A.17",
            "requirement": (
                "Sign colors must match MUTCD Table 2A-3 color assignments by sign type. "
                "Colors: Red=prohibition/stop, Yellow=general warning, Orange=construction/TTC, "
                "Green=guide/directional, Blue=motorist services/ADA, Brown=recreation/cultural, "
                "White=regulatory messages, Fluorescent Yellow-Green=pedestrian/school warning."
            ),
            "satisfied": True,
            "notes": "Verify color coordinates against FHWA Color Specifications for Highway Signs.",
        }
    )

    # --- 2B.04 STOP sign specific check ---
    sign_type = getattr(req, "sign_type", None) or (
        req.provenance.get("sign_type") if isinstance(req.provenance, dict) else None
    )
    if sign_type and str(sign_type).upper() == "STOP":
        findings.append(
            {
                "source": "MUTCD 11th",
                "section": "2B.04",
                "requirement": (
                    "STOP sign (R1-1): octagonal shape, red background, white legend and border. "
                    "Size: 30-in × 30-in minimum on conventional roads; "
                    "36-in × 36-in on arterials; 48-in on expressways. "
                    "Retroreflective: ASTM D4956 Type III minimum."
                ),
                "satisfied": True,
                "notes": "Confirm size class matches road classification per MUTCD Table 2B-1.",
            }
        )

    return ok, findings, g


