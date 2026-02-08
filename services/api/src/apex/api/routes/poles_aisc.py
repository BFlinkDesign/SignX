"""Enhanced pole/support selection with real AISC data"""

from __future__ import annotations

import asyncpg
import structlog
from fastapi import APIRouter, HTTPException

from ..common.envelope import calc_confidence
from ..common.models import make_envelope
from ..schemas import ResponseEnvelope, add_assumption

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/signage/poles", tags=["poles-aisc"])

# Database connection
DATABASE_URL = "postgresql://apex:apex@localhost:5432/apex"


async def get_aisc_connection():
    """Get database connection for AISC data"""
    return await asyncpg.connect(DATABASE_URL)


@router.post("/cantilever-options", response_model=ResponseEnvelope)
async def get_cantilever_options(req: dict) -> ResponseEnvelope:
    """Get optimal cantilever pole options from AISC database.
    
    Body: {
        moment_kipft: float,  # Required moment capacity
        arm_length_ft: float,  # Cantilever arm length
        prefer_a1085: bool,    # Prefer ASTM A1085 HSS
        max_weight_plf: float, # Maximum weight constraint
        num_options: int       # Number of options to return
    }
    """
    logger.info("cantilever.options", moment=req.get("moment_kipft"))
    assumptions: list[str] = []
    
    moment_kipft = float(req.get("moment_kipft", 100))
    arm_length_ft = float(req.get("arm_length_ft", 20))
    prefer_a1085 = req.get("prefer_a1085", False)
    max_weight = req.get("max_weight_plf", 200)
    num_options = int(req.get("num_options", 10))
    
    # Connect to database
    conn = await get_aisc_connection()
    
    try:
        # Calculate required section modulus
        fy_ksi = 50  # A500 Gr. C or A1085
        phi = 0.9    # Resistance factor for flexure
        required_sx = moment_kipft * 12 / (fy_ksi * phi)
        
        add_assumption(assumptions, f"Using Fy={fy_ksi} ksi, φ={phi}")
        add_assumption(assumptions, f"Required Sx >= {required_sx:.1f} in³")
        
        # Query optimal sections
        query = """
        SELECT 
            aisc_manual_label as designation,
            type,
            w as weight_plf,
            sx as sx_in3,
            ix as ix_in4,
            rx as rx_in,
            j as j_in4,
            is_astm_a1085,
            -- Calculate stress ratio
            $1 * 12 / (sx * $2 * $3) as stress_ratio,
            -- Estimate deflection (simplified)
            CASE 
                WHEN ix > 0 THEN $4 * 12 * POW($4 * 12, 2) / (3 * 29000 * ix)
                ELSE 999
            END as deflection_estimate_in
        FROM aisc_shapes_v16
        WHERE type IN ('HSS', 'PIPE')
            AND sx >= $5
            AND w <= $6
            AND ($7 = false OR is_astm_a1085 = true)
        ORDER BY 
            CASE WHEN $7 AND is_astm_a1085 THEN 0 ELSE 1 END,
            w
        LIMIT $8
        """
        
        results = await conn.fetch(
            query, 
            moment_kipft,  # $1
            fy_ksi,        # $2
            phi,           # $3
            arm_length_ft, # $4
            required_sx,   # $5
            max_weight,    # $6
            prefer_a1085,  # $7
            num_options    # $8
        )
        
        if not results:
            add_assumption(assumptions, f"No sections found with Sx >= {required_sx:.1f} in³")
            confidence = calc_confidence(assumptions)
            return make_envelope(
                result={"options": [], "recommended": None},
                assumptions=assumptions,
                confidence=confidence,
                inputs=req,
                outputs={"feasible_count": 0}
            )
        
        # Format options
        options = []
        for row in results:
            # Calculate torsional capacity for cantilever
            j_in4 = row['j_in4'] or 0
            torsional_capacity = j_in4 * 0.6 * fy_ksi / (arm_length_ft * 12) if j_in4 > 0 else 0
            
            option = {
                "designation": row['designation'],
                "type": row['type'],
                "weight_plf": round(row['weight_plf'], 2),
                "sx_in3": round(row['sx_in3'], 2),
                "ix_in4": round(row['ix_in4'], 2),
                "stress_ratio": round(row['stress_ratio'], 3),
                "deflection_est_in": round(row['deflection_estimate_in'], 2),
                "torsional_capacity_kipft": round(torsional_capacity, 1),
                "is_a1085": row['is_astm_a1085'],
                "cost_factor": 1.1 if row['is_astm_a1085'] else 1.0
            }
            options.append(option)
        
        # Determine recommended (first option is lightest)
        recommended = options[0] if options else None
        
        if recommended:
            add_assumption(assumptions, f"Recommended: {recommended['designation']} at {recommended['weight_plf']} lb/ft")
        
        add_assumption(assumptions, f"Found {len(options)} feasible sections from AISC database")
        confidence = calc_confidence(assumptions) * 0.95  # High confidence with real data
        
        return make_envelope(
            result={
                "options": options,
                "recommended": recommended,
                "feasible_count": len(options),
                "design_criteria": {
                    "required_sx_in3": round(required_sx, 2),
                    "moment_capacity_kipft": moment_kipft,
                    "arm_length_ft": arm_length_ft,
                    "fy_ksi": fy_ksi,
                    "phi": phi
                }
            },
            assumptions=assumptions,
            confidence=confidence,
            inputs=req,
            outputs={
                "feasible_count": len(options),
                "min_weight": options[0]['weight_plf'] if options else None
            }
        )
    
    finally:
        await conn.close()


