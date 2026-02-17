"""
SignX-Takeoff — Unified Channel Letter Takeoff, Estimation & Structural Server.

Run:  python app.py
Open: http://localhost:8765

Combines PDF → PF extraction (PyMuPDF), ABC formula engine,
structural engineering (ASCE 7-22, AISC 360, ACI 318-19),
and KeyedIn-ready output into a single web application.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

import httpx
import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

logger = logging.getLogger("signx-takeoff")

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_BID_PIPELINE_DB = os.environ.get("NOTION_BID_PIPELINE", "")
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}
NOTIFY_WEBHOOK_URL = os.environ.get("NOTIFY_WEBHOOK_URL", "")

# SMS Configuration
SMS_PHONE = os.environ.get("SMS_PHONE", "7122666482")
SMS_CARRIER_GATEWAY = os.environ.get("SMS_CARRIER_GATEWAY", "vtext.com")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "")

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
    estimate_cabinet,
    estimate_dimensional,
    estimate_directional,
    estimate_monument,
    estimate_pylon,
    estimate_removal,
    get_footage_chart,
    interpolate_pf,
)
from customer_intel import (
    find_similar_jobs,
    get_customer_profile,
    get_market_intel,
    warehouse_stats,
)
from drawing_search import search_drawings, search_for_bid
from extract_pf_from_pdf import extract_pf_from_pdf
from project_files import scan_project_files
from bid_scoring import (
    score_bid,
    get_win_rate_stats,
    get_price_recommendation,
    scoring_stats,
)
from bid_model import predict_win_probability, get_model_diagnostics
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


# ── Pylon/Pole Estimate ─────────────────────────────────────────────────────

class PylonRequest(BaseModel):
    width_ft: float = Field(8.0, description="Cabinet face width (ft)")
    height_ft: float = Field(6.0, description="Cabinet face height (ft)")
    face_area_sf: Optional[float] = Field(None, description="Override face area (SF)")
    num_faces: int = Field(2, description="Number of cabinet faces (1 or 2)")
    pole_height_ft: float = Field(25.0, description="Total pole height to top of sign (ft)")
    illuminated: bool = Field(True, description="Has illumination (LED/electrical)")
    has_vinyl: bool = Field(True, description="Has vinyl graphics")
    include_footing: bool = Field(True, description="Self-performed footing")
    miles: float = Field(0.0, description="One-way travel miles")
    crew_size: int = Field(3, description="Crew size (3 standard for crane)")


@app.post("/api/estimate/pylon")
async def run_pylon_estimate(req: PylonRequest):
    """Run pylon/pole sign estimation engine (POLLIT or POLNON)."""
    sf = req.face_area_sf if req.face_area_sf and req.face_area_sf > 0 else req.width_ft * req.height_ft
    job = JobInput(
        sign_type=SignType.POLLIT if req.illuminated else SignType.POLNON,
        sign_sf_per_face=sf,
        num_faces=req.num_faces,
        is_illuminated=req.illuminated,
        has_vinyl=req.has_vinyl,
        has_structural_steel=True,  # Pylons always have steel poles
        has_footing=req.include_footing,
        install_height_ft=req.pole_height_ft,
        miles_one_way=req.miles,
        crew_size=req.crew_size,
    )
    result = estimate_pylon(job)
    total_est_hours = result.total_man_hours + result.total_crew_hours
    bench = benchmark(total_est_hours)
    bench_data = _format_benchmark(bench) if bench else None
    return _format_estimate_result(result, bench_data)


# ── Cabinet Estimate ────────────────────────────────────────────────────────

class CabinetRequest(BaseModel):
    width_ft: float = Field(6.0, description="Cabinet width (ft)")
    height_ft: float = Field(4.0, description="Cabinet height (ft)")
    face_area_sf: Optional[float] = Field(None, description="Override face area (SF)")
    num_faces: int = Field(1, description="Number of faces (1=single, 2=double)")
    illuminated: bool = Field(True, description="Has illumination")
    has_vinyl: bool = Field(True, description="Has vinyl graphics")
    mount_type: str = Field("wall", description="Mount type: wall, roof, or pipe")
    install_height_ft: float = Field(12.0, description="Mounting height (ft)")
    miles: float = Field(0.0, description="One-way travel miles")
    crew_size: int = Field(2, description="Crew size")


@app.post("/api/estimate/cabinet")
async def run_cabinet_estimate(req: CabinetRequest):
    """Run aluminum cabinet sign estimation engine."""
    sf = req.face_area_sf if req.face_area_sf and req.face_area_sf > 0 else req.width_ft * req.height_ft
    job = JobInput(
        sign_type=SignType.ALULIT if req.illuminated else SignType.ALUNON,
        sign_sf_per_face=sf,
        num_faces=req.num_faces,
        is_illuminated=req.illuminated,
        has_vinyl=req.has_vinyl,
        has_structural_steel=False,
        install_height_ft=req.install_height_ft,
        miles_one_way=req.miles,
        crew_size=req.crew_size,
        install_mount_type=req.mount_type,
    )
    result = estimate_cabinet(job)
    total_est_hours = result.total_man_hours + result.total_crew_hours
    bench = benchmark(total_est_hours)
    bench_data = _format_benchmark(bench) if bench else None
    return _format_estimate_result(result, bench_data)


# ── Directional Estimate ───────────────────────────────────────────────────

class DirectionalRequest(BaseModel):
    width_ft: float = Field(4.0, description="Panel width (ft)")
    height_ft: float = Field(2.0, description="Panel height (ft)")
    face_area_sf: Optional[float] = Field(None, description="Override face area (SF)")
    num_units: int = Field(1, description="Number of directional panels")
    has_vinyl: bool = Field(True, description="Has vinyl graphics")
    paint_colors: int = Field(1, description="Number of paint colors")
    miles: float = Field(0.0, description="One-way travel miles")
    crew_size: int = Field(1, description="Crew size")


@app.post("/api/estimate/directional")
async def run_directional_estimate(req: DirectionalRequest):
    """Run directional/wayfinding sign estimation engine."""
    sf = req.face_area_sf if req.face_area_sf and req.face_area_sf > 0 else req.width_ft * req.height_ft
    job = JobInput(
        sign_type=SignType.DIRECT,
        sign_sf_per_face=sf,
        num_faces=1,
        num_units=req.num_units,
        has_vinyl=req.has_vinyl,
        paint_colors=req.paint_colors,
        miles_one_way=req.miles,
        crew_size=req.crew_size,
    )
    result = estimate_directional(job)
    total_est_hours = result.total_man_hours + result.total_crew_hours
    bench = benchmark(total_est_hours)
    bench_data = _format_benchmark(bench) if bench else None
    return _format_estimate_result(result, bench_data)


# ── Dimensional/Gemini Estimate ───────────────────────────────────────────

class DimensionalRequest(BaseModel):
    letter_count: int = Field(10, description="Number of letters")
    letter_height_inches: float = Field(8.0, description="Letter height (inches)")
    paint_colors: int = Field(1, description="Number of paint colors")
    miles: float = Field(0.0, description="One-way travel miles")
    crew_size: int = Field(1, description="Crew size")


@app.post("/api/estimate/dimensional")
async def run_dimensional_estimate(req: DimensionalRequest):
    """Run dimensional/Gemini letters estimation engine."""
    job = JobInput(
        sign_type=SignType.GEMINI,
        letter_count=req.letter_count,
        letter_height_inches=req.letter_height_inches,
        paint_colors=req.paint_colors,
        miles_one_way=req.miles,
        crew_size=req.crew_size,
    )
    result = estimate_dimensional(job)
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

# ── Calibration Endpoints ────────────────────────────────────────────────────


@app.get("/api/calibration")
async def get_calibration():
    """Get current calibration data and metadata."""
    from calibrate import load_calibration
    cal = load_calibration()
    meta = cal.get("metadata", {})
    return {
        "ok": True,
        "calibration_date": meta.get("calibration_date"),
        "sign_types": meta.get("total_sign_types", 0),
        "total_cells": meta.get("total_cells", 0),
        "buffer": meta.get("buffer_multiplier", 1.2),
        "warnings": meta.get("warnings", []),
        "install_floors": cal.get("install_floors", {}),
        "removal_floors": cal.get("removal_floors", {}),
        "ot_factors": {
            k: {
                "fab_prob": v.get("fab_ot_probability", 0),
                "inst_prob": v.get("install_ot_probability", 0),
                "expected": v.get("expected_total", 0),
                "n": v.get("total_jobs", 0),
            }
            for k, v in cal.get("ot_factors", {}).items()
        },
        "defaults": cal.get("defaults", {}),
    }


class CalibrateRequest(BaseModel):
    sign_type: str | None = Field(None, description="Recalibrate single sign type (or all)")
    buffer: float = Field(1.2, description="Buffer multiplier (P50 * buffer = floor)")
    dry_run: bool = Field(False, description="Preview without writing to disk")


@app.post("/api/calibrate")
async def run_calibration(req: CalibrateRequest):
    """Trigger recalibration from warehouse data."""
    import asyncio
    from calibrate import recalibrate

    def _run():
        return recalibrate(
            sign_type=req.sign_type,
            buffer=req.buffer,
            dry_run=req.dry_run,
        )

    cal = await asyncio.to_thread(_run)

    # Reload into abc_engine if not dry run
    if not req.dry_run:
        from abc_engine import reload_calibration
        reload_calibration()

    meta = cal.get("metadata", {})
    return {
        "ok": True,
        "dry_run": req.dry_run,
        "calibration_date": meta.get("calibration_date"),
        "sign_types": meta.get("total_sign_types", 0),
        "total_cells": meta.get("total_cells", 0),
        "warnings": meta.get("warnings", []),
        "install_floors_count": len(cal.get("install_floors", {})),
        "removal_floors_count": len(cal.get("removal_floors", {})),
        "ot_factors_count": len(cal.get("ot_factors", {})),
    }


# ── Structural Endpoints ────────────────────────────────────────────────────


# Iowa defaults — covers ~90% of Eagle Sign jobs
IOWA_DEFAULTS = {
    "V_mph": 115.0,
    "exposure": "C",
    "elevation_ft": 800.0,
    "risk_category": "II",
    "Kzt": 1.0,
    "soil_type": "medium_clay",
    "f_c_psi": 3000.0,
    "bolt_grade": "F1554-36",
    "label": "Iowa Defaults",
    "description": "115 mph wind, open flat land, 800 ft elevation — covers most Iowa jobs",
}


@app.get("/api/structural/defaults")
async def get_structural_defaults():
    """Return default site conditions for Iowa (90% of Eagle Sign jobs)."""
    return {"ok": True, "defaults": IOWA_DEFAULTS}


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


# ── Drawing Search (G: Drive //ES-FS02/Customers2) ────────────────────────

@app.get("/api/drawings/search")
async def api_drawing_search(
    customer: str,
    sign_type: Optional[str] = None,
    wo_number: Optional[str] = None,
    max_results: int = 25,
):
    """Search G: drive for customer drawings.

    Args:
        customer: Customer name to search for
        sign_type: Optional sign type filter (monument, pylon, channel_letter, etc.)
        wo_number: Optional WO number to search for (format: MMYY-NNNNN)
        max_results: Max results to return (default 25)
    """
    try:
        result = await asyncio.to_thread(
            search_drawings,
            customer_name=customer,
            sign_type_filter=sign_type,
            wo_number=wo_number,
            max_results=max_results,
        )
        return {
            "ok": True,
            "customer_folder": result.customer_folder,
            "total_files_scanned": result.total_files,
            "sign_types_found": result.sign_types_found,
            "warnings": result.warnings,
            "latest_revisions": [
                {
                    "filename": m.filename,
                    "path": m.path,
                    "wo_number": m.wo_number,
                    "revision": m.revision,
                    "sign_type": m.sign_type_guess,
                    "size_kb": round(m.size_bytes / 1024, 1),
                }
                for m in result.latest_revisions
            ],
            "all_drawings": [
                {
                    "filename": m.filename,
                    "path": m.path,
                    "wo_number": m.wo_number,
                    "revision": m.revision,
                    "sign_type": m.sign_type_guess,
                    "is_pdf": m.is_pdf,
                    "is_cdr": m.is_cdr,
                    "size_kb": round(m.size_bytes / 1024, 1),
                }
                for m in result.drawings
            ],
            "pdf_count": len(result.pdfs),
            "drawing_count": len(result.drawings),
        }
    except Exception as e:
        logger.exception("Drawing search failed for %s", customer)
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


@app.post("/api/drawings/bid-lookup")
async def api_drawings_for_bid(req: dict):
    """Search G: drive for drawings matching a bid's customer and sign type.

    Accepts: {"customer": "...", "sign_type": "EMC_POLE", "sq_ft": 48.0}
    """
    customer = req.get("customer", "")
    sign_type = req.get("sign_type")
    sq_ft = req.get("sq_ft")
    if not customer:
        return JSONResponse(status_code=400, content={"ok": False, "error": "customer is required"})
    try:
        result = await asyncio.to_thread(search_for_bid, customer, sign_type=sign_type, sq_ft=sq_ft)
        return {
            "ok": True,
            "customer_folder": result.customer_folder,
            "total_files_scanned": result.total_files,
            "sign_types_found": result.sign_types_found,
            "warnings": result.warnings,
            "latest_revisions": [
                {
                    "filename": m.filename,
                    "path": m.path,
                    "wo_number": m.wo_number,
                    "revision": m.revision,
                    "sign_type": m.sign_type_guess,
                    "size_kb": round(m.size_bytes / 1024, 1),
                }
                for m in result.latest_revisions
            ],
            "drawing_count": len(result.drawings),
        }
    except Exception as e:
        logger.exception("Bid drawing lookup failed for %s", customer)
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


# ══════════════════════════════════════════════════════════════════════════════
# NOTION BID PIPELINE INTEGRATION
# ══════════════════════════════════════════════════════════════════════════════

# Sign type mapping: Notion sign_type → estimator function + default params
SIGN_TYPE_MAP = {
    "CHANNEL_LETTERS":          ("channel_letter", {}),
    "CHANNEL_LOGO":             ("channel_letter", {"logo_pf": 5.0}),
    "MONUMENT_BASE":            ("monument", {"illuminated": False}),
    "MONUMENT_MANUAL_READER":   ("monument", {"illuminated": False, "num_faces": 2}),
    "EMC_MONUMENT":             ("monument", {"illuminated": True}),
    "EMC_POLE":                 ("pylon", {"illuminated": True}),
    "POLE_SIGN":                ("pylon", {"illuminated": False}),
    "EMC_RETROFIT":             ("cabinet", {"illuminated": True}),
    "EMC":                      ("cabinet", {"illuminated": True}),
    "CABINET_ILLUMINATED":      ("cabinet", {"illuminated": True}),
    "INFO_PANEL":               ("directional", {}),
    "REMOVAL":                  ("removal", {}),
    "STRUCTURAL_BASE":          ("pylon", {"illuminated": True, "include_footing": True}),
    "MASONRY_SUB":              ("monument", {"illuminated": False}),
}


def _notion_prop(props: dict, key: str, ptype: str):
    """Extract value from Notion property."""
    p = props.get(key)
    if not p:
        return None
    if ptype == "title":
        t = p.get("title")
        return t[0].get("plain_text", "") if t else ""
    elif ptype == "rich_text":
        t = p.get("rich_text")
        return t[0].get("plain_text", "") if t else ""
    elif ptype == "number":
        return p.get("number")
    elif ptype == "select":
        s = p.get("select")
        return s.get("name") if s else None
    elif ptype == "checkbox":
        return p.get("checkbox", False)
    elif ptype == "date":
        d = p.get("date")
        return d.get("start") if d else None
    elif ptype == "multi_select":
        return [s.get("name") for s in p.get("multi_select", [])]
    return None


def _parse_notion_bid(entry: dict) -> dict:
    """Parse a single Notion page into a clean bid dict."""
    props = entry.get("properties", {})
    return {
        "page_id": entry.get("id", ""),
        "quote_number": _notion_prop(props, "Quote #", "title"),
        "customer": _notion_prop(props, "Customer", "rich_text"),
        "description": _notion_prop(props, "Description", "rich_text"),
        "sign_type": _notion_prop(props, "Sign Type", "select"),
        "sq_ft": _notion_prop(props, "Sq Ft", "number"),
        "faces": _notion_prop(props, "Faces", "number"),
        "cabinet_dims": _notion_prop(props, "Cabinet Dims", "rich_text"),
        "est_value": _notion_prop(props, "Est. Value", "number"),
        "pipeline_stage": _notion_prop(props, "Pipeline Stage", "select"),
        "status": _notion_prop(props, "Status", "select"),
        "salesman": _notion_prop(props, "Salesman", "select"),
        "location": _notion_prop(props, "Location", "rich_text"),
        "email_received": _notion_prop(props, "Email Received", "date"),
        "age_days": _notion_prop(props, "Age(Days)", "number"),
        "blocking": _notion_prop(props, "Blocking", "multi_select"),
        "blocking_owner": _notion_prop(props, "Blocking Owner", "select"),
        "takeoff_done": _notion_prop(props, "\u2705 Takeoff Done", "checkbox"),
        "quoted": _notion_prop(props, "\u2705 Quoted", "checkbox"),
    }


@app.get("/api/notion/bids")
async def get_notion_bids():
    """Fetch active bids from Notion Bid Pipeline."""
    if not NOTION_TOKEN or not NOTION_BID_PIPELINE_DB:
        return {"error": "Notion not configured. Set NOTION_TOKEN and NOTION_BID_PIPELINE in .env", "bids": []}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"https://api.notion.com/v1/databases/{NOTION_BID_PIPELINE_DB}/query",
                headers=NOTION_HEADERS,
                json={
                    "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
                    "page_size": 50,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        bids = [_parse_notion_bid(entry) for entry in data.get("results", [])]
        # Summary stats
        stages = {}
        for b in bids:
            s = b.get("pipeline_stage") or "UNKNOWN"
            stages[s] = stages.get(s, 0) + 1
        total_value = sum(b.get("est_value") or 0 for b in bids)
        return {
            "bids": bids,
            "total": len(bids),
            "total_pipeline_value": total_value,
            "stage_counts": stages,
            "ready_to_takeoff": [b for b in bids if b.get("pipeline_stage") == "READY_TO_TAKEOFF" and not b.get("takeoff_done")],
        }
    except httpx.HTTPStatusError as e:
        return JSONResponse(status_code=e.response.status_code, content={"error": f"Notion API error: {e.response.text}", "bids": []})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e), "bids": []})


class TakeoffRequest(BaseModel):
    page_id: str = Field(..., description="Notion page ID for the bid")


@app.post("/api/notion/takeoff")
async def run_notion_takeoff(req: TakeoffRequest):
    """Run takeoff estimate for a Notion bid, mark it done, return results."""
    if not NOTION_TOKEN:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Notion not configured"})
    try:
        # 1. Fetch the bid from Notion
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"https://api.notion.com/v1/pages/{req.page_id}",
                headers=NOTION_HEADERS,
            )
            resp.raise_for_status()
            page = resp.json()

        bid = _parse_notion_bid(page)
        sign_type_raw = bid.get("sign_type") or "CABINET_ILLUMINATED"
        sq_ft = bid.get("sq_ft") or 24.0
        faces = bid.get("faces") or 1

        # 2. Map sign type to estimator
        est_key, defaults = SIGN_TYPE_MAP.get(sign_type_raw, ("cabinet", {"illuminated": True}))

        # 3. Build job and run estimator
        if est_key == "channel_letter":
            job = JobInput(
                font_type=FontType.BLOCK,
                construction=ConstructionType.FACE_LIT,
                pf_manual=sq_ft * 2.5,  # rough PF estimate from SF
                letter_height_inches=12.0,
                logo_pf=defaults.get("logo_pf", 0.0),
            )
            result = estimate(job)
        elif est_key == "monument":
            job = JobInput(
                sign_type=SignType.MONDF if faces >= 2 else SignType.MONSF,
                sign_sf_per_face=sq_ft / max(faces, 1),
                num_faces=faces,
                is_illuminated=defaults.get("illuminated", False),
                has_vinyl=True,
            )
            result = estimate_monument(job)
        elif est_key == "pylon":
            _pyl_lit = defaults.get("illuminated", True)
            job = JobInput(
                sign_type=SignType.POLLIT if _pyl_lit else SignType.POLNON,
                sign_sf_per_face=sq_ft / max(faces, 1),
                num_faces=max(faces, 2),
                is_illuminated=_pyl_lit,
                has_vinyl=True,
                has_structural_steel=True,
                has_footing=defaults.get("include_footing", True),
                install_height_ft=25.0,
                crew_size=3,
            )
            result = estimate_pylon(job)
        elif est_key == "cabinet":
            job = JobInput(
                sign_type=SignType.ALULIT if defaults.get("illuminated", True) else SignType.ALUNON,
                sign_sf_per_face=sq_ft / max(faces, 1),
                num_faces=faces,
                is_illuminated=defaults.get("illuminated", True),
                has_vinyl=True,
            )
            result = estimate_cabinet(job)
        elif est_key == "directional":
            job = JobInput(
                sign_type=SignType.DIRECT,
                sign_sf_per_face=sq_ft,
                num_faces=1,
                num_units=1,
                has_vinyl=True,
            )
            result = estimate_directional(job)
        elif est_key == "removal":
            job = JobInput(
                sign_type=SignType.CLLIT,
                num_units=1,
                face_sf_override=sq_ft if sq_ft else None,
            )
            result = estimate_removal(job)
        else:
            # Default fallback
            job = JobInput(
                sign_type=SignType.ALULIT,
                sign_sf_per_face=sq_ft / max(faces, 1),
                num_faces=faces,
                is_illuminated=True,
                has_vinyl=True,
            )
            result = estimate_cabinet(job)

        # 4. Format result
        total_est = result.total_man_hours + result.total_crew_hours
        bench = benchmark(total_est)
        bench_data = _format_benchmark(bench) if bench else None
        estimate_data = _format_estimate_result(result, bench_data)

        # 5. Mark takeoff done in Notion + update Pipeline Stage to IN_PROGRESS
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.patch(
                f"https://api.notion.com/v1/pages/{req.page_id}",
                headers=NOTION_HEADERS,
                json={
                    "properties": {
                        "\u2705 Takeoff Done": {"checkbox": True},
                        "Pipeline Stage": {"select": {"name": "IN_PROGRESS"}},
                    }
                },
            )

        return {
            "ok": True,
            "bid": bid,
            "estimator_used": est_key,
            "estimate": estimate_data,
            "notion_updated": True,
        }
    except httpx.HTTPStatusError as e:
        return JSONResponse(status_code=e.response.status_code, content={"ok": False, "error": f"Notion API: {e.response.text}"})
    except Exception as e:
        logger.exception("Takeoff failed for %s", req.page_id)
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


# ── Notion Status Update ───────────────────────────────────────────────────

PIPELINE_STAGES = [
    "INTAKE", "NEEDS_INFO", "NEEDS_VENDOR_QUOTE", "NEEDS_SUB_QUOTE",
    "READY_TO_TAKEOFF", "IN_PROGRESS", "QUOTED", "WON", "LOST",
]


class StatusUpdateRequest(BaseModel):
    page_id: str = Field(..., description="Notion page ID")
    pipeline_stage: Optional[str] = Field(None, description="New pipeline stage")
    est_value: Optional[float] = Field(None, description="Estimated value ($)")
    salesman: Optional[str] = Field(None, description="Salesman name")
    blocking: Optional[List[str]] = Field(None, description="Blocking items")


@app.patch("/api/notion/bid")
async def update_notion_bid(req: StatusUpdateRequest):
    """Update a bid's properties in Notion (stage, value, salesman, blocking)."""
    if not NOTION_TOKEN:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Notion not configured"})

    props = {}
    if req.pipeline_stage:
        if req.pipeline_stage not in PIPELINE_STAGES:
            return JSONResponse(status_code=400, content={
                "ok": False,
                "error": f"Invalid stage '{req.pipeline_stage}'. Must be one of: {PIPELINE_STAGES}",
            })
        props["Pipeline Stage"] = {"select": {"name": req.pipeline_stage}}
    if req.est_value is not None:
        props["Est. Value"] = {"number": req.est_value}
    if req.salesman:
        props["Salesman"] = {"select": {"name": req.salesman}}
    if req.blocking is not None:
        props["Blocking"] = {"multi_select": [{"name": b} for b in req.blocking]}

    if not props:
        return {"ok": False, "error": "No fields to update"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.patch(
                f"https://api.notion.com/v1/pages/{req.page_id}",
                headers=NOTION_HEADERS,
                json={"properties": props},
            )
            resp.raise_for_status()
        return {"ok": True, "updated": list(props.keys()), "page_id": req.page_id}
    except httpx.HTTPStatusError as e:
        return JSONResponse(status_code=e.response.status_code, content={
            "ok": False, "error": f"Notion API: {e.response.text}",
        })
    except Exception as e:
        logger.exception("Notion update failed for %s", req.page_id)
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


# ── Notification: SMS / Webhook ─────────────────────────────────────────────

class NotifyRequest(BaseModel):
    quote_number: str
    customer: str
    total_hours: float
    estimator_type: str
    message: str = ""


SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")


def _send_sms(body: str) -> dict:
    """Send SMS via SMTP email-to-SMS gateway.

    Uses M365 authenticated SMTP (smtp.office365.com:587 with STARTTLS)
    or a local SMTP relay (port 25, no auth).

    Requires SMTP_SERVER and SMTP_FROM in .env.
    SMS_PHONE defaults to 7122666482 (Brady Flink).
    SMS_CARRIER_GATEWAY defaults to vtext.com (Verizon).

    Common carrier gateways:
        Verizon:    vtext.com
        AT&T:       txt.att.net
        T-Mobile:   tmomail.net
        US Cellular: email.uscc.net
        Sprint:     messaging.sprintpcs.com
    """
    if not SMTP_SERVER or not SMTP_FROM:
        return {"sent": False, "reason": "SMTP_SERVER and SMTP_FROM not configured in .env"}
    if not SMS_PHONE:
        return {"sent": False, "reason": "SMS_PHONE not configured in .env"}

    to_addr = f"{SMS_PHONE}@{SMS_CARRIER_GATEWAY}"
    msg = MIMEText(body)
    msg["From"] = SMTP_FROM
    msg["To"] = to_addr
    msg["Subject"] = "SignX Bid Ready"

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as smtp:
            smtp.ehlo()
            if SMTP_PORT == 587:
                smtp.starttls()
                smtp.ehlo()
            if SMTP_USER and SMTP_PASS:
                smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
        return {"sent": True, "to": to_addr, "gateway": SMS_CARRIER_GATEWAY}
    except Exception as e:
        logger.warning("SMS send failed: %s", e)
        return {"sent": False, "reason": str(e)}


@app.post("/api/notify/bid-ready")
async def notify_bid_ready(req: NotifyRequest):
    """Send notification that a bid takeoff is complete and ready for review.

    Delivery methods (in order):
    1. SMS via SMTP email-to-SMS gateway (if SMTP_SERVER configured)
    2. Power Automate HTTP trigger webhook (if NOTIFY_WEBHOOK_URL configured)
    3. Server log (always)
    """
    text = req.message or (
        f"SIGNX: Takeoff done - {req.quote_number} ({req.customer}). "
        f"{req.total_hours:.1f}h {req.estimator_type}. Ready for review."
    )
    payload = {
        "event": "bid_takeoff_complete",
        "quote_number": req.quote_number,
        "customer": req.customer,
        "total_hours": req.total_hours,
        "estimator_type": req.estimator_type,
        "message": text,
        "timestamp": datetime.now().isoformat(),
    }

    # 1. SMS via SMTP gateway
    sms_result = _send_sms(text)

    # 2. Power Automate webhook
    webhook_sent = False
    if NOTIFY_WEBHOOK_URL:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(NOTIFY_WEBHOOK_URL, json=payload)
                resp.raise_for_status()
                webhook_sent = True
        except Exception as e:
            logger.warning("Webhook notification failed: %s", e)

    # 3. Always log
    logger.info("BID READY: %s %s — %.1f hrs (%s)", req.quote_number, req.customer, req.total_hours, req.estimator_type)

    return {
        "ok": True,
        "sms": sms_result,
        "webhook_sent": webhook_sent,
        "payload": payload,
    }


# ── PA Flow Status ──────────────────────────────────────────────────────────

@app.get("/api/notion/flow-status")
async def get_flow_status():
    """Return Power Automate flow integration status."""
    return {
        "flows": [
            {
                "name": "CORRESPONDENCE-CLASSIFIER",
                "flow_id": "1a6f964f-54a8-47ba-bec8-a259227d1daa",
                "status": "active",
                "type": "BID-INTAKE-PROOF",
                "description": "Watches Inbox/BID REQUEST/Jeff Fye, extracts bid fields via Claude Sonnet, creates Notion rows",
                "scope": "Jeff Fye subfolder (Phase 1)",
            },
        ],
        "planned_flows": [
            {"name": "Phase 2: All Salespeople", "status": "planned", "description": "Extend to Joe Phillips, Rich Thompson, House"},
            {"name": "VENDOR-QUOTE-EXTRACT", "status": "planned", "description": "Extract pricing from vendor/supplier quote emails"},
            {"name": "DAILY-BID-DIGEST", "status": "planned", "description": "Morning summary pushed to Notion vault"},
        ],
        "salesmen": ["Jeff Fye", "Joe Phillips", "Rich Thompson", "House"],
        "email_folder": "Inbox/BID REQUEST/{salesperson}",
        "last_check": datetime.now().isoformat(),
    }


# ── KeyedIn Formatting ──────────────────────────────────────────────────────

class KeyedInFormatRequest(BaseModel):
    quote_number: str
    customer: str
    labor_lines: list = Field(default_factory=list)
    install_lines: list = Field(default_factory=list)


@app.post("/api/keyedin/format")
async def format_for_keyedin(req: KeyedInFormatRequest):
    """Format estimate results for KeyedIn ERP quote entry.
    Returns work orders ready to paste into KeyedIn."""
    all_lines = req.labor_lines + req.install_lines
    work_orders = []
    for line in all_lines:
        work_orders.append({
            "work_code": line.get("code", ""),
            "description": line.get("desc", ""),
            "hours": line.get("hours", 0),
            "unit_type": line.get("unit", "man-hrs"),
            "department": line.get("dept", ""),
            "section": line.get("section", ""),
        })
    total_man = sum(l["hours"] for l in work_orders if "CREW" not in l["unit_type"].upper())
    total_crew = sum(l["hours"] for l in work_orders if "CREW" in l["unit_type"].upper())
    return {
        "keyedin_ready": True,
        "quote_number": req.quote_number,
        "customer": req.customer,
        "work_orders": work_orders,
        "total_man_hours": round(total_man, 2),
        "total_crew_hours": round(total_crew, 2),
        "line_count": len(work_orders),
        "instructions": "Copy work orders to KeyedIn Quote Entry → Direct Purchase tab. Use Work Code as line item code. Man-hrs go to standard entry, CREW-hrs get crew multiplier.",
    }


# ══════════════════════════════════════════════════════════════════════════════
# PROJECT DOSSIER — Unified intelligence view per project
# ══════════════════════════════════════════════════════════════════════════════


@app.get("/api/dossier")
async def get_project_dossier(customer: str, sign_type: Optional[str] = None,
                              wo_number: Optional[str] = None,
                              revenue: Optional[float] = None,
                              salesperson: Optional[str] = None):
    """Build a complete project dossier for a customer.

    Aggregates: Notion bids, G: drive files + drawings, warehouse history,
    customer intelligence, similar past jobs, win probability, price
    recommendations, and completeness checklist.
    One call = everything you need to know about a project.
    """
    dossier: dict = {
        "customer_query": customer,
        "generated": datetime.now().isoformat(),
        "warnings": [],
    }

    # ── 1. Customer Intelligence (from 27K warehouse jobs) ────────────────
    try:
        profile = await asyncio.to_thread(get_customer_profile, customer)
    except Exception as e:
        logger.warning("Customer profile failed: %s", e)
        profile = None
        dossier["warnings"].append(f"Customer profile unavailable: {e}")

    if profile:
        # Group jobs by location for multi-location breakout
        location_groups = {}
        for job in profile.recent_jobs:
            loc = job.get("location") or "Unknown"
            location_groups.setdefault(loc, []).append(job)

        dossier["customer"] = {
            "customer_name": profile.customer_name,
            "customer_no": profile.customer_no,
            "total_jobs": profile.total_jobs,
            "total_revenue": round(profile.total_revenue, 2),
            "avg_revenue_per_job": round(profile.avg_revenue_per_job, 2),
            "avg_gm_pct": profile.avg_gm_pct,
            "margin_trend": profile.margin_trend,
            "relationship_score": profile.relationship_score,
            "relationship_label": profile.relationship_label,
            "top_sign_type": profile.top_sign_type,
            "sign_type_breakdown": profile.sign_type_breakdown[:8],
            "locations": profile.locations[:20],
            "last_job_date": profile.last_job_date,
            "months_since_last": profile.months_since_last,
            "insights": profile.insights,
            "recent_jobs": profile.recent_jobs,
            "jobs_by_location": {
                loc: jobs for loc, jobs in sorted(
                    location_groups.items(),
                    key=lambda x: len(x[1]),
                    reverse=True,
                )
            },
        }
        dossier["insights"] = profile.insights
    else:
        dossier["customer"] = None
        dossier["insights"] = ["New customer -- no warehouse history"]

    # ── 2. Similar Past Jobs ──────────────────────────────────────────────
    try:
        if sign_type:
            similar = await asyncio.to_thread(
                find_similar_jobs, sign_type,
                revenue_estimate=revenue or 0, max_results=8,
            )
        elif profile and profile.top_sign_type:
            similar = await asyncio.to_thread(
                find_similar_jobs, profile.top_sign_type,
                revenue_estimate=revenue or 0, max_results=8,
            )
        else:
            similar = []
    except Exception as e:
        logger.warning("Similar jobs failed: %s", e)
        similar = []
        dossier["warnings"].append(f"Similar jobs unavailable: {e}")

    dossier["similar_jobs"] = [
        {
            "wo": s.work_order,
            "customer": s.customer,
            "location": s.location,
            "type": s.sign_type,
            "description": s.description,
            "revenue": s.billing,
            "gm_pct": s.gm_pct,
            "similarity": s.similarity_score,
        }
        for s in similar
    ]

    # ── 3. Market Intel for this sign type ────────────────────────────────
    effective_sign_type = sign_type or (profile.top_sign_type if profile else None)
    try:
        if effective_sign_type:
            mkt = await asyncio.to_thread(get_market_intel, effective_sign_type)
            if mkt:
                dossier["market"] = {
                    "sign_type": mkt.sign_type,
                    "total_jobs": mkt.total_jobs,
                    "avg_revenue": mkt.avg_revenue,
                    "median_revenue": mkt.median_revenue,
                    "avg_gm_pct": mkt.avg_gm_pct,
                    "p25_revenue": mkt.p25_revenue,
                    "p75_revenue": mkt.p75_revenue,
                }
            else:
                dossier["market"] = None
        else:
            dossier["market"] = None
    except Exception as e:
        logger.warning("Market intel failed: %s", e)
        dossier["market"] = None
        dossier["warnings"].append(f"Market intel unavailable: {e}")

    # ── 4. G: Drive Project Files (classified) ────────────────────────────
    try:
        files = await asyncio.to_thread(
            scan_project_files, customer, wo_number=wo_number, sign_type=sign_type,
        )
        dossier["project_files"] = {
            "customer_folder": files.customer_folder,
            "folder_path": files.customer_folder,
            "total_scanned": files.total_files_scanned,
            "sign_types_found": files.sign_types_found,
            "wo_numbers_found": files.wo_numbers_found,
            "checklist": files.checklist,
            "completeness_pct": files.completeness_pct,
            "warnings": files.warnings,
            "by_type": {
                dtype: [
                    {
                        "filename": f.filename,
                        "path": f.path,
                        "doc_type": f.doc_type,
                        "doc_type_label": f.doc_type_label,
                        "wo_number": f.wo_number,
                        "revision": f.revision,
                        "sign_type": f.sign_type,
                        "size_kb": round(f.size_bytes / 1024, 1),
                        "modified": f.modified,
                        "subfolder": f.subfolder,
                        "relevance": f.relevance,
                    }
                    for f in flist[:20]
                ]
                for dtype, flist in files.by_type.items()
            },
            "files": [
                {
                    "filename": f.filename,
                    "path": f.path,
                    "doc_type": f.doc_type,
                    "doc_type_label": f.doc_type_label,
                    "wo_number": f.wo_number,
                    "revision": f.revision,
                    "sign_type": f.sign_type,
                    "size_kb": round(f.size_bytes / 1024, 1),
                    "modified": f.modified,
                }
                for f in files.files[:50]
            ],
            "total_files": len(files.files),
            "updated": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.warning("Project files scan failed: %s", e)
        dossier["project_files"] = {
            "warnings": [f"G: drive not accessible: {e}"],
            "files": [],
            "total_files": 0,
            "updated": datetime.now().isoformat(),
        }
        dossier["warnings"].append(f"Project files unavailable: {e}")

    # ── 5. Drawing Search (G: drive — always search by customer) ──────────
    try:
        drawings_result = await asyncio.to_thread(
            search_drawings, customer, sign_type_filter=sign_type, max_results=25,
        )
        dossier["drawings"] = {
            "customer_folder": drawings_result.customer_folder,
            "total_files": drawings_result.total_files,
            "sign_types_found": drawings_result.sign_types_found,
            "latest_revisions": [
                {
                    "filename": d.filename,
                    "path": d.path,
                    "wo_number": d.wo_number,
                    "revision": d.revision,
                    "sign_type_guess": d.sign_type_guess,
                    "size_kb": round(d.size_bytes / 1024, 1),
                }
                for d in drawings_result.latest_revisions[:15]
            ],
            "pdfs": [
                {
                    "filename": d.filename,
                    "wo_number": d.wo_number,
                    "revision": d.revision,
                    "sign_type_guess": d.sign_type_guess,
                }
                for d in drawings_result.pdfs[:20]
            ],
            "warnings": drawings_result.warnings,
            "updated": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.warning("Drawing search failed: %s", e)
        dossier["drawings"] = {"warnings": [str(e)], "latest_revisions": [], "pdfs": []}
        dossier["warnings"].append(f"Drawing search unavailable: {e}")

    # ── 6. Win Probability (heuristic + ML) ───────────────────────────────
    est_price = revenue or (profile.avg_revenue_per_job if profile else 0) or 5000
    eff_sign = effective_sign_type or "CHANNEL_LETTER"
    try:
        heuristic = await asyncio.to_thread(
            score_bid, customer, eff_sign, est_price, salesperson,
        )
        dossier["win_probability"] = {
            "heuristic": {
                "score": heuristic.win_probability,
                "confidence": heuristic.confidence,
                "comparable_wins": heuristic.comparable_wins,
                "comparable_losses": heuristic.comparable_losses,
                "factors": {
                    f.name: {
                        "score": round(f.score, 4),
                        "weight": f.weight,
                        "weighted": round(f.weighted, 4),
                        "explanation": f.explanation,
                    }
                    for f in heuristic.factors
                },
                "recommendations": heuristic.recommendations,
            },
            "updated": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.warning("Heuristic bid scoring failed: %s", e)
        dossier["win_probability"] = {"heuristic": None, "warnings": [str(e)]}
        dossier["warnings"].append(f"Win probability (heuristic) unavailable: {e}")

    try:
        ml_pred = await asyncio.to_thread(
            predict_win_probability, customer, eff_sign, est_price, salesperson,
        )
        wp = dossier.get("win_probability", {})
        wp["ml"] = {
            "score": round(ml_pred.win_probability * 100, 1) if ml_pred.win_probability else None,
            "confidence": ml_pred.confidence,
            "model_available": ml_pred.model_available,
            "risk_factors": ml_pred.risk_factors,
            "positive_factors": ml_pred.positive_factors,
        }
        dossier["win_probability"] = wp
    except Exception as e:
        logger.warning("ML win prediction failed: %s", e)
        wp = dossier.get("win_probability", {})
        wp["ml"] = None
        dossier["win_probability"] = wp

    # ── 7. Price Recommendation ───────────────────────────────────────────
    try:
        if effective_sign_type:
            price_rec = await asyncio.to_thread(
                get_price_recommendation, effective_sign_type, customer,
            )
            if price_rec:
                dossier["price_recommendation"] = {
                    "sign_type": price_rec.sign_type,
                    "conservative": price_rec.conservative,
                    "balanced": price_rec.balanced,
                    "aggressive": price_rec.aggressive,
                    "data_points": price_rec.data_points,
                    "customer_adjusted": price_rec.customer_adjusted,
                    "customer_avg_spend": price_rec.customer_avg_spend,
                    "customer_job_count": price_rec.customer_job_count,
                    "updated": datetime.now().isoformat(),
                }
            else:
                dossier["price_recommendation"] = None
        else:
            dossier["price_recommendation"] = None
    except Exception as e:
        logger.warning("Price recommendation failed: %s", e)
        dossier["price_recommendation"] = None
        dossier["warnings"].append(f"Price recommendation unavailable: {e}")

    # ── 8. Notion Bids for this customer ──────────────────────────────────
    notion_bids = []
    if NOTION_TOKEN and NOTION_BID_PIPELINE_DB:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"https://api.notion.com/v1/databases/{NOTION_BID_PIPELINE_DB}/query",
                    headers=NOTION_HEADERS,
                    json={
                        "filter": {
                            "property": "Customer",
                            "rich_text": {"contains": customer},
                        },
                        "page_size": 20,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    notion_bids = [
                        _parse_notion_bid(e) for e in data.get("results", [])
                    ]
        except Exception as e:
            logger.warning("Notion query failed in dossier: %s", e)
            dossier["warnings"].append(f"Notion bids unavailable: {e}")

    dossier["bids"] = notion_bids
    dossier["active_bids"] = len([b for b in notion_bids if b.get("pipeline_stage") not in ("WON", "LOST", None)])

    return dossier


@app.post("/api/dossier/prefetch")
async def prefetch_dossier(customer: str, sign_type: Optional[str] = None,
                           wo_number: Optional[str] = None):
    """Pre-warm the G: drive file cache for a customer. Fire-and-forget from UI."""
    await asyncio.to_thread(scan_project_files, customer, wo_number=wo_number,
                            sign_type=sign_type)
    return {"ok": True, "message": f"Cache warmed for {customer}"}


@app.get("/api/cache/stats")
async def cache_stats():
    """Return current cache status for monitoring."""
    from project_files import _cache, _bg_scans
    return {
        "cached_customers": len(_cache),
        "active_scans": len(_bg_scans),
        "cache_keys": list(_cache.keys()),
    }


@app.get("/api/intel/customer/{customer_name}")
async def api_customer_intel(customer_name: str):
    """Customer intelligence from warehouse history."""
    profile = await asyncio.to_thread(get_customer_profile, customer_name)
    if not profile:
        return JSONResponse(status_code=404, content={
            "ok": False,
            "error": f"No warehouse history found for '{customer_name}'",
        })
    return {
        "ok": True,
        "customer_name": profile.customer_name,
        "customer_no": profile.customer_no,
        "total_jobs": profile.total_jobs,
        "total_revenue": round(profile.total_revenue, 2),
        "avg_revenue_per_job": round(profile.avg_revenue_per_job, 2),
        "avg_gm_pct": profile.avg_gm_pct,
        "margin_trend": profile.margin_trend,
        "relationship_score": profile.relationship_score,
        "relationship_label": profile.relationship_label,
        "top_sign_type": profile.top_sign_type,
        "sign_type_breakdown": profile.sign_type_breakdown,
        "locations": profile.locations,
        "last_job_date": profile.last_job_date,
        "months_since_last": profile.months_since_last,
        "insights": profile.insights,
        "recent_jobs": profile.recent_jobs,
    }


@app.get("/api/intel/similar")
async def api_similar_jobs(sign_type: str, revenue: float = 0, location: str = "",
                           limit: int = 10):
    """Find similar historical jobs by sign type and revenue range."""
    similar = await asyncio.to_thread(find_similar_jobs, sign_type, revenue_estimate=revenue,
                                      location=location, max_results=limit)
    return {
        "ok": True,
        "sign_type": sign_type,
        "matches": len(similar),
        "jobs": [
            {
                "wo": s.work_order,
                "customer": s.customer,
                "location": s.location,
                "type": s.sign_type,
                "description": s.description,
                "revenue": s.billing,
                "labor_cost": s.labor_cost,
                "gm_pct": s.gm_pct,
                "date": s.date_completed,
                "similarity": s.similarity_score,
            }
            for s in similar
        ],
    }


@app.get("/api/intel/market/{sign_type}")
async def api_market_intel(sign_type: str):
    """Market intelligence for a sign type — pricing, volume, margins."""
    mkt = await asyncio.to_thread(get_market_intel, sign_type)
    if not mkt:
        return JSONResponse(status_code=404, content={
            "ok": False,
            "error": f"No market data for '{sign_type}'",
        })
    return {
        "ok": True,
        "sign_type": mkt.sign_type,
        "total_jobs": mkt.total_jobs,
        "avg_revenue": mkt.avg_revenue,
        "median_revenue": mkt.median_revenue,
        "avg_gm_pct": mkt.avg_gm_pct,
        "p25_revenue": mkt.p25_revenue,
        "p75_revenue": mkt.p75_revenue,
        "top_customers": mkt.top_customers,
    }


@app.get("/api/intel/warehouse")
async def api_warehouse_stats():
    """Top-level warehouse statistics."""
    return await asyncio.to_thread(warehouse_stats)


@app.get("/api/project-files")
async def api_project_files(customer: str, wo_number: Optional[str] = None,
                            sign_type: Optional[str] = None):
    """Scan G: drive for all project files, classified by document type."""
    result = await asyncio.to_thread(scan_project_files, customer, wo_number=wo_number, sign_type=sign_type)
    return {
        "ok": True,
        "customer_folder": result.customer_folder,
        "total_scanned": result.total_files_scanned,
        "sign_types_found": result.sign_types_found,
        "wo_numbers_found": result.wo_numbers_found,
        "checklist": result.checklist,
        "completeness_pct": result.completeness_pct,
        "warnings": result.warnings,
        "files": [
            {
                "filename": f.filename,
                "path": f.path,
                "doc_type": f.doc_type,
                "doc_type_label": f.doc_type_label,
                "wo_number": f.wo_number,
                "revision": f.revision,
                "sign_type": f.sign_type,
                "ext": f.ext,
                "size_kb": round(f.size_bytes / 1024, 1),
                "modified": f.modified,
                "subfolder": f.subfolder,
                "relevance": f.relevance,
            }
            for f in result.files[:100]
        ],
        "total_files": len(result.files),
    }


# ── Bid Scoring Endpoints ────────────────────────────────────────────────────


@app.post("/api/bid/score")
async def api_bid_score(
    customer: str,
    sign_type: str,
    price: float,
    salesperson: Optional[str] = None,
):
    """Score the win probability for a bid opportunity.

    Uses 6 weighted signals cross-validated against 18,670 labeled quotes.
    """
    result = await asyncio.to_thread(score_bid, customer, sign_type, price, salesperson)
    return {
        "ok": True,
        "win_probability": result.win_probability,
        "confidence": result.confidence,
        "comparable_wins": result.comparable_wins,
        "comparable_losses": result.comparable_losses,
        "factors": [
            {
                "name": f.name,
                "score": round(f.score, 4),
                "weight": f.weight,
                "weighted": round(f.weighted, 4),
                "explanation": f.explanation,
            }
            for f in result.factors
        ],
        "recommendations": result.recommendations,
    }


@app.get("/api/bid/win-rates")
async def api_win_rates():
    """Aggregate win rate statistics: overall, by year, salesperson, bracket, sign type."""
    return await asyncio.to_thread(get_win_rate_stats)


@app.get("/api/bid/price-recommendation")
async def api_price_recommendation(sign_type: str, customer: Optional[str] = None):
    """3-tier pricing recommendation based on won bid distribution."""
    rec = await asyncio.to_thread(get_price_recommendation, sign_type, customer)
    if not rec:
        return JSONResponse(status_code=404, content={
            "ok": False,
            "error": f"No pricing data for sign type '{sign_type}'",
        })
    return {
        "ok": True,
        "sign_type": rec.sign_type,
        "conservative": rec.conservative,
        "balanced": rec.balanced,
        "aggressive": rec.aggressive,
        "data_points": rec.data_points,
        "customer_adjusted": rec.customer_adjusted,
        "customer_avg_spend": rec.customer_avg_spend,
        "customer_job_count": rec.customer_job_count,
    }


@app.get("/api/bid/scoring-health")
async def api_scoring_health():
    """Scoring engine diagnostics — data sizes, cache state, coverage."""
    return await asyncio.to_thread(scoring_stats)


# ── ML Model Endpoints ─────────────────────────────────────────────────────


@app.post("/api/bid/ml-score")
async def api_ml_score(
    customer: str,
    sign_type: str,
    price: float,
    salesperson: Optional[str] = None,
):
    """ML-trained win probability using logistic regression on 18K+ labeled quotes.

    Complements the heuristic /api/bid/score with a data-driven model.
    AUC-ROC ~0.80, Brier ~0.19.
    """
    pred = await asyncio.to_thread(
        predict_win_probability, customer, sign_type, price, salesperson
    )
    return {
        "ok": True,
        "win_probability": pred.win_probability,
        "confidence": pred.confidence,
        "model_available": pred.model_available,
        "risk_factors": pred.risk_factors,
        "positive_factors": pred.positive_factors,
        "feature_contributions": pred.feature_contributions,
        "feature_values": {k: round(v, 4) for k, v in pred.feature_values.items()},
    }


@app.get("/api/bid/ml-diagnostics")
async def api_ml_diagnostics():
    """ML model health: AUC-ROC, Brier, coefficients, data coverage."""
    return await asyncio.to_thread(get_model_diagnostics)


if __name__ == "__main__":
    print("\n  SignX-Takeoff Server v3.0 — Intelligence Platform")
    print("  http://localhost:8765")
    print("  Endpoints:")
    print("    Estimation: /api/estimate, /api/estimate/monument, /api/estimate/pylon, ...")
    print("    Structural: /api/structural/wind, /api/structural/full-design, ...")
    print("    Drawings:   /api/drawings/search, /api/drawings/bid-lookup")
    print("    Pipeline:   /api/notion/bids, /api/notion/takeoff, /api/notion/flow-status")
    print("    KeyedIn:    /api/keyedin/format")
    print("    Notify:     /api/notify/bid-ready  (SMS to %s@%s)" % (SMS_PHONE, SMS_CARRIER_GATEWAY))
    print()
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")
