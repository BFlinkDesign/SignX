"""Create sign-specific database views

Revision ID: 001c_sign_views  
Revises: 001b_material_costs
Create Date: 2025-11-01

Creates optimized views for sign engineering calculations that reference
the AISC foundation catalog. These views are shared across all sign modules.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '001c_sign_views'
down_revision: Union[str, None] = '001b_material_costs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sign-specific views and functions."""
    
    # View for sign pole sections (filtered and optimized)
    op.execute("""
    CREATE OR REPLACE VIEW sign_pole_sections AS
    SELECT 
        s.aisc_manual_label as designation,
        s.type,
        s.w as weight_plf,
        s.area as area_in2,
        s.d as depth_in,
        s.bf as width_in,
        s.ix as ix_in4,
        s.sx as sx_in3,
        s.rx as rx_in,
        s.zx as zx_in3,
        s.iy as iy_in4,
        s.sy as sy_in3,
        s.ry as ry_in,
        s.zy as zy_in3,
        s.j as j_in4,
        s.is_astm_a1085,
        -- Calculate max cantilever span (conservative estimate)
        CASE 
            WHEN s.type = 'HSS' THEN 
                LEAST(s.d * 2.5, 30)  -- 2.5x depth or 30ft max
            WHEN s.type = 'PIPE' THEN 
                LEAST(s.d * 2.0, 25)  -- 2x diameter or 25ft max
            WHEN s.type = 'W' THEN 
                LEAST(s.d * 1.5, 20)  -- 1.5x depth or 20ft max
            ELSE s.d
        END as max_cantilever_ft,
        -- Calculate max single pole height based on slenderness
        CASE 
            WHEN s.rx > 0 THEN 
                LEAST(s.rx * 200 / 12, 50)  -- L/r=200 or 50ft max
            ELSE 0
        END as max_height_ft,
        -- Material efficiency score (Sx per pound)
        CASE 
            WHEN s.w > 0 THEN s.sx / s.w
            ELSE 0
        END as efficiency_ratio
    FROM aisc_shapes_v16 s
    WHERE s.type IN ('HSS', 'PIPE', 'W', 'WT')
        AND s.w > 10  -- Min 10 lb/ft for structural signs
        AND s.sx > 5  -- Min section modulus
        AND s.is_available = true
    ORDER BY s.type, s.w;
    """)
    
    # View for cantilever arm sections
    op.execute("""
    CREATE OR REPLACE VIEW cantilever_arm_sections AS
    SELECT 
        s.aisc_manual_label as designation,
        s.type,
        s.w as weight_plf,
        s.sx as sx_in3,
        s.ix as ix_in4,
        s.j as j_in4,
        s.is_astm_a1085,
        -- Moment capacity at Fy=50ksi, phi=0.9
        s.sx * 50 * 0.9 / 12 as moment_capacity_kipft,
        -- Torsional stiffness
        s.j * 11200 as torsional_stiffness,  -- GJ with G=11200 ksi
        -- Recommended max cantilever length
        CASE 
            WHEN s.sx < 10 THEN 10
            WHEN s.sx < 25 THEN 15
            WHEN s.sx < 50 THEN 20
            WHEN s.sx < 100 THEN 25
            ELSE 30
        END as recommended_span_ft,
        -- A1085 tolerance factor
        CASE 
            WHEN s.is_astm_a1085 THEN 0.93
            ELSE 0.86
        END as tolerance_factor,
        -- Deflection parameter (EI/L^3 factor)
        29000 * s.ix as flexural_stiffness
    FROM aisc_shapes_v16 s
    WHERE s.type IN ('HSS', 'PIPE')
        AND s.sx >= 10  -- Min for cantilever signs
        AND s.w <= 100  -- Max practical weight
        AND s.is_available = true
    ORDER BY s.sx;
    """)
    
    # View for monument/pylon columns
    op.execute("""
    CREATE OR REPLACE VIEW monument_column_sections AS
    SELECT 
        s.aisc_manual_label as designation,
        s.type,
        s.w as weight_plf,
        s.area as area_in2,
        s.rx as rx_in,
        s.ry as ry_in,
        LEAST(s.rx, s.ry) as r_min,
        -- Axial capacity at Fy=50ksi, phi=0.9
        s.area * 50 * 0.9 as axial_capacity_kips,
        -- Max unbraced length for KL/r = 120 (monuments)
        LEAST(s.rx, s.ry) * 120 / 12 as max_unbraced_ft,
        -- Column classification
        CASE 
            WHEN s.type = 'HSS' AND s.bf_2tf <= 35 THEN 'Compact'
            WHEN s.type = 'HSS' AND s.bf_2tf <= 42 THEN 'Noncompact'
            WHEN s.type = 'PIPE' AND s.d_t <= 0.11 * 29000/50 THEN 'Compact'
            WHEN s.type = 'W' AND s.bf_2tf <= 9.2 THEN 'Compact'
            ELSE 'Slender'
        END as classification,
        s.is_astm_a1085
    FROM aisc_shapes_v16 s
    WHERE s.type IN ('HSS', 'PIPE', 'W')
        AND s.area >= 3.0  -- Min area for columns
        AND LEAST(s.rx, s.ry) >= 1.5  -- Min radius of gyration
        AND s.is_available = true
    ORDER BY s.type, s.area;
    """)
    
    -- View for wall mount brackets (channels and angles)
    op.execute("""
    CREATE OR REPLACE VIEW wall_bracket_sections AS
    SELECT 
        s.aisc_manual_label as designation,
        s.type,
        s.w as weight_plf,
        s.area as area_in2,
        s.sx as sx_in3,
        s.ix as ix_in4,
        -- For angles: distance to centroid
        s.x_bar,
        s.y_bar,
        -- Max bracket projection (conservative)
        CASE 
            WHEN s.type = 'C' THEN s.d * 1.5
            WHEN s.type = 'MC' THEN s.d * 1.5
            WHEN s.type = 'L' THEN GREATEST(s.d, s.bf) * 2.0
            ELSE s.d
        END as max_projection_in,
        -- Moment capacity for bracket
        s.sx * 50 * 0.9 / 12 as moment_capacity_kipft
    FROM aisc_shapes_v16 s
    WHERE s.type IN ('C', 'MC', 'L', '2L')
        AND s.w <= 50  -- Practical limit for wall brackets
        AND s.is_available = true
    ORDER BY s.type, s.w;
    """)
    
    # Combined view with cost estimates
    op.execute("""
    CREATE OR REPLACE VIEW sign_sections_with_cost AS
    SELECT 
        s.designation,
        s.type,
        s.weight_plf,
        s.sx_in3,
        s.max_cantilever_ft,
        s.max_height_ft,
        -- Get current material cost
        COALESCE(p.price_per_lb, 0.90) * s.weight_plf as material_cost_per_ft,
        -- Add fabrication (75% of material)
        COALESCE(p.price_per_lb, 0.90) * s.weight_plf * 1.75 as fabricated_cost_per_ft,
        -- Add galvanizing ($0.35/lb)
        s.weight_plf * 0.35 as galvanizing_cost_per_ft,
        -- Total installed cost estimate
        COALESCE(p.price_per_lb, 0.90) * s.weight_plf * 2.5 + s.weight_plf * 0.35 as total_cost_per_ft,
        p.price_date,
        s.efficiency_ratio
    FROM sign_pole_sections s
    LEFT JOIN current_material_prices p ON p.material = 'STEEL_STRUCTURAL'
    ORDER BY s.type, s.weight_plf;
    """)
    
    # Function to find optimal section for given requirements
    op.execute("""
    CREATE OR REPLACE FUNCTION find_optimal_sign_pole(
        p_moment_kipft FLOAT,
        p_height_ft FLOAT DEFAULT NULL,
        p_shape_type VARCHAR DEFAULT NULL,
        p_max_weight FLOAT DEFAULT 200,
        p_prefer_a1085 BOOLEAN DEFAULT FALSE
    )
    RETURNS TABLE (
        designation VARCHAR,
        type VARCHAR,
        weight_plf FLOAT,
        sx_in3 FLOAT,
        stress_ratio FLOAT,
        total_cost_per_ft NUMERIC,
        is_a1085 BOOLEAN
    )
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_required_sx FLOAT;
        v_min_r FLOAT;
    BEGIN
        -- Calculate required section modulus
        v_required_sx := p_moment_kipft * 12 / (50 * 0.9);
        
        -- Calculate min radius of gyration if height specified
        IF p_height_ft IS NOT NULL THEN
            v_min_r := p_height_ft * 12 / 200;  -- L/r = 200
        ELSE
            v_min_r := 0;
        END IF;
        
        RETURN QUERY
        SELECT 
            s.aisc_manual_label,
            s.type,
            s.w,
            s.sx,
            (p_moment_kipft * 12) / (s.sx * 50 * 0.9) as stress_ratio,
            COALESCE(p.price_per_lb, 0.90) * s.w * 2.85 as total_cost,
            s.is_astm_a1085
        FROM aisc_shapes_v16 s
        LEFT JOIN current_material_prices p ON p.material = 'STEEL_STRUCTURAL'
        WHERE s.sx >= v_required_sx
            AND s.w <= p_max_weight
            AND (p_shape_type IS NULL OR s.type = p_shape_type)
            AND (v_min_r = 0 OR s.rx >= v_min_r)
            AND (NOT p_prefer_a1085 OR s.is_astm_a1085 = true)
            AND s.is_available = true
        ORDER BY 
            CASE WHEN p_prefer_a1085 AND s.is_astm_a1085 THEN 0 ELSE 1 END,
            s.w
        LIMIT 10;
    END;
    $$;
    """)
    
    # Function to calculate sign pole utilization
    op.execute("""
    CREATE OR REPLACE FUNCTION calculate_pole_utilization(
        p_designation VARCHAR,
        p_moment_kipft FLOAT,
        p_shear_kip FLOAT DEFAULT 0,
        p_axial_kip FLOAT DEFAULT 0
    )
    RETURNS TABLE (
        flexure_ratio FLOAT,
        shear_ratio FLOAT,
        axial_ratio FLOAT,
        combined_ratio FLOAT,
        status VARCHAR
    )
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_sx FLOAT;
        v_area FLOAT;
        v_aw FLOAT;
        v_flexure_ratio FLOAT;
        v_shear_ratio FLOAT;
        v_axial_ratio FLOAT;
    BEGIN
        -- Get section properties
        SELECT sx, area, COALESCE(aw, area * 0.6) 
        INTO v_sx, v_area, v_aw
        FROM aisc_shapes_v16
        WHERE UPPER(aisc_manual_label) = UPPER(p_designation);
        
        IF v_sx IS NULL THEN
            RAISE EXCEPTION 'Section % not found', p_designation;
        END IF;
        
        -- Calculate utilization ratios
        v_flexure_ratio := (p_moment_kipft * 12) / (v_sx * 50 * 0.9);
        v_shear_ratio := p_shear_kip / (v_aw * 30 * 0.9);  -- 0.6Fy
        v_axial_ratio := p_axial_kip / (v_area * 50 * 0.9);
        
        RETURN QUERY
        SELECT 
            v_flexure_ratio,
            v_shear_ratio,
            v_axial_ratio,
            -- Simplified combined check (AISC H1-1)
            GREATEST(
                v_axial_ratio + 8/9 * v_flexure_ratio,
                v_axial_ratio/2 + v_flexure_ratio
            ) as combined,
            CASE 
                WHEN GREATEST(v_flexure_ratio, v_shear_ratio, v_axial_ratio) > 1.0 THEN 'FAIL'
                WHEN GREATEST(v_flexure_ratio, v_shear_ratio, v_axial_ratio) > 0.95 THEN 'WARNING'
                ELSE 'OK'
            END as status;
    END;
    $$;
    """)
    
    # Materialized view for fast lookups of common sign poles
    op.execute("""
    CREATE MATERIALIZED VIEW common_sign_poles AS
    WITH ranked_poles AS (
        SELECT 
            s.*,
            ROW_NUMBER() OVER (
                PARTITION BY 
                    s.type,
                    CASE 
                        WHEN s.sx < 20 THEN 'Small'
                        WHEN s.sx < 50 THEN 'Medium'
                        WHEN s.sx < 100 THEN 'Large'
                        ELSE 'XLarge'
                    END
                ORDER BY s.w
            ) as rank
        FROM sign_pole_sections s
    )
    SELECT * FROM ranked_poles
    WHERE rank <= 3;  -- Top 3 in each category
    
    CREATE INDEX ix_common_poles_type ON common_sign_poles(type);
    CREATE INDEX ix_common_poles_sx ON common_sign_poles(sx_in3);
    """)
    
    logger.info("[OK] Created sign_pole_sections view")
    logger.info("[OK] Created cantilever_arm_sections view")
    logger.info("[OK] Created monument_column_sections view")
    logger.info("[OK] Created wall_bracket_sections view")
    logger.info("[OK] Created sign_sections_with_cost view")
    logger.info("[OK] Created find_optimal_sign_pole function")
    logger.info("[OK] Created calculate_pole_utilization function")
    logger.info("[OK] Created common_sign_poles materialized view")


def downgrade() -> None:
    """Remove sign-specific views and functions."""
    
    # Drop materialized view
    op.execute("DROP MATERIALIZED VIEW IF EXISTS common_sign_poles CASCADE")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS calculate_pole_utilization CASCADE")
    op.execute("DROP FUNCTION IF EXISTS find_optimal_sign_pole CASCADE")
    
    # Drop views
    op.execute("DROP VIEW IF EXISTS sign_sections_with_cost CASCADE")
    op.execute("DROP VIEW IF EXISTS wall_bracket_sections CASCADE")
    op.execute("DROP VIEW IF EXISTS monument_column_sections CASCADE")
    op.execute("DROP VIEW IF EXISTS cantilever_arm_sections CASCADE")
    op.execute("DROP VIEW IF EXISTS sign_pole_sections CASCADE")