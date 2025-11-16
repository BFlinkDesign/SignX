#!/usr/bin/env python3
"""
Seed AISC Steel Sections Database
Download v16.0 from: https://www.aisc.org/resources/shapes-database/
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


import csv
import hashlib
import sys
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    logger.error("ERROR: Install psycopg2-binary: pip install psycopg2-binary")
    sys.exit(1)


def sha256(content: str) -> str:
    """Compute SHA256 hash of string content."""
    return hashlib.sha256(content.encode()).hexdigest()


def load_aisc_csv(csv_path: str) -> list[dict]:
    """Load AISC shapes CSV and return filtered HSS/Pipe rows."""
    rows = []
    with open(csv_path, encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Filter relevant types
            if row.get("Type", "") in {"HSS", "Pipe", "W"}:
                rows.append(row)
    return rows


def normalize_row(row: dict, edition: str = "V16.0") -> dict:
    """Convert CSV row to DB schema format."""
    return {
        "type": row.get("Type", "").strip(),
        "edition": edition,
        "shape": row.get("Shape", "").strip(),
        "w_lbs_per_ft": float(row.get("W", 0) or 0),
        "a_in2": float(row.get("A", 0) or 0),
        "d_in": float(row.get("d", 0) or 0) if row.get("d") else None,
        "t_in": float(row.get("t", 0) or 0) if row.get("t") else None,
        "ix_in4": float(row.get("Ix", 0) or 0),
        "sx_in3": float(row.get("Sx", 0) or 0),
        "rx_in": float(row.get("rx", 0) or 0),
        "zx_in3": float(row.get("Zx", 0) or 0),
        "fy_ksi": float(row.get("Fy", 46.0) or 46.0),
        "grade": row.get("Grade", "A500B").strip(),
    }


def main():
    import os
import logging

logger = logging.getLogger(__name__)

    # Configuration
    db_url = os.environ.get("DATABASE_URL", f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    csv_path = os.environ.get("AISC_CSV_PATH", "data/aisc-shapes-v16.csv")

    if not Path(csv_path).exists():
        logger.error(f"ERROR: AISC CSV not found at {csv_path}")
        logger.info("Download from: https://www.aisc.org/resources/shapes-database/")
        sys.exit(1)

    # Load and normalize
    logger.info(f"Loading AISC CSV: {csv_path}")
    raw = load_aisc_csv(csv_path)
    normalized = [normalize_row(r) for r in raw]
    logger.info(f"Loaded {len(normalized)} sections")

    # DB Insert
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Truncate and reload
    cur.execute("TRUNCATE TABLE pole_sections RESTART IDENTITY CASCADE;")

    # Batch insert
    cols = [
        "type",
        "edition",
        "shape",
        "w_lbs_per_ft",
        "a_in2",
        "d_in",
        "t_in",
        "ix_in4",
        "sx_in3",
        "rx_in",
        "zx_in3",
        "fy_ksi",
        "grade",
    ]
    tuples = [(row[c] for c in cols) for row in normalized]

    execute_values(cur, f"INSERT INTO pole_sections ({','.join(cols)}) VALUES %s", tuples)

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f"✓ Inserted {len(normalized)} pole sections into database")


if __name__ == "__main__":
    main()

