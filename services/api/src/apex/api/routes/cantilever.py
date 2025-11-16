"""Cantilever sign analysis endpoints."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Add domain path for imports
_domains_path = Path(__file__).parent.parent.parent / "domains" / "signage"
if str(_domains_path) not in sys.path:
    sys.path.insert(0, str(_domains_path))

from cantilever_solver import (
    CantileverConfig,
    CantileverLoads,
    CantileverType,
    ConnectionType,
    analyze_cantilever_sign,
    optimize_cantilever_design,
    calculate_cantilever_foundation_loads,
)

from ..common.models import make_envelope
from ..common.envelope import calc_confidence
from ..common.transactions import with_transaction
from ..deps import get_code_version, get_model_config
from ..db import get_db, Project
from ..schemas import ResponseEnvelope, add_assumption

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/signage/cantilever", tags=["cantilever"])


@router.post("/analyze", response_model=ResponseEnvelope)
async def analyze_cantilever(
    req: dict,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """
    Analyze cantilever sign structure for loads and stresses.
    
    Request body:
    ```json
    {
        "project_id": "proj_123",  // Optional - saves to project if provided
        "config": {
            "type": "single",  // single, double, truss, cable
            "arm_length_ft": 15.0,
            "arm_angle_deg": 0.0,  // 0 = horizontal, positive = upward
            "arm_section": "HSS8x8x1/2",
            "connection_type": "bolted_flange",
            "num_arms": 1,
            "arm_spacing_ft": 0.0
        },
        "loads": {
            "sign_weight_lb": 500.0,
            "sign_area_ft2": 48.0,
            "wind_pressure_psf": 35.0,
            "ice_thickness_in": 0.5,  // Optional
            "eccentricity_ft": 0.0  // Optional offset from centerline
        },
        "pole_height_ft": 20.0,
        "include_fatigue": true,  // Optional, default true
        "design_life_years": 50  // Optional, default 50
    }
    ```
    
    Returns cantilever analysis with moments, stresses, deflections, and fatigue assessment.
    """
    logger.info("cantilever.analyze", project_id=req.get("project_id"))
    assumptions: list[str] = []
    
    try:
        # Parse configuration
        config_data = req.get("config", {})
        config = CantileverConfig(
            type=CantileverType(config_data.get("type", "single")),
            arm_length_ft=float(config_data.get("arm_length_ft", 10.0)),
            arm_angle_deg=float(config_data.get("arm_angle_deg", 0.0)),
            arm_section=config_data.get("arm_section", "HSS8x8x1/2"),
            connection_type=ConnectionType(config_data.get("connection_type", "bolted_flange")),
            num_arms=int(config_data.get("num_arms", 1)),
            arm_spacing_ft=float(config_data.get("arm_spacing_ft", 0.0)),
        )
        
        # Parse loads
        loads_data = req.get("loads", {})
        loads = CantileverLoads(
            sign_weight_lb=float(loads_data.get("sign_weight_lb", 500.0)),
            sign_area_ft2=float(loads_data.get("sign_area_ft2", 48.0)),
            wind_pressure_psf=float(loads_data.get("wind_pressure_psf", 35.0)),
            ice_thickness_in=float(loads_data.get("ice_thickness_in", 0.0)),
            eccentricity_ft=float(loads_data.get("eccentricity_ft", 0.0)),
        )
        
        pole_height_ft = float(req.get("pole_height_ft", 20.0))
        include_fatigue = req.get("include_fatigue", True)
        design_life_years = int(req.get("design_life_years", 50))
        
        # Perform analysis
        result = analyze_cantilever_sign(
            config=config,
            loads=loads,
            pole_height_ft=pole_height_ft,
            include_fatigue=include_fatigue,
            design_life_years=design_life_years,
        )
        
        # Add analysis assumptions
        assumptions.extend(result.assumptions)
        
        # Calculate content hash for caching
        content_str = json.dumps({
            "config": config_data,
            "loads": loads_data,
            "pole_height_ft": pole_height_ft,
        }, sort_keys=True)
        content_sha256 = hashlib.sha256(content_str.encode()).hexdigest()
        
        # Save to project if requested
        project_id = req.get("project_id")
        if project_id:
            await _save_cantilever_to_project(
                db,
                project_id,
                config,
                result,
                content_sha256,
            )
            add_assumption(assumptions, f"Cantilever analysis saved to project {project_id}")
        
        # Build response
        response_data = {
            "analysis": result.dict(),
            "foundation_loads": calculate_cantilever_foundation_loads(result),
            "content_sha256": content_sha256,
        }
        
        # Add warnings if any
        if result.warnings:
            response_data["warnings"] = result.warnings
        
        confidence = calc_confidence(assumptions)
        
        return make_envelope(
            result=response_data,
            assumptions=assumptions,
            confidence=confidence,
            code_version=get_code_version(),
            model_config=get_model_config(),
        )
        
    except ValueError as e:
        logger.error("cantilever.analyze.validation_error", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("cantilever.analyze.error", error=str(e))
        raise HTTPException(status_code=500, detail="Analysis failed")


@router.post("/optimize", response_model=ResponseEnvelope)
async def optimize_cantilever(req: dict) -> ResponseEnvelope:
    """
    Optimize cantilever design for given loads and constraints.
    
    Request body:
    ```json
    {
        "loads": {
            "sign_weight_lb": 500.0,
            "sign_area_ft2": 48.0,
            "wind_pressure_psf": 35.0,
            "ice_thickness_in": 0.0,
            "eccentricity_ft": 0.0
        },
        "pole_height_ft": 20.0,
        "max_arm_length_ft": 25.0,  // Optional, default 25ft
        "min_arm_length_ft": 5.0,   // Optional, default 5ft
        "target_stress_ratio": 0.9   // Optional, default 0.9
    }
    ```
    
    Returns optimized cantilever configuration with minimum weight.
    """
    logger.info("cantilever.optimize")
    assumptions: list[str] = []
    
    try:
        # Parse loads
        loads_data = req.get("loads", {})
        loads = CantileverLoads(
            sign_weight_lb=float(loads_data.get("sign_weight_lb", 500.0)),
            sign_area_ft2=float(loads_data.get("sign_area_ft2", 48.0)),
            wind_pressure_psf=float(loads_data.get("wind_pressure_psf", 35.0)),
            ice_thickness_in=float(loads_data.get("ice_thickness_in", 0.0)),
            eccentricity_ft=float(loads_data.get("eccentricity_ft", 0.0)),
        )
        
        pole_height_ft = float(req.get("pole_height_ft", 20.0))
        max_arm_length_ft = float(req.get("max_arm_length_ft", 25.0))
        min_arm_length_ft = float(req.get("min_arm_length_ft", 5.0))
        target_stress_ratio = float(req.get("target_stress_ratio", 0.9))
        
        # Optimize design
        optimal_config, analysis_result = optimize_cantilever_design(
            loads=loads,
            pole_height_ft=pole_height_ft,
            max_arm_length_ft=max_arm_length_ft,
            min_arm_length_ft=min_arm_length_ft,
            target_stress_ratio=target_stress_ratio,
        )
        
        add_assumption(assumptions, f"Optimized for target stress ratio {target_stress_ratio}")
        add_assumption(assumptions, f"Arm length range: {min_arm_length_ft}-{max_arm_length_ft}ft")
        assumptions.extend(analysis_result.assumptions)
        
        response_data = {
            "optimal_config": {
                "type": optimal_config.type.value,
                "arm_length_ft": optimal_config.arm_length_ft,
                "arm_section": optimal_config.arm_section,
                "connection_type": optimal_config.connection_type.value,
            },
            "analysis": analysis_result.dict(),
            "foundation_loads": calculate_cantilever_foundation_loads(analysis_result),
        }
        
        confidence = calc_confidence(assumptions)
        
        return make_envelope(
            result=response_data,
            assumptions=assumptions,
            confidence=confidence,
            code_version=get_code_version(),
            model_config=get_model_config(),
        )
        
    except ValueError as e:
        logger.error("cantilever.optimize.error", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("cantilever.optimize.error", error=str(e))
        raise HTTPException(status_code=500, detail="Optimization failed")


@router.get("/sections", response_model=ResponseEnvelope)
async def get_cantilever_sections(
    max_span_ft: Optional[float] = None,
    shape_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """
    Get available cantilever sections from catalog.
    
    Query parameters:
    - max_span_ft: Filter sections by maximum recommended span
    - shape_type: Filter by shape (HSS, PIPE, W-SHAPE)
    
    Returns list of suitable cantilever sections with properties.
    """
    logger.info("cantilever.sections", max_span=max_span_ft, shape=shape_type)
    assumptions: list[str] = []
    
    try:
        # Build query
        query = "SELECT * FROM cantilever_sections WHERE 1=1"
        params = {}
        
        if max_span_ft is not None:
            query += " AND max_span_ft >= :max_span"
            params["max_span"] = max_span_ft
            add_assumption(assumptions, f"Filtered for spans up to {max_span_ft}ft")
        
        if shape_type:
            query += " AND shape_type = :shape"
            params["shape"] = shape_type.upper()
            add_assumption(assumptions, f"Filtered for {shape_type} shapes")
        
        query += " ORDER BY weight_plf ASC"
        
        # Execute query
        result = await db.execute(query, params)
        sections = result.fetchall()
        
        # Format results
        sections_data = []
        for row in sections:
            sections_data.append({
                "designation": row.designation,
                "shape_type": row.shape_type,
                "weight_plf": row.weight_plf,
                "area_in2": row.area_in2,
                "ix_in4": row.ix_in4,
                "sx_in3": row.sx_in3,
                "max_span_ft": row.max_span_ft,
            })
        
        add_assumption(assumptions, f"Found {len(sections_data)} suitable sections")
        
        confidence = calc_confidence(assumptions)
        
        return make_envelope(
            result={"sections": sections_data, "count": len(sections_data)},
            assumptions=assumptions,
            confidence=confidence,
            code_version=get_code_version(),
            model_config=get_model_config(),
        )
        
    except Exception as e:
        logger.exception("cantilever.sections.error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve sections")


@router.post("/check", response_model=ResponseEnvelope)
async def check_cantilever_feasibility(req: dict) -> ResponseEnvelope:
    """
    Quick feasibility check for cantilever sign.
    
    Request body:
    ```json
    {
        "sign_area_ft2": 48.0,
        "sign_weight_lb": 500.0,
        "desired_offset_ft": 15.0,
        "pole_height_ft": 20.0,
        "wind_speed_mph": 90.0
    }
    ```
    
    Returns feasibility assessment with recommendations.
    """
    logger.info("cantilever.check")
    assumptions: list[str] = []
    
    sign_area_ft2 = float(req.get("sign_area_ft2", 48.0))
    sign_weight_lb = float(req.get("sign_weight_lb", 500.0))
    desired_offset_ft = float(req.get("desired_offset_ft", 15.0))
    pole_height_ft = float(req.get("pole_height_ft", 20.0))
    wind_speed_mph = float(req.get("wind_speed_mph", 90.0))
    
    # Calculate wind pressure (simplified ASCE 7)
    wind_pressure_psf = 0.00256 * 1.0 * wind_speed_mph ** 2  # Exposure C
    
    # Estimate moment at base
    wind_force_lb = sign_area_ft2 * wind_pressure_psf
    moment_wind_ftlb = wind_force_lb * pole_height_ft
    moment_dead_ftlb = sign_weight_lb * desired_offset_ft
    total_moment_ftlb = math.sqrt(moment_wind_ftlb**2 + moment_dead_ftlb**2)
    
    # Feasibility checks
    feasible = True
    recommendations = []
    warnings = []
    
    if desired_offset_ft > 25:
        feasible = False
        warnings.append(f"Offset {desired_offset_ft}ft exceeds practical limit of 25ft")
        recommendations.append("Consider double-pole configuration or reduce offset")
    
    if total_moment_ftlb > 500000:  # 500 kip-ft
        warnings.append(f"High moment {total_moment_ftlb/1000:.0f} kip-ft requires special design")
        recommendations.append("Consider using truss-type cantilever or multiple poles")
    
    if sign_area_ft2 / (desired_offset_ft * 4) > 5:  # Aspect ratio check
        warnings.append("High sign area to cantilever ratio")
        recommendations.append("Consider increasing cantilever arm section size")
    
    # Recommend minimum section
    if total_moment_ftlb < 100000:
        recommended_section = "HSS8x8x3/8"
    elif total_moment_ftlb < 200000:
        recommended_section = "HSS10x10x1/2"
    else:
        recommended_section = "HSS12x12x1/2 or larger"
    
    add_assumption(assumptions, f"Wind pressure calculated as {wind_pressure_psf:.1f} psf")
    add_assumption(assumptions, "Feasibility based on typical cantilever limits")
    
    response_data = {
        "feasible": feasible,
        "estimated_moment_kipft": total_moment_ftlb / 1000.0,
        "wind_force_lb": wind_force_lb,
        "recommended_section": recommended_section,
        "recommendations": recommendations,
        "warnings": warnings,
    }
    
    confidence = 0.8 if feasible else 0.5
    
    return make_envelope(
        result=response_data,
        assumptions=assumptions,
        confidence=confidence,
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


async def _save_cantilever_to_project(
    db: AsyncSession,
    project_id: str,
    config: CantileverConfig,
    result,
    content_sha256: str,
) -> None:
    """Save cantilever configuration and analysis to project."""
    try:
        # Check if project exists
        project_result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Update project to indicate cantilever
        project.has_cantilever = True
        await db.commit()
        
        logger.info("cantilever.saved_to_project", project_id=project_id)
        
    except Exception as e:
        await db.rollback()
        logger.error("cantilever.save_error", error=str(e))
        raise