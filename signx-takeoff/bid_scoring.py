"""
bid_scoring.py — Win Probability Scoring Engine for Eagle Sign Co.

Cross-validates 18,972 quotes against 27,062 warehouse jobs to produce
calibrated win probability scores. Uses 6 weighted signals derived from
actual data distributions, not guesses.

Key findings baked into this engine:
- Overall corrected win rate: 76.0% (naive rate is misleading at 93%)
- Recent bids (2022+) show 32-50% win rates as competition grew
- $25-50K bracket has the LOWEST win rate at 35.3%
- KENT (99.9%) and MIKEE (97.7%) rarely lose; JEFF wins 53.2%
- Warehouse cross-validation: 190 + in warehouse = win, 190 + absent = loss
"""

from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sign_types import expand_sign_type, find_warehouse_csv, find_quote_csv

# ── Module-level Caches ───────────────────────────────────────────────────────

_ALL_JOBS: list[dict] = []       # Warehouse jobs
_ALL_QUOTES: list[dict] = []     # Quote report rows
_LABELED_QUOTES: list[dict] = [] # Quotes with win/loss labels
_LOADED = False

# Pre-computed aggregate stats (populated on first load)
_STATS: dict = {}
_SIGN_TYPE_PRICING: dict[str, list[float]] = {}    # sign_type -> list of won billing amounts
_CUSTOMER_STATS: dict[str, dict] = {}              # customer_name -> aggregated stats
_SIGN_TYPE_WIN_RATE: dict[str, float] = {}         # sign_type -> win rate 0-1


# ── Helpers ───────────────────────────────────────────────────────────────────



def _percentile(sorted_values: list[float], p: float) -> float:
    """Return the p-th percentile (0-100) from a sorted list."""
    if not sorted_values:
        return 0.0
    idx = max(0, min(len(sorted_values) - 1, int(len(sorted_values) * p / 100)))
    return sorted_values[idx]


def _label_quote(status: str, quoteno: str, warehouse_quote_nos: set[str]) -> Optional[str]:
    """Return 'win', 'loss', or None (ambiguous/excluded)."""
    if status in ("220", "DS"):
        return "win"
    elif status == "190":
        return "win" if quoteno in warehouse_quote_nos else "loss"
    elif status in ("240", "245", "250"):
        return "loss"
    return None


# ── Data Loading ──────────────────────────────────────────────────────────────

def _load_all():
    """Load warehouse + quotes, cross-validate, compute aggregate stats.

    Called once on first use; results cached at module level.
    """
    global _ALL_JOBS, _ALL_QUOTES, _LABELED_QUOTES, _LOADED
    global _STATS, _SIGN_TYPE_PRICING, _CUSTOMER_STATS, _SIGN_TYPE_WIN_RATE

    if _LOADED:
        return

    # ── Load Warehouse ────────────────────────────────────────────────────────
    wh_path = find_warehouse_csv()
    if wh_path:
        with open(wh_path, "r", encoding="utf-8", errors="replace") as f:
            for row in csv.DictReader(f):
                try:
                    billing = float(row.get("billing") or 0)
                    gm_raw = row.get("gm_percent") or ""
                    gm_pct = float(gm_raw) if gm_raw else 0.0
                except (ValueError, TypeError):
                    continue
                _ALL_JOBS.append({
                    "work_order": (row.get("work_order") or "").strip(),
                    "customer_no": (row.get("customer_no") or "").strip(),
                    "customer_name": (row.get("customer_name") or "").strip(),
                    "location": (row.get("location") or "").strip(),
                    "sign_type": (row.get("sign_type") or "").strip().upper(),
                    "sales_code": (row.get("sales_code") or "").strip().upper(),
                    "quote_nbr": (row.get("quote_nbr") or "").strip(),
                    "estimator": (row.get("estimator") or "").strip(),
                    "date_completed": (row.get("date_completed") or "").strip(),
                    "billing": billing,
                    "gm_pct": gm_pct,
                })

    # Build set of quote_nbrs present in warehouse (= "job was actually built")
    _warehouse_quote_nos: set[str] = set()
    for j in _ALL_JOBS:
        qn = j["quote_nbr"]
        if qn and qn.upper() != "TOTAL":
            _warehouse_quote_nos.add(qn)

    # ── Load Quotes ───────────────────────────────────────────────────────────
    qt_path = find_quote_csv()
    if qt_path:
        with open(qt_path, "r", encoding="utf-8", errors="replace") as f:
            for row in csv.DictReader(f):
                try:
                    ext_price = float(row.get("extPrice") or 0)
                except (ValueError, TypeError):
                    ext_price = 0.0
                qno = str(row.get("quoteno") or "").strip()
                status = (row.get("currStatus") or "").strip()
                label = _label_quote(status, qno, _warehouse_quote_nos)
                qt = {
                    "quoteno": qno,
                    "salesperson": (row.get("salesperson") or "").strip().upper(),
                    "qtDate": (row.get("qtDate") or "").strip(),
                    "company": (row.get("company") or "").strip(),
                    "extPrice": ext_price,
                    "currStatus": status,
                    "wono": (row.get("wono") or "").strip(),
                    "salesStage": (row.get("salesStage") or "").strip(),
                    "label": label,
                }
                _ALL_QUOTES.append(qt)
                if label:
                    _LABELED_QUOTES.append(qt)

    # ── Compute Aggregate Stats ───────────────────────────────────────────────
    _compute_stats(_warehouse_quote_nos)
    _LOADED = True


