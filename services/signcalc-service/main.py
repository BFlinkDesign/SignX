from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException

from apex_signcalc.contracts import (
    SCHEMA_VERSION,
    SignDesignRequest,
    SignDesignResponse,
    ResultSelected,
    SelectedSupport,
    Foundation,
    Checks,
)
from apex_signcalc.wind_asce7 import interpolate_kz, qz_psf
from apex_signcalc.wind_en1991 import qb_pa, qp_pa
from apex_signcalc.sections import catalogs_for_order
from apex_signcalc.supports_pipe import check_section as check_pipe
from apex_signcalc.supports_wshape import check_section as check_w
from apex_signcalc.supports_tube import check_section as check_tube
from apex_signcalc.foundation_embed import design_embed
from apex_signcalc.anchors_baseplate import design_anchors
from apex_signcalc.rebar_schedules import schedule_for
from apex_signcalc.report_render import render_calc_json, render_pdf, render_dxf

import yaml


app = FastAPI(title="APEX Sign Calculation Service", version="0.1.0")

ROOT = Path(__file__).parent.resolve()
PACKS_DIR = ROOT / "apex_signcalc" / "packs"


# Use shared utilities if available (for monorepo), otherwise keep local
try:
    import sys
    from pathlib import Path as PathLib
    # Try to import from packages if running in monorepo context
    repo_root = PathLib(__file__).resolve().parents[2]  # Go up to repo root
    if (repo_root / "apex" / "packages").exists():
        sys.path.insert(0, str(repo_root / "apex"))
        from packages.utils import sha256_digest as _sha256_bytes, load_yaml as _load_yaml_func
        def _load_yaml(path: Path) -> Dict[str, Any]:
            return _load_yaml_func(path)
    else:
        raise ImportError
except (ImportError, IndexError):
    # Fallback to local implementation
    def _sha256_bytes(b: bytes) -> str:
        return hashlib.sha256(b).hexdigest()
    
    def _load_yaml(path: Path) -> Dict[str, Any]:
        return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_packs() -> Dict[str, Dict[str, Any]]:
    packs: Dict[str, Dict[str, Any]] = {}
    for p in PACKS_DIR.rglob("*.yaml"):
        packs[str(p.relative_to(PACKS_DIR))] = _load_yaml(p)
    for p in PACKS_DIR.rglob("*.json"):
        try:
            from packages.utils import load_json
            packs[str(p.relative_to(PACKS_DIR))] = load_json(p)
        except ImportError:
            packs[str(p.relative_to(PACKS_DIR))] = json.loads(p.read_text(encoding="utf-8"))
    return packs


