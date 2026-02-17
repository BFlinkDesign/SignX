"""
calibrate.py — Auto-Calibration Engine for ABC Estimators.

Queries signx.duckdb warehouse data and produces calibration.json
consumed by abc_engine.py. Replaces all hardcoded P50/correction/OT values.

Three-tier calibration:
  Tier 1: Warehouse P50 x buffer (primary — crew-specific, recalibratable)
  Tier 2: ABC formula fallback (crew-independent, for sign types with no data)
  Tier 3: Industry benchmark rails (sanity-check bounds from ISA/Signs101 research)

Usage:
  python calibrate.py                  # Full recalibration from warehouse
  python calibrate.py --dry-run        # Preview without writing
  python calibrate.py --sign-type CLLIT  # Single sign type only

Called from:
  - app.py POST /api/calibrate (manual trigger from UI)
  - Startup check (if calibration.json missing or stale)
  - Scheduled task (future: weekly auto-recalibrate)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

WAREHOUSE_DB = os.environ.get(
    "SIGNX_WAREHOUSE_DB",
    "C:/Scripts/signx-warehouse/warehouse/signx.duckdb",
)
CALIBRATION_DIR = Path(__file__).parent / "data"
CALIBRATION_FILE = CALIBRATION_DIR / "calibration.json"
RAW_MATRIX_FILE = CALIBRATION_DIR / "calibration_matrix_raw.json"

# Buffer multiplier: P50 * BUFFER = floor value
# 1.20 = 20% buffer above median (conservative: wins 60% of the time)
BUFFER = 1.20

# Minimum sample size for "confident" calibration
MIN_SAMPLES_CONFIDENT = 10
MIN_SAMPLES_USABLE = 3

# OT detection: work codes that indicate overtime
OT_FAB_CODES = {"9200"}       # Fabrication OT
OT_INSTALL_CODES = {"9600"}   # Installation OT

# Install work codes (for install floor computation)
INSTALL_CODES = {"0630", "0640", "0650"}  # 1-man, 2-man, 3-man install

# Removal work code
REMOVAL_CODE = "0625"

# Travel work code
TRAVEL_CODE = "0620"

# Industry benchmark rails (from research: ISA, Signs101, vendor guides)
# Format: {sign_type: {work_code: (min_hours, max_hours)}}
# If a warehouse P50 falls outside these rails, flag a warning.
INDUSTRY_RAILS: dict[str, dict[str, tuple[float, float]]] = {
    "CLLIT": {
        "0630": (3.0, 10.0),    # CL install: 3-5 hrs industry (2-crew)
        "0625": (1.0, 6.0),     # CL removal: 1-4 hrs industry
    },
    "MONDF": {
        "0630": (2.0, 16.0),    # Monument install: 4-8 hrs industry
        "0625": (1.0, 6.0),     # Monument removal
    },
    "POLLIT": {
        "0650": (4.0, 12.0),    # Pylon install: 4-8 hrs + crane
        "0625": (2.0, 8.0),     # Pylon removal: 2-4 hrs + crane
    },
    "AWNNON": {
        "0630": (4.0, 12.0),    # Awning install: 4-8 hrs
    },
    "GEMINI": {
        "0630": (2.0, 8.0),     # Dimensional letters: simpler install
    },
}


# ---------------------------------------------------------------------------
# Core calibration logic
# ---------------------------------------------------------------------------

def query_calibration_matrix(
    db_path: str = WAREHOUSE_DB,
    sign_type_filter: str | None = None,
) -> dict[str, dict[str, dict[str, Any]]]:
    """
    Query warehouse for full (sign_type x work_code) calibration matrix.

    Returns:
        {sign_type: {work_code: {n, p25, p50, p75, mean, std}}}
    """
    import duckdb

    con = duckdb.connect(db_path, read_only=True)

    where_clause = """
        WHERE l.actual_hours > 0
          AND c.sign_type IS NOT NULL
          AND c.sign_type != ''
    """
    if sign_type_filter:
        where_clause += f" AND c.sign_type = '{sign_type_filter}'"

    rows = con.execute(f"""
        SELECT
            c.sign_type,
            l.work_code,
            COUNT(*) as n,
            ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY l.actual_hours), 2) as p25,
            ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY l.actual_hours), 2) as p50,
            ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY l.actual_hours), 2) as p75,
            ROUND(AVG(l.actual_hours), 2) as mean,
            ROUND(STDDEV(l.actual_hours), 2) as std
        FROM so_contract_labor l
        JOIN so_contracts c ON l.wo_number = c.work_order
        {where_clause}
        GROUP BY c.sign_type, l.work_code
        HAVING COUNT(*) >= {MIN_SAMPLES_USABLE}
        ORDER BY c.sign_type, n DESC
    """).fetchall()

    con.close()

    matrix: dict[str, dict[str, dict[str, Any]]] = {}
    for r in rows:
        st = r[0]
        if st not in matrix:
            matrix[st] = {}
        matrix[st][r[1]] = {
            "n": r[2],
            "p25": float(r[3]),
            "p50": float(r[4]),
            "p75": float(r[5]),
            "mean": float(r[6]),
            "std": float(r[7]) if r[7] is not None else 0.0,
        }

    return matrix


def compute_ot_factors(
    db_path: str = WAREHOUSE_DB,
) -> dict[str, dict[str, Any]]:
    """
    Compute overtime probability and mean hours for each sign type.

    Returns:
        {sign_type: {
            fab_ot_probability, fab_ot_mean,
            install_ot_probability, install_ot_mean,
            expected_total
        }}
    """
    import duckdb

    con = duckdb.connect(db_path, read_only=True)

    # Get total job count per sign type
    job_counts = {}
    for row in con.execute("""
        SELECT c.sign_type, COUNT(DISTINCT l.wo_number) as n
        FROM so_contract_labor l
        JOIN so_contracts c ON l.wo_number = c.work_order
        WHERE c.sign_type IS NOT NULL AND c.sign_type != ''
        GROUP BY c.sign_type
        HAVING COUNT(DISTINCT l.wo_number) >= 10
    """).fetchall():
        job_counts[row[0]] = row[1]

    # Get OT occurrence counts and mean hours
    ot_data: dict[str, dict[str, Any]] = {}

    for st, total_n in job_counts.items():
        ot_data[st] = {}

        # Fab OT (9200)
        fab_row = con.execute(f"""
            SELECT COUNT(DISTINCT l.wo_number) as n_jobs,
                   ROUND(AVG(l.actual_hours), 2) as avg_hrs,
                   ROUND(MEDIAN(l.actual_hours), 2) as med_hrs
            FROM so_contract_labor l
            JOIN so_contracts c ON l.wo_number = c.work_order
            WHERE c.sign_type = '{st}'
              AND l.work_code = '9200'
              AND l.actual_hours > 0
        """).fetchone()

        fab_n = fab_row[0] if fab_row else 0
        fab_avg = float(fab_row[1]) if fab_row and fab_row[1] else 0.0
        fab_prob = round(fab_n / total_n, 3) if total_n > 0 else 0.0

        # Install OT (9600)
        inst_row = con.execute(f"""
            SELECT COUNT(DISTINCT l.wo_number) as n_jobs,
                   ROUND(AVG(l.actual_hours), 2) as avg_hrs,
                   ROUND(MEDIAN(l.actual_hours), 2) as med_hrs
            FROM so_contract_labor l
            JOIN so_contracts c ON l.wo_number = c.work_order
            WHERE c.sign_type = '{st}'
              AND l.work_code = '9600'
              AND l.actual_hours > 0
        """).fetchone()

        inst_n = inst_row[0] if inst_row else 0
        inst_avg = float(inst_row[1]) if inst_row and inst_row[1] else 0.0
        inst_prob = round(inst_n / total_n, 3) if total_n > 0 else 0.0

        expected = round(fab_prob * fab_avg + inst_prob * inst_avg, 2)

        ot_data[st] = {
            "total_jobs": total_n,
            "fab_ot_probability": fab_prob,
            "fab_ot_mean": fab_avg,
            "install_ot_probability": inst_prob,
            "install_ot_mean": inst_avg,
            "expected_total": expected,
        }

    con.close()
    return ot_data


def build_calibration(
    matrix: dict[str, dict[str, dict[str, Any]]],
    ot_factors: dict[str, dict[str, Any]],
    buffer: float = BUFFER,
) -> dict[str, Any]:
    """
    Build calibration.json from raw matrix + OT factors.

    Produces:
      - install_floors: {sign_type: {value, p50, n, confidence}}
      - removal_floors: {sign_type: {value, p50, n, confidence}}
      - ot_factors: {sign_type: {fab_prob, fab_mean, inst_prob, inst_mean, expected}}
      - work_code_medians: {sign_type: {work_code: {p50, n, confidence}}}
      - correction_factors: {sign_type: {work_code: {factor, wh_median, n, confidence}}}
      - metadata: {date, buffer, db_path, total_sign_types, total_cells, warnings}
    """
    warnings: list[str] = []
    install_floors: dict[str, dict[str, Any]] = {}
    removal_floors: dict[str, dict[str, Any]] = {}
    work_code_medians: dict[str, dict[str, dict[str, Any]]] = {}
    travel_medians: dict[str, dict[str, Any]] = {}

    for st, codes in matrix.items():
        # -- Install floor: best install code (0630 > 0640 > 0650)
        for ic in ["0630", "0640", "0650"]:
            if ic in codes:
                data = codes[ic]
                p50 = data["p50"]
                n = data["n"]
                confidence = (
                    "HIGH" if n >= MIN_SAMPLES_CONFIDENT
                    else "MEDIUM" if n >= MIN_SAMPLES_USABLE
                    else "LOW"
                )
                floor_val = round(p50 * buffer, 2)

                # Check industry rails
                rails = INDUSTRY_RAILS.get(st, {}).get(ic)
                if rails and (p50 < rails[0] or p50 > rails[1]):
                    warnings.append(
                        f"RAIL WARNING: {st}/{ic} P50={p50}h outside "
                        f"industry range [{rails[0]}-{rails[1]}h]"
                    )

                install_floors[st] = {
                    "value": floor_val,
                    "p50": p50,
                    "n": n,
                    "confidence": confidence,
                    "install_code": ic,
                    "formula": f"P50({p50}) x {buffer} = {floor_val}",
                }
                break

        # -- Removal floor
        if REMOVAL_CODE in codes:
            data = codes[REMOVAL_CODE]
            p50 = data["p50"]
            n = data["n"]
            confidence = (
                "HIGH" if n >= MIN_SAMPLES_CONFIDENT
                else "MEDIUM" if n >= MIN_SAMPLES_USABLE
                else "LOW"
            )
            floor_val = round(p50 * buffer, 2)

            rails = INDUSTRY_RAILS.get(st, {}).get(REMOVAL_CODE)
            if rails and (p50 < rails[0] or p50 > rails[1]):
                warnings.append(
                    f"RAIL WARNING: {st}/{REMOVAL_CODE} P50={p50}h outside "
                    f"industry range [{rails[0]}-{rails[1]}h]"
                )

            removal_floors[st] = {
                "value": floor_val,
                "p50": p50,
                "n": n,
                "confidence": confidence,
                "formula": f"P50({p50}) x {buffer} = {floor_val}",
            }

        # -- Travel median
        if TRAVEL_CODE in codes:
            data = codes[TRAVEL_CODE]
            travel_medians[st] = {
                "p50": data["p50"],
                "n": data["n"],
                "confidence": (
                    "HIGH" if data["n"] >= MIN_SAMPLES_CONFIDENT
                    else "MEDIUM" if data["n"] >= MIN_SAMPLES_USABLE
                    else "LOW"
                ),
            }

        # -- All work code medians
        work_code_medians[st] = {}
        for wc, data in codes.items():
            work_code_medians[st][wc] = {
                "p50": data["p50"],
                "p25": data["p25"],
                "p75": data["p75"],
                "mean": data["mean"],
                "std": data["std"],
                "n": data["n"],
                "confidence": (
                    "HIGH" if data["n"] >= MIN_SAMPLES_CONFIDENT
                    else "MEDIUM" if data["n"] >= MIN_SAMPLES_USABLE
                    else "LOW"
                ),
            }

    # Compute overall defaults
    all_install_p50s = [v["p50"] for v in install_floors.values()]
    all_removal_p50s = [v["p50"] for v in removal_floors.values()]

    overall_install_p50 = round(
        sorted(all_install_p50s)[len(all_install_p50s) // 2], 2
    ) if all_install_p50s else 4.0

    overall_removal_p50 = round(
        sorted(all_removal_p50s)[len(all_removal_p50s) // 2], 2
    ) if all_removal_p50s else 2.0

    calibration = {
        "metadata": {
            "calibration_date": datetime.now(timezone.utc).isoformat(),
            "buffer_multiplier": buffer,
            "min_samples_confident": MIN_SAMPLES_CONFIDENT,
            "min_samples_usable": MIN_SAMPLES_USABLE,
            "warehouse_db": WAREHOUSE_DB,
            "total_sign_types": len(matrix),
            "total_cells": sum(len(v) for v in matrix.values()),
            "warnings": warnings,
            "version": "1.0.0",
        },
        "defaults": {
            "install_floor": round(overall_install_p50 * buffer, 2),
            "install_p50": overall_install_p50,
            "removal_floor": round(overall_removal_p50 * buffer, 2),
            "removal_p50": overall_removal_p50,
        },
        "install_floors": install_floors,
        "removal_floors": removal_floors,
        "travel_medians": travel_medians,
        "ot_factors": ot_factors,
        "work_code_medians": work_code_medians,
    }

    return calibration


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def recalibrate(
    db_path: str = WAREHOUSE_DB,
    sign_type: str | None = None,
    buffer: float = BUFFER,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Run full recalibration from warehouse data.

    Args:
        db_path: Path to signx.duckdb
        sign_type: If set, recalibrate only this sign type
        buffer: Multiplier for P50 -> floor (default 1.20)
        dry_run: If True, return calibration without writing to disk

    Returns:
        calibration dict (also written to calibration.json unless dry_run)
    """
    print(f"[calibrate] Querying warehouse: {db_path}")
    matrix = query_calibration_matrix(db_path, sign_type)
    print(f"[calibrate] Matrix: {len(matrix)} sign types, "
          f"{sum(len(v) for v in matrix.values())} cells")

    print("[calibrate] Computing OT factors...")
    ot_factors = compute_ot_factors(db_path)
    print(f"[calibrate] OT factors for {len(ot_factors)} sign types")

    print("[calibrate] Building calibration...")
    calibration = build_calibration(matrix, ot_factors, buffer)

    if calibration["metadata"]["warnings"]:
        for w in calibration["metadata"]["warnings"]:
            print(f"[calibrate] WARNING: {w}")

    # If recalibrating a single sign type, merge into existing calibration
    if sign_type and not dry_run and CALIBRATION_FILE.exists():
        existing = json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))
        for section in [
            "install_floors", "removal_floors", "travel_medians",
            "ot_factors", "work_code_medians",
        ]:
            if sign_type in calibration.get(section, {}):
                if section not in existing:
                    existing[section] = {}
                existing[section][sign_type] = calibration[section][sign_type]
        existing["metadata"]["calibration_date"] = calibration["metadata"]["calibration_date"]
        existing["metadata"]["warnings"] = calibration["metadata"]["warnings"]
        calibration = existing

    if not dry_run:
        CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)
        CALIBRATION_FILE.write_text(
            json.dumps(calibration, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"[calibrate] Written to {CALIBRATION_FILE}")

        # Also save raw matrix
        RAW_MATRIX_FILE.write_text(
            json.dumps(matrix, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"[calibrate] Raw matrix saved to {RAW_MATRIX_FILE}")

    return calibration


def load_calibration() -> dict[str, Any]:
    """
    Load calibration.json. If missing or stale (>7 days), trigger recalibration.
    Returns the calibration dict consumed by abc_engine.py.
    """
    if CALIBRATION_FILE.exists():
        cal = json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))

        # Check staleness
        cal_date_str = cal.get("metadata", {}).get("calibration_date", "")
        if cal_date_str:
            try:
                cal_date = datetime.fromisoformat(cal_date_str)
                age_days = (datetime.now(timezone.utc) - cal_date).days
                if age_days > 7:
                    print(f"[calibrate] Calibration is {age_days} days old. "
                          "Consider running recalibrate().")
            except (ValueError, TypeError):
                pass

        return cal

    # No calibration file — try to generate
    print("[calibrate] No calibration.json found. Attempting recalibration...")
    if os.path.exists(WAREHOUSE_DB):
        return recalibrate()
    else:
        print(f"[calibrate] Warehouse not found at {WAREHOUSE_DB}. "
              "Using empty calibration (abc_engine will use hardcoded defaults).")
        return {"metadata": {"error": "no_warehouse"}}