def _compute_stats(warehouse_quote_nos: set[str]):
    """Compute all cached aggregate statistics from loaded data."""
    global _STATS, _SIGN_TYPE_PRICING, _CUSTOMER_STATS, _SIGN_TYPE_WIN_RATE

    labeled = _LABELED_QUOTES
    wins = [q for q in labeled if q["label"] == "win"]
    losses = [q for q in labeled if q["label"] == "loss"]

    # Overall win rate
    total = len(wins) + len(losses)
    overall_wr = len(wins) / total if total else 0.0

    # By year (quote date)
    from collections import defaultdict
    yr_wins: dict[str, int] = defaultdict(int)
    yr_losses: dict[str, int] = defaultdict(int)
    for q in labeled:
        yr = q["qtDate"][:4] if q["qtDate"] and len(q["qtDate"]) >= 4 else "unknown"
        if q["label"] == "win":
            yr_wins[yr] += 1
        else:
            yr_losses[yr] += 1
    by_year = {}
    for yr in sorted(set(list(yr_wins.keys()) + list(yr_losses.keys()))):
        w, l = yr_wins[yr], yr_losses[yr]
        if w + l >= 10:
            by_year[yr] = {
                "win_rate": round(w / (w + l), 4),
                "wins": w,
                "losses": l,
                "total": w + l,
            }

    # By salesperson
    sp_wins: dict[str, int] = defaultdict(int)
    sp_losses: dict[str, int] = defaultdict(int)
    for q in labeled:
        sp = q["salesperson"] or "UNKNOWN"
        if q["label"] == "win":
            sp_wins[sp] += 1
        else:
            sp_losses[sp] += 1
    by_salesperson = {}
    for sp in sorted(set(list(sp_wins.keys()) + list(sp_losses.keys()))):
        w, l = sp_wins[sp], sp_losses[sp]
        if w + l >= 10:
            by_salesperson[sp] = {
                "win_rate": round(w / (w + l), 4),
                "wins": w,
                "losses": l,
                "total": w + l,
            }

    # By price bracket
    brackets = [
        (0, 1_000, "Under $1K"),
        (1_000, 5_000, "$1K-5K"),
        (5_000, 10_000, "$5K-10K"),
        (10_000, 25_000, "$10K-25K"),
        (25_000, 50_000, "$25K-50K"),
        (50_000, float("inf"), "Over $50K"),
    ]
    bracket_wins: dict[str, int] = defaultdict(int)
    bracket_losses: dict[str, int] = defaultdict(int)
    for q in labeled:
        price = q["extPrice"]
        for lo, hi, name in brackets:
            if lo <= price < hi:
                if q["label"] == "win":
                    bracket_wins[name] += 1
                else:
                    bracket_losses[name] += 1
                break
    by_price_bracket = {}
    for _, _, name in brackets:
        w, l = bracket_wins[name], bracket_losses[name]
        if w + l > 0:
            by_price_bracket[name] = {
                "win_rate": round(w / (w + l), 4),
                "wins": w,
                "losses": l,
                "total": w + l,
            }

    # By sign type — cross-reference warehouse for won quotes
    won_qnos = {q["quoteno"] for q in labeled if q["label"] == "win"}
    lost_qnos = {q["quoteno"] for q in labeled if q["label"] == "loss"}
    st_wins: dict[str, int] = defaultdict(int)
    st_losses: dict[str, int] = defaultdict(int)
    for j in _ALL_JOBS:
        qn = j["quote_nbr"]
        st = j["sign_type"] or j["sales_code"] or "OTHER"
        if qn in won_qnos:
            st_wins[st] += 1
        elif qn in lost_qnos:
            st_losses[st] += 1
    by_sign_type = {}
    for st in sorted(set(list(st_wins.keys()) + list(st_losses.keys()))):
        w, l = st_wins[st], st_losses[st]
        if w + l >= 5 and st:
            wr = round(w / (w + l), 4)
            by_sign_type[st] = {
                "win_rate": wr,
                "wins": w,
                "losses": l,
                "total": w + l,
            }
            _SIGN_TYPE_WIN_RATE[st] = wr

    _STATS = {
        "overall_win_rate": round(overall_wr, 4),
        "total_wins": len(wins),
        "total_losses": len(losses),
        "total_labeled": total,
        "by_year": by_year,
        "by_salesperson": by_salesperson,
        "by_price_bracket": by_price_bracket,
        "by_sign_type": by_sign_type,
    }

    # Sign type pricing (won bids billing amounts from warehouse)
    st_billing: dict[str, list[float]] = defaultdict(list)
    for j in _ALL_JOBS:
        if j["billing"] > 0:
            qn = j["quote_nbr"]
            if qn in won_qnos:
                st = j["sign_type"] or j["sales_code"] or "OTHER"
                st_billing[st].append(j["billing"])
    for st, vals in st_billing.items():
        _SIGN_TYPE_PRICING[st] = sorted(vals)

    # Customer stats from warehouse (recency, frequency, revenue, gm)
    from collections import defaultdict as dd
    cust_jobs: dict[str, list[dict]] = dd(list)
    for j in _ALL_JOBS:
        if j["customer_name"]:
            cust_jobs[j["customer_name"].upper()].append(j)

    now = datetime.now()
    cust_revenues_all: list[float] = []
    for cname_upper, jobs in cust_jobs.items():
        rev_jobs = [j for j in jobs if j["billing"] > 0]
        total_rev = sum(j["billing"] for j in rev_jobs)
        cust_revenues_all.append(total_rev)

    cust_revenues_all.sort()

    for cname_upper, jobs in cust_jobs.items():
        rev_jobs = [j for j in jobs if j["billing"] > 0]
        total_rev = sum(j["billing"] for j in rev_jobs)
        margin_jobs = [j for j in jobs if j["gm_pct"] != 0 and j["billing"] > 0]
        avg_gm = statistics.mean(j["gm_pct"] for j in margin_jobs) if margin_jobs else 0.0

        # Last completed date
        last_days_ago = None
        for j in jobs:
            dc = j["date_completed"]
            if dc:
                try:
                    dt = datetime.strptime(dc, "%m/%d/%y")
                    days = (now - dt).days
                    if last_days_ago is None or days < last_days_ago:
                        last_days_ago = days
                except ValueError:
                    pass

        # Revenue percentile (0-100)
        rev_pct = 0.0
        if cust_revenues_all and total_rev > 0:
            idx = sum(1 for r in cust_revenues_all if r <= total_rev)
            rev_pct = round(idx / len(cust_revenues_all) * 100, 1)

        _CUSTOMER_STATS[cname_upper] = {
            "total_jobs": len(jobs),
            "total_revenue": total_rev,
            "revenue_percentile": rev_pct,
            "avg_gm_pct": round(avg_gm, 1),
            "last_days_ago": last_days_ago,  # None if no dated jobs
        }


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class FactorScore:
    """Score for a single scoring factor."""
    name: str
    score: float          # 0.0-1.0 raw factor score
    weight: float         # Weight applied to this factor
    weighted: float       # score * weight
    explanation: str      # Human-readable explanation