def _packs_sha() -> str:
    packs = _load_packs()
    data = json.dumps(packs, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(data)


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    ok = PACKS_DIR.exists()
    return {"status": "ok" if ok else "degraded"}


@app.get(f"/schemas/{SCHEMA_VERSION}.json")
def schema() -> Dict[str, Any]:
    return SignDesignRequest.model_json_schema()


@app.get("/packs")
def packs() -> Dict[str, Any]:
    out: List[Dict[str, Any]] = []
    for rel, data in _load_packs().items():
        h = _sha256_bytes(json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        out.append({"name": rel, "sha256": h})
    return {"packs": sorted(out, key=lambda x: x["name"])}


@app.post("/v1/signs/design")
def design(req: SignDesignRequest) -> SignDesignResponse:
    if req.schema_version != SCHEMA_VERSION:
        raise HTTPException(status_code=422, detail="schema_version mismatch")

    assumptions: List[str] = []
    packs_sha = _packs_sha()

    # Wind loads
    area_ft2 = req.sign.width_ft * req.sign.height_ft
    if req.jurisdiction == "US" and req.standard.code == "ASCE7":
        std = _load_yaml(PACKS_DIR / "us.asce7-16" / "wind.yaml")
        kz = interpolate_kz(std["Kz"], req.site.exposure, req.sign.centroid_height_ft)
        V_basic_used = std.get("V_default_mph", 100)
        q = qz_psf(V_basic=V_basic_used, kz=kz, kzt=1.0, kd=0.85, G=0.85)
        cf = float(std.get("cf_sign", 1.8))
        F = q * cf * area_ft2
        loads = {"V_basic": V_basic_used, "qz_psf": q, "F_w_sign_lbf": F}
        assumptions.append("ASCE 7 pack used (us.asce7-16)")
    elif req.jurisdiction == "EU" and req.standard.code == "EN1991":
        std = _load_yaml(PACKS_DIR / "eu.en1991-1-4" / "wind.yaml")
        qb = qb_pa(std.get("rho_air", 1.25), std.get("v_b", 26.0))
        qp = qp_pa(std.get("c_e_z", 1.0), std.get("c_e_T", 1.0), qb)
        cf = float(std.get("c_f", 1.8))
        area_m2 = area_ft2 * 0.092903
        F = cf * qp * area_m2 * 0.224809
        loads = {"V_basic": std.get("v_b", 26.0), "qb_pa": qb, "F_w_sign_lbf": F}
        assumptions.append("EN 1991 pack used (eu.en1991-1-4)")
    else:
        raise HTTPException(status_code=422, detail="unsupported jurisdiction/standard")

    # Member selection (iterate catalogs by order)
    M = loads["F_w_sign_lbf"] * (req.sign.centroid_height_ft * 12.0)  # in-lb
    V = loads["F_w_sign_lbf"]
    L = req.sign.centroid_height_ft * 12.0
    chosen = None
    check_data: Dict[str, float] = {}
    for sec in catalogs_for_order(req.support_options):
        ok = False
        if sec.family == "pipe":
            ok, data = check_pipe(sec, M, V, L)
        elif sec.family == "W":
            ok, data = check_w(sec, M, V, L)
        else:
            ok, data = check_tube(sec, M, V, L)
        if ok:
            chosen = sec
            check_data = data
            break
    if chosen is None:
        raise HTTPException(status_code=422, detail="no passing support section")

    # Foundation
    fdim, fchecks = design_embed(V, M, constraints=json.loads(req.constraints.model_dump_json()))
    rebar_ref = schedule_for(fdim.get("dia_in", 0.0), fdim.get("depth_in", 0.0))

    # Anchors if baseplate
    anchor_ref = None
    if req.embed.get("type") == "baseplate":
        anc, achecks = design_anchors(V, M)
        anchor_ref = anc.get("ref")
        fchecks["T_sf"] = achecks["T_sf"]
        fchecks["V_sf"] = achecks["V_sf"]

    # Compose selected and loads
    selected = ResultSelected(
        support=SelectedSupport(type=chosen.family, designation=chosen.designation),
        foundation=Foundation(shape="cyl", dia_in=fdim.get("dia_in"), width_in=None, depth_in=fdim["depth_in"], rebar_schedule_ref=rebar_ref, anchor_bolt_ref=anchor_ref),
        checks=Checks(OT_sf=fchecks["OT_sf"], BRG_sf=fchecks["BRG_sf"], SLIDE_sf=fchecks["SLIDE_sf"], UPLIFT_sf=fchecks["UPLIFT_sf"], DEF_ok=check_data.get("DEF_in", 0.0) <= L/120.0),
    )

    # Reports
    calc_payload = {
        "request": json.loads(req.model_dump_json()),
        "loads": loads,
        "selected": json.loads(selected.model_dump_json()),
        "packs_sha": packs_sha,
    }
    calc_sha, calc_ref = render_calc_json(ROOT, calc_payload)
    pdf_sha, pdf_ref = render_pdf(ROOT, "Sign Calc Report", calc_payload)
    dxf_sha, dxf_ref = render_dxf(ROOT, "Sign Foundation")

    # Confidence heuristic
    margins = [selected.checks.OT_sf, selected.checks.BRG_sf, selected.checks.SLIDE_sf, selected.checks.UPLIFT_sf]
    min_margin = min(margins)
    confidence = max(0.0, min(1.0, (min_margin - 1.0) / 1.0))

    # Build envelope
    result: Dict[str, Any] = {
        "selected": json.loads(selected.model_dump_json()),
        "alternates": [],
        "loads": loads,
        "reports": {"calc_json_ref": calc_ref, "pdf_ref": pdf_ref, "dxf_ref": dxf_ref},
    }
    data_bytes = json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
    inputs_bytes = json.dumps(json.loads(req.model_dump_json()), sort_keys=True, separators=(",", ":")).encode("utf-8")
    envelope = {
        "result": result,
        "assumptions": assumptions,
        "confidence": round(confidence, 3),
        "trace": {
            "data_sha256": _sha256_bytes(data_bytes),
            "inputs_sha256": _sha256_bytes(inputs_bytes),
            "code_version": {"git_sha": "dev", "dirty": False},
            "standards_pack_sha256": packs_sha,
        },
    }
    return SignDesignResponse(**envelope)