def get_floor(
    cal: dict[str, Any],
    floor_type: str,
    sign_type: str,
) -> tuple[float, str, str]:
    """
    Get a floor value from calibration data.

    Args:
        cal: Loaded calibration dict
        floor_type: "install_floors" or "removal_floors"
        sign_type: Sign type code (e.g., "CLLIT")

    Returns:
        (value, confidence, formula) tuple
    """
    floors = cal.get(floor_type, {})
    if sign_type in floors:
        f = floors[sign_type]
        return f["value"], f["confidence"], f["formula"]

    # Fallback to default
    defaults = cal.get("defaults", {})
    if floor_type == "install_floors":
        default_val = defaults.get("install_floor", 4.80)
        return default_val, "DEFAULT", f"Overall default = {default_val}h"
    else:
        default_val = defaults.get("removal_floor", 2.40)
        return default_val, "DEFAULT", f"Overall default = {default_val}h"


def get_work_code_median(
    cal: dict[str, Any],
    sign_type: str,
    work_code: str,
) -> tuple[float | None, int, str]:
    """
    Get warehouse median for a specific sign_type + work_code.

    Returns:
        (p50_or_None, n, confidence)
    """
    medians = cal.get("work_code_medians", {})
    if sign_type in medians and work_code in medians[sign_type]:
        d = medians[sign_type][work_code]
        return d["p50"], d["n"], d["confidence"]
    return None, 0, "NONE"


