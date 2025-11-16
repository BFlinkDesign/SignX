#!/usr/bin/env python3
"""Seed default calibration constants."""

import os
import sys
from datetime import date
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text

# Import psycopg2 for synchronous database operations
import psycopg2
import logging

logger = logging.getLogger(__name__)


def seed_constants():
    """Seed calibration constants and defaults."""
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://apex:apex@localhost:5432/apex"
    )
    
    constants = [
        ("K_footing_direct_burial", "v1", 1.5, "dimensionless", "Eagle Sign calibration 2023", "AISC 360 + site calibration", date(2025, 1, 1)),
        ("phi_bending", "v1", 0.9, "dimensionless", "AISC 360-16 Section F1", "AISC 360-16 F1.1", date(2025, 1, 1)),
        ("weld_fexx", "v1", 70.0, "ksi", "E70XX electrode standard", "AWS D1.1", date(2025, 1, 1)),
        ("soil_bearing_default_iowa", "v1", 2000.0, "psf", "Iowa soil typical", "ASCE 7-16 12.7.1", date(2025, 1, 1)),
        ("K_FACTOR", "footing_v1", 0.15, "unitless", "Calibrated K factor for direct burial depth calculation", "ASCE 7-16 + calibration", date(2025, 1, 1)),
        ("SOIL_BEARING_DEFAULT", "footing_v1", 3000.0, "psf", "Default allowable soil bearing pressure", "ASCE 7-16 12.7.1", date(2025, 1, 1)),
        ("CONCRETE_DENSITY", "material_v1", 150.0, "pcf", "Normal weight concrete density", "ACI 318", date(2025, 1, 1)),
        ("STEEL_YIELD_A36", "material_v1", 36.0, "ksi", "A36 steel yield strength", "AISC 360", date(2025, 1, 1)),
        ("STEEL_YIELD_A572", "material_v1", 50.0, "ksi", "A572 Grade 50 yield strength", "AISC 360", date(2025, 1, 1)),
        ("STEEL_MODULUS", "material_v1", 29000.0, "ksi", "Steel modulus of elasticity", "AISC 360", date(2025, 1, 1)),
    ]
    
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        for name, version, value, unit, description, source, effective_from in constants:
            try:
                conn.execute(text("""
                    INSERT INTO calibration_constants (name, version, value, unit, description, source, effective_from)
                    VALUES (:name, :version, :value, :unit, :description, :source, :effective_from)
                    ON CONFLICT (name, version) DO UPDATE
                    SET value = EXCLUDED.value,
                        unit = EXCLUDED.unit,
                        description = EXCLUDED.description,
                        source = EXCLUDED.source,
                        effective_from = EXCLUDED.effective_from,
                        updated_at = NOW()
                """), {
                    'name': name,
                    'version': version,
                    'value': value,
                    'unit': unit,
                    'description': description,
                    'source': source,
                    'effective_from': effective_from
                })
            except Exception as e:
                logger.error(f"Warning: Failed to insert {name} v{version}: {e}")
        
        conn.commit()
        
        # Verify
        result = conn.execute(text("SELECT COUNT(*) FROM calibration_constants"))
        count = result.scalar()
        logger.info(f"✅ Seeded {count} calibration constants")


if __name__ == "__main__":
    seed_constants()

