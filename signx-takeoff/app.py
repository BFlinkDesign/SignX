"""
SignX-Takeoff — Unified Channel Letter Takeoff, Estimation & Structural Server.

Run:  python app.py
Open: http://localhost:8765

Combines PDF → PF extraction (PyMuPDF), ABC formula engine,
structural engineering (ASCE 7-22, AISC 360, ACI 318-19),
and KeyedIn-ready output into a single web application.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from abc_engine import (
    ConstructionType,
    EstimateResult,
    FontType,
    JobInput,
    MountLocation,
    SignType,
    calculate_logo_pf,
    calculate_pf_from_chart,
    estimate,
    estimate_awning,
    estimate_monument,
    estimate_removal,
    get_footage_chart,
    interpolate_pf,
)
from extract_pf_from_pdf import extract_pf_from_pdf
from warehouse import benchmark

# Add signcalc-service to path for structural modules
_SIGNCALC_DIR = str(Path(__file__).resolve().parent.parent / "services" / "signcalc-service")
if _SIGNCALC_DIR not in sys.path:
    sys.path.insert(0, _SIGNCALC_DIR)

from apex_signcalc.wind_asce7 import wind_force_on_sign, load_combinations
from apex_signcalc.foundation_embed import design_embed
from apex_signcalc.anchors_baseplate import design_anchors
from apex_signcalc.supports_pipe import check_section, select_member
from apex_signcalc.sections import get_section, load_catalog

app = FastAPI(title="SignX-Takeoff", version="2.0.0")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    return FileResponse(str(STATIC_DIR / "index.html"))


# ── PDF Upload ───────────────────────────────────────────────────────────────

@app.post("/api/extract-pf")
async def extract_pf(file: UploadFile = File(...), page: int = 0,
                     scale_factor: float = 0.0,
                     known_letter_height: float = 0.0):
    """Extract peripheral feet from an uploaded PDF."""
    content = await file.read()
    result = extract_pf_from_pdf(content, filename=file.filename or "upload.pdf",
                                 page_num=page, scale_factor=scale_factor,
                                 known_letter_height=known_letter_height)
    return {
        "filename": result.filename,
        "page": result.page_number,
        "total_pf": round(result.total_pf, 2),
        "total_face_sf": round(result.total_face_sf, 2),
        "letter_count": result.letter_count,
        "max_height_inches": round(result.max_height_inches, 1),
        "min_height_inches": round(result.min_height_inches, 1),
        "warnings": result.warnings,
        "letters": [
            {
                "index": l.index,
                "pf": round(l.perimeter_feet, 2),
                "area_sf": round(l.area_sq_feet, 2),
                "height": round(l.height_inches, 1),
                "width": round(l.width_inches, 1),
            }
            for l in result.letters[:50]  # Cap at 50 for UI
        ],
    }


# ── Footage Chart ────────────────────────────────────────────────────────────

class FootageRequest(BaseModel):
    letter_count: int
    height_inches: float
    font_type: str = "block"


@app.post("/api/footage-chart")
async def footage_chart(req: FootageRequest):
    """Calculate PF from footage chart."""
    font = FontType(req.font_type)
    chart = get_footage_chart(font)
    pf_per_letter = interpolate_pf(req.height_inches, chart)
    total_pf = pf_per_letter * req.letter_count
    return {
        "pf_per_letter": round(pf_per_letter, 2),
        "total_pf": round(total_pf, 2),
        "font_type": req.font_type,
        "letter_count": req.letter_count,
        "height_inches": req.height_inches,
    }


# ── Full Estimate ────────────────────────────────────────────────────────────

class EstimateRequest(BaseModel):
    # PF source
    pf_source: str = "manual"  # "manual", "pdf", "chart"
    pf_value: float = 0.0  # For manual/pdf
    # Chart params
    letter_count: int = 0
    height_inches: float = 12.0
    font_type: str = "block"
    # Logo
    logo_pf: float = 0.0
    # Construction
    construction: str = "face_lit"
    return_depth: float = 5.0
    # Installation
    install_height: float = 15.0
    raceway_lf: float = 0.0
    substrate: str = "standard"
    miles: float = 0.0
    crew_size: int = 2
    num_units: int = 1
    include_removal: bool = False
    # Face area override
    face_sf: float = 0.0


@app.post("/api/estimate")
async def run_estimate(req: EstimateRequest):
    """Run the full ABC estimation engine."""
    job = JobInput(
        font_type=FontType(req.font_type),
        construction=ConstructionType(req.construction),
        return_depth_inches=req.return_depth,
        install_height_ft=req.install_height,
        raceway_lf=req.raceway_lf,
        substrate=req.substrate,
        miles_one_way=req.miles,
        crew_size=req.crew_size,
        num_units=req.num_units,
        include_removal=req.include_removal,
        logo_pf=req.logo_pf,
    )

    if req.pf_source == "manual" or req.pf_source == "pdf":
        job.pf_manual = req.pf_value
    elif req.pf_source == "chart":
        job.letter_count = req.letter_count
        job.letter_height_inches = req.height_inches

    if req.face_sf > 0:
        job.face_sf_override = req.face_sf

    # Pass height for rate selection even on manual PF entry
    if req.height_inches > 0:
        job.letter_height_inches = req.height_inches

    result = estimate(job)
    total_est_hours = result.total_man_hours + result.total_crew_hours
    bench = benchmark(total_est_hours)
    bench_data = _format_benchmark(bench) if bench else None
    return _format_estimate_result(result, bench_data)


# ── Monument Estimate ────────────────────────────────────────────────────────

class MonumentRequest(BaseModel):
    width_ft: float = Field(8.0, description="Sign face width (ft)")
    height_ft: float = Field(4.0, description="Sign face height (ft)")
    face_area_sf: Optional[float] = Field(None, description="Override face area (SF)")
    num_faces: int = Field(2, description="Number of faces (1=single, 2=double)")
    illuminated: bool = Field(False, description="Has illumination")
    has_vinyl: bool = Field(True, description="Has vinyl graphics")
    install_height_ft: float = Field(6.0, description="Monument top height (ft)")
    miles: float = Field(0.0, description="One-way travel miles")
    crew_size: int = Field(2, description="Crew size")


@app.post("/api/estimate/monument")
async def run_monument_estimate(req: MonumentRequest):
    """Run monument sign estimation engine."""
    sf = req.face_area_sf if req.face_area_sf and req.face_area_sf > 0 else req.width_ft * req.height_ft
    job = JobInput(
        sign_type=SignType.MONDF if req.num_faces >= 2 else SignType.MONSF,
        sign_sf_per_face=sf,
        num_faces=req.num_faces,
        is_illuminated=req.illuminated,
        has_vinyl=req.has_vinyl,
        install_height_ft=req.install_height_ft,
        miles_one_way=req.miles,
        crew_size=req.crew_size,
    )
    result = estimate_monument(job)
    total_est_hours = result.total_man_hours + result.total_crew_hours
    bench = benchmark(total_est_hours)
    bench_data = _format_benchmark(bench) if bench else None
    return _format_estimate_result(result, bench_data)


# ── Awning Estimate ──────────────────────────────────────────────────────────

class AwningRequest(BaseModel):
    width_ft: float = Field(10.0, description="Awning width (ft)")
    projection_ft: float = Field(3.0, description="Horizontal projection (ft)")
    valance_height_in: float = Field(12.0, description="Valance face height (in)")
    num_bays: int = Field(1, description="Number of structural bays")
    face_area_sf: Optional[float] = Field(None, description="Override face area (SF)")
    install_height_ft: float = Field(10.0, description="Bottom of awning (ft)")
    miles: float = Field(0.0, description="One-way travel miles")
    crew_size: int = Field(2, description="Crew size")


@app.post("/api/estimate/awning")
async def run_awning_estimate(req: AwningRequest):
    """Run awning estimation engine."""
    if req.face_area_sf and req.face_area_sf > 0:
        sf = req.face_area_sf
    else:
        sf = req.width_ft * (req.valance_height_in / 12.0)
    job = JobInput(
        sign_type=SignType.AWNNON,
        sign_sf_per_face=sf,
        num_faces=1,
        install_height_ft=req.install_height_ft,
        miles_one_way=req.miles,
        crew_size=req.crew_size,
    )
    result = estimate_awning(job)
    total_est_hours = result.total_man_hours + result.total_crew_hours
    bench = benchmark(total_est_hours)
    bench_data = _format_benchmark(bench) if bench else None
    return _format_estimate_result(result, bench_data)


# ── Removal Estimate ─────────────────────────────────────────────────────────

class RemovalRequest(BaseModel):
    sign_type: str = Field("CLLIT", description="Type of sign being removed")
    num_units: int = Field(1, description="Number of sign units to remove")
    face_area_sf: float = Field(0.0, description="Total face area (SF)")
    remove_height_ft: float = Field(15.0, description="Sign height (ft)")
    miles: float = Field(0.0, description="One-way travel miles")
    crew_size: int = Field(2, description="Crew size")


@app.post("/api/estimate/removal")
async def run_removal_estimate(req: RemovalRequest):
    """Run removal estimation engine."""
    try:
        st = SignType(req.sign_type)
    except ValueError:
        st = SignType.CLLIT
    job = JobInput(
        sign_type=st,
        num_units=req.num_units,
        face_sf_override=req.face_area_sf if req.face_area_sf > 0 else None,
        install_height_ft=req.remove_height_ft,
        miles_one_way=req.miles,
        crew_size=req.crew_size,
    )
    result = estimate_removal(job)
    total_est_hours = result.total_man_hours + result.total_crew_hours
    bench = benchmark(total_est_hours)
    bench_data = _format_benchmark(bench) if bench else None
    return _format_estimate_result(result, bench_data)


# ── Shared formatters ────────────────────────────────────────────────────────

def _format_benchmark(bench):
    return {
        "matching_jobs": bench.matching_jobs,
        "avg_hours": bench.avg_labor_hours,
        "median_hours": bench.median_labor_hours,
        "std_dev": bench.std_dev,
        "min_hours": bench.min_hours,
        "max_hours": bench.max_hours,
        "avg_revenue": bench.avg_revenue,
        "avg_margin_pct": bench.avg_margin_pct,
        "confidence": bench.confidence,
        "similar_jobs": bench.similar_jobs[:5],
    }


def _format_estimate_result(result, bench_data):
    return {
        "total_pf": result.total_pf,
        "pf_source": result.pf_source,
        "construction": result.construction,
        "height_category": result.height_category,
        "letter_count": result.letter_count,
        "labor": [
            {
                "code": l.work_code, "desc": l.description,
                "hours": l.hours, "unit": l.unit_type,
                "dept": l.department, "formula": l.formula, "section": l.section,
            }
            for l in result.labor_lines
        ],
        "install": [
            {
                "code": l.work_code, "desc": l.description,
                "hours": l.hours, "unit": l.unit_type,
                "dept": l.department, "formula": l.formula, "section": l.section,
            }
            for l in result.install_lines
        ],
        "total_man_hours": result.total_man_hours,
        "total_crew_hours": result.total_crew_hours,
        "led": result.led_spec,
        "materials": result.material_bom,
        "warnings": result.warnings,
        "benchmark": bench_data,
    }


# ── Structural: Wind Load (ASCE 7-22 Section 29.3) ─────────────────────────

class WindRequest(BaseModel):
    V_mph: float = Field(115.0, description="Basic wind speed (mph)")
    sign_width_ft: float = Field(10.0, description="Sign width (ft)")
    sign_height_ft: float = Field(5.0, description="Sign height (ft)")
    height_to_top_ft: float = Field(20.0, description="Height to top of sign (ft)")
    exposure: str = Field("C", description="Exposure category: B, C, or D")
    Kzt: float = Field(1.0, description="Topographic factor")
    elevation_ft: float = Field(0.0, description="Site elevation above sea level (ft)")
    risk_category: str = Field("II", description="Risk category: I, II, III, or IV")


@app.post("/api/structural/wind")
async def calc_wind(req: WindRequest):
    """ASCE 7-22 Section 29.3 wind load on freestanding sign."""
    try:
        result = wind_force_on_sign(
            V_mph=req.V_mph,
            sign_width_ft=req.sign_width_ft,
            sign_height_ft=req.sign_height_ft,
            height_to_top_ft=req.height_to_top_ft,
            exposure=req.exposure,
            Kzt=req.Kzt,
            elevation_ft=req.elevation_ft,
            risk_category=req.risk_category,
        )
        return {"ok": True, "result": result}
    except Exception as e:
        return JSONResponse(status_code=422, content={"ok": False, "error": str(e)})


# ── Structural: Foundation Design (Broms / IBC 1807.3.1) ───────────────────

class FoundationRequest(BaseModel):
    F_lbf: float = Field(..., description="Lateral force at base (lbf)")
    M_inlb: float = Field(..., description="Overturning moment at base (in-lb)")
    max_dia_in: Optional[float] = Field(None, description="Max foundation diameter (in)")
    max_embed_in: Optional[float] = Field(None, description="Max embedment depth (in)")


@app.post("/api/structural/foundation")
async def calc_foundation(req: FoundationRequest):
    """Foundation design using Broms/IBC 1807.3.1 methods."""
    try:
        constraints = {}
        if req.max_dia_in is not None:
            constraints["max_foundation_dia_in"] = req.max_dia_in
        if req.max_embed_in is not None:
            constraints["max_embed_in"] = req.max_embed_in
        geometry, checks = design_embed(req.F_lbf, req.M_inlb, constraints or None)
        return {"ok": True, "geometry": geometry, "checks": checks}
    except Exception as e:
        return JSONResponse(status_code=422, content={"ok": False, "error": str(e)})


# ── Structural: Anchor / Baseplate Design (ACI 318-19 Ch 17) ───────────────

class AnchorRequest(BaseModel):
    F_lbf: float = Field(..., description="Shear force (lbf)")
    M_inlb: float = Field(..., description="Overturning moment (in-lb)")
    P_lbf: float = Field(0.0, description="Axial compression (lbf)")
    f_c_psi: float = Field(3000.0, description="Concrete compressive strength (psi)")
    bolt_grade: str = Field("F1554-36", description="Bolt grade: A307, F1554-36, F1554-55, F1554-105, A36")
    n_bolts: int = Field(4, description="Number of anchor bolts")


@app.post("/api/structural/anchors")
async def calc_anchors(req: AnchorRequest):
    """Anchor bolt + base plate design per ACI 318-19 Chapter 17."""
    try:
        geometry, checks = design_anchors(
            F_lbf=req.F_lbf,
            M_inlb=req.M_inlb,
            P_lbf=req.P_lbf,
            f_c_psi=req.f_c_psi,
            bolt_grade=req.bolt_grade,
            n_bolts=req.n_bolts,
        )
        return {"ok": True, "geometry": geometry, "checks": checks}
    except ValueError as e:
        return JSONResponse(status_code=422, content={"ok": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


# ── Structural: Member Selection (AISC 360-22) ─────────────────────────────

class MemberCheckRequest(BaseModel):
    designation: str = Field(..., description="AISC section designation (e.g. Pipe4STD, W14X22, HSS6X6X1/4)")
    M_inlb: float = Field(..., description="Required moment (in-lb)")
    V_lbf: float = Field(..., description="Required shear (lbf)")
    L_in: float = Field(..., description="Unbraced length (in)")
    P_lbf: float = Field(0.0, description="Axial force (lbf)")
    K: float = Field(1.0, description="Effective length factor")
    load_type: str = Field("cantilever", description="cantilever, cantilever_udl, simple_point, simple_udl, fixed_point")


@app.post("/api/structural/member-check")
async def calc_member_check(req: MemberCheckRequest):
    """Check a specific AISC section per AISC 360-22."""
    try:
        sec = get_section(req.designation)
        if sec is None:
            return JSONResponse(status_code=404, content={"ok": False, "error": f"Section '{req.designation}' not found"})
        ok, data = check_section(sec, req.M_inlb, req.V_lbf, req.L_in,
                                  P_lbf=req.P_lbf, K=req.K, load_type=req.load_type)
        return {"ok": True, "passes": ok, "designation": sec.designation, "checks": data}
    except Exception as e:
        return JSONResponse(status_code=422, content={"ok": False, "error": str(e)})


class MemberSelectRequest(BaseModel):
    M_inlb: float = Field(..., description="Required moment (in-lb)")
    V_lbf: float = Field(..., description="Required shear (lbf)")
    L_in: float = Field(..., description="Unbraced length (in)")
    P_lbf: float = Field(0.0, description="Axial force (lbf)")
    K: float = Field(1.0, description="Effective length factor")
    load_type: str = Field("cantilever", description="Load configuration")
    families: Optional[List[str]] = Field(None, description="Shape families to search: pipe, W, HSS_square, HSS_round, etc.")


@app.post("/api/structural/member-select")
async def calc_member_select(req: MemberSelectRequest):
    """Auto-select lightest passing AISC section per AISC 360-22."""
    try:
        sec, data = select_member(
            M_inlb=req.M_inlb, V_lbf=req.V_lbf, L_in=req.L_in,
            P_lbf=req.P_lbf, K=req.K, load_type=req.load_type,
            families=req.families,
        )
        if sec is None:
            return JSONResponse(status_code=422, content={"ok": False, "error": "No passing section found"})
        return {"ok": True, "designation": sec.designation, "family": sec.family,
                "weight_plf": sec.W_plf, "checks": data}
    except Exception as e:
        return JSONResponse(status_code=422, content={"ok": False, "error": str(e)})


# ── Structural: Full Sign Design (Wind → Member → Foundation → Anchors) ────

class FullDesignRequest(BaseModel):
    sign_width_ft: float = Field(..., description="Sign width (ft)")
    sign_height_ft: float = Field(..., description="Sign height (ft)")
    height_to_top_ft: float = Field(..., description="Height to top of sign (ft)")
    V_mph: float = Field(115.0, description="Basic wind speed (mph)")
    exposure: str = Field("C", description="Exposure category")
    elevation_ft: float = Field(0.0, description="Site elevation (ft)")
    support_families: Optional[List[str]] = Field(None, description="Preferred support types")
    f_c_psi: float = Field(3000.0, description="Concrete strength (psi)")
    bolt_grade: str = Field("F1554-36", description="Anchor bolt grade")


@app.post("/api/structural/full-design")
async def full_sign_design(req: FullDesignRequest):
    """Complete sign structural design: wind → member → foundation → anchors."""
    try:
        # 1. Wind loads
        wind = wind_force_on_sign(
            V_mph=req.V_mph, sign_width_ft=req.sign_width_ft,
            sign_height_ft=req.sign_height_ft, height_to_top_ft=req.height_to_top_ft,
            exposure=req.exposure, elevation_ft=req.elevation_ft,
        )

        F = wind["governing_F_lbf"]
        M_ftlb = wind["governing_M_ftlbf"]
        M_inlb = M_ftlb * 12.0
        L_in = req.height_to_top_ft * 12.0

        # 2. Member selection
        sec, member_checks = select_member(
            M_inlb=M_inlb, V_lbf=F, L_in=L_in,
            families=req.support_families, load_type="cantilever",
        )
        member_result = None
        if sec:
            member_result = {"designation": sec.designation, "family": sec.family,
                             "weight_plf": sec.W_plf, "checks": member_checks}

        # 3. Foundation
        geo, fnd_checks = design_embed(F, M_inlb)

        # 4. Anchors
        try:
            anc_geo, anc_checks = design_anchors(
                F_lbf=F, M_inlb=M_inlb, f_c_psi=req.f_c_psi, bolt_grade=req.bolt_grade,
            )
            anchor_result = {"geometry": anc_geo, "checks": anc_checks}
        except ValueError as e:
            anchor_result = {"error": str(e)}

        return {
            "ok": True,
            "wind": wind,
            "member": member_result,
            "foundation": {"geometry": geo, "checks": fnd_checks},
            "anchors": anchor_result,
        }
    except Exception as e:
        return JSONResponse(status_code=422, content={"ok": False, "error": str(e)})


# ── Sections Database ───────────────────────────────────────────────────────

@app.get("/api/structural/sections")
async def list_sections(family: Optional[str] = None, limit: int = 50):
    """List available AISC sections, optionally filtered by family."""
    sections = load_catalog()
    if family:
        sections = [s for s in sections if s.family and s.family.lower() == family.lower()]
    return {
        "total": len(sections),
        "sections": [
            {"designation": s.designation, "family": s.family, "W_plf": s.weight_plf,
             "d_in": s.d_in, "Ix_in4": s.Ix_in4, "Sx_in3": s.Sx_in3}
            for s in sections[:limit]
        ],
    }


if __name__ == "__main__":
    print("\n  SignX-Takeoff Server v2.0")
    print("  http://localhost:8765")
    print("  Endpoints: /api/estimate, /api/structural/wind, /api/structural/full-design, ...")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")