def get_ot_factor(
    cal: dict[str, Any],
    sign_type: str,
) -> tuple[float, float, float, float, float]:
    """
    Get OT factors for a sign type.

    Returns:
        (fab_prob, fab_mean, inst_prob, inst_mean, expected_total)
    """
    ot = cal.get("ot_factors", {}).get(sign_type, {})
    return (
        ot.get("fab_ot_probability", 0.0),
        ot.get("fab_ot_mean", 0.0),
        ot.get("install_ot_probability", 0.0),
        ot.get("install_ot_mean", 0.0),
        ot.get("expected_total", 0.0),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    """CLI entry point for manual recalibration."""
    import argparse

    parser = argparse.ArgumentParser(description="SignX ABC Engine Calibration")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--sign-type", type=str, help="Recalibrate single sign type")
    parser.add_argument("--buffer", type=float, default=BUFFER, help=f"Buffer multiplier (default {BUFFER})")
    parser.add_argument("--db", type=str, default=WAREHOUSE_DB, help="Warehouse DB path")
    parser.add_argument("--summary", action="store_true", help="Print calibration summary")
    args = parser.parse_args()

    cal = recalibrate(
        db_path=args.db,
        sign_type=args.sign_type,
        buffer=args.buffer,
        dry_run=args.dry_run,
    )

    if args.summary or args.dry_run:
        print("\n" + "=" * 70)
        print("CALIBRATION SUMMARY")
        print("=" * 70)

        print(f"\nDate: {cal['metadata']['calibration_date']}")
        print(f"Sign types: {cal['metadata']['total_sign_types']}")
        print(f"Total cells: {cal['metadata']['total_cells']}")
        print(f"Buffer: {cal['metadata']['buffer_multiplier']}x")

        print("\n-- Install Floors ------------------------------------")
        for st, data in sorted(cal.get("install_floors", {}).items()):
            conf_tag = f"[{data['confidence']}]"
            print(f"  {st:10s} {data['value']:6.2f}h  "
                  f"(P50={data['p50']:.2f}, n={data['n']:4d}) {conf_tag}")

        print("\n-- Removal Floors ------------------------------------")
        for st, data in sorted(cal.get("removal_floors", {}).items()):
            conf_tag = f"[{data['confidence']}]"
            print(f"  {st:10s} {data['value']:6.2f}h  "
                  f"(P50={data['p50']:.2f}, n={data['n']:4d}) {conf_tag}")

        print("\n-- OT Factors ----------------------------------------")
        for st, data in sorted(cal.get("ot_factors", {}).items()):
            fab_p = data.get("fab_ot_probability", 0)
            inst_p = data.get("install_ot_probability", 0)
            exp = data.get("expected_total", 0)
            print(f"  {st:10s} Fab={fab_p:.1%} Install={inst_p:.1%} "
                  f"Expected={exp:.1f}h (n={data.get('total_jobs', 0)})")

        defaults = cal.get("defaults", {})
        print(f"\n-- Defaults ------------------------------------------")
        print(f"  Install default: {defaults.get('install_floor', '?')}h")
        print(f"  Removal default: {defaults.get('removal_floor', '?')}h")

        if cal["metadata"]["warnings"]:
            print(f"\n-- Warnings ({len(cal['metadata']['warnings'])}) --------")
            for w in cal["metadata"]["warnings"]:
                print(f"  ! {w}")


if __name__ == "__main__":
    main()
