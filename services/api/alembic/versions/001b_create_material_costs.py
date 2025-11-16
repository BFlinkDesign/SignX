"""Create material cost tracking tables

Revision ID: 001b_material_costs
Revises: 001a_aisc_foundation
Create Date: 2025-11-01

Material cost indices and pricing for all structural materials.
Shared by all modules for cost estimation.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '001b_material_costs'
down_revision: Union[str, None] = '001a_aisc_foundation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create material cost tracking tables."""
    
    # Create material type enum
    material_enum = postgresql.ENUM(
        'STEEL_STRUCTURAL', 'STEEL_PLATE', 'STEEL_REBAR',
        'ALUMINUM_6061', 'ALUMINUM_6063', 'ALUMINUM_CAST',
        'STAINLESS_304', 'STAINLESS_316',
        'CONCRETE', 'GROUT', 'ANCHOR_BOLTS',
        'GALVANIZING', 'POWDER_COATING', 'PAINT',
        name='material_type_enum',
        create_type=True
    )
    material_enum.create(op.get_bind(), checkfirst=True)
    
    # Main material cost tracking table
    op.create_table(
        'material_cost_indices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('material', sa.Enum(material_enum), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer()),  # Q1, Q2, Q3, Q4
        
        # Pricing data
        sa.Column('index_value', sa.Float(), nullable=False),  # 100 = baseline
        sa.Column('price_per_lb', sa.Numeric(10, 4)),  # Steel, aluminum
        sa.Column('price_per_cy', sa.Numeric(10, 2)),  # Concrete (cubic yard)
        sa.Column('price_per_sqft', sa.Numeric(10, 2)),  # Coatings
        sa.Column('price_per_unit', sa.Numeric(10, 2)),  # Generic unit price
        
        # Additional cost factors
        sa.Column('fabrication_multiplier', sa.Float(), server_default='1.75'),
        sa.Column('installation_multiplier', sa.Float(), server_default='1.5'),
        sa.Column('transportation_per_lb', sa.Numeric(10, 4)),
        
        # Source and metadata
        sa.Column('source', sa.String(100)),  # ENR, LME, Producer Price Index
        sa.Column('region', sa.String(50), server_default='US_NATIONAL'),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('material', 'year', 'month', name='uq_material_year_month')
    )
    
    # Create indexes
    op.create_index('ix_cost_material', 'material_cost_indices', ['material'])
    op.create_index('ix_cost_year_month', 'material_cost_indices', ['year', 'month'])
    op.create_index('ix_cost_material_date', 'material_cost_indices', ['material', 'year', 'month'])
    
    # Regional cost adjustments table
    op.create_table(
        'regional_cost_factors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('state', sa.String(2), nullable=False),
        sa.Column('city', sa.String(100)),
        sa.Column('county', sa.String(100)),
        sa.Column('zip_code', sa.String(10)),
        
        # Regional multipliers (1.0 = national average)
        sa.Column('material_factor', sa.Float(), server_default='1.0'),
        sa.Column('labor_factor', sa.Float(), server_default='1.0'),
        sa.Column('equipment_factor', sa.Float(), server_default='1.0'),
        sa.Column('overall_factor', sa.Float(), server_default='1.0'),
        
        # Specific adjustments
        sa.Column('steel_adjustment', sa.Float(), server_default='1.0'),
        sa.Column('concrete_adjustment', sa.Float(), server_default='1.0'),
        sa.Column('transportation_adjustment', sa.Float(), server_default='1.0'),
        
        sa.Column('effective_date', sa.Date()),
        sa.Column('source', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('ix_regional_state', 'regional_cost_factors', ['state'])
    op.create_index('ix_regional_city_state', 'regional_cost_factors', ['city', 'state'])
    op.create_index('ix_regional_zip', 'regional_cost_factors', ['zip_code'])
    
    # Material suppliers/vendors table
    op.create_table(
        'material_suppliers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('supplier_name', sa.String(200), nullable=False),
        sa.Column('supplier_code', sa.String(50), unique=True),
        sa.Column('material_type', sa.Enum(material_enum)),
        
        # Pricing tiers
        sa.Column('base_price_per_lb', sa.Numeric(10, 4)),
        sa.Column('volume_discount_1000lb', sa.Float()),  # % discount
        sa.Column('volume_discount_5000lb', sa.Float()),
        sa.Column('volume_discount_10000lb', sa.Float()),
        
        # Lead times
        sa.Column('standard_lead_days', sa.Integer()),
        sa.Column('expedited_lead_days', sa.Integer()),
        sa.Column('expedite_surcharge', sa.Float()),  # % surcharge
        
        # Contact and location
        sa.Column('contact_email', sa.String(200)),
        sa.Column('contact_phone', sa.String(50)),
        sa.Column('address', sa.Text()),
        sa.Column('delivery_radius_miles', sa.Integer()),
        
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('ix_supplier_material', 'material_suppliers', ['material_type'])
    op.create_index('ix_supplier_active', 'material_suppliers', ['is_active'])
    
    # Insert baseline cost indices
    op.execute("""
    INSERT INTO material_cost_indices 
    (material, year, month, quarter, index_value, price_per_lb, source)
    VALUES 
    -- Steel structural indices (historical to current)
    ('STEEL_STRUCTURAL', 2020, 1, 1, 100.0, 0.65, 'ENR'),
    ('STEEL_STRUCTURAL', 2021, 1, 1, 115.2, 0.75, 'ENR'),
    ('STEEL_STRUCTURAL', 2022, 1, 1, 142.8, 0.93, 'ENR'),
    ('STEEL_STRUCTURAL', 2023, 1, 1, 128.5, 0.84, 'ENR'),
    ('STEEL_STRUCTURAL', 2024, 1, 1, 135.2, 0.88, 'ENR'),
    ('STEEL_STRUCTURAL', 2025, 1, 1, 138.7, 0.90, 'ENR'),
    ('STEEL_STRUCTURAL', 2025, 11, 4, 140.2, 0.91, 'ENR'),  -- Current
    
    -- Aluminum indices
    ('ALUMINUM_6061', 2020, 1, 1, 100.0, 1.85, 'LME'),
    ('ALUMINUM_6061', 2021, 1, 1, 108.5, 2.01, 'LME'),
    ('ALUMINUM_6061', 2022, 1, 1, 125.3, 2.32, 'LME'),
    ('ALUMINUM_6061', 2023, 1, 1, 118.2, 2.19, 'LME'),
    ('ALUMINUM_6061', 2024, 1, 1, 122.5, 2.27, 'LME'),
    ('ALUMINUM_6061', 2025, 1, 1, 124.8, 2.31, 'LME'),
    ('ALUMINUM_6061', 2025, 11, 4, 126.1, 2.33, 'LME'),  -- Current
    
    -- Galvanizing costs
    ('GALVANIZING', 2025, 11, 4, 100.0, 0.35, 'Industry Average'),
    
    -- Concrete prices
    ('CONCRETE', 2025, 11, 4, 145.0, NULL, 'Local Average')
    ON CONFLICT (material, year, month) DO NOTHING;
    """)
    
    # Insert regional factors for major markets
    op.execute("""
    INSERT INTO regional_cost_factors 
    (state, city, material_factor, labor_factor, overall_factor)
    VALUES 
    ('TX', 'Houston', 0.95, 0.90, 0.93),
    ('TX', 'Dallas', 0.96, 0.92, 0.94),
    ('CA', 'Los Angeles', 1.12, 1.35, 1.24),
    ('CA', 'San Francisco', 1.15, 1.45, 1.30),
    ('NY', 'New York', 1.18, 1.42, 1.30),
    ('FL', 'Miami', 1.02, 0.95, 0.99),
    ('IL', 'Chicago', 1.05, 1.20, 1.13),
    ('AZ', 'Phoenix', 0.98, 0.88, 0.93),
    ('GA', 'Atlanta', 0.97, 0.93, 0.95),
    ('WA', 'Seattle', 1.08, 1.25, 1.17);
    """)
    
    # Create function to get current material price
    op.execute("""
    CREATE OR REPLACE FUNCTION get_current_material_price(
        p_material material_type_enum,
        p_weight_lb FLOAT DEFAULT 1.0,
        p_state VARCHAR DEFAULT NULL
    )
    RETURNS TABLE (
        base_price NUMERIC,
        regional_factor FLOAT,
        total_price NUMERIC,
        price_date DATE
    )
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_price_per_lb NUMERIC;
        v_regional_factor FLOAT;
        v_year INT;
        v_month INT;
    BEGIN
        -- Get latest price
        SELECT price_per_lb, year, month INTO v_price_per_lb, v_year, v_month
        FROM material_cost_indices
        WHERE material = p_material
        ORDER BY year DESC, month DESC
        LIMIT 1;
        
        -- Get regional factor
        IF p_state IS NOT NULL THEN
            SELECT COALESCE(overall_factor, 1.0) INTO v_regional_factor
            FROM regional_cost_factors
            WHERE state = p_state
            LIMIT 1;
        ELSE
            v_regional_factor := 1.0;
        END IF;
        
        RETURN QUERY
        SELECT 
            v_price_per_lb * p_weight_lb AS base_price,
            v_regional_factor AS regional_factor,
            v_price_per_lb * p_weight_lb * v_regional_factor AS total_price,
            make_date(v_year, v_month, 1) AS price_date;
    END;
    $$;
    """)
    
    # Create view for current prices
    op.execute("""
    CREATE OR REPLACE VIEW current_material_prices AS
    WITH latest_prices AS (
        SELECT DISTINCT ON (material)
            material,
            year,
            month,
            index_value,
            price_per_lb,
            price_per_cy,
            price_per_sqft,
            fabrication_multiplier,
            installation_multiplier
        FROM material_cost_indices
        ORDER BY material, year DESC, month DESC
    )
    SELECT 
        material,
        make_date(year, month, 1) as price_date,
        index_value,
        price_per_lb,
        price_per_cy,
        price_per_sqft,
        price_per_lb * fabrication_multiplier as fabricated_price_per_lb,
        price_per_lb * (1 + fabrication_multiplier + installation_multiplier) as installed_price_per_lb
    FROM latest_prices;
    """)
    
    logger.info("[OK] Created material_cost_indices table")
    logger.info("[OK] Created regional_cost_factors table")
    logger.info("[OK] Created material_suppliers table")
    logger.info("[OK] Inserted baseline cost data")
    logger.info("[OK] Created price calculation function")
    logger.info("[OK] Created current_material_prices view")


def downgrade() -> None:
    """Remove material cost tracking tables."""
    
    # Drop views and functions
    op.execute("DROP VIEW IF EXISTS current_material_prices")
    op.execute("DROP FUNCTION IF EXISTS get_current_material_price")
    
    # Drop indexes
    op.drop_index('ix_supplier_active', 'material_suppliers')
    op.drop_index('ix_supplier_material', 'material_suppliers')
    op.drop_index('ix_regional_zip', 'regional_cost_factors')
    op.drop_index('ix_regional_city_state', 'regional_cost_factors')
    op.drop_index('ix_regional_state', 'regional_cost_factors')
    op.drop_index('ix_cost_material_date', 'material_cost_indices')
    op.drop_index('ix_cost_year_month', 'material_cost_indices')
    op.drop_index('ix_cost_material', 'material_cost_indices')
    
    # Drop tables
    op.drop_table('material_suppliers')
    op.drop_table('regional_cost_factors')
    op.drop_table('material_cost_indices')
    
    # Drop enum
    material_enum = postgresql.ENUM(
        'STEEL_STRUCTURAL', 'STEEL_PLATE', 'STEEL_REBAR',
        'ALUMINUM_6061', 'ALUMINUM_6063', 'ALUMINUM_CAST',
        'STAINLESS_304', 'STAINLESS_316',
        'CONCRETE', 'GROUT', 'ANCHOR_BOLTS',
        'GALVANIZING', 'POWDER_COATING', 'PAINT',
        name='material_type_enum'
    )
    material_enum.drop(op.get_bind(), checkfirst=True)