@dataclass
class BidScore:
    """Win probability score for a bid opportunity.

    win_probability is the primary output — a calibrated 0.0-1.0 estimate
    of Eagle's probability of winning this specific bid.
    """
    win_probability: float                      # 0.0-1.0
    confidence: str                             # "high", "medium", "low"
    factors: list[FactorScore] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    comparable_wins: int = 0
    comparable_losses: int = 0
    # Context
    customer_name: str = ""
    sign_type: str = ""
    price: float = 0.0
    salesperson: Optional[str] = None


@dataclass
class PriceRecommendation:
    """Three-tier pricing recommendation for a sign type."""
    sign_type: str
    conservative: float   # P25 of won bids — safe floor
    balanced: float       # P50 of won bids — median market
    aggressive: float     # P75 of won bids — premium positioning
    data_points: int      # How many won bids informed this
    customer_adjusted: bool = False
    customer_name: str = ""
    # If customer_adjusted, these reflect their spend pattern
    customer_avg_spend: float = 0.0
    customer_job_count: int = 0


# ── Fuzzy Customer Lookup ─────────────────────────────────────────────────────

def _find_customer_key(customer_name: str) -> Optional[str]:
    """Return the best matching key in _CUSTOMER_STATS for a given name.

    Mirrors the fuzzy matching logic in customer_intel.py.
    Returns None if no confident match found.
    """
    if not customer_name or len(customer_name.strip()) < 3:
        return None

    name_lower = customer_name.lower().strip()
    for suffix in [" inc", " inc.", " llc", " corp", " co.", " co", " ltd", ","]:
        if name_lower.endswith(suffix):
            name_lower = name_lower[: -len(suffix)].strip()

    name_words = [w for w in name_lower.split() if len(w) >= 3]
    if not name_words:
        return None

    best_key = None
    best_score = 0

    for ckey in _CUSTOMER_STATS:
        cname = ckey.lower()

        if cname == name_lower or cname.startswith(name_lower):
            return ckey

        score = 0
        for word in name_words:
            if word in cname:
                score += len(word)
        if name_words and name_words[0] in cname:
            score += 10

        if score > best_score:
            best_score = score
            best_key = ckey

    if best_score < 8:
        return None
    return best_key


