"""
bid_model.py — Logistic Regression Win Probability Model for Eagle Sign Co.

Trains a scikit-learn logistic regression on 18,000+ labeled quotes
cross-validated against the warehouse. Complements the heuristic bid_scoring.py
with a data-driven probabilistic model.

Label logic:
  WIN:  currStatus in ('220', 'DS')
  WIN:  currStatus == '190' AND quoteno in warehouse quote_nbr
  LOSS: currStatus in ('240', '245', '250')
  LOSS: currStatus == '190' AND quoteno NOT in warehouse AND quote age > 6 months
  EXCL: everything else

Features:
  price_log             : log1p(extPrice)
  salesperson_encoded   : target encoding (win rate per salesperson)
  quarter               : 1-4 from qtDate
  days_to_expiry        : (expDate - qtDate).days, clipped [0, 365]
  customer_job_count    : count of past warehouse jobs for this customer
  customer_total_revenue: sum of billing for this customer
  customer_avg_margin   : mean gm_percent for this customer
  days_since_last_job   : days since most recent date_completed, clipped [0, 3650]
  is_repeat_customer    : 1 if customer_job_count > 0
  price_vs_type_avg     : extPrice / mean extPrice for same sign_type (warehouse)
"""

from __future__ import annotations

import csv
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── sklearn imports (deferred to _train() so import errors are clear) ─────────

WAREHOUSE_PATHS = [
    Path(r"C:\Scripts\signx-warehouse\warehouse\raw\so_contracts_parsed.csv"),
    Path(r"C:\Scripts\SignX\Keyedin\warehouse\warehouse\raw\so_contracts_parsed.csv"),
]

QUOTE_PATHS = [
    Path(r"C:\Scripts\signx-warehouse\warehouse\raw\quote_status_report.csv"),
    Path(r"C:\Scripts\SignX\Keyedin\warehouse\warehouse\raw\quote_status_report.csv"),
]

# ── Module-level cache ─────────────────────────────────────────────────────────

_MODEL_BUNDLE: Optional["ModelBundle"] = None
_TRAINING_DONE: bool = False
_TRAINING_ERROR: Optional[str] = None

# Time-decay half-life for sample weighting (years)
# 5 years: conservative — preserves historical signal while downweighting oldest data
# (3 years was too aggressive, pushed accuracy to 44.6%)
_HALF_LIFE_YEARS = 5.0

# Feature names in the order the model expects them
_FEATURE_NAMES = [
    "price_log",
    "salesperson_encoded",
    "quarter",
    "month_sin",
    "month_cos",
    "days_to_expiry",
    "customer_job_count",
    "customer_total_revenue_log",
    "customer_avg_margin",
    "days_since_last_job",
    "is_repeat_customer",
    "price_vs_type_avg",
]

_FEATURE_DESCRIPTIONS = {
    "price_log":                  "Quote price (log-scaled)",
    "salesperson_encoded":        "Salesperson historical win rate",
    "quarter":                    "Quote quarter (1-4)",
    "month_sin":                  "Seasonal month (sin component)",
    "month_cos":                  "Seasonal month (cos component)",
    "days_to_expiry":             "Days from quote date to expiry",
    "customer_job_count":         "Past jobs for this customer",
    "customer_total_revenue_log": "Customer lifetime revenue (log-scaled)",
    "customer_avg_margin":        "Customer historical avg gross margin %",
    "days_since_last_job":        "Days since last completed job",
    "is_repeat_customer":         "1 = returning customer, 0 = new",
    "price_vs_type_avg":          "Price relative to sign-type average",
}


# ── Data Classes ───────────────────────────────────────────────────────────────

@dataclass
class ModelBundle:
    """Everything produced by train_model()."""
    model: object                          # fitted LogisticRegression
    scaler: object                         # fitted StandardScaler
    feature_names: list[str]
    metrics: dict                          # AUC-ROC, Brier, accuracy, n_train
    coefficients: dict[str, float]         # feature -> coefficient
    # Lookup tables built during training
    salesperson_win_rates: dict[str, float]
    sign_type_avg_prices: dict[str, float]
    customer_stats: dict[str, dict]        # normalized name -> stats
    overall_win_rate: float


