"""
warehouse.py — Warehouse benchmarking against historical job data.

Loads so_contracts_parsed.csv (25,400 rows) and provides benchmark
comparisons: "ABC says X hours, similar jobs averaged Y +/- Z hours".

CRITICAL: Revenue = `billing` column, NOT `quoted_price`.
"""

from __future__ import annotations

import csv
import os
import statistics
from dataclasses import dataclass, field
from pathlib import Path

# Path to warehouse CSV (try multiple locations)
WAREHOUSE_PATHS = [
    Path(r"C:\Scripts\signx-warehouse\warehouse\raw\so_contracts_parsed.csv"),
    Path(r"C:\Scripts\SignX\Keyedin\warehouse\warehouse\raw\so_contracts_parsed.csv"),
]


@dataclass
class BenchmarkResult:
    """Historical benchmark for a job type."""
    sign_type: str
    matching_jobs: int
    avg_labor_hours: float
    median_labor_hours: float
    std_dev: float
    min_hours: float
    max_hours: float
    avg_revenue: float
    avg_margin_pct: float
    confidence: str  # "high", "medium", "low"
    similar_jobs: list[dict] = field(default_factory=list)


def _find_warehouse_csv() -> Path | None:
    for p in WAREHOUSE_PATHS:
        if p.exists():
            return p
    return None


def _load_channel_letter_jobs(csv_path: Path) -> list[dict]:
    """Load channel letter jobs from warehouse CSV."""
    jobs = []
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Filter for channel letter sales codes
            sales_code = (row.get("sales_code") or "").strip().upper()
            sign_type = (row.get("sign_type") or "").strip().upper()

            is_channel = (
                sales_code in ("CHANNL", "CHANL", "CHNL", "CHLET")
                or "CLLIT" in sign_type
                or "CLNON" in sign_type
                or "CHANNEL" in (row.get("description") or "").upper()
            )

            if not is_channel:
                continue

            try:
                labor_cost = float(row.get("labor_cost") or 0)
                billing = float(row.get("billing") or 0)
                total_cost = float(row.get("total_cost") or 0)
                gm_pct_raw = row.get("gm_percent") or ""
                gm_pct = float(gm_pct_raw) if gm_pct_raw else 0.0
            except (ValueError, TypeError):
                continue

            if labor_cost <= 0 and billing <= 0:
                continue

            jobs.append({
                "work_order": row.get("work_order", ""),
                "customer": row.get("customer_name", ""),
                "location": row.get("location", ""),
                "sign_type": sign_type,
                "sales_code": sales_code,
                "labor_cost": labor_cost,
                "billing": billing,
                "total_cost": total_cost,
                "gm_pct": gm_pct,
                "description": row.get("description", ""),
            })

    return jobs


_cache: dict[str, list[dict]] = {}


def benchmark(abc_estimate_hours: float,
              sign_type_filter: str = "CHANNL") -> BenchmarkResult | None:
    """
    Compare an ABC estimate against historical warehouse data.

    Returns benchmark with statistics from similar jobs, or None if
    warehouse data is unavailable.
    """
    csv_path = _find_warehouse_csv()
    if csv_path is None:
        return None

    cache_key = str(csv_path)
    if cache_key not in _cache:
        _cache[cache_key] = _load_channel_letter_jobs(csv_path)

    jobs = _cache[cache_key]

    if not jobs:
        return None

    # Extract labor hours from cost (using implied rate from warehouse)
    # Average implied rate from ABC guide is ~$40/hr
    IMPLIED_RATE = 40.0

    labor_hours_list = []
    revenue_list = []
    margin_list = []
    similar = []

    for job in jobs:
        est_hours = job["labor_cost"] / IMPLIED_RATE if job["labor_cost"] > 0 else 0
        if est_hours <= 0:
            continue

        labor_hours_list.append(est_hours)
        if job["billing"] > 0:
            revenue_list.append(job["billing"])
        if job["gm_pct"] != 0:
            margin_list.append(job["gm_pct"])

        similar.append({
            "wo": job["work_order"],
            "customer": job["customer"],
            "hours_est": round(est_hours, 1),
            "revenue": round(job["billing"], 2),
            "gm": round(job["gm_pct"], 1),
        })

    if len(labor_hours_list) < 3:
        return None

    avg_hrs = statistics.mean(labor_hours_list)
    median_hrs = statistics.median(labor_hours_list)
    std_dev = statistics.stdev(labor_hours_list) if len(labor_hours_list) > 1 else 0

    # Confidence based on sample size
    n = len(labor_hours_list)
    if n >= 50:
        confidence = "high"
    elif n >= 15:
        confidence = "medium"
    else:
        confidence = "low"

    return BenchmarkResult(
        sign_type=sign_type_filter,
        matching_jobs=n,
        avg_labor_hours=round(avg_hrs, 1),
        median_labor_hours=round(median_hrs, 1),
        std_dev=round(std_dev, 1),
        min_hours=round(min(labor_hours_list), 1),
        max_hours=round(max(labor_hours_list), 1),
        avg_revenue=round(statistics.mean(revenue_list), 2) if revenue_list else 0,
        avg_margin_pct=round(statistics.mean(margin_list), 1) if margin_list else 0,
        confidence=confidence,
        similar_jobs=sorted(similar, key=lambda x: abs(x["hours_est"] - abc_estimate_hours))[:10],
    )
