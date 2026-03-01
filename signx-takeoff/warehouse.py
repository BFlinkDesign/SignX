"""
warehouse.py -- Warehouse benchmarking against historical job data.

Loads so_contracts_parsed.csv (25,400 rows) and provides benchmark
comparisons: "ABC says X hours, similar jobs averaged Y +/- Z hours".

Supports any sign type via expand_sign_type() from sign_types.py.

CRITICAL: Revenue = `billing` column, NOT `quoted_price`.
"""

from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from sign_types import expand_sign_type, find_warehouse_csv, sign_type_label


@dataclass
class BenchmarkResult:
    """Historical benchmark for a job type."""
    sign_type: str
    sign_type_label: str
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


def _load_all_jobs(csv_path: Path) -> list[dict]:
    """Load all jobs with valid financial data from warehouse CSV."""
    jobs = []
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sales_code = (row.get("sales_code") or "").strip().upper()
            st = (row.get("sign_type") or "").strip().upper()

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
                "sign_type": st,
                "sales_code": sales_code,
                "labor_cost": labor_cost,
                "billing": billing,
                "total_cost": total_cost,
                "gm_pct": gm_pct,
                "description": row.get("description", ""),
            })

    return jobs


# Legacy compatibility -- kept for test_validation.py source inspection
def _load_channel_letter_jobs(csv_path: Path) -> list[dict]:
    """Load channel letter jobs from warehouse CSV."""
    channel_codes = expand_sign_type("CHANNEL_LETTER")
    all_jobs = _load_all_jobs(csv_path)
    return [
        j for j in all_jobs
        if j["sales_code"] in channel_codes
        or j["sign_type"] in channel_codes
        or "CHANNEL" in j["description"].upper()
    ]


_cache: dict[str, list[dict]] = {}


def _get_cached_jobs() -> list[dict] | None:
    """Load and cache all warehouse jobs. Returns None if CSV unavailable."""
    csv_path = find_warehouse_csv()
    if csv_path is None:
        return None

    cache_key = str(csv_path)
    if cache_key not in _cache:
        _cache[cache_key] = _load_all_jobs(csv_path)

    return _cache[cache_key]


def benchmark(abc_estimate_hours: float,
              sign_type_filter: str = "CHANNEL_LETTER") -> BenchmarkResult | None:
    """
    Compare an ABC estimate against historical warehouse data.

    Args:
        abc_estimate_hours: ABC engine's estimated hours for the job.
        sign_type_filter: Sign type code or group name (e.g. "CLLIT",
            "CHANNEL_LETTER", "MONUMENT"). Uses expand_sign_type() to
            match all related codes.

    Returns benchmark with statistics from similar jobs, or None if
    warehouse data is unavailable or insufficient matches.
    """
    all_jobs = _get_cached_jobs()
    if all_jobs is None:
        return None

    # Expand the filter to all related codes
    match_codes = expand_sign_type(sign_type_filter)

    # Filter jobs matching this sign type
    jobs = [
        j for j in all_jobs
        if j["sales_code"] in match_codes
        or j["sign_type"] in match_codes
    ]

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
        sign_type_label=sign_type_label(sign_type_filter),
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
