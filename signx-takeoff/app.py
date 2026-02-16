"""
SignX-Takeoff — Unified Channel Letter Takeoff & Estimation Server.

Run:  python app.py
Open: http://localhost:8765

Combines PDF → PF extraction (PyMuPDF), ABC formula engine, and
KeyedIn-ready output into a single web application.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

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
    calculate_logo_pf,
    calculate_pf_from_chart,
    estimate,
    get_footage_chart,
    interpolate_pf,
)
from extract_pf_from_pdf import extract_pf_from_pdf
from warehouse import benchmark

app = FastAPI(title="SignX-Takeoff", version="1.0.0")

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

    # Warehouse benchmark
    total_est_hours = result.total_man_hours + result.total_crew_hours
    bench = benchmark(total_est_hours)
    bench_data = None
    if bench:
        bench_data = {
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

    return {
        "total_pf": result.total_pf,
        "pf_source": result.pf_source,
        "construction": result.construction,
        "height_category": result.height_category,
        "letter_count": result.letter_count,
        "labor": [
            {
                "code": l.work_code,
                "desc": l.description,
                "hours": l.hours,
                "unit": l.unit_type,
                "dept": l.department,
                "formula": l.formula,
                "section": l.section,
            }
            for l in result.labor_lines
        ],
        "install": [
            {
                "code": l.work_code,
                "desc": l.description,
                "hours": l.hours,
                "unit": l.unit_type,
                "dept": l.department,
                "formula": l.formula,
                "section": l.section,
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


if __name__ == "__main__":
    print("\n  SignX-Takeoff Server")
    print("  http://localhost:8765\n")
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")