@dataclass
class MLPrediction:
    """Win probability prediction from the logistic regression model."""
    win_probability: float
    confidence: str                          # "high", "medium", "low"
    risk_factors: list[str] = field(default_factory=list)
    positive_factors: list[str] = field(default_factory=list)
    feature_contributions: dict[str, float] = field(default_factory=dict)
    feature_values: dict[str, float] = field(default_factory=dict)
    model_available: bool = True


# ── Path helpers ──────────────────────────────────────────────────────────────

def _find_csv(paths: list[Path]) -> Optional[Path]:
    for p in paths:
        if p.exists():
            return p
    return None


# ── Date parsing ──────────────────────────────────────────────────────────────

_DATE_FMTS = ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d"]


def _parse_date(s: str) -> Optional[datetime]:
    if not s or not s.strip():
        return None
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


# ── Customer name normalizer (same fuzzy logic as bid_scoring.py) ─────────────

def _normalize_name(name: str) -> str:
    name = name.strip().upper()
    for suffix in [" INC", " INC.", " LLC", " CORP", " CO.", " CO", " LTD", ","]:
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()
    return name


def _fuzzy_lookup(name: str, table: dict[str, dict]) -> Optional[str]:
    if not name or len(name.strip()) < 3:
        return None
    name_norm = _normalize_name(name)
    name_words = [w for w in name_norm.split() if len(w) >= 3]
    if not name_words:
        return None

    best_key = None
    best_score = 0
    for ckey in table:
        if ckey == name_norm or ckey.startswith(name_norm):
            return ckey
        score = sum(len(w) for w in name_words if w in ckey)
        if name_words and name_words[0] in ckey:
            score += 10
        if score > best_score:
            best_score = score
            best_key = ckey
    if best_score < 8:
        return None
    return best_key


# ── Core training function ─────────────────────────────────────────────────────

def train_model() -> ModelBundle:
    """Load data, engineer features, train LR, evaluate via CV, return bundle.

    Prints AUC-ROC, Brier score, and feature importances to stdout.
    Called once on module load; result cached in _MODEL_BUNDLE.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.metrics import roc_auc_score, brier_score_loss

    now = datetime.now()

    # ── 1. Load warehouse ──────────────────────────────────────────────────────
    print("[bid_model] Loading warehouse...")
    wh_path = _find_csv(WAREHOUSE_PATHS)
    all_jobs: list[dict] = []
    if wh_path:
        with open(wh_path, "r", encoding="utf-8", errors="replace") as f:
            for row in csv.DictReader(f):
                try:
                    billing = float(row.get("billing") or 0)
                except (ValueError, TypeError):
                    billing = 0.0
                try:
                    gm_pct = float(row.get("gm_percent") or 0)
                except (ValueError, TypeError):
                    gm_pct = 0.0
                quote_nbr = (row.get("quote_nbr") or "").strip()
                if quote_nbr.upper() == "TOTAL":
                    quote_nbr = ""
                all_jobs.append({
                    "work_order":    (row.get("work_order") or "").strip(),
                    "customer_name": (row.get("customer_name") or "").strip(),
                    "sign_type":     (row.get("sign_type") or "").strip().upper(),
                    "sales_code":    (row.get("sales_code") or "").strip().upper(),
                    "quote_nbr":     quote_nbr,
                    "date_completed": (row.get("date_completed") or "").strip(),
                    "billing":       billing,
                    "gm_pct":        gm_pct,
                })

    print(f"[bid_model]   {len(all_jobs):,} warehouse jobs loaded")

    # Warehouse quote_nbr set
    wh_quote_nos: set[str] = {j["quote_nbr"] for j in all_jobs if j["quote_nbr"]}

    # quote_nbr -> sign_type (for feature engineering)
    quote_to_sign_type: dict[str, str] = {}
    for j in all_jobs:
        qn = j["quote_nbr"]
        if qn:
            st = j["sign_type"] or j["sales_code"] or ""
            if st and qn not in quote_to_sign_type:
                quote_to_sign_type[qn] = st

    # ── 2. Build customer stats from warehouse ─────────────────────────────────
    cust_jobs: dict[str, list[dict]] = defaultdict(list)
    for j in all_jobs:
        cname = j["customer_name"]
        if cname:
            cust_jobs[_normalize_name(cname)].append(j)

    customer_stats: dict[str, dict] = {}
    for cname_norm, jobs in cust_jobs.items():
        rev_jobs = [j for j in jobs if j["billing"] > 0]
        total_rev = sum(j["billing"] for j in rev_jobs)
        margin_jobs = [j for j in jobs if j["gm_pct"] != 0 and j["billing"] > 0]
        avg_gm = statistics.mean(j["gm_pct"] for j in margin_jobs) if margin_jobs else 0.0

        last_days_ago = None
        for j in jobs:
            dc_dt = _parse_date(j["date_completed"])
            if dc_dt:
                days = (now - dc_dt).days
                if last_days_ago is None or days < last_days_ago:
                    last_days_ago = days

        customer_stats[cname_norm] = {
            "job_count":       len(jobs),
            "total_revenue":   total_rev,
            "avg_margin":      round(avg_gm, 2),
            "last_days_ago":   last_days_ago,
        }

    # ── 3. Sign type average prices (from warehouse billing on won quotes) ─────
    # We'll build this after labeling, but seed with all billing for now
    st_prices: dict[str, list[float]] = defaultdict(list)
    for j in all_jobs:
        if j["billing"] > 0:
            st = j["sign_type"] or j["sales_code"] or "OTHER"
            st_prices[st].append(j["billing"])
    sign_type_avg_prices: dict[str, float] = {
        st: statistics.mean(vals) for st, vals in st_prices.items() if vals
    }

    # ── 4. Load quotes and build labels ───────────────────────────────────────
    print("[bid_model] Loading quotes and building labels...")
    qt_path = _find_csv(QUOTE_PATHS)
    labeled_rows: list[dict] = []

    if qt_path:
        with open(qt_path, "r", encoding="utf-8", errors="replace") as f:
            for row in csv.DictReader(f):
                status = (row.get("currStatus") or "").strip()
                qno = str(row.get("quoteno") or "").strip()
                try:
                    ext_price = float(row.get("extPrice") or 0)
                except (ValueError, TypeError):
                    ext_price = 0.0

                qt_date_str = (row.get("qtDate") or "").strip()
                exp_date_str = (row.get("expDate") or "").strip()
                salesperson = (row.get("salesperson") or "").strip().upper()
                company = (row.get("company") or "").strip()

                # Labeling
                label: Optional[int] = None
                if status in ("220", "DS"):
                    label = 1
                elif status in ("240", "245", "250"):
                    label = 0
                elif status == "190":
                    if qno in wh_quote_nos:
                        label = 1
                    else:
                        qt_dt = _parse_date(qt_date_str)
                        if qt_dt:
                            age_days = (now - qt_dt).days
                            if age_days > 180:
                                label = 0
                        # else exclude (too recent / ambiguous)

                if label is None:
                    continue

                labeled_rows.append({
                    "quoteno":     qno,
                    "label":       label,
                    "ext_price":   ext_price,
                    "salesperson": salesperson,
                    "qt_date":     qt_date_str,
                    "exp_date":    exp_date_str,
                    "company":     company,
                    "sign_type":   quote_to_sign_type.get(qno, ""),
                })

    n_wins = sum(1 for r in labeled_rows if r["label"] == 1)
    n_losses = sum(1 for r in labeled_rows if r["label"] == 0)
    print(f"[bid_model]   {len(labeled_rows):,} labeled quotes "
          f"({n_wins:,} wins, {n_losses:,} losses)")
    overall_win_rate = n_wins / len(labeled_rows) if labeled_rows else 0.5

    # ── 5. Target encode salesperson (smoothed) ────────────────────────────────
    sp_wins: dict[str, int] = defaultdict(int)
    sp_total: dict[str, int] = defaultdict(int)
    for r in labeled_rows:
        sp = r["salesperson"] or "UNKNOWN"
        sp_total[sp] += 1
        if r["label"] == 1:
            sp_wins[sp] += 1

    # Bayesian smoothing: blend with global rate, k=20 pseudo-obs
    k = 20.0
    salesperson_win_rates: dict[str, float] = {}
    for sp, total in sp_total.items():
        raw_rate = sp_wins[sp] / total
        smoothed = (sp_wins[sp] + k * overall_win_rate) / (total + k)
        salesperson_win_rates[sp] = round(smoothed, 4)

    # ── 6. Feature engineering ─────────────────────────────────────────────────
    print("[bid_model] Engineering features...")

    def _engineer_features(r: dict) -> list[float]:
        """Produce the 12-element feature vector for a labeled row."""
        # price_log
        price_log = math.log1p(max(0, r["ext_price"]))

        # salesperson_encoded
        sp = r["salesperson"] or "UNKNOWN"
        sp_enc = salesperson_win_rates.get(sp, overall_win_rate)

        # quarter + cyclical month (sin/cos captures Dec≈Jan proximity)
        qt_dt = _parse_date(r["qt_date"])
        quarter = float((qt_dt.month - 1) // 3 + 1) if qt_dt else 2.5
        if qt_dt:
            month_sin = math.sin(2 * math.pi * qt_dt.month / 12)
            month_cos = math.cos(2 * math.pi * qt_dt.month / 12)
        else:
            month_sin = 0.0
            month_cos = 0.0

        # days_to_expiry
        exp_dt = _parse_date(r["exp_date"])
        if qt_dt and exp_dt:
            days_to_expiry = float(max(0, min(365, (exp_dt - qt_dt).days)))
        else:
            days_to_expiry = 30.0  # median fallback

        # Customer stats
        ckey = _fuzzy_lookup(r["company"], customer_stats) if r["company"] else None
        cstats = customer_stats.get(ckey) if ckey else None

        if cstats:
            customer_job_count = float(cstats["job_count"])
            customer_total_revenue_log = math.log1p(max(0, cstats["total_revenue"]))
            customer_avg_margin = float(cstats["avg_margin"])
            days_since_last_job = float(
                min(3650, cstats["last_days_ago"] or 3650)
            )
            is_repeat = 1.0
        else:
            customer_job_count = 0.0
            customer_total_revenue_log = 0.0
            customer_avg_margin = 0.0
            days_since_last_job = 3650.0
            is_repeat = 0.0

        # price_vs_type_avg
        st = r["sign_type"]
        st_avg = sign_type_avg_prices.get(st) if st else None
        if st_avg and st_avg > 0 and r["ext_price"] > 0:
            price_vs_type_avg = r["ext_price"] / st_avg
        else:
            price_vs_type_avg = 1.0  # neutral

        return [
            price_log,
            sp_enc,
            quarter,
            month_sin,
            month_cos,
            days_to_expiry,
            customer_job_count,
            customer_total_revenue_log,
            customer_avg_margin,
            days_since_last_job,
            is_repeat,
            price_vs_type_avg,
        ]

    X_raw: list[list[float]] = []
    y: list[int] = []
    qt_dates: list[Optional[datetime]] = []
    for r in labeled_rows:
        feats = _engineer_features(r)
        X_raw.append(feats)
        y.append(r["label"])
        qt_dates.append(_parse_date(r["qt_date"]))

    # ── 7. Scale ───────────────────────────────────────────────────────────────
    scaler = StandardScaler()
    X = scaler.fit_transform(X_raw)

    # ── 7b. Compute time-decay sample weights ────────────────────────────────
    # Exponential decay: w = 0.5^(years_ago / half_life)
    # Mitigates data artifact (old lost quotes purged → inflated win rates)
    # Combined with class weights for balanced + time-aware training
    from sklearn.utils.class_weight import compute_sample_weight

    gamma = 0.5 ** (1.0 / _HALF_LIFE_YEARS)
    time_weights = []
    for dt in qt_dates:
        if dt:
            years_ago = (now - dt).days / 365.25
            time_weights.append(gamma ** max(0, years_ago))
        else:
            time_weights.append(0.5)  # unknown date → median weight

    class_weights = compute_sample_weight("balanced", y)
    combined_weights = [cw * tw for cw, tw in zip(class_weights, time_weights)]

    avg_tw = sum(time_weights) / len(time_weights)
    print(f"[bid_model]   Time-decay: half_life={_HALF_LIFE_YEARS}y, "
          f"avg_weight={avg_tw:.3f}, min={min(time_weights):.4f}, max={max(time_weights):.4f}")

    # ── 8. Cross-validated metrics (manual loop to pass sample_weight) ────────
    import numpy as np

    print("[bid_model] Running 5-fold stratified cross-validation...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    X_np = np.array(X)
    y_np = np.array(y)
    w_np = np.array(combined_weights)
    y_prob_cv = np.zeros(len(y))

    for train_idx, test_idx in cv.split(X_np, y_np):
        fold_model = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
        fold_model.fit(X_np[train_idx], y_np[train_idx], sample_weight=w_np[train_idx])
        y_prob_cv[test_idx] = fold_model.predict_proba(X_np[test_idx])[:, 1]

    y_pred_cv = (y_prob_cv >= 0.5).astype(int)
    auc = roc_auc_score(y, y_prob_cv)
    brier = brier_score_loss(y, y_prob_cv)
    accuracy = sum(int(p == t) for p, t in zip(y_pred_cv, y)) / len(y)

    print(f"[bid_model]   CV AUC-ROC : {auc:.4f}")
    print(f"[bid_model]   CV Brier   : {brier:.4f}")
    print(f"[bid_model]   CV Accuracy: {accuracy:.4f}")

    # ── 9. Fit final model on all data with combined weights ──────────────────
    print("[bid_model] Training final model on full dataset (time-decay weighted)...")
    model = LogisticRegression(
        C=1.0, max_iter=1000, random_state=42
    )
    model.fit(X, y, sample_weight=combined_weights)

    # ── 10. Coefficients ───────────────────────────────────────────────────────
    coefs = dict(zip(_FEATURE_NAMES, model.coef_[0].tolist()))

    print("\n[bid_model] Feature coefficients (sorted by absolute impact):")
    for fname, coef in sorted(coefs.items(), key=lambda x: abs(x[1]), reverse=True):
        direction = "+" if coef >= 0 else "-"
        desc = _FEATURE_DESCRIPTIONS.get(fname, fname)
        print(f"  {direction}{abs(coef):.4f}  {fname:<30}  ({desc})")

    metrics = {
        "auc_roc":            round(auc, 4),
        "brier_score":        round(brier, 4),
        "cv_accuracy":        round(accuracy, 4),
        "n_train":            len(y),
        "n_wins":             n_wins,
        "n_losses":           n_losses,
        "overall_win_rate":   round(overall_win_rate, 4),
        "n_features":         len(_FEATURE_NAMES),
        "time_decay_half_life_years": _HALF_LIFE_YEARS,
        "avg_time_weight":    round(avg_tw, 4),
    }

    bundle = ModelBundle(
        model=model,
        scaler=scaler,
        feature_names=_FEATURE_NAMES,
        metrics=metrics,
        coefficients=coefs,
        salesperson_win_rates=salesperson_win_rates,
        sign_type_avg_prices=sign_type_avg_prices,
        customer_stats=customer_stats,
        overall_win_rate=overall_win_rate,
    )

    print(f"\n[bid_model] Model ready. "
          f"AUC={auc:.3f}, Brier={brier:.4f}, n={len(y):,}")
    return bundle


# ── Module-level training ──────────────────────────────────────────────────────

def _ensure_trained():
    """Load and train once; cache result. Called by all public functions."""
    global _MODEL_BUNDLE, _TRAINING_DONE, _TRAINING_ERROR
    if _TRAINING_DONE:
        return
    _TRAINING_DONE = True
    try:
        _MODEL_BUNDLE = train_model()
    except Exception as exc:
        _TRAINING_ERROR = str(exc)
        print(f"[bid_model] WARNING: Training failed — {exc}")
        print("[bid_model] predict_win_probability will return fallback scores.")


# Train eagerly on import (mirrors bid_scoring.py pattern)
_ensure_trained()


# ── Feature vector builder for inference ──────────────────────────────────────

def _build_inference_features(
    customer_name: str,
    sign_type: str,
    price: float,
    salesperson: Optional[str],
    bundle: ModelBundle,
    qt_date: Optional[datetime] = None,
    exp_date: Optional[datetime] = None,
) -> list[float]:
    """Build the 12-element feature vector for a new bid."""
    # price_log
    price_log = math.log1p(max(0, price))

    # salesperson_encoded
    sp = (salesperson or "").strip().upper() or "UNKNOWN"
    sp_enc = bundle.salesperson_win_rates.get(sp, bundle.overall_win_rate)

    # quarter + cyclical month
    if qt_date:
        quarter = float((qt_date.month - 1) // 3 + 1)
        month_sin = math.sin(2 * math.pi * qt_date.month / 12)
        month_cos = math.cos(2 * math.pi * qt_date.month / 12)
    else:
        quarter = 2.5
        month_sin = 0.0
        month_cos = 0.0

    # days_to_expiry
    if qt_date and exp_date:
        days_to_expiry = float(max(0, min(365, (exp_date - qt_date).days)))
    else:
        days_to_expiry = 30.0

    # Customer stats
    ckey = _fuzzy_lookup(customer_name, bundle.customer_stats) if customer_name else None
    cstats = bundle.customer_stats.get(ckey) if ckey else None

    if cstats:
        customer_job_count = float(cstats["job_count"])
        customer_total_revenue_log = math.log1p(max(0, cstats["total_revenue"]))
        customer_avg_margin = float(cstats["avg_margin"])
        days_since_last_job = float(min(3650, cstats["last_days_ago"] or 3650))
        is_repeat = 1.0
    else:
        customer_job_count = 0.0
        customer_total_revenue_log = 0.0
        customer_avg_margin = 0.0
        days_since_last_job = 3650.0
        is_repeat = 0.0

    # price_vs_type_avg
    st = sign_type.strip().upper() if sign_type else ""
    st_avg = bundle.sign_type_avg_prices.get(st)
    if st_avg and st_avg > 0 and price > 0:
        price_vs_type_avg = price / st_avg
    else:
        price_vs_type_avg = 1.0

    return [
        price_log,
        sp_enc,
        quarter,
        month_sin,
        month_cos,
        days_to_expiry,
        customer_job_count,
        customer_total_revenue_log,
        customer_avg_margin,
        days_since_last_job,
        is_repeat,
        price_vs_type_avg,
    ]


# ── Feature contribution decomposition ────────────────────────────────────────

def _decompose_contributions(
    feature_values_scaled: list[float],
    bundle: ModelBundle,
) -> dict[str, float]:
    """Return per-feature additive log-odds contributions.

    contribution[i] = coef[i] * scaled_value[i]
    These sum to the log-odds (plus intercept), so they are truly additive.
    """
    coef_vals = bundle.model.coef_[0]
    contributions = {}
    for fname, coef, val in zip(_FEATURE_NAMES, coef_vals, feature_values_scaled):
        contributions[fname] = round(float(coef * val), 4)
    return contributions


# ── Public API ─────────────────────────────────────────────────────────────────

def predict_win_probability(
    customer_name: str,
    sign_type: str,
    price: float,
    salesperson: Optional[str] = None,
    qt_date: Optional[datetime] = None,
    exp_date: Optional[datetime] = None,
) -> MLPrediction:
    """Predict win probability using the trained logistic regression model.

    Parameters
    ----------
    customer_name : str
        Customer name (fuzzy-matched against warehouse history).
    sign_type : str
        Sign type code (e.g. 'CLLIT', 'MONDF') or alias.
    price : float
        Quoted price in dollars.
    salesperson : str, optional
        Salesperson code (e.g. 'KENT', 'JEFF').
    qt_date : datetime, optional
        Quote date (defaults to today).
    exp_date : datetime, optional
        Expiry date (defaults to qt_date + 30 days).

    Returns
    -------
    MLPrediction
        Dataclass with win_probability, risk/positive factors,
        feature_contributions, and confidence.
    """
    if _MODEL_BUNDLE is None:
        # Training failed — return neutral fallback
        return MLPrediction(
            win_probability=0.5,
            confidence="low",
            risk_factors=["Model unavailable: " + (_TRAINING_ERROR or "unknown error")],
            model_available=False,
        )

    bundle = _MODEL_BUNDLE

    # Defaults for dates
    now = datetime.now()
    if qt_date is None:
        qt_date = now
    if exp_date is None:
        exp_date = datetime(qt_date.year, qt_date.month, qt_date.day)
        from datetime import timedelta
        exp_date = qt_date + timedelta(days=30)

    # Build raw feature vector
    raw_feats = _build_inference_features(
        customer_name=customer_name,
        sign_type=sign_type,
        price=price,
        salesperson=salesperson,
        bundle=bundle,
        qt_date=qt_date,
        exp_date=exp_date,
    )

    # Scale
    scaled_feats = bundle.scaler.transform([raw_feats])[0].tolist()

    # Predict
    prob = float(bundle.model.predict_proba([scaled_feats])[0][1])

    # Contributions
    contribs = _decompose_contributions(scaled_feats, bundle)

    # Feature values dict (unscaled, human-readable)
    feat_vals = dict(zip(_FEATURE_NAMES, raw_feats))

    # Interpret risk vs positive factors
    # A feature is "risk" if its contribution is negative (hurts win prob)
    # A feature is "positive" if its contribution is positive
    risk_factors: list[str] = []
    positive_factors: list[str] = []

    ckey = _fuzzy_lookup(customer_name, bundle.customer_stats) if customer_name else None
    cstats = bundle.customer_stats.get(ckey) if ckey else None

    for fname, contrib in sorted(contribs.items(), key=lambda x: x[1]):
        desc = _FEATURE_DESCRIPTIONS.get(fname, fname)
        val = feat_vals[fname]

        if fname == "price_log":
            label = f"Price ${price:,.0f} (log={val:.2f})"
        elif fname == "salesperson_encoded":
            sp = (salesperson or "UNKNOWN").upper()
            sp_wr = bundle.salesperson_win_rates.get(sp, bundle.overall_win_rate)
            label = f"Salesperson {sp} win rate {sp_wr:.1%}"
        elif fname == "customer_job_count":
            label = f"Customer job history: {int(val)} jobs"
        elif fname == "customer_avg_margin":
            label = f"Customer avg margin: {val:.1f}%"
        elif fname == "days_since_last_job":
            if val >= 3650:
                label = "No prior job history (new customer)"
            else:
                label = f"Last job {int(val)}d ago"
        elif fname == "is_repeat_customer":
            label = "Repeat customer" if val >= 1 else "New customer (no history)"
        elif fname == "price_vs_type_avg":
            st_avg = bundle.sign_type_avg_prices.get(sign_type.upper().strip(), 0)
            if st_avg:
                label = f"Price {val:.2f}x sign-type avg (avg=${st_avg:,.0f})"
            else:
                label = "No sign-type pricing benchmark"
        elif fname == "days_to_expiry":
            label = f"Quote expires in {int(val)}d"
        elif fname == "quarter":
            label = f"Q{int(val)} quote"
        else:
            label = f"{desc}: {val:.2f}"

        if contrib < -0.05:
            risk_factors.append(label)
        elif contrib > 0.05:
            positive_factors.append(label)

    # Confidence based on data density
    has_customer_data = cstats is not None and cstats.get("job_count", 0) >= 3
    st_known = sign_type.upper().strip() in bundle.sign_type_avg_prices
    sp_known = (salesperson or "").upper() in bundle.salesperson_win_rates

    if has_customer_data and st_known and sp_known:
        confidence = "high"
    elif has_customer_data or (st_known and sp_known):
        confidence = "medium"
    else:
        confidence = "low"

    return MLPrediction(
        win_probability=round(prob, 4),
        confidence=confidence,
        risk_factors=list(reversed(risk_factors)),  # worst first
        positive_factors=list(reversed(positive_factors)),  # best first
        feature_contributions=contribs,
        feature_values=feat_vals,
        model_available=True,
    )


def get_model_diagnostics() -> dict:
    """Return model health information and training statistics.

    Returns
    -------
    dict with engine state, metrics, coefficient summary, data coverage.
    """
    if _MODEL_BUNDLE is None:
        return {
            "engine": "bid_model v1.0",
            "status": "unavailable",
            "error": _TRAINING_ERROR or "not trained",
        }

    bundle = _MODEL_BUNDLE
    top_features = sorted(
        bundle.coefficients.items(), key=lambda x: abs(x[1]), reverse=True
    )[:5]

    return {
        "engine":               "bid_model v1.0",
        "status":               "ready",
        "model_type":           "LogisticRegression(balanced, C=1.0)",
        "n_features":           len(bundle.feature_names),
        "feature_names":        bundle.feature_names,
        "metrics":              bundle.metrics,
        "top_5_features":       {f: round(c, 4) for f, c in top_features},
        "salesperson_coverage": len(bundle.salesperson_win_rates),
        "sign_type_coverage":   len(bundle.sign_type_avg_prices),
        "customer_coverage":    len(bundle.customer_stats),
        "overall_win_rate":     bundle.overall_win_rate,
        "intercept":            round(float(bundle.model.intercept_[0]), 4),
    }


# ── Module self-test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print("bid_model.py — Logistic Regression Model Self-Test")
    print("=" * 70)

    diag = get_model_diagnostics()
    print(f"\nStatus : {diag['status']}")
    if diag["status"] == "ready":
        m = diag["metrics"]
        print(f"AUC-ROC: {m['auc_roc']:.4f}  (>0.70 = useful, >0.80 = good)")
        print(f"Brier  : {m['brier_score']:.4f}  (<0.25 = well-calibrated)")
        print(f"n_train: {m['n_train']:,}  ({m['n_wins']:,} wins, {m['n_losses']:,} losses)")
        print(f"Win %  : {m['overall_win_rate']:.1%}")
        print(f"\nTop 5 features by |coefficient|:")
        for feat, coef in diag["top_5_features"].items():
            print(f"  {coef:+.4f}  {feat}")
    print()

    # Test cases
    test_cases = [
        {
            "customer_name": "McDonald's",
            "sign_type":     "CLLIT",
            "price":         12_500,
            "salesperson":   "KENT",
            "label":         "Known repeat customer / top salesperson",
        },
        {
            "customer_name": "New Prospect LLC",
            "sign_type":     "MONDF",
            "price":         85_000,
            "salesperson":   "JEFF",
            "label":         "New customer / high price / avg salesperson",
        },
        {
            "customer_name": "Walgreens",
            "sign_type":     "POLLIT",
            "price":         35_000,
            "salesperson":   "MIKEE",
            "label":         "Possible repeat customer / pylon / top closer",
        },
        {
            "customer_name": "Unknown Startup",
            "sign_type":     "UNKNOWN",
            "price":         5_000,
            "salesperson":   None,
            "label":         "Unknown everything — should fallback gracefully",
        },
    ]

    for tc in test_cases:
        print(f"--- {tc['label']} ---")
        pred = predict_win_probability(
            customer_name=tc["customer_name"],
            sign_type=tc["sign_type"],
            price=tc["price"],
            salesperson=tc.get("salesperson"),
        )
        print(f"  Win probability : {pred.win_probability:.1%}")
        print(f"  Confidence      : {pred.confidence}")
        if pred.positive_factors:
            print(f"  Positive factors:")
            for pf in pred.positive_factors[:3]:
                print(f"    + {pf}")
        if pred.risk_factors:
            print(f"  Risk factors:")
            for rf in pred.risk_factors[:3]:
                print(f"    - {rf}")
        print(f"  Feature contribs (top 3 by |impact|):")
        top_contribs = sorted(
            pred.feature_contributions.items(),
            key=lambda x: abs(x[1]), reverse=True
        )[:3]
        for fname, c in top_contribs:
            print(f"    {c:+.4f}  {fname}")
        print()
