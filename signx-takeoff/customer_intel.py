"""
customer_intel.py — Customer Intelligence Engine for Eagle Sign Co.

Mines 27,063 historical jobs from the KeyedIn warehouse to produce
actionable intelligence: customer profiles, similar job matching,
margin analysis, and risk scoring.

This is the brain of the SignX platform. No other sign company has this.
"""

from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sign_types import expand_sign_type, find_warehouse_csv

# Shared cache — load once, query many
_ALL_JOBS: list[dict] = []
_LOADED = False


def _load_warehouse():
    """Load the full warehouse into memory. Called once, cached forever."""
    global _ALL_JOBS, _LOADED
    if _LOADED:
        return

    csv_path = find_warehouse_csv()
    if not csv_path:
        _LOADED = True
        return

    jobs = []
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                billing = float(row.get("billing") or 0)
                labor_cost = float(row.get("labor_cost") or 0)
                material_cost = float(row.get("material_cost") or 0)
                total_cost = float(row.get("total_cost") or 0)
                gm_raw = row.get("gm_percent") or ""
                gm_pct = float(gm_raw) if gm_raw else 0.0
            except (ValueError, TypeError):
                continue

            jobs.append({
                "work_order": (row.get("work_order") or "").strip(),
                "customer_no": (row.get("customer_no") or "").strip(),
                "customer_name": (row.get("customer_name") or "").strip(),
                "location": (row.get("location") or "").strip(),
                "sign_type": (row.get("sign_type") or "").strip().upper(),
                "sales_code": (row.get("sales_code") or "").strip().upper(),
                "description": (row.get("description") or "").strip(),
                "quote_nbr": (row.get("quote_nbr") or "").strip(),
                "estimator": (row.get("estimator") or "").strip(),
                "date_completed": (row.get("date_completed") or "").strip(),
                "billing": billing,
                "labor_cost": labor_cost,
                "material_cost": material_cost,
                "total_cost": total_cost,
                "gm_pct": gm_pct,
            })

    _ALL_JOBS = jobs
    _LOADED = True


# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class CustomerProfile:
    """Complete intelligence profile for a customer."""
    customer_name: str
    customer_no: str
    # Volume
    total_jobs: int = 0
    total_revenue: float = 0.0
    avg_revenue_per_job: float = 0.0
    # Margins
    avg_gm_pct: float = 0.0
    margin_trend: str = ""  # "improving", "stable", "declining"
    # Sign types they buy
    sign_type_breakdown: list[dict] = field(default_factory=list)
    top_sign_type: str = ""
    # Locations
    locations: list[str] = field(default_factory=list)
    # Recency
    last_job_date: str = ""
    last_job_wo: str = ""
    months_since_last: int = 0
    # Relationship score (0-100)
    relationship_score: int = 0
    relationship_label: str = ""  # "Key Account", "Regular", "Occasional", "Dormant", "New"
    # Insights
    insights: list[str] = field(default_factory=list)
    # Recent jobs
    recent_jobs: list[dict] = field(default_factory=list)


@dataclass
class SimilarJob:
    """A historical job similar to a proposed one."""
    work_order: str
    customer: str
    location: str
    sign_type: str
    description: str
    billing: float
    labor_cost: float
    gm_pct: float
    date_completed: str
    similarity_score: float  # 0-1


@dataclass
class MarketIntel:
    """Market intelligence for a sign type."""
    sign_type: str
    total_jobs: int = 0
    avg_revenue: float = 0.0
    median_revenue: float = 0.0
    avg_gm_pct: float = 0.0
    p25_revenue: float = 0.0
    p75_revenue: float = 0.0
    top_customers: list[dict] = field(default_factory=list)


# ── Core Intelligence Functions ──────────────────────────────────────────────

