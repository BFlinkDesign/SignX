"""Create AISC shapes foundation catalog

Revision ID: 001a_aisc_foundation
Revises: 009_add_audit_rbac_compliance_tables
Create Date: 2025-11-01

This creates the foundational AISC Shapes Database v16.0 that serves as the
shared reference catalog for ALL structural modules in the platform:
- Cantilever arms → HSS, PIPE sections
- Monument poles → HSS, PIPE sections  
- Pylon structures → W-shapes, HSS columns
- Wall brackets → Channels, angles, tubes
- Custom fabrications → All shape types
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '001a_aisc_foundation'
down_revision: Union[str, None] = '009_add_audit_rbac_compliance_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create AISC shapes foundation tables."""
    
    # Create the main AISC shapes catalog table
    # This is the authoritative source for all steel shapes
    op.create_table(
        'aisc_shapes_v16',
        # Primary identification
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),  # HSS, PIPE, W, C, L, etc.
        sa.Column('edi_std_nomenclature', sa.String(100)),
        sa.Column('aisc_manual_label', sa.String(100), nullable=False, unique=True),
        
        # Material specifications
        sa.Column('t_f', sa.String(10)),  # Material spec reference
        sa.Column('is_astm_a1085', sa.Boolean(), server_default='false'),  # Superior HSS
        sa.Column('fy_ksi', sa.Float(), server_default='50'),  # Yield strength
        sa.Column('fu_ksi', sa.Float(), server_default='65'),  # Ultimate strength
        
        # Weight and area
        sa.Column('w', sa.Float()),  # Weight per foot (lb/ft)
        sa.Column('area', sa.Float()),  # Cross-sectional area (in²)
        
        # Primary dimensions
        sa.Column('d', sa.Float()),  # Depth/height (in)
        sa.Column('d_det', sa.Float()),  # Detailed depth
        sa.Column('ht', sa.Float()),  # Total height
        sa.Column('h', sa.Float()),  # Clear distance between flanges
        sa.Column('od', sa.Float()),  # Outside diameter (pipes)
        sa.Column('id_dim', sa.Float()),  # Inside diameter (pipes)
        
        # Width dimensions
        sa.Column('bf', sa.Float()),  # Flange width
        sa.Column('bf_det', sa.Float()),  # Detailed flange width
        sa.Column('b', sa.Float()),  # Width (HSS, angles)
        
        # Thickness dimensions
        sa.Column('tw', sa.Float()),  # Web thickness
        sa.Column('tw_det', sa.Float()),  # Detailed web thickness
        sa.Column('tf', sa.Float()),  # Flange thickness
        sa.Column('tf_det', sa.Float()),  # Detailed flange thickness
        sa.Column('tnom', sa.Float()),  # Nominal thickness (HSS)
        sa.Column('tdes', sa.Float()),  # Design thickness (HSS)
        
        # Section properties - Strong axis (x-x)
        sa.Column('ix', sa.Float()),  # Moment of inertia (in⁴)
        sa.Column('sx', sa.Float()),  # Section modulus (in³)
        sa.Column('rx', sa.Float()),  # Radius of gyration (in)
        sa.Column('zx', sa.Float()),  # Plastic modulus (in³)
        
        # Section properties - Weak axis (y-y)
        sa.Column('iy', sa.Float()),  # Moment of inertia (in⁴)
        sa.Column('sy', sa.Float()),  # Section modulus (in³)
        sa.Column('ry', sa.Float()),  # Radius of gyration (in)
        sa.Column('zy', sa.Float()),  # Plastic modulus (in³)
        
        # Torsional and warping properties
        sa.Column('j', sa.Float()),  # Torsional constant (in⁴)
        sa.Column('cw', sa.Float()),  # Warping constant (in⁶)
        sa.Column('rts', sa.Float()),  # Effective radius of gyration
        sa.Column('ho', sa.Float()),  # Distance between flange centroids
        
        # Shear properties
        sa.Column('aw', sa.Float()),  # Web area (in²)
        sa.Column('ag', sa.Float()),  # Gross area
        sa.Column('an', sa.Float()),  # Net area
        
        # Slenderness ratios
        sa.Column('bf_2tf', sa.Float()),  # Flange slenderness
        sa.Column('h_tw', sa.Float()),  # Web slenderness
        sa.Column('d_t', sa.Float()),  # Diameter to thickness (pipes)
        sa.Column('b_t', sa.Float()),  # Width to thickness (HSS)
        
        # For angles (L shapes)
        sa.Column('x_bar', sa.Float()),  # X centroid
        sa.Column('y_bar', sa.Float()),  # Y centroid
        sa.Column('ro', sa.Float()),  # Polar radius of gyration
        sa.Column('h_bar', sa.Float()),  # H value for single angles
        sa.Column('tan_alpha', sa.Float()),  # Tangent of principal angle
        
        # Classification and availability
        sa.Column('wt_class', sa.String(20)),  # Weight class
        sa.Column('is_available', sa.Boolean(), server_default='true'),
        sa.Column('is_slender', sa.Boolean(), server_default='false'),
        
        # Search optimization
        sa.Column('nominal_depth', sa.Integer()),  # Rounded depth for filtering
        sa.Column('nominal_weight', sa.Integer()),  # Rounded weight for filtering
        
        # Metadata
        sa.Column('source', sa.String(50), server_default='AISC_v16.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create comprehensive indexes for performance
    op.create_index('ix_aisc_type', 'aisc_shapes_v16', ['type'])
    op.create_index('ix_aisc_weight', 'aisc_shapes_v16', ['w'])
    op.create_index('ix_aisc_sx', 'aisc_shapes_v16', ['sx'])
    op.create_index('ix_aisc_ix', 'aisc_shapes_v16', ['ix'])
    op.create_index('ix_aisc_rx', 'aisc_shapes_v16', ['rx'])
    op.create_index('ix_aisc_ry', 'aisc_shapes_v16', ['ry'])
    op.create_index('ix_aisc_label', 'aisc_shapes_v16', ['aisc_manual_label'])
    op.create_index('ix_aisc_nominal', 'aisc_shapes_v16', ['nominal_depth', 'nominal_weight'])
    op.create_index('ix_aisc_type_sx', 'aisc_shapes_v16', ['type', 'sx'])  # Composite index
    op.create_index('ix_aisc_type_w', 'aisc_shapes_v16', ['type', 'w'])  # Composite index
    op.create_index('ix_aisc_a1085', 'aisc_shapes_v16', ['is_astm_a1085'])  # For A1085 filtering
    
    # Create shape type enum for validation
    shape_type_enum = postgresql.ENUM(
        'W', 'S', 'HP', 'M', 'C', 'MC', 'L', '2L', 'WT', 'ST', 
        'HSS', 'PIPE', 'TUBE', 'CUSTOM',
        name='shape_type_enum',
        create_type=True
    )
    shape_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Create view for commonly used sign/structural sections
    op.execute("""
    CREATE OR REPLACE VIEW structural_sections AS
    SELECT 
        aisc_manual_label as designation,
        type,
        w as weight_plf,
        area as area_in2,
        d as depth_in,
        bf as width_in,
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
        is_astm_a1085,
        CASE 
            WHEN type = 'HSS' THEN 'Hollow Structural Section'
            WHEN type = 'PIPE' THEN 'Steel Pipe'
            WHEN type = 'W' THEN 'Wide Flange'
            WHEN type = 'C' THEN 'Channel'
            WHEN type = 'L' THEN 'Angle'
            WHEN type = 'WT' THEN 'Structural Tee'
            ELSE 'Other'
        END as shape_category
    FROM aisc_shapes_v16
    WHERE is_available = true
    ORDER BY type, w;
    """)
    
    # Create materialized view for HSS sections (most common for signs)
    op.execute("""
    CREATE MATERIALIZED VIEW hss_sections AS
    SELECT 
        aisc_manual_label as designation,
        w as weight_plf,
        area as area_in2,
        b as width,
        d as height,
        tnom as wall_nominal,
        tdes as wall_design,
        ix as ix_in4,
        sx as sx_in3,
        rx as rx_in,
        iy as iy_in4,
        sy as sy_in3,
        ry as ry_in,
        j as j_in4,
        is_astm_a1085,
        b_t as width_thickness_ratio,
        CASE 
            WHEN b_t <= 35 THEN 'Compact'
            WHEN b_t <= 42 THEN 'Noncompact'
            ELSE 'Slender'
        END as classification,
        CASE 
            WHEN is_astm_a1085 THEN 0.93  -- Better tolerance factor
            ELSE 0.86  -- Standard A500
        END as design_thickness_factor
    FROM aisc_shapes_v16
    WHERE type = 'HSS'
    ORDER BY w;
    
    CREATE INDEX ix_hss_weight ON hss_sections(weight_plf);
    CREATE INDEX ix_hss_sx ON hss_sections(sx_in3);
    """)
    
    logger.info("[OK] Created aisc_shapes_v16 foundation table")
    logger.info("[OK] Created comprehensive indexes for performance")
    logger.info("[OK] Created structural_sections view")
    logger.info("[OK] Created hss_sections materialized view")


def downgrade() -> None:
    """Remove AISC shapes foundation tables."""
    
    # Drop materialized view
    op.execute("DROP MATERIALIZED VIEW IF EXISTS hss_sections CASCADE")
    
    # Drop views
    op.execute("DROP VIEW IF EXISTS structural_sections CASCADE")
    
    # Drop indexes
    op.drop_index('ix_aisc_a1085', 'aisc_shapes_v16')
    op.drop_index('ix_aisc_type_w', 'aisc_shapes_v16')
    op.drop_index('ix_aisc_type_sx', 'aisc_shapes_v16')
    op.drop_index('ix_aisc_nominal', 'aisc_shapes_v16')
    op.drop_index('ix_aisc_label', 'aisc_shapes_v16')
    op.drop_index('ix_aisc_ry', 'aisc_shapes_v16')
    op.drop_index('ix_aisc_rx', 'aisc_shapes_v16')
    op.drop_index('ix_aisc_ix', 'aisc_shapes_v16')
    op.drop_index('ix_aisc_sx', 'aisc_shapes_v16')
    op.drop_index('ix_aisc_weight', 'aisc_shapes_v16')
    op.drop_index('ix_aisc_type', 'aisc_shapes_v16')
    
    # Drop table
    op.drop_table('aisc_shapes_v16')
    
    # Drop enum
    shape_type_enum = postgresql.ENUM('W', 'S', 'HP', 'M', 'C', 'MC', 'L', '2L', 'WT', 'ST', 
                                     'HSS', 'PIPE', 'TUBE', 'CUSTOM', name='shape_type_enum')
    shape_type_enum.drop(op.get_bind(), checkfirst=True)