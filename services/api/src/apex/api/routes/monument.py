"""Monument sign pole API endpoints.

Provides monument sign engineering analysis using ASCE 7-22 wind loads
and the AISC shapes database for optimal section selection.
"""

from __future__ import annotations

import asyncpg
import structlog
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional

from ...domains.signage.monument_solver import (
    MonumentSolver, MonumentConfig, SectionProperties,
    ExposureCategory, ImportanceFactor, optimize_monument_pole
)
from ..common.models import make_envelope
from ..common.envelope import calc_confidence
from ..schemas import ResponseEnvelope, add_assumption

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/signage/monument", tags=["monument"])

# Database connection
DATABASE_URL = "postgresql://apex:apex@localhost:5432/apex"


async def get_db_connection():
    """Get database connection."""
    return await asyncpg.connect(DATABASE_URL)


async def get_section_properties(conn: asyncpg.Connection, designation: str) -> Optional[SectionProperties]:
    """Get AISC section properties from database."""
    
    result = await conn.fetchrow("""
        SELECT 
            aisc_manual_label as designation,
            type,
            w as weight_plf,
            area as area_in2,
            ix as ix_in4,
            sx as sx_in3,
            rx as rx_in,
            COALESCE(fy_ksi, 50) as fy_ksi,
            is_astm_a1085
        FROM aisc_shapes_v16
        WHERE UPPER(aisc_manual_label) = UPPER($1)
    """, designation)
    
    if not result:
        return None
    
    return SectionProperties(
        designation=result['designation'],
        type=result['type'],
        weight_plf=result['weight_plf'],
        area_in2=result['area_in2'],
        ix_in4=result['ix_in4'],
        sx_in3=result['sx_in3'],
        rx_in=result['rx_in'],
        fy_ksi=result['fy_ksi'],
        is_a1085=result['is_astm_a1085']
    )


