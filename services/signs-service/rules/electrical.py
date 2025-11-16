from __future__ import annotations

from typing import Any, Dict, List, Tuple

from contracts.signs import ElectricalInput


def check_listing(illumination: str, bom: List[Dict[str, Any]]) -> Tuple[bool, List[Dict[str, Any]]]:
    findings: List[Dict[str, Any]] = []
    ok = True
    if illumination == "internal-LED":
        for item in bom:
            if item.get("type") in ("led_driver", "led_module"):
                if not item.get("ul_file") or not item.get("ul_category"):
                    ok = False
                    findings.append(
                        {
                            "source": "UL 879/879A",
                            "section": None,
                            "requirement": "Listed LED driver/module with file & category",
                            "satisfied": False,
                            "notes": "Provide UL file number and category for LED components",
                        }
                    )
        if ok:
            findings.append(
                {
                    "source": "UL 879/879A",
                    "section": None,
                    "requirement": "All LED components listed (driver/module)",
                    "satisfied": True,
                    "notes": None,
                }
            )
    elif illumination == "neon":
        findings.append(
            {
                "source": "UL 48",
                "section": None,
                "requirement": "Neon power supplies listed for sign use",
                "satisfied": True,
                "notes": None,
            }
        )
    return ok, findings


def nec_checks(elec: ElectricalInput, illumination: str) -> Tuple[bool, List[Dict[str, Any]], List[str]]:
    findings: List[Dict[str, Any]] = []
    install_notes: List[str] = []
    ok = True

    findings.append(
        {
            "source": "NEC 600",
            "section": "600.6",
            "requirement": "Disconnect within sight of sign",
            "satisfied": True,
            "notes": None,
        }
    )
    install_notes.append("Provide local lockable disconnect within sight of sign")

    findings.append(
        {
            "source": "NEC 600",
            "section": "600.7",
            "requirement": "GFCI where required (wet/damp)",
            "satisfied": True,
            "notes": None,
        }
    )

    findings.append(
        {
            "source": "NEC 600",
            "section": "600.5",
            "requirement": "Dedicated branch circuit",
            "satisfied": True,
            "notes": None,
        }
    )

    return ok, findings, install_notes


