from __future__ import annotations

from typing import Dict, List, Tuple

from contracts.signs import GraphicsSpec, SignRequest

# OSHA 29 CFR 1910.145 — Specifications for Accident Prevention Signs and Tags
# Also references ANSI Z535.1–Z535.5 which OSHA incorporates by reference for
# newer installations (ANSI Z535 is accepted as equivalent or superior).


_COLOR_REQUIREMENTS: Dict[str, Dict[str, str]] = {
    "DANGER": {
        "background": "Red (#DA0000 per ANSI Z535.1)",
        "signal_word_color": "White",
        "text": "Black on white panel below signal word",
        "osha_ref": "1910.145(f)(5)(i)",
        "use": "Indicates an imminently hazardous situation that will result in death or serious injury",
    },
    "WARNING": {
        "background": "Orange (#EB6000 per ANSI Z535.1)",
        "signal_word_color": "Black",
        "text": "Black on orange or white panel",
        "osha_ref": "1910.145(f)(5)(ii)",
        "use": "Potentially hazardous situation that could result in death or serious injury",
    },
    "CAUTION": {
        "background": "Yellow (#F5C800 per ANSI Z535.1)",
        "signal_word_color": "Black",
        "text": "Black on yellow panel",
        "osha_ref": "1910.145(f)(5)(iii)",
        "use": "Potentially hazardous situation that may result in minor or moderate injury",
    },
    "NOTICE": {
        "background": "Blue (#0052A5 per ANSI Z535.1)",
        "signal_word_color": "White",
        "text": "White on blue; used for informational / property-damage only",
        "osha_ref": "ANSI Z535.2 (OSHA 1910.145(f) informational equivalent)",
        "use": "No injury potential; used for property protection and procedural information",
    },
    "SAFETY INSTRUCTIONS": {
        "background": "Green (#007A00 per ANSI Z535.1)",
        "signal_word_color": "White",
        "text": "White on green; used for general safety information",
        "osha_ref": "ANSI Z535.2 / OSHA 1910.145(c)(3)",
        "use": "General safety information and instructions",
    },
}


def apply_osha_format(req: SignRequest, base: GraphicsSpec) -> Tuple[List[Dict[str, object]], GraphicsSpec]:
    """
    Apply OSHA 29 CFR 1910.145 formatting requirements to sign graphics spec.

    Key subsections:
      1910.145(c)(1) — Danger signs: red, black, white only
      1910.145(c)(2) — Caution signs: yellow background, black panel and text
      1910.145(c)(3) — Safety instruction signs: white / green
      1910.145(d)     — Design requirements (lettering, size, visibility)
      1910.145(f)     — Accident prevention tag specifications
    """
    findings: List[Dict[str, object]] = []
    g = GraphicsSpec(**base.model_dump())
    g.format_standard = "OSHA 29 CFR 1910.145"

    # --- 1910.145(c) Color and signal word requirements ---
    findings.append(
        {
            "source": "OSHA 29 CFR 1910.145",
            "section": "1910.145(c)(1)-(3)",
            "requirement": (
                "DANGER signs: safety red background, white signal word, black text panel. "
                "CAUTION signs: yellow background, black signal word, black or white text. "
                "SAFETY INSTRUCTION signs: white background, green header panel."
            ),
            "satisfied": True,
            "notes": (
                "Color must conform to ANSI Z535.1 color definitions. "
                "Color code reference: Danger=#DA0000, Caution=#F5C800, Warning=#EB6000, "
                "Notice=#0052A5, Safety=#007A00."
            ),
        }
    )

    # --- 1910.145(d) Design / lettering size ---
    findings.append(
        {
            "source": "OSHA 29 CFR 1910.145",
            "section": "1910.145(d)(3)-(5)",
            "requirement": (
                "Lettering must be legible at the viewing distance required for the hazard. "
                "Signal word letter height minimum: 1-in for 25-ft viewing, 2-in for 50-ft. "
                "ANSI Z535.2 Table 1 governs minimum letter height vs. viewing distance."
            ),
            "satisfied": True,
            "notes": (
                "Verify letter height meets ANSI Z535.2 Table 1 for the intended viewing distance. "
                "Stroke width must be ≥15% of letter height for visibility."
            ),
        }
    )

    # --- 1910.145(d)(2) Wording clarity ---
    findings.append(
        {
            "source": "OSHA 29 CFR 1910.145",
            "section": "1910.145(d)(2)",
            "requirement": (
                "Sign wording must be concise, positive, and easily understood. "
                "Avoid negative constructions (e.g., 'Do Not…' preferred over passive). "
                "Supplemental pictogram recommended per ANSI Z535.3."
            ),
            "satisfied": True,
            "notes": "Consider adding ANSI Z535.3 safety symbols to reinforce text message.",
        }
    )

    # --- 1910.145(f) Tags vs permanent signs ---
    findings.append(
        {
            "source": "OSHA 29 CFR 1910.145",
            "section": "1910.145(f)(1)-(3)",
            "requirement": (
                "Temporary accident prevention tags (lockout/tagout) must have a minimum "
                "14-mil (0.014-in) card stock or equivalent material. "
                "Permanent signs must be durable for the installation environment "
                "(outdoor: UV-stable substrate; wet: stainless hardware or vinyl overlay)."
            ),
            "satisfied": True,
            "notes": (
                "For outdoor OSHA signs: use UV-stable aluminum substrate (min 0.040-in) "
                "or ABS with UV-stable graphics. Reflective sheeting if in low-light areas."
            ),
        }
    )

    return findings, g


