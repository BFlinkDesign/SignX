#!/usr/bin/env python3
"""
Seed Default Calibration Constants and Pricing
"""

from __future__ import annotations

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build database URL from environment variables
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "signx_studio")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


import os
import sys

try:
    import psycopg2
import logging

logger = logging.getLogger(__name__)
except ImportError:
    logger.error("ERROR: Install psycopg2-binary: pip install psycopg2-binary")
    sys.exit(1)


def seed_calib_constants(cur):
    """Insert calibration constants with sources and versions."""
    constants = [
        {
            "name": "K_footing",
            "value": 1.0,
            "source": "Enercalc v10 + USDA empirical proxy",
            "version": "v1",
            "notes": "Dimensionally consistent constant for direct burial footing depth calculation",
        },
        {
            "name": "phi_bending",
            "value": 0.9,
            "source": "AISC 360-16 Specification for Structural Steel Buildings",
            "version": "v1",
            "notes": "Resistance factor for flexural yielding of steel members",
        },
        {
            "name": "Fexx_weld",
            "value": 70.0,
            "source": "AWS D1.1 Structural Welding Code",
            "version": "v1",
            "notes": "E70XX electrode strength (ksi) for fillet welds",
        },
        {
            "name": "load_factor_wind",
            "value": 1.6,
            "source": "ASCE 7-22 Load Combinations (Strength Design)",
            "version": "v1",
            "notes": "Load factor for wind loads in ultimate strength design",
        },
        {
            "name": "soil_bearing_default_psf",
            "value": 3000.0,
            "source": "Typical clay/medium density soil (engineering judgment)",
            "version": "v1",
            "notes": "Default allowable bearing pressure; user should override with geotech data",
        },
    ]

    for c in constants:
        cur.execute(
            """
            INSERT INTO calib_constants (name, value, source, version, notes)
            VALUES (%(name)s, %(value)s, %(source)s, %(version)s, %(notes)s)
            ON CONFLICT (name) DO UPDATE SET
                value = EXCLUDED.value,
                source = EXCLUDED.source,
                version = EXCLUDED.version,
                notes = EXCLUDED.notes
            """,
            c,
        )

    logger.info(f"✓ Seeded {len(constants)} calibration constants")


def seed_pricing(cur):
    """Insert pricing table v1."""
    pricing = [
        {
            "code": "base_<=25ft",
            "label": "Engineering ≤25 ft",
            "amount_usd": 200.0,
            "version": "v1",
            "active": True,
        },
        {
            "code": "base_>25ft",
            "label": "Engineering >25 ft",
            "amount_usd": 300.0,
            "version": "v1",
            "active": True,
        },
        {
            "code": "calc_packet",
            "label": "Formal Calculation Packet",
            "amount_usd": 35.0,
            "version": "v1",
            "active": True,
        },
        {
            "code": "hard_copies",
            "label": "Hard Copies",
            "amount_usd": 30.0,
            "version": "v1",
            "active": True,
        },
    ]

    for p in pricing:
        cur.execute(
            """
            INSERT INTO config_pricing (code, label, amount_usd, version, active)
            VALUES (%(code)s, %(label)s, %(amount_usd)s, %(version)s, %(active)s)
            ON CONFLICT (code) DO UPDATE SET
                label = EXCLUDED.label,
                amount_usd = EXCLUDED.amount_usd,
                version = EXCLUDED.version,
                active = EXCLUDED.active
            """,
            p,
        )

    logger.info(f"✓ Seeded {len(pricing)} pricing items")


def main():
    db_url = os.environ.get("DATABASE_URL", f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        seed_calib_constants(cur)
        seed_pricing(cur)
        conn.commit()
        logger.info("\n✓ All defaults seeded successfully")
    except Exception as e:
        conn.rollback()
        logger.error(f"\n✗ Error: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()

