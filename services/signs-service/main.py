from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException

from contracts.signs import (
    BomItem,
    ComplianceFinding,
    ElectricalInput,
    GraphicsSpec,
    Jurisdiction,
    MechanicalSpec,
    MountingParams,
    SignRequest,
    SignResponse,
    Spec,
)
from .rules.electrical import check_listing, nec_checks
from .rules.labels import ul969_label_set
from .rules.mutcd import apply_mutcd_constraints
from .rules.osha_format import apply_osha_format
from .rules.mechanical import mechanical_from_env
from .cad.macro import build_freecad_macro
from .bom.listing import infer_listing_category


SCHEMA_VERSION = "1.0.0"

app = FastAPI(title="APEX Signs Service", version="0.1.0")


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/schema")
def schema() -> Dict[str, object]:
    # export contract schemas for discovery
    from contracts.signs import schemas as export

    return export()


def _normalize_environment(env: str) -> str:
    e = env.lower()
    if any(k in e for k in ["salt-spray", "marine", "seacoast", "coastal"]):
        return "coastal"
    return env


@app.post("/v1/signs/spec")
def build_spec(req: SignRequest) -> Dict[str, Any]:
    # Validate NAICS lock
    if req.naics_code != "339950":
        raise HTTPException(status_code=422, detail="naics_code must be '339950'")

    assumptions: List[str] = [
        "Scope: NAICS 339950 – Sign Manufacturing (excludes design-only, paper signs, install-only)",
    ]

    # Normalize environment semantics
    norm_env = _normalize_environment(req.environment)
    if norm_env != req.environment:
        assumptions.append(f"Normalized environment '{req.environment}' -> '{norm_env}'")

    # Decide applicable code bundle
    codes_applied: List[str] = []
    if req.illumination in ("internal-LED", "neon"):
        codes_applied.extend(["UL 48", "NEC 600", "UL 879/879A", "UL 969"])
    if req.labels_required:
        if "UL 969" not in codes_applied:
            codes_applied.append("UL 969")
    if req.traffic_control_context:
        codes_applied.append("MUTCD 11th")
    # OSHA for safety/industrial contexts; as a proxy, if use_case includes wayfinding/traffic or explicit flag later
    if req.use_case in ("wayfinding", "traffic"):
        codes_applied.append("OSHA 1910.145")

    # Seed minimal BOM from inputs (caller may pass richer BOM in future)
    bom: List[BomItem] = []
    if req.illumination == "internal-LED":
        bom.append(BomItem(type="led_driver", description="LED Driver", quantity=1.0))
        bom.append(BomItem(type="led_module", description="LED Strip/Module", quantity=1.0))

    # Electrical listing/category inference and checks
    listing_category = infer_listing_category(req.illumination)
    ok_listing, listing_findings = check_listing(req.illumination, [b.model_dump() for b in bom])

    # NEC checks (disconnect, GFCI, bonding, labeling visibility)
    nec_ok, nec_findings, install_notes = nec_checks(req.electrical, req.illumination)

    # Labels set per UL 969
    label_defs = ul969_label_set(req)

    # Mechanical/environmental spec
    mech = mechanical_from_env(norm_env, req.mounting.type)

    # Graphics and formatting (OSHA / MUTCD gates)
    graphics = GraphicsSpec()
    abstain = False
    if req.traffic_control_context:
        mutcd_ok, mutcd_findings, graphics = apply_mutcd_constraints(req, graphics)
        if not mutcd_ok:
            abstain = True
    if req.use_case in ("wayfinding", "traffic"):
        osha_findings, graphics = apply_osha_format(req, graphics)
    else:
        osha_findings = []

    # Compliance matrix and risks
    compliance: List[ComplianceFinding] = []
    compliance += [ComplianceFinding(**f) for f in listing_findings]
    compliance += [ComplianceFinding(**f) for f in nec_findings]
    compliance += [ComplianceFinding(**f) for f in osha_findings]

    # Compose spec structures
    spec = Spec(
        materials=["5052-H32 Al", "316 SS fasteners"] if norm_env == "coastal" else ["A36 steel", "zinc hardware"],
        finishes=["powdercoat"],
        ip_rating_target="IP54" if norm_env in ("outdoor", "coastal") else None,
        enclosure_class="UL 48" if req.illumination in ("internal-LED", "neon") else None,
    )
    electrical_spec = ElectricalSpec(
        disconnect="local lockable within sight (NEC 600.6)",
        max_input_current_A=max(0.1, float(req.electrical.available_circuit_A) * 0.8 if req.illumination != "none" else 0.0),
        branch_circuit_A=max(15.0, float(req.electrical.available_circuit_A)),
        listing_category=listing_category,
        required_field_labels=[l["name"] for l in label_defs],
    )
    mechanical_spec = MechanicalSpec(
        mounting_pattern=mech["mounting_pattern"],
        min_fastener_grade=mech["min_fastener_grade"],
        sealants=mech["sealants"],
        gasket_material=mech.get("gasket_material"),
    )

    # CAD macro text
    macro_text = build_freecad_macro(req)

    # Assemble domain result
    domain: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "result": SignResponse(
            spec=spec,
            electrical_spec=electrical_spec,
            mechanical_spec=mechanical_spec,
            graphics_spec=graphics,
            bom=bom,
            cad_macro=macro_text,
            install_notes=install_notes,
            compliance=compliance,
            risks=[],
        ).model_dump(mode="json"),
        "assumptions": assumptions + [
            "Code families applied: " + ", ".join(codes_applied)
        ],
        "confidence": 0.82 if ok_listing and nec_ok and not abstain else 0.4,
        "abstain": bool(abstain),
        "trace": {
            "citations": [
                "Census.gov – NAICS 339950",
                "International Sign Association – UL 48 overview",
                "Connect NCDOT – NEC 600 summary",
                "NJSL Digital Collections – MUTCD 11th",
                "shopulstandards.com – UL 879/879A",
                "u.dianyuan.com – UL 969",
                "Eurofins E&E NA – OSHA 1910.145",
            ],
            "data_sha256": None,
            "blob_refs": [],
        },
    }

    # data_sha256 of result payload
    payload = json.dumps(domain["result"], sort_keys=True, separators=(",", ":")).encode("utf-8")
    domain["trace"]["data_sha256"] = hashlib.sha256(payload).hexdigest()

    return domain