@router.post("/analyze", response_model=ResponseEnvelope)
async def analyze_monument(req: dict) -> ResponseEnvelope:
    """Analyze monument sign with specified pole section.
    
    Body: {
        project_id: str,
        pole_height_ft: float,
        pole_section: str,  // AISC designation
        sign_width_ft: float,
        sign_height_ft: float,
        basic_wind_speed_mph: float,
        exposure_category: str,  // B, C, D
        soil_bearing_capacity_psf: float,
        // ... optional parameters
    }
    """
    logger.info("monument.analyze", 
                pole_section=req.get("pole_section"),
                wind_speed=req.get("basic_wind_speed_mph"))
    
    assumptions: list[str] = []
    
    try:
        # Parse required parameters
        project_id = req.get("project_id", f"monument_{uuid.uuid4().hex[:8]}")
        config_id = f"monument_config_{uuid.uuid4().hex[:8]}"
        
        pole_height_ft = float(req["pole_height_ft"])
        pole_section = req["pole_section"]
        sign_width_ft = float(req["sign_width_ft"])
        sign_height_ft = float(req["sign_height_ft"])
        basic_wind_speed_mph = float(req["basic_wind_speed_mph"])
        
        # Parse optional parameters
        exposure_cat = ExposureCategory(req.get("exposure_category", "C"))
        importance = ImportanceFactor(req.get("importance_factor", "II"))
        soil_bearing = float(req.get("soil_bearing_capacity_psf", 2000))
        
        # Calculate sign area
        sign_area_sqft = sign_width_ft * sign_height_ft
        
        # Create configuration
        config = MonumentConfig(
            project_id=project_id,
            config_id=config_id,
            pole_height_ft=pole_height_ft,
            pole_section=pole_section,
            sign_width_ft=sign_width_ft,
            sign_height_ft=sign_height_ft,
            sign_area_sqft=sign_area_sqft,
            basic_wind_speed_mph=basic_wind_speed_mph,
            exposure_category=exposure_cat,
            importance_factor=importance,
            soil_bearing_capacity_psf=soil_bearing,
            clearance_to_grade_ft=float(req.get("clearance_to_grade_ft", 8.0)),
            sign_thickness_in=float(req.get("sign_thickness_in", 0.125)),
        )
        
        # Get section properties from database
        conn = await get_db_connection()
        
        try:
            section_props = await get_section_properties(conn, pole_section)
            
            if not section_props:
                raise HTTPException(
                    status_code=404,
                    detail=f"Pole section '{pole_section}' not found in AISC database"
                )
            
            # Perform analysis
            solver = MonumentSolver()
            results = solver.analyze_monument_sign(config, section_props)
            
            # Format response
            analysis_result = {
                "configuration": {
                    "pole_height_ft": config.pole_height_ft,
                    "pole_section": config.pole_section,
                    "sign_dimensions_ft": f"{config.sign_width_ft} x {config.sign_height_ft}",
                    "sign_area_sqft": config.sign_area_sqft,
                    "wind_speed_mph": config.basic_wind_speed_mph,
                    "exposure_category": config.exposure_category.value,
                    "soil_bearing_psf": config.soil_bearing_capacity_psf
                },
                "section_properties": {
                    "designation": section_props.designation,
                    "type": section_props.type,
                    "weight_plf": section_props.weight_plf,
                    "sx_in3": section_props.sx_in3,
                    "ix_in4": section_props.ix_in4,
                    "is_a1085": section_props.is_a1085
                },
                "wind_analysis": {
                    "design_pressure_psf": round(results.design_wind_pressure_psf, 1),
                    "total_force_lbs": round(results.total_wind_force_lbs, 0),
                    "moment_at_base_kipft": round(results.wind_moment_at_base_kipft, 1),
                    "velocity_pressure_psf": round(results.velocity_pressure_qz_psf, 1)
                },
                "structural_analysis": {
                    "max_bending_stress_ksi": round(results.max_bending_stress_ksi, 1),
                    "stress_ratio": round(results.combined_stress_ratio, 3),
                    "deflection_in": round(results.max_deflection_in, 2),
                    "deflection_ratio": f"L/{results.deflection_ratio:.0f}",
                    "pole_adequate": results.pole_adequate
                },
                "foundation_analysis": {
                    "overturning_moment_kipft": round(results.overturning_moment_kipft, 1),
                    "safety_factor": round(results.overturning_safety_factor, 2),
                    "max_soil_pressure_psf": round(results.max_soil_pressure_psf, 0),
                    "foundation_size_ft": f"{results.foundation_width_ft:.1f} x {results.foundation_length_ft:.1f}",
                    "foundation_adequate": results.foundation_adequate
                },
                "overall_status": {
                    "passes_code": results.overall_passes,
                    "status": "PASS" if results.overall_passes else "FAIL",
                    "warnings": results.warnings
                }
            }
            
            # Add assumptions
            for assumption in results.assumptions:
                add_assumption(assumptions, assumption)
            
            confidence = calc_confidence(assumptions) * 0.95  # High confidence with real analysis
            
            return make_envelope(
                result=analysis_result,
                assumptions=assumptions,
                confidence=confidence,
                inputs=req,
                outputs={
                    "overall_passes": results.overall_passes,
                    "stress_ratio": results.combined_stress_ratio,
                    "safety_factor": results.overturning_safety_factor
                }
            )
            
        finally:
            await conn.close()
            
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("monument.analyze.error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/optimize", response_model=ResponseEnvelope)
async def optimize_monument(req: dict) -> ResponseEnvelope:
    """Find optimal monument pole section for given requirements.
    
    Body: {
        pole_height_ft: float,
        sign_width_ft: float,
        sign_height_ft: float,
        basic_wind_speed_mph: float,
        exposure_category: str,
        max_diameter_in: int,  // Optional, default 14
        prefer_a1085: bool,    // Optional, default false
        max_options: int       // Optional, default 10
    }
    """
    logger.info("monument.optimize", 
                height=req.get("pole_height_ft"),
                wind_speed=req.get("basic_wind_speed_mph"))
    
    assumptions: list[str] = []
    
    try:
        # Parse parameters
        pole_height_ft = float(req["pole_height_ft"])
        sign_width_ft = float(req["sign_width_ft"])
        sign_height_ft = float(req["sign_height_ft"])
        basic_wind_speed_mph = float(req["basic_wind_speed_mph"])
        exposure_cat = ExposureCategory(req.get("exposure_category", "C"))
        
        max_diameter_in = int(req.get("max_diameter_in", 14))
        prefer_a1085 = req.get("prefer_a1085", False)
        max_options = int(req.get("max_options", 10))
        
        # Connect to database
        conn = await get_db_connection()
        
        try:
            # Use database function for initial filtering
            results = await conn.fetch("""
                SELECT * FROM select_monument_pole(
                    p_wind_moment_kipft := $1,
                    p_height_ft := $2,
                    p_max_diameter_in := $3,
                    p_prefer_a1085 := $4
                )
                WHERE status = 'OK'
                LIMIT $5
            """, 100.0,  # Placeholder moment - will be refined
                         pole_height_ft, max_diameter_in, prefer_a1085, max_options)
            
            if not results:
                add_assumption(assumptions, f"No suitable sections found for {pole_height_ft} ft height")
                return make_envelope(
                    result={"options": [], "recommended": None},
                    assumptions=assumptions,
                    confidence=0.3,
                    inputs=req,
                    outputs={"feasible_count": 0}
                )
            
            # Get detailed section properties for top candidates
            options = []
            for i, row in enumerate(results):
                section_props = await get_section_properties(conn, row['designation'])
                if not section_props:
                    continue
                
                # Quick wind moment estimate for ranking
                sign_area = sign_width_ft * sign_height_ft
                wind_pressure_est = 0.00256 * 1.0 * basic_wind_speed_mph**2 * 0.85 * 1.2  # Simplified
                wind_force_est = wind_pressure_est * sign_area
                wind_moment_est = wind_force_est * (8 + sign_height_ft/2) / 1000  # kip-ft
                
                stress_ratio_est = wind_moment_est * 12 / (section_props.sx_in3 * 50 * 0.9)
                
                option = {
                    "rank": i + 1,
                    "designation": section_props.designation,
                    "type": section_props.type,
                    "diameter_in": row['diameter_in'],
                    "weight_plf": section_props.weight_plf,
                    "moment_capacity_kipft": round(section_props.sx_in3 * 50 * 0.9 / 12, 1),
                    "stress_ratio_est": round(stress_ratio_est, 3),
                    "cost_per_ft": round(section_props.weight_plf * 0.90, 2),
                    "is_a1085": section_props.is_a1085,
                    "efficiency": round(section_props.sx_in3 / section_props.weight_plf, 2)
                }
                options.append(option)
            
            # Recommend the first option (best combination of strength and weight)
            recommended = options[0] if options else None
            
            add_assumption(assumptions, f"Searched {len(results)} feasible sections")
            add_assumption(assumptions, f"Wind speed: {basic_wind_speed_mph} mph, Exposure {exposure_cat.value}")
            add_assumption(assumptions, f"Sign area: {sign_width_ft} x {sign_height_ft} = {sign_area:.0f} sq ft")
            
            if prefer_a1085:
                add_assumption(assumptions, "Preferred ASTM A1085 HSS sections")
            
            confidence = calc_confidence(assumptions) * 0.9
            
            return make_envelope(
                result={
                    "options": options,
                    "recommended": recommended,
                    "search_criteria": {
                        "max_diameter_in": max_diameter_in,
                        "prefer_a1085": prefer_a1085,
                        "estimated_wind_moment_kipft": round(wind_moment_est, 1) if 'wind_moment_est' in locals() else None
                    }
                },
                assumptions=assumptions,
                confidence=confidence,
                inputs=req,
                outputs={
                    "feasible_count": len(options),
                    "recommended_designation": recommended['designation'] if recommended else None
                }
            )
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error("monument.optimize.error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.get("/sections", response_model=ResponseEnvelope)
async def get_monument_sections(
    max_diameter: int = 14,
    min_diameter: int = 6,
    prefer_a1085: bool = False
) -> ResponseEnvelope:
    """Get available monument pole sections from AISC database.
    
    Query params:
    - max_diameter: Maximum diameter in inches (default 14)
    - min_diameter: Minimum diameter in inches (default 6)  
    - prefer_a1085: Show only A1085 sections (default false)
    """
    assumptions: list[str] = []
    
    try:
        conn = await get_db_connection()
        
        try:
            # Query monument-suitable sections
            query = """
            SELECT 
                designation,
                type,
                diameter_in,
                weight_plf,
                moment_capacity_kipft,
                max_height_ft,
                efficiency_ratio,
                material_cost_per_ft,
                typical_application,
                (SELECT COUNT(*) FROM aisc_shapes_v16 s2 WHERE s2.is_astm_a1085 AND s2.aisc_manual_label = s.designation) > 0 as is_a1085
            FROM optimal_monument_poles s
            WHERE diameter_in BETWEEN $1 AND $2
                AND ($3 = false OR (SELECT is_astm_a1085 FROM aisc_shapes_v16 s2 WHERE s2.aisc_manual_label = s.designation))
            ORDER BY diameter_in, weight_plf
            """
            
            results = await conn.fetch(query, min_diameter, max_diameter, prefer_a1085)
            
            if not results:
                add_assumption(assumptions, f"No sections found for {min_diameter}-{max_diameter}\" diameter range")
                return make_envelope(
                    result={"sections": []},
                    assumptions=assumptions,
                    confidence=0.9,
                    inputs={"max_diameter": max_diameter, "min_diameter": min_diameter},
                    outputs={"count": 0}
                )
            
            # Format sections
            sections = []
            for row in results:
                section = {
                    "designation": row['designation'],
                    "type": row['type'],
                    "diameter_in": row['diameter_in'],
                    "weight_plf": row['weight_plf'],
                    "moment_capacity_kipft": row['moment_capacity_kipft'],
                    "max_height_ft": row['max_height_ft'],
                    "efficiency": row['efficiency_ratio'],
                    "cost_per_ft": row['material_cost_per_ft'],
                    "application": row['typical_application'],
                    "is_a1085": row['is_a1085']
                }
                sections.append(section)
            
            add_assumption(assumptions, f"Diameter range: {min_diameter}-{max_diameter} inches")
            add_assumption(assumptions, f"Found {len(sections)} suitable sections")
            
            if prefer_a1085:
                add_assumption(assumptions, "Filtered for ASTM A1085 sections only")
            
            confidence = calc_confidence(assumptions) * 0.95
            
            return make_envelope(
                result={"sections": sections},
                assumptions=assumptions,
                confidence=confidence,
                inputs={"max_diameter": max_diameter, "min_diameter": min_diameter, "prefer_a1085": prefer_a1085},
                outputs={"count": len(sections)}
            )
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error("monument.sections.error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.post("/foundation", response_model=ResponseEnvelope)
async def design_foundation(req: dict) -> ResponseEnvelope:
    """Design foundation for monument sign.
    
    Body: {
        overturning_moment_kipft: float,
        dead_load_lbs: float,
        soil_bearing_capacity_psf: float,
        safety_factor_required: float  // Optional, default 1.5
    }
    """
    assumptions: list[str] = []
    
    try:
        overturning_moment = float(req["overturning_moment_kipft"])
        dead_load = float(req["dead_load_lbs"])
        soil_bearing = float(req["soil_bearing_capacity_psf"])
        required_sf = float(req.get("safety_factor_required", 1.5))
        
        # Foundation design (simplified)
        # Try different foundation sizes until requirements are met
        
        concrete_weight_pcf = 150
        best_foundation = None
        
        for width_ft in [3, 4, 5, 6, 7, 8, 9, 10]:
            for depth_ft in [3, 4, 5, 6]:
                # Foundation weight
                volume_ft3 = width_ft * width_ft * depth_ft
                foundation_weight = volume_ft3 * concrete_weight_pcf
                total_dead_load = dead_load + foundation_weight
                
                # Resisting moment
                resisting_moment = total_dead_load * width_ft / 2 / 1000  # kip-ft
                
                # Safety factor
                safety_factor = resisting_moment / overturning_moment if overturning_moment > 0 else float('inf')
                
                # Soil pressure
                net_moment = max(0, overturning_moment - resisting_moment)
                avg_pressure = total_dead_load / (width_ft * width_ft)
                moment_pressure = net_moment * 1000 * 6 / (width_ft**3)
                max_soil_pressure = avg_pressure + moment_pressure
                
                # Check if this foundation works
                if safety_factor >= required_sf and max_soil_pressure <= soil_bearing:
                    foundation = {
                        "width_ft": width_ft,
                        "length_ft": width_ft,
                        "depth_ft": depth_ft,
                        "volume_cy": volume_ft3 / 27,
                        "concrete_weight_lbs": foundation_weight,
                        "safety_factor": round(safety_factor, 2),
                        "max_soil_pressure_psf": round(max_soil_pressure, 0),
                        "passes": True
                    }
                    
                    if best_foundation is None or volume_ft3 < best_foundation["volume_cy"] * 27:
                        best_foundation = foundation
        
        if best_foundation is None:
            # Return largest attempted foundation with failure note
            width_ft = 10
            depth_ft = 6
            volume_ft3 = width_ft * width_ft * depth_ft
            foundation_weight = volume_ft3 * concrete_weight_pcf
            total_dead_load = dead_load + foundation_weight
            resisting_moment = total_dead_load * width_ft / 2 / 1000
            safety_factor = resisting_moment / overturning_moment if overturning_moment > 0 else float('inf')
            
            best_foundation = {
                "width_ft": width_ft,
                "length_ft": width_ft,
                "depth_ft": depth_ft,
                "volume_cy": volume_ft3 / 27,
                "concrete_weight_lbs": foundation_weight,
                "safety_factor": round(safety_factor, 2),
                "max_soil_pressure_psf": round(avg_pressure + moment_pressure, 0),
                "passes": False,
                "note": "Foundation exceeds practical limits - consider piles or soil improvement"
            }
        
        add_assumption(assumptions, f"Overturning moment: {overturning_moment:.1f} kip-ft")
        add_assumption(assumptions, f"Required safety factor: {required_sf}")
        add_assumption(assumptions, f"Soil bearing capacity: {soil_bearing:.0f} psf")
        add_assumption(assumptions, "Concrete unit weight: 150 pcf")
        
        confidence = calc_confidence(assumptions) * 0.85  # Foundation design is simplified
        
        return make_envelope(
            result=best_foundation,
            assumptions=assumptions,
            confidence=confidence,
            inputs=req,
            outputs={
                "foundation_passes": best_foundation["passes"],
                "safety_factor": best_foundation["safety_factor"]
            }
        )
        
    except Exception as e:
        logger.error("monument.foundation.error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Foundation design failed: {str(e)}")