@router.post("/single-pole-options", response_model=ResponseEnvelope)
async def get_single_pole_options(req: dict) -> ResponseEnvelope:
    """Get optimal single pole options from AISC database.
    
    Body: {
        height_ft: float,      # Pole height
        moment_kipft: float,   # Base moment
        lateral_kip: float,    # Lateral force
        shape_types: List[str],# Allowed types: HSS, PIPE, W
        num_options: int       # Number of options
    }
    """
    logger.info("single-pole.options", height=req.get("height_ft"))
    assumptions: list[str] = []
    
    height_ft = float(req.get("height_ft", 30))
    moment_kipft = float(req.get("moment_kipft", 50))
    lateral_kip = float(req.get("lateral_kip", 2))
    shape_types = req.get("shape_types", ["HSS", "PIPE"])
    num_options = int(req.get("num_options", 10))
    
    # Connect to database
    conn = await get_aisc_connection()
    
    try:
        # Calculate requirements
        fy_ksi = 50
        phi_b = 0.9  # Flexure
        phi_c = 0.9  # Compression
        
        # Slenderness check: L/r <= 200
        min_r = height_ft * 12 / 200
        
        # Required section modulus for moment
        required_sx = moment_kipft * 12 / (fy_ksi * phi_b)
        
        add_assumption(assumptions, f"Height={height_ft} ft, Min r={min_r:.2f} in")
        add_assumption(assumptions, f"Required Sx >= {required_sx:.1f} in³")
        
        # Build shape type filter
        shape_filter = "'" + "','".join(shape_types) + "'"
        
        # Query optimal sections with buckling check
        query = f"""
        WITH pole_analysis AS (
            SELECT 
                aisc_manual_label as designation,
                type,
                w as weight_plf,
                area as area_in2,
                sx as sx_in3,
                rx as rx_in,
                ry as ry_in,
                -- Slenderness ratios
                {height_ft * 12} / rx as lambda_x,
                {height_ft * 12} / GREATEST(ry, 0.1) as lambda_y,
                -- Euler buckling load (conservative)
                CASE 
                    WHEN rx > 0 THEN 
                        3.14159 * 3.14159 * 29000 * area / 
                        POWER({height_ft * 12} / rx, 2)
                    ELSE 0
                END as pe_kips,
                -- Combined stress check (simplified)
                {moment_kipft} * 12 / (sx * {fy_ksi} * {phi_b}) as flexure_ratio
            FROM aisc_shapes_v16
            WHERE type IN ({shape_filter})
                AND sx >= {required_sx}
                AND rx >= {min_r * 0.8}  -- Some margin on r
        )
        SELECT 
            designation,
            type,
            weight_plf,
            area_in2,
            sx_in3,
            rx_in,
            ry_in,
            lambda_x,
            lambda_y,
            pe_kips,
            flexure_ratio,
            CASE 
                WHEN lambda_x > 200 OR lambda_y > 200 THEN 'Slender - Check Required'
                WHEN pe_kips < 10 THEN 'Low Buckling Capacity'
                ELSE 'OK'
            END as stability_note
        FROM pole_analysis
        WHERE flexure_ratio < 1.0
        ORDER BY weight_plf
        LIMIT {num_options}
        """
        
        results = await conn.fetchall(query)
        
        if not results:
            add_assumption(assumptions, "No feasible single poles found")
            confidence = calc_confidence(assumptions)
            return make_envelope(
                result={"options": [], "recommended": None},
                assumptions=assumptions,
                confidence=confidence,
                inputs=req,
                outputs={"feasible_count": 0}
            )
        
        # Format options
        options = []
        for row in results:
            option = {
                "designation": row['designation'],
                "type": row['type'],
                "weight_plf": round(row['weight_plf'], 2),
                "area_in2": round(row['area_in2'], 2),
                "sx_in3": round(row['sx_in3'], 2),
                "rx_in": round(row['rx_in'], 2),
                "ry_in": round(row['ry_in'], 2),
                "slenderness_x": round(row['lambda_x'], 1),
                "slenderness_y": round(row['lambda_y'], 1),
                "euler_load_kips": round(row['pe_kips'], 1),
                "flexure_ratio": round(row['flexure_ratio'], 3),
                "stability": row['stability_note'],
                "cost_per_ft": round(row['weight_plf'] * 0.90, 2)  # Estimate $0.90/lb
            }
            options.append(option)
        
        # Recommend first stable option
        recommended = None
        for opt in options:
            if opt['stability'] == 'OK':
                recommended = opt
                break
        
        if not recommended and options:
            recommended = options[0]
            add_assumption(assumptions, "WARNING: All options require stability verification")
        
        add_assumption(assumptions, f"Found {len(options)} poles from AISC database")
        confidence = calc_confidence(assumptions) * 0.95
        
        return make_envelope(
            result={
                "options": options,
                "recommended": recommended,
                "feasible_count": len(options),
                "design_criteria": {
                    "height_ft": height_ft,
                    "moment_kipft": moment_kipft,
                    "min_radius_gyration": round(min_r, 2),
                    "max_slenderness": 200,
                    "shape_types": shape_types
                }
            },
            assumptions=assumptions,
            confidence=confidence,
            inputs=req,
            outputs={
                "feasible_count": len(options),
                "min_weight": options[0]['weight_plf'] if options else None
            }
        )
    
    finally:
        await conn.close()