def get_customer_profile(customer_name: str) -> Optional[CustomerProfile]:
    """Build a complete intelligence profile for a customer.

    Searches by customer name (fuzzy) across all 27K+ warehouse jobs.
    Returns volume, margins, sign type preferences, recency, and a
    relationship score.
    """
    _load_warehouse()
    if not _ALL_JOBS:
        return None

    # Reject empty/trivial queries
    name_lower = customer_name.lower().strip()
    if len(name_lower) < 3:
        return None

    # Strip common suffixes
    for suffix in [" inc", " inc.", " llc", " corp", " co.", " co", " ltd", ","]:
        if name_lower.endswith(suffix):
            name_lower = name_lower[: -len(suffix)].strip()

    name_words = [w for w in name_lower.split() if len(w) >= 3]
    if not name_words:
        return None

    # Score each unique customer_no against the query
    customer_jobs: dict[str, list[dict]] = {}
    for job in _ALL_JOBS:
        customer_jobs.setdefault(job["customer_no"], []).append(job)

    best_cno = None
    best_score = 0
    best_name = ""

    for cno, jobs in customer_jobs.items():
        if not jobs:
            continue
        cname = jobs[0]["customer_name"].lower()

        # Exact match
        if cname == name_lower or cname.startswith(name_lower):
            best_cno = cno
            best_name = jobs[0]["customer_name"]
            best_score = 100
            break

        # Word scoring
        score = 0
        for word in name_words:
            if word in cname:
                score += len(word)
        if name_words and name_words[0] in cname:
            score += 10

        if score > best_score:
            best_score = score
            best_cno = cno
            best_name = jobs[0]["customer_name"]

    if not best_cno or best_score < 8:
        return None

    jobs = customer_jobs[best_cno]
    profile = CustomerProfile(
        customer_name=best_name,
        customer_no=best_cno,
    )

    # Volume
    revenue_jobs = [j for j in jobs if j["billing"] > 0]
    profile.total_jobs = len(jobs)
    profile.total_revenue = sum(j["billing"] for j in revenue_jobs)
    profile.avg_revenue_per_job = (
        profile.total_revenue / len(revenue_jobs) if revenue_jobs else 0
    )

    # Margins
    margin_jobs = [j for j in jobs if j["gm_pct"] != 0 and j["billing"] > 0]
    if margin_jobs:
        profile.avg_gm_pct = round(
            statistics.mean(j["gm_pct"] for j in margin_jobs), 1
        )
        # Trend: compare first half vs second half margins
        if len(margin_jobs) >= 6:
            half = len(margin_jobs) // 2
            early_gm = statistics.mean(j["gm_pct"] for j in margin_jobs[:half])
            late_gm = statistics.mean(j["gm_pct"] for j in margin_jobs[half:])
            if late_gm > early_gm + 3:
                profile.margin_trend = "improving"
            elif late_gm < early_gm - 3:
                profile.margin_trend = "declining"
            else:
                profile.margin_trend = "stable"

    # Sign type breakdown
    type_counts: dict[str, dict] = {}
    for j in jobs:
        st = j["sign_type"] or j["sales_code"] or "OTHER"
        if st not in type_counts:
            type_counts[st] = {"count": 0, "revenue": 0.0}
        type_counts[st]["count"] += 1
        type_counts[st]["revenue"] += j["billing"]

    profile.sign_type_breakdown = sorted(
        [
            {"type": k, "count": v["count"], "revenue": round(v["revenue"], 2)}
            for k, v in type_counts.items()
        ],
        key=lambda x: x["revenue"],
        reverse=True,
    )
    if profile.sign_type_breakdown:
        profile.top_sign_type = profile.sign_type_breakdown[0]["type"]

    # Locations
    locs = set()
    for j in jobs:
        if j["location"]:
            locs.add(j["location"])
    profile.locations = sorted(locs)[:20]

    # Recency
    dates = []
    for j in jobs:
        dc = j["date_completed"]
        if dc:
            try:
                dt = datetime.strptime(dc, "%m/%d/%y")
                dates.append((dt, j["work_order"]))
            except ValueError:
                pass
    if dates:
        dates.sort(reverse=True)
        last_dt, last_wo = dates[0]
        profile.last_job_date = last_dt.strftime("%Y-%m-%d")
        profile.last_job_wo = last_wo
        now = datetime.now()
        profile.months_since_last = max(
            0, (now.year - last_dt.year) * 12 + (now.month - last_dt.month)
        )

    # Relationship score (0-100)
    score = 0
    # Volume factor (up to 30 pts)
    score += min(30, profile.total_jobs * 2)
    # Revenue factor (up to 25 pts)
    if profile.total_revenue > 100000:
        score += 25
    elif profile.total_revenue > 50000:
        score += 20
    elif profile.total_revenue > 10000:
        score += 15
    elif profile.total_revenue > 1000:
        score += 5
    # Recency factor (up to 25 pts)
    if profile.months_since_last <= 3:
        score += 25
    elif profile.months_since_last <= 6:
        score += 20
    elif profile.months_since_last <= 12:
        score += 15
    elif profile.months_since_last <= 24:
        score += 10
    else:
        score += 0
    # Margin factor (up to 20 pts)
    if profile.avg_gm_pct >= 50:
        score += 20
    elif profile.avg_gm_pct >= 40:
        score += 15
    elif profile.avg_gm_pct >= 30:
        score += 10
    elif profile.avg_gm_pct >= 20:
        score += 5

    profile.relationship_score = min(100, score)
    if score >= 75:
        profile.relationship_label = "Key Account"
    elif score >= 50:
        profile.relationship_label = "Regular"
    elif score >= 25:
        profile.relationship_label = "Occasional"
    elif profile.total_jobs > 0:
        profile.relationship_label = "Dormant"
    else:
        profile.relationship_label = "New"

    # Insights
    insights = []
    if profile.total_jobs >= 10:
        insights.append(
            f"Repeat customer: {profile.total_jobs} jobs, ${profile.total_revenue:,.0f} lifetime revenue"
        )
    if profile.avg_gm_pct >= 50:
        insights.append(f"High margin account ({profile.avg_gm_pct:.0f}% avg GM)")
    elif profile.avg_gm_pct < 30 and profile.avg_gm_pct > 0:
        insights.append(
            f"Low margin account ({profile.avg_gm_pct:.0f}% avg GM) — review pricing"
        )
    if profile.margin_trend == "declining":
        insights.append("Margin trend declining — may need to renegotiate")
    if profile.months_since_last > 12:
        insights.append(
            f"Dormant: last job {profile.months_since_last} months ago — re-engagement opportunity"
        )
    if len(profile.locations) >= 5:
        insights.append(
            f"Multi-location customer ({len(profile.locations)} sites) — program pricing opportunity"
        )
    profile.insights = insights

    # Recent jobs (last 10 with revenue)
    recent = sorted(
        [j for j in jobs if j["billing"] > 0],
        key=lambda j: j["work_order"],
        reverse=True,
    )[:10]
    profile.recent_jobs = [
        {
            "wo": j["work_order"],
            "type": j["sign_type"] or j["sales_code"],
            "description": j["description"][:80],
            "revenue": round(j["billing"], 2),
            "gm_pct": round(j["gm_pct"], 1),
            "location": j["location"],
        }
        for j in recent
    ]

    return profile


def find_similar_jobs(
    sign_type: str,
    revenue_estimate: float = 0,
    location: str = "",
    max_results: int = 10,
) -> list[SimilarJob]:
    """Find historical jobs most similar to a proposed one.

    Matches on sign type, revenue range, and optionally location.
    Returns up to max_results ranked by similarity.
    """
    _load_warehouse()
    if not _ALL_JOBS:
        return []

    match_codes = expand_sign_type(sign_type)

    # Filter jobs by sign type
    candidates = []
    for j in _ALL_JOBS:
        if j["sign_type"] in match_codes or j["sales_code"] in match_codes:
            if j["billing"] > 0:
                candidates.append(j)

    if not candidates:
        return []

    # Score similarity
    loc_lower = location.lower() if location else ""
    scored = []
    for j in candidates:
        sim = 0.5  # base: same sign type

        # Revenue proximity (up to 0.3)
        if revenue_estimate > 0 and j["billing"] > 0:
            ratio = min(j["billing"], revenue_estimate) / max(
                j["billing"], revenue_estimate
            )
            sim += ratio * 0.3

        # Location match (up to 0.2)
        if loc_lower and j["location"]:
            jloc = j["location"].lower()
            if loc_lower in jloc or jloc in loc_lower:
                sim += 0.2
            elif loc_lower.split(",")[0].strip() in jloc:
                sim += 0.1

        scored.append(
            SimilarJob(
                work_order=j["work_order"],
                customer=j["customer_name"],
                location=j["location"],
                sign_type=j["sign_type"],
                description=j["description"][:100],
                billing=round(j["billing"], 2),
                labor_cost=round(j["labor_cost"], 2),
                gm_pct=round(j["gm_pct"], 1),
                date_completed=j["date_completed"],
                similarity_score=round(sim, 2),
            )
        )

    scored.sort(key=lambda s: s.similarity_score, reverse=True)
    return scored[:max_results]


def get_market_intel(sign_type: str) -> Optional[MarketIntel]:
    """Get market intelligence for a sign type.

    Returns pricing benchmarks, volume, and top customers across
    all historical data.
    """
    _load_warehouse()
    if not _ALL_JOBS:
        return None

    match_codes = expand_sign_type(sign_type)

    matching = [
        j
        for j in _ALL_JOBS
        if (j["sign_type"] in match_codes or j["sales_code"] in match_codes)
        and j["billing"] > 0
    ]

    if not matching:
        return None

    revenues = [j["billing"] for j in matching]
    margins = [j["gm_pct"] for j in matching if j["gm_pct"] != 0]

    # Top customers by revenue
    cust_rev: dict[str, float] = {}
    for j in matching:
        cust_rev[j["customer_name"]] = (
            cust_rev.get(j["customer_name"], 0) + j["billing"]
        )
    top_custs = sorted(cust_rev.items(), key=lambda x: x[1], reverse=True)[:10]

    sorted_rev = sorted(revenues)
    p25_idx = max(0, len(sorted_rev) // 4 - 1)
    p75_idx = min(len(sorted_rev) - 1, (len(sorted_rev) * 3) // 4)

    return MarketIntel(
        sign_type=sign_type,
        total_jobs=len(matching),
        avg_revenue=round(statistics.mean(revenues), 2),
        median_revenue=round(statistics.median(revenues), 2),
        avg_gm_pct=round(statistics.mean(margins), 1) if margins else 0,
        p25_revenue=round(sorted_rev[p25_idx], 2),
        p75_revenue=round(sorted_rev[p75_idx], 2),
        top_customers=[
            {"customer": c, "total_revenue": round(r, 2)} for c, r in top_custs
        ],
    )


def warehouse_stats() -> dict:
    """Return top-level warehouse statistics."""
    _load_warehouse()
    if not _ALL_JOBS:
        return {"loaded": False, "total_jobs": 0}

    total_revenue = sum(j["billing"] for j in _ALL_JOBS if j["billing"] > 0)
    unique_customers = len(set(j["customer_no"] for j in _ALL_JOBS))
    sign_types = {}
    for j in _ALL_JOBS:
        st = j["sign_type"] or "OTHER"
        sign_types[st] = sign_types.get(st, 0) + 1

    return {
        "loaded": True,
        "total_jobs": len(_ALL_JOBS),
        "total_revenue": round(total_revenue, 2),
        "unique_customers": unique_customers,
        "sign_type_counts": dict(
            sorted(sign_types.items(), key=lambda x: x[1], reverse=True)[:15]
        ),
    }
