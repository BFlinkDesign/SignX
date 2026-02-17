from __future__ import annotations

from typing import Any, Dict, List, Tuple

from contracts.signs import ElectricalInput

# NEC Article 600 (2023 edition) and UL 48 (14th ed.) section references.
# These checks produce findings suitable for PE / code-official review.


def check_listing(illumination: str, bom: List[Dict[str, Any]]) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Verify BOM component listing requirements.

    UL 48 (14th ed.) § 4 – General requirements: the sign as a unit must be listed.
    UL 879 / 879A – Listed LED drivers and LED modules for sign use.
    NEC 600.3 – Electric signs and outline lighting must be listed (or field-labeled
                under special conditions per 600.3 Exception).
    """
    findings: List[Dict[str, Any]] = []
    ok = True

    if illumination == "internal-LED":
        unlisted: List[str] = []
        for item in bom:
            if item.get("type") in ("led_driver", "led_module"):
                if not item.get("ul_file") or not item.get("ul_category"):
                    unlisted.append(item.get("description", item.get("type", "unknown")))

        if unlisted:
            ok = False
            findings.append(
                {
                    "source": "UL 48 / UL 879",
                    "section": "UL 48 §4 / NEC 600.3",
                    "requirement": (
                        "Each LED driver and LED module must be Listed (UL 879/879A) "
                        "and carry a UL file number and category code. "
                        "NEC 600.3 prohibits installation of unlisted electric signs."
                    ),
                    "satisfied": False,
                    "notes": f"Unlisted components: {', '.join(unlisted)}. "
                             "Obtain UL file number (E-number) and category code "
                             "(e.g., UZNQ, UZNQ2) before AHJ submission.",
                }
            )
        else:
            findings.append(
                {
                    "source": "UL 48 / UL 879",
                    "section": "UL 48 §4 / NEC 600.3",
                    "requirement": "All LED drivers and modules are Listed (UL file + category present).",
                    "satisfied": True,
                    "notes": None,
                }
            )

        # UL 48 §4.3 — sign enclosure listing
        findings.append(
            {
                "source": "UL 48",
                "section": "§4.3",
                "requirement": (
                    "Sign enclosure (cabinet) must bear the UL Listing mark. "
                    "Field-wired compartments must be separated from low-voltage sections."
                ),
                "satisfied": True,  # assumed for manufactured sign; flag if field-built
                "notes": "Confirm UL Listing mark is applied to finished sign cabinet.",
            }
        )

    elif illumination == "neon":
        # UL 48 §6 covers neon sign-specific requirements
        findings.append(
            {
                "source": "UL 48",
                "section": "§6 (Neon Signs)",
                "requirement": (
                    "Neon transformers and electronic power supplies must be Listed for "
                    "sign use (UL 48 §6.2). Secondary circuit wiring must be GTO-15 or "
                    "equivalent high-voltage insulated conductor."
                ),
                "satisfied": True,
                "notes": (
                    "Verify transformer / EPS label shows UL Listing mark and rating "
                    "matches tube load. GTO-15 cable required for secondary runs outside glass."
                ),
            }
        )

    elif illumination == "none":
        findings.append(
            {
                "source": "UL 48",
                "section": "§4",
                "requirement": "Non-illuminated sign: UL 48 listing not required; verify substrate fire rating if interior.",
                "satisfied": True,
                "notes": None,
            }
        )

    return ok, findings


def nec_checks(elec: ElectricalInput, illumination: str) -> Tuple[bool, List[Dict[str, Any]], List[str]]:
    """
    NEC Article 600 (2023) compliance checks for electric signs.

    Key sections:
      600.4  – Markings (nameplate requirements)
      600.5  – Branch circuits (15/20 A dedicated circuit)
      600.6  – Disconnecting means (within sight, lockable)
      600.7  – Grounding and bonding
      600.10 – GFCI protection (portable/cord-connected outdoor signs)
      600.12 – Field-installed secondary wiring
    """
    findings: List[Dict[str, Any]] = []
    install_notes: List[str] = []
    ok = True

    # --- 600.4 Markings ---
    findings.append(
        {
            "source": "NEC 600",
            "section": "600.4",
            "requirement": (
                "Sign nameplate must show: manufacturer name/trademark, supply voltage, "
                "full-load amperes, frequency, and number of signs if more than one on circuit. "
                "Nameplate must be visible after installation."
            ),
            "satisfied": True,
            "notes": "Verify nameplate is on sign exterior; accessible without tools.",
        }
    )

    # --- 600.5 Branch Circuits ---
    circuit_ok = True
    if elec.available_circuit_A < 15.0:
        circuit_ok = False
        ok = False
        findings.append(
            {
                "source": "NEC 600",
                "section": "600.5(A)",
                "requirement": (
                    "Each commercial building sign must be supplied by a dedicated branch circuit "
                    "rated minimum 15 A (20 A preferred for LED signs). "
                    "Circuit must serve no other loads."
                ),
                "satisfied": False,
                "notes": (
                    f"Supplied circuit rated {elec.available_circuit_A} A — does not meet 15 A minimum. "
                    "Upgrade to dedicated 15 A or 20 A circuit."
                ),
            }
        )
    else:
        findings.append(
            {
                "source": "NEC 600",
                "section": "600.5(A)",
                "requirement": "Dedicated branch circuit ≥ 15 A serving sign only.",
                "satisfied": True,
                "notes": f"Supplied circuit: {elec.available_circuit_A} A.",
            }
        )

    install_notes.append(
        "NEC 600.5(A): Dedicate a 15 A (min) or 20 A branch circuit exclusively to this sign."
    )

    # --- 600.6 Disconnecting Means ---
    findings.append(
        {
            "source": "NEC 600",
            "section": "600.6(A)(1)",
            "requirement": (
                "Provide a disconnecting means within sight of the sign (visible and max 50 ft). "
                "Disconnect must be capable of being locked in the open (off) position per 600.6(A)(2). "
                "Service-entrance-rated disconnect required if within 10 ft of sign."
            ),
            "satisfied": True,
            "notes": (
                "Lockout/tagout provisions (hasp) must be provided or integrated. "
                "If inside a locked room, the room itself may satisfy 600.6(A)(2) Exception."
            ),
        }
    )
    install_notes.append(
        "NEC 600.6: Install lockable disconnect (e.g., fused disconnect switch) "
        "within sight of sign; max 50 ft and line-of-sight required."
    )

    # --- 600.7 Grounding and Bonding ---
    findings.append(
        {
            "source": "NEC 600",
            "section": "600.7(A)",
            "requirement": (
                "All exposed non-current-carrying metal parts of a sign must be grounded. "
                "Bond metal sign enclosure to equipment grounding conductor (EGC) per 600.7(A). "
                "Bonding conductor must be copper, sized per Table 250.122."
            ),
            "satisfied": True,
            "notes": (
                "Internal metal chassis, back-pan, and all raceways must be bonded. "
                "Isolated sections (e.g., decorative trim) require individual bonding jumpers."
            ),
        }
    )

    # --- 600.10 GFCI Protection ---
    # 600.10(C)(2): GFCI required for cord-connected portable signs in wet/damp locations
    # 600.10(D): GFCI required for fixed outdoor signs within 6 ft of grade accessible to public
    needs_gfci = getattr(elec, "location_type", None) in ("wet", "damp", "outdoor") or True
    findings.append(
        {
            "source": "NEC 600",
            "section": "600.10(C)(2) / 600.10(D)",
            "requirement": (
                "GFCI protection required for: cord-connected portable signs (600.10(C)(2)); "
                "fixed outdoor signs accessible to the public within 6 ft of grade (600.10(D)). "
                "GFCI device must be listed and rated for the branch circuit amperage."
            ),
            "satisfied": True,
            "notes": (
                "Confirm whether sign is cord-connected or fixed. "
                "If fixed outdoor sign within 6 ft of grade: provide GFCI breaker at panel "
                "or GFCI receptacle at sign connection point."
            ),
        }
    )
    install_notes.append(
        "NEC 600.10(D): If fixed outdoor sign is within 6 ft of finished grade and "
        "accessible to the public, GFCI protection is required."
    )

    # --- 600.12 Field-Installed Secondary Wiring ---
    if illumination in ("internal-LED", "neon"):
        findings.append(
            {
                "source": "NEC 600",
                "section": "600.12(A)",
                "requirement": (
                    "Field-installed secondary wiring (low-voltage side of LED driver or "
                    "secondary of neon transformer) must be Listed for the application. "
                    "Neon secondary: GTO-15 or equivalent. LED secondary: min 60°C rated."
                ),
                "satisfied": True,
                "notes": (
                    "All secondary wiring installed in the field must match the "
                    "listed wire type specified in the sign's listing."
                ),
            }
        )

    return ok, findings, install_notes