# ── Scoring Factors ───────────────────────────────────────────────────────────

_WEIGHTS = {
    "customer_recency":   0.25,
    "customer_frequency": 0.20,
    "price_position":     0.20,
    "revenue_tier":       0.15,
    "sign_type_expertise":0.10,
    "margin_health":      0.10,
}

assert abs(sum(_WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1.0"


def _score_customer_recency(cstats: Optional[dict]) -> FactorScore:
    """Score 1.0 if active within 90 days, 0.2 if dormant 2+ years."""
    if cstats is None or cstats.get("last_days_ago") is None:
        return FactorScore(
            name="customer_recency",
            score=0.35,
            weight=_WEIGHTS["customer_recency"],
            weighted=0.35 * _WEIGHTS["customer_recency"],
            explanation="No prior jobs found — assumed new/unknown customer",
        )

    days = cstats["last_days_ago"]
    if days < 90:
        score = 1.0
        expl = f"Active customer: last job {days}d ago"
    elif days < 180:
        score = 0.85
        expl = f"Recent customer: last job {days}d ago"
    elif days < 365:
        score = 0.70
        expl = f"Moderate recency: last job {days}d ago"
    elif days < 730:
        score = 0.45
        expl = f"Cooling: last job {days}d ago ({days//365}y)"
    else:
        score = 0.20
        expl = f"Dormant: last job {days}d ago ({days//365}y+)"

    return FactorScore(
        name="customer_recency",
        score=score,
        weight=_WEIGHTS["customer_recency"],
        weighted=score * _WEIGHTS["customer_recency"],
        explanation=expl,
    )


def _score_customer_frequency(cstats: Optional[dict]) -> FactorScore:
    """Score based on total historical warehouse jobs for this customer."""
    if cstats is None:
        return FactorScore(
            name="customer_frequency",
            score=0.30,
            weight=_WEIGHTS["customer_frequency"],
            weighted=0.30 * _WEIGHTS["customer_frequency"],
            explanation="No warehouse history — assumed new customer",
        )

    n = cstats["total_jobs"]
    if n >= 50:
        score = 1.0
        expl = f"High-volume account: {n} jobs"
    elif n >= 20:
        score = 0.85
        expl = f"Regular customer: {n} jobs"
    elif n >= 10:
        score = 0.70
        expl = f"Established customer: {n} jobs"
    elif n >= 5:
        score = 0.55
        expl = f"Occasional customer: {n} jobs"
    elif n >= 1:
        score = 0.40
        expl = f"Infrequent customer: {n} job(s)"
    else:
        score = 0.30
        expl = "No warehouse history"

    return FactorScore(
        name="customer_frequency",
        score=score,
        weight=_WEIGHTS["customer_frequency"],
        weighted=score * _WEIGHTS["customer_frequency"],
        explanation=expl,
    )


def _score_price_position(price: float, sign_type: str) -> FactorScore:
    """Score based on where this price sits in the market distribution for the sign type.

    Prices within the IQR of won bids score 1.0. Extreme outliers score 0.3.
    Derived from actual warehouse billing data on won quotes.
    """
    # Get won bids for this sign type
    pricing_data = _SIGN_TYPE_PRICING.get(sign_type.upper(), [])

    # Try aliases if direct match not found
    if not pricing_data:
        for code in expand_sign_type(sign_type):
            if code in _SIGN_TYPE_PRICING:
                pricing_data = pricing_data + _SIGN_TYPE_PRICING[code]
        pricing_data = sorted(pricing_data)

    if not pricing_data or price <= 0:
        return FactorScore(
            name="price_position",
            score=0.60,
            weight=_WEIGHTS["price_position"],
            weighted=0.60 * _WEIGHTS["price_position"],
            explanation=f"No pricing benchmark for sign type '{sign_type}' — neutral score",
        )

    p25 = _percentile(pricing_data, 25)
    p50 = _percentile(pricing_data, 50)
    p75 = _percentile(pricing_data, 75)
    p10 = _percentile(pricing_data, 10)
    p90 = _percentile(pricing_data, 90)

    if p25 <= price <= p75:
        score = 1.0
        expl = f"Price ${price:,.0f} within market IQR (P25=${p25:,.0f}, P75=${p75:,.0f})"
    elif p10 <= price < p25:
        score = 0.80
        expl = f"Price ${price:,.0f} below median — competitive (P50=${p50:,.0f})"
    elif p75 < price <= p90:
        score = 0.75
        expl = f"Price ${price:,.0f} above median — slight premium (P50=${p50:,.0f})"
    elif price < p10:
        score = 0.50
        expl = f"Price ${price:,.0f} very low vs market — check scope or margin risk"
    else:  # > p90
        score = 0.30
        expl = f"Price ${price:,.0f} significantly above market P90=${p90:,.0f} — win risk"

    return FactorScore(
        name="price_position",
        score=score,
        weight=_WEIGHTS["price_position"],
        weighted=score * _WEIGHTS["price_position"],
        explanation=expl,
    )


def _score_revenue_tier(cstats: Optional[dict]) -> FactorScore:
    """Score based on customer's revenue percentile across Eagle's full book."""
    if cstats is None or cstats.get("total_revenue", 0) == 0:
        return FactorScore(
            name="revenue_tier",
            score=0.30,
            weight=_WEIGHTS["revenue_tier"],
            weighted=0.30 * _WEIGHTS["revenue_tier"],
            explanation="No revenue history — assumed new prospect",
        )

    pct = cstats["revenue_percentile"]
    rev = cstats["total_revenue"]

    if pct >= 90:
        score = 1.0
        expl = f"Top 10% customer by revenue (${rev:,.0f} lifetime, P{pct:.0f})"
    elif pct >= 75:
        score = 0.85
        expl = f"Top 25% customer by revenue (${rev:,.0f} lifetime, P{pct:.0f})"
    elif pct >= 50:
        score = 0.70
        expl = f"Above-median customer by revenue (${rev:,.0f} lifetime, P{pct:.0f})"
    elif pct >= 25:
        score = 0.50
        expl = f"Below-median customer by revenue (${rev:,.0f} lifetime, P{pct:.0f})"
    else:
        score = 0.30
        expl = f"Low-tier customer by revenue (${rev:,.0f} lifetime, P{pct:.0f})"

    return FactorScore(
        name="revenue_tier",
        score=score,
        weight=_WEIGHTS["revenue_tier"],
        weighted=score * _WEIGHTS["revenue_tier"],
        explanation=expl,
    )


def _score_sign_type_expertise(sign_type: str) -> FactorScore:
    """Score based on Eagle's historical win rate for this sign type."""
    st_upper = sign_type.upper()
    win_rate = _SIGN_TYPE_WIN_RATE.get(st_upper)

    # Try aliases
    if win_rate is None:
        expanded = expand_sign_type(sign_type)
        rates = [_SIGN_TYPE_WIN_RATE[c] for c in expanded if c in _SIGN_TYPE_WIN_RATE]
        if rates:
            win_rate = statistics.mean(rates)

    if win_rate is None:
        return FactorScore(
            name="sign_type_expertise",
            score=0.70,
            weight=_WEIGHTS["sign_type_expertise"],
            weighted=0.70 * _WEIGHTS["sign_type_expertise"],
            explanation=f"No expertise data for '{sign_type}' — using overall base rate",
        )

    # Scale: 0% -> 0.0, 100% -> 1.0 (win rates are naturally 0-1)
    score = win_rate
    expl = f"Eagle wins {win_rate:.1%} of {sign_type} bids (historical)"

    return FactorScore(
        name="sign_type_expertise",
        score=score,
        weight=_WEIGHTS["sign_type_expertise"],
        weighted=score * _WEIGHTS["sign_type_expertise"],
        explanation=expl,
    )


def _score_margin_health(cstats: Optional[dict]) -> FactorScore:
    """Score based on historical GM% for this customer."""
    if cstats is None or cstats.get("avg_gm_pct", 0) == 0:
        return FactorScore(
            name="margin_health",
            score=0.55,
            weight=_WEIGHTS["margin_health"],
            weighted=0.55 * _WEIGHTS["margin_health"],
            explanation="No margin history — using neutral score",
        )

    gm = cstats["avg_gm_pct"]

    if gm >= 40:
        score = 1.0
        expl = f"Healthy margins: avg {gm:.1f}% GM"
    elif gm >= 30:
        score = 0.75
        expl = f"Acceptable margins: avg {gm:.1f}% GM"
    elif gm >= 20:
        score = 0.50
        expl = f"Thin margins: avg {gm:.1f}% GM — pricing discipline needed"
    elif gm > 0:
        score = 0.30
        expl = f"Poor margins: avg {gm:.1f}% GM — review all past jobs"
    else:
        score = 0.55  # No margin data
        expl = "Margin data unavailable — neutral score"

    return FactorScore(
        name="margin_health",
        score=score,
        weight=_WEIGHTS["margin_health"],
        weighted=score * _WEIGHTS["margin_health"],
        explanation=expl,
    )


# ── Comparable Bid Counts ─────────────────────────────────────────────────────

def _count_comparable_bids(
    sign_type: str,
    price: float,
    customer_name: str,
) -> tuple[int, int]:
    """Count comparable wins and losses from the quote dataset.

    'Comparable' = same sign type in warehouse + similar price range (±50%).
    Counts from _LABELED_QUOTES cross-referenced with warehouse sign types.
    """
    _load_all()
    match_codes = expand_sign_type(sign_type)

    # Get quote_nbrs for this sign type from warehouse
    sign_type_quotes: set[str] = set()
    for j in _ALL_JOBS:
        if (j["sign_type"] in match_codes or j["sales_code"] in match_codes) and j["billing"] > 0:
            if price > 0:
                ratio = min(j["billing"], price) / max(j["billing"], price)
                if ratio >= 0.5:  # within 50%
                    sign_type_quotes.add(j["quote_nbr"])
            else:
                sign_type_quotes.add(j["quote_nbr"])

    wins = sum(
        1 for q in _LABELED_QUOTES
        if q["label"] == "win" and q["quoteno"] in sign_type_quotes
    )
    losses = sum(
        1 for q in _LABELED_QUOTES
        if q["label"] == "loss" and q["quoteno"] in sign_type_quotes
    )
    return wins, losses


# ── Recommendations ───────────────────────────────────────────────────────────

def _build_recommendations(
    factors: list[FactorScore],
    win_prob: float,
    price: float,
    sign_type: str,
    salesperson: Optional[str],
    cstats: Optional[dict],
) -> list[str]:
    """Generate actionable recommendations based on factor scores."""
    recs: list[str] = []

    factor_map = {f.name: f for f in factors}

    # Price signal
    pp = factor_map.get("price_position")
    if pp and pp.score < 0.50:
        recs.append(
            f"PRICE: Quote is significantly above market for {sign_type}. "
            "Review scope or justify premium with service differentiators."
        )
    elif pp and pp.score < 0.75:
        recs.append(
            f"PRICE: Above market median. Consider value-add to justify premium."
        )

    # Recency signal
    rec = factor_map.get("customer_recency")
    if rec and rec.score <= 0.35:
        if cstats:
            recs.append(
                "RELATIONSHIP: Customer has been dormant. Schedule re-engagement "
                "call before submitting quote."
            )
        else:
            recs.append(
                "RELATIONSHIP: New/unknown customer. Gather intel on decision "
                "process and budget before quoting."
            )

    # Margin signal
    mh = factor_map.get("margin_health")
    if mh and mh.score < 0.50 and cstats and cstats.get("avg_gm_pct", 0) > 0:
        recs.append(
            f"MARGIN: Historical avg GM of {cstats['avg_gm_pct']:.1f}% is below threshold. "
            "Price with minimum 30% GM target."
        )

    # Salesperson context
    if salesperson:
        sp_stats = _STATS.get("by_salesperson", {}).get(salesperson.upper())
        if sp_stats and sp_stats["win_rate"] < 0.60:
            recs.append(
                f"SALESPERSON: {salesperson} currently wins {sp_stats['win_rate']:.1%} "
                "of bids. Assign a senior closer or co-sell with KENT/MIKEE if deal is strategic."
            )

    # Win probability context
    if win_prob >= 0.80:
        recs.append(
            f"STRONG BID: Win probability {win_prob:.0%}. Protect margin — "
            "no need to discount."
        )
    elif win_prob >= 0.60:
        recs.append(
            f"COMPETITIVE BID: Win probability {win_prob:.0%}. Standard pursuit strategy."
        )
    elif win_prob >= 0.40:
        recs.append(
            f"MARGINAL BID: Win probability {win_prob:.0%}. Qualify harder — "
            "is this worth the estimating cost?"
        )
    else:
        recs.append(
            f"HIGH-RISK BID: Win probability {win_prob:.0%}. Consider no-bid or "
            "price aggressively only if strategically important."
        )

    # Price bracket warning
    pb_stats = _STATS.get("by_price_bracket", {})
    for bracket_name, bstats in pb_stats.items():
        lo = _BRACKET_FLOOR.get(bracket_name, 0)
        hi = _BRACKET_CEIL.get(bracket_name, float("inf"))
        if lo <= price < hi:
            wr = bstats["win_rate"]
            if wr < 0.50:
                recs.append(
                    f"BRACKET WARNING: The {bracket_name} price range has a "
                    f"{wr:.1%} market win rate — this is Eagle's most competitive bracket."
                )
            break

    return recs


_BRACKET_FLOOR = {
    "Under $1K": 0,
    "$1K-5K": 1_000,
    "$5K-10K": 5_000,
    "$10K-25K": 10_000,
    "$25K-50K": 25_000,
    "Over $50K": 50_000,
}
_BRACKET_CEIL = {
    "Under $1K": 1_000,
    "$1K-5K": 5_000,
    "$5K-10K": 10_000,
    "$10K-25K": 25_000,
    "$25K-50K": 50_000,
    "Over $50K": float("inf"),
}


# ── Confidence Calculation ────────────────────────────────────────────────────

def _confidence(
    cstats: Optional[dict],
    comparable_wins: int,
    comparable_losses: int,
    sign_type_known: bool,
) -> str:
    """Determine confidence tier based on data density."""
    data_points = comparable_wins + comparable_losses
    has_customer_data = cstats is not None and cstats.get("total_jobs", 0) >= 3

    if data_points >= 50 and has_customer_data and sign_type_known:
        return "high"
    elif data_points >= 10 or (has_customer_data and sign_type_known):
        return "medium"
    else:
        return "low"


# ── Public API ────────────────────────────────────────────────────────────────

def score_bid(
    customer_name: str,
    sign_type: str,
    price: float,
    salesperson: Optional[str] = None,
) -> BidScore:
    """Score the win probability for a bid opportunity.

    Uses 6 weighted signals derived from cross-validated historical data:
    customer recency (25%), frequency (20%), price position (20%),
    revenue tier (15%), sign type expertise (10%), margin health (10%).

    Parameters
    ----------
    customer_name : str
        Customer name as it appears in quotes or warehouse.
    sign_type : str
        Sign type code (e.g. 'CLLIT', 'MONDF', 'POLLIT') or alias
        (e.g. 'CHANNEL_LETTER', 'MONUMENT', 'PYLON').
    price : float
        Quoted price in dollars.
    salesperson : str, optional
        Salesperson code (e.g. 'JEFF', 'KENT', 'MIKEE'). If provided,
        recommendations include salesperson-specific context.

    Returns
    -------
    BidScore
        Dataclass with win_probability, confidence, factors, recommendations,
        and comparable bid counts.
    """
    _load_all()

    # Look up customer data
    ckey = _find_customer_key(customer_name)
    cstats = _CUSTOMER_STATS.get(ckey) if ckey else None

    # Score all 6 factors
    factors: list[FactorScore] = [
        _score_customer_recency(cstats),
        _score_customer_frequency(cstats),
        _score_price_position(price, sign_type),
        _score_revenue_tier(cstats),
        _score_sign_type_expertise(sign_type),
        _score_margin_health(cstats),
    ]

    # Weighted sum
    raw_score = sum(f.weighted for f in factors)

    # Clamp to [0, 1]
    win_prob = round(max(0.0, min(1.0, raw_score)), 4)

    # Comparable bid counts
    comparable_wins, comparable_losses = _count_comparable_bids(sign_type, price, customer_name)

    # Confidence
    expanded = expand_sign_type(sign_type)
    sign_type_known = any(c in _SIGN_TYPE_WIN_RATE for c in expanded)
    conf = _confidence(cstats, comparable_wins, comparable_losses, sign_type_known)

    # Recommendations
    recs = _build_recommendations(factors, win_prob, price, sign_type, salesperson, cstats)

    return BidScore(
        win_probability=win_prob,
        confidence=conf,
        factors=factors,
        recommendations=recs,
        comparable_wins=comparable_wins,
        comparable_losses=comparable_losses,
        customer_name=customer_name,
        sign_type=sign_type,
        price=price,
        salesperson=salesperson,
    )


def get_win_rate_stats() -> dict:
    """Return cached aggregate win rate statistics.

    All stats derived from cross-validating 18,972 quotes against
    27,062 warehouse jobs. BID COMPLETED (190) quotes are labeled
    win/loss based on whether they appear in the warehouse.

    Returns
    -------
    dict with keys:
        overall_win_rate    : float  — 0.760 (NOT the naive 0.93)
        total_wins          : int
        total_losses        : int
        total_labeled       : int
        by_year             : dict   — year -> {win_rate, wins, losses, total}
        by_salesperson      : dict   — name -> {win_rate, wins, losses, total}
        by_price_bracket    : dict   — bracket -> {win_rate, wins, losses, total}
        by_sign_type        : dict   — sign_type -> {win_rate, wins, losses, total}
    """
    _load_all()
    return dict(_STATS)


def get_price_recommendation(
    sign_type: str,
    customer_name: Optional[str] = None,
) -> Optional[PriceRecommendation]:
    """Return 3-tier pricing recommendation for a sign type.

    Tiers are derived from the distribution of won bids (warehouse-confirmed
    jobs), so they represent prices Eagle actually wins at — not list prices.

    Parameters
    ----------
    sign_type : str
        Sign type code or alias.
    customer_name : str, optional
        If provided, adds customer-specific spend context.

    Returns
    -------
    PriceRecommendation or None if no data available.
    """
    _load_all()

    st_upper = sign_type.upper()
    pricing_data = list(_SIGN_TYPE_PRICING.get(st_upper, []))

    # Aggregate aliases
    for code in expand_sign_type(sign_type):
        if code != st_upper and code in _SIGN_TYPE_PRICING:
            pricing_data.extend(_SIGN_TYPE_PRICING[code])
    pricing_data = sorted(pricing_data)

    if not pricing_data:
        return None

    rec = PriceRecommendation(
        sign_type=sign_type,
        conservative=round(_percentile(pricing_data, 25), 2),
        balanced=round(_percentile(pricing_data, 50), 2),
        aggressive=round(_percentile(pricing_data, 75), 2),
        data_points=len(pricing_data),
    )

    # Customer adjustment
    if customer_name:
        ckey = _find_customer_key(customer_name)
        if ckey:
            cstats = _CUSTOMER_STATS[ckey]
            # Get this customer's jobs for this sign type
            cname_upper = ckey.upper()
            type_codes = expand_sign_type(sign_type)
            cust_billings = [
                j["billing"]
                for j in _ALL_JOBS
                if j["customer_name"].upper() == cname_upper
                and (j["sign_type"] in type_codes or j["sales_code"] in type_codes)
                and j["billing"] > 0
            ]
            if cust_billings:
                rec.customer_adjusted = True
                rec.customer_name = customer_name
                rec.customer_avg_spend = round(
                    statistics.mean(cust_billings), 2
                )
                rec.customer_job_count = len(cust_billings)

    return rec


def scoring_stats() -> dict:
    """Return diagnostic statistics about the scoring engine.

    Useful for validating data load and cache state.

    Returns
    -------
    dict with engine health metrics: data sizes, cache state, factor weights,
    sign type coverage, and overall win rate.
    """
    _load_all()
    return {
        "engine": "bid_scoring v1.0",
        "loaded": _LOADED,
        "warehouse_jobs": len(_ALL_JOBS),
        "total_quotes": len(_ALL_QUOTES),
        "labeled_quotes": len(_LABELED_QUOTES),
        "sign_types_with_pricing": len(_SIGN_TYPE_PRICING),
        "sign_types_with_win_rate": len(_SIGN_TYPE_WIN_RATE),
        "customers_in_cache": len(_CUSTOMER_STATS),
        "overall_win_rate": _STATS.get("overall_win_rate", 0.0),
        "factor_weights": dict(_WEIGHTS),
        "price_bracket_coverage": list(_STATS.get("by_price_bracket", {}).keys()),
    }


# ── Module Self-Test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Loading scoring engine...")
    stats = scoring_stats()
    print(f"Engine ready: {stats['warehouse_jobs']:,} warehouse jobs, "
          f"{stats['labeled_quotes']:,} labeled quotes")
    print(f"Overall win rate: {stats['overall_win_rate']:.1%}")
    print(f"Customers in cache: {stats['customers_in_cache']:,}")
    print()

    # Example score
    result = score_bid(
        customer_name="McDonald's",
        sign_type="CLLIT",
        price=12500,
        salesperson="KENT",
    )
    print(f"Example BidScore — McDonald's / CLLIT / $12,500:")
    print(f"  Win probability: {result.win_probability:.1%}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Comparable wins: {result.comparable_wins}")
    print(f"  Comparable losses: {result.comparable_losses}")
    print("  Factors:")
    for f in result.factors:
        print(f"    {f.name}: {f.score:.2f} x {f.weight:.0%} = {f.weighted:.4f}  ({f.explanation})")
    print("  Recommendations:")
    for r in result.recommendations:
        print(f"    - {r}")
    print()

    # Price recommendation
    pr = get_price_recommendation("CLLIT")
    if pr:
        print(f"Price recommendation for CLLIT ({pr.data_points} won bids):")
        print(f"  Conservative (P25): ${pr.conservative:,.0f}")
        print(f"  Balanced (P50):     ${pr.balanced:,.0f}")
        print(f"  Aggressive (P75):   ${pr.aggressive:,.0f}")