@router.get("/material-cost", response_model=ResponseEnvelope)
async def get_material_cost(weight_lb: float = 100) -> ResponseEnvelope:
    """Get current material cost estimate from database.
    
    Query params:
    - weight_lb: Weight in pounds
    """
    assumptions: list[str] = []
    
    conn = await get_aisc_connection()
    
    try:
        # Get latest cost index
        result = await conn.fetchrow("""
            SELECT year, month, index_value, price_per_lb
            FROM material_cost_indices
            WHERE material = 'STEEL_STRUCTURAL'
            ORDER BY year DESC, month DESC
            LIMIT 1
        """)
        
        if not result:
            add_assumption(assumptions, "No cost data available, using default $0.90/lb")
            price_per_lb = 0.90
        else:
            price_per_lb = float(result['price_per_lb'])
            add_assumption(assumptions, f"Using {result['year']} pricing: ${price_per_lb:.2f}/lb")
        
        material_cost = weight_lb * price_per_lb
        
        # Add fabrication and galvanizing estimates
        fabrication_cost = material_cost * 0.75  # 75% of material
        galvanizing_cost = weight_lb * 0.35      # $0.35/lb
        
        total_cost = material_cost + fabrication_cost + galvanizing_cost
        
        confidence = calc_confidence(assumptions) * 0.85
        
        return make_envelope(
            result={
                "material_cost": round(material_cost, 2),
                "fabrication_cost": round(fabrication_cost, 2),
                "galvanizing_cost": round(galvanizing_cost, 2),
                "total_cost": round(total_cost, 2),
                "price_per_lb": price_per_lb,
                "weight_lb": weight_lb
            },
            assumptions=assumptions,
            confidence=confidence,
            inputs={"weight_lb": weight_lb},
            outputs={"total_cost": round(total_cost, 2)}
        )
    
    finally:
        await conn.close()


@router.get("/shape-properties/{designation}", response_model=ResponseEnvelope)
async def get_shape_properties(designation: str) -> ResponseEnvelope:
    """Get detailed properties for a specific AISC shape.
    
    Path params:
    - designation: AISC designation (e.g., "HSS8x8x1/2")
    """
    assumptions: list[str] = []
    
    conn = await get_aisc_connection()
    
    try:
        # Query shape properties
        result = await conn.fetchrow("""
            SELECT 
                aisc_manual_label as designation,
                type,
                w as weight_plf,
                area as area_in2,
                d as depth,
                bf as width,
                tw as web_thickness,
                tf as flange_thickness,
                ix as ix_in4,
                sx as sx_in3,
                rx as rx_in,
                zx as zx_in3,
                iy as iy_in4,
                sy as sy_in3,
                ry as ry_in,
                zy as zy_in3,
                j as j_in4,
                cw as cw_in6,
                is_astm_a1085
            FROM aisc_shapes_v16
            WHERE UPPER(aisc_manual_label) = UPPER($1)
        """, designation)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Shape '{designation}' not found in AISC database"
            )
        
        # Convert to dict and handle None values
        properties = dict(result)
        for key, value in properties.items():
            if value is None:
                properties[key] = 0 if key not in ['designation', 'type'] else ""
            elif isinstance(value, float):
                properties[key] = round(value, 3)
        
        add_assumption(assumptions, "Properties from AISC v16.0 database")
        if properties.get('is_astm_a1085'):
            add_assumption(assumptions, "ASTM A1085 - Superior tolerances")
        
        confidence = calc_confidence(assumptions) * 0.98  # Very high confidence
        
        return make_envelope(
            result=properties,
            assumptions=assumptions,
            confidence=confidence,
            inputs={"designation": designation},
            outputs=properties
        )
    
    finally:
        await conn.close()