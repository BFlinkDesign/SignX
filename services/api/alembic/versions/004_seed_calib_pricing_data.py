"""seed_calib_pricing_data

Revision ID: 004
Revises: 003
Create Date: 2025-01-27 14:30:00.000000

Seeds calibration constants, pricing configs, and AISC/ASCE catalog stubs.
"""
from __future__ import annotations

from typing import Sequence, Union
from datetime import date

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Seed calibration constants
    op.execute(
        """
        INSERT INTO calibration_constants (name, version, value, unit, description, source, effective_from) VALUES
        ('K_FACTOR', 'footing_v1', 0.15, 'unitless', 'Calibrated K factor for direct burial depth calculation', 'ASCE 7-16 + calibration', '2025-01-01'),
        ('SOIL_BEARING_DEFAULT', 'footing_v1', 3000.0, 'psf', 'Default allowable soil bearing pressure', 'ASCE 7-16 12.7.1', '2025-01-01'),
        ('CONCRETE_DENSITY', 'material_v1', 150.0, 'pcf', 'Normal weight concrete density', 'ACI 318', '2025-01-01'),
        ('STEEL_YIELD_A36', 'material_v1', 36.0, 'ksi', 'A36 steel yield strength', 'AISC 360', '2025-01-01'),
        ('STEEL_YIELD_A572', 'material_v1', 50.0, 'ksi', 'A572 Grade 50 yield strength', 'AISC 360', '2025-01-01'),
        ('STEEL_MODULUS', 'material_v1', 29000.0, 'ksi', 'Steel modulus of elasticity', 'AISC 360', '2025-01-01')
        ON CONFLICT (name, version) DO NOTHING
        """
    )
    
    # Seed pricing configurations
    op.execute(
        """
        INSERT INTO pricing_configs (item_code, version, price_usd, description, category, effective_from) VALUES
        ('base_est', 'v1', 150.00, 'Base estimation service', 'base', '2025-01-01'),
        ('calc_packet', 'v1', 35.00, 'Calculation packet add-on', 'addon', '2025-01-01'),
        ('hard_copies', 'v1', 50.00, 'Hard copies shipping', 'addon', '2025-01-01'),
        ('expedited', 'v1', 100.00, 'Expedited processing (3-day)', 'addon', '2025-01-01'),
        ('permit_pkg', 'v1', 250.00, 'Permit package preparation', 'permit', '2025-01-01')
        ON CONFLICT (item_code, version) DO NOTHING
        """
    )
    
    # Seed material catalog stubs
    op.execute(
        """
        INSERT INTO material_catalog (material_id, standard, grade, shape, properties, dimensions, source_table) VALUES
        ('AISC_99_A36', 'AISC', 'A36', 'HSS', 
         '{"fy_ksi": 36.0, "E_ksi": 29000.0, "G_ksi": 11200.0, "nu": 0.30}', 
         '{"A_in2": 1.54, "Ix_in4": 0.811, "Iy_in4": 0.811, "r_in": 0.726}', 
         'AISC Manual Table 1-12'),
        ('AISC_99_A572', 'AISC', 'A572_50', 'HSS',
         '{"fy_ksi": 50.0, "E_ksi": 29000.0, "G_ksi": 11200.0, "nu": 0.30}',
         '{"A_in2": 2.65, "Ix_in4": 1.39, "Iy_in4": 1.39, "r_in": 0.724}',
         'AISC Manual Table 1-12'),
        ('ASTM_A53_A36', 'ASTM', 'A36', 'Pipe',
         '{"fy_ksi": 36.0, "E_ksi": 29000.0, "t_min_in": 0.237}',
         '{"OD_in": 3.5, "A_in2": 2.43, "I_in4": 3.02, "r_in": 1.114}',
         'ASTM A53 Grade A'),
        ('ASTM_A53_A53B', 'ASTM', 'A53_B', 'Pipe',
         '{"fy_ksi": 35.0, "E_ksi": 29000.0, "t_min_in": 0.237}',
         '{"OD_in": 4.0, "A_in2": 2.81, "I_in4": 4.79, "r_in": 1.305}',
         'ASTM A53 Grade B')
        ON CONFLICT (material_id) DO NOTHING
        """
    )
    
    # Seed code references
    op.execute(
        """
        INSERT INTO code_references (ref_id, code, section, title, formula, application) VALUES
        ('ASCE_7_16_26_10_1', 'ASCE 7-16', '26.10.1', 'Basic wind speed V mapping',
         '{"type": "lookup_table", "ref": "Figure 26.5-1"}',
         'Wind speed map determination by location'),
        ('ASCE_7_16_29_5', 'ASCE 7-16', '29.5', 'Sign wind loads',
         '{"type": "formula", "expr": "qp * GCp"}',
         'Net design wind pressure for signs'),
        ('AISC_360_F2_2', 'AISC 360', 'F2.2', 'Nominal flexural strength Mn',
         '{"type": "formula", "expr": "Mp = Fy * Zx"}',
         'Plastic moment for compact sections'),
        ('ACI_318_22_2_2', 'ACI 318-19', '22.2.2', 'Nominal shear strength',
         '{"type": "formula", "expr": "Vn = Vc + Vs"}',
         'Shear strength for concrete members'),
        ('BROMS_1964', 'Broms', '1964', 'Lateral capacity of piles',
         '{"type": "empirical", "ref": "soil-pile interaction"}',
         'Direct burial foundation design')
        ON CONFLICT (ref_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM code_references")
    op.execute("DELETE FROM material_catalog")
    op.execute("DELETE FROM pricing_configs")
    op.execute("DELETE FROM calibration_constants")

