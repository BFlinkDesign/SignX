"""
Phase 6: Eagle Sign Decision Intelligence Engine
=================================================
8 analytical modules querying the unified warehouse (eagle_warehouse.db).

Modules:
  A. Estimating Accuracy Engine   — Est vs actual labor by sign type/estimator
  B. Shadow Burden Model          — ERP burden vs calculated overhead (needs user input)
  C. Dead Stock Report            — Inventory not issued in N days
  D. Win/Loss Ratio               — Quote conversion (blocked until Phase 2 quote data)
  E. True Job Profitability       — Full cost picture per WO and customer
  F. Root Cause Decomposition     — Mix/rate/productivity efficiency breakdown
  G. Material Cost Tracking       — Material costs over time by part/sign type
  H. Capacity Model               — Available vs utilized hours by department

Usage:
  python decision_engine.py                  # Run all modules, output reports
  python decision_engine.py --module A       # Run single module
  python decision_engine.py --format csv     # Output as CSV (default: markdown)
  python decision_engine.py --year 2024      # Filter to specific year
"""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_PATH = Path(r"C:\Scripts\signx-warehouse\warehouse\production\eagle_warehouse.db")
REPORT_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\reports")

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("engine")


def get_conn(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Module A: Estimating Accuracy Engine
# ---------------------------------------------------------------------------


def estimating_accuracy(conn: sqlite3.Connection, year: int | None = None) -> pd.DataFrame:
    """Compare estimated vs actual labor hours per WO, segmented by sign type and estimator."""
    year_filter = f"AND substr(w.date_completed, 1, 4) = '{year}'" if year else ""

    query = f"""
    SELECT
        w.wo_number,
        w.sign_type,
        w.estimator,
        w.date_completed,
        w.customer_name,
        w.total_labor_cost,
        w.total_cost,
        w.quoted_price,
        w.billing,
        w.gross_margin,
        w.gm_pct,
        SUM(ls.est_hrs) as total_est_hrs,
        SUM(ls.actual_hrs) as total_actual_hrs,
        SUM(ls.hrs_variance) as total_hrs_variance,
        SUM(ls.est_cost) as total_est_cost,
        SUM(ls.job_cost) as total_job_cost
    FROM work_orders w
    LEFT JOIN labor_summary ls ON w.wo_number = ls.wo_number
    WHERE ls.est_hrs IS NOT NULL AND ls.est_hrs > 0
        {year_filter}
    GROUP BY w.wo_number
    HAVING total_est_hrs > 0
    ORDER BY w.date_completed DESC
    """
    df = pd.read_sql_query(query, conn)

    if df.empty:
        return df

    df["variance_pct"] = ((df["total_actual_hrs"] - df["total_est_hrs"]) / df["total_est_hrs"] * 100).round(1)
    df["over_under"] = df["variance_pct"].apply(
        lambda x: "OVER" if x > 15 else ("UNDER" if x < -15 else "OK")
    )
    return df


def estimating_accuracy_summary(conn: sqlite3.Connection, year: int | None = None) -> dict:
    """Summarize estimating accuracy by sign type and estimator."""
    df = estimating_accuracy(conn, year)
    if df.empty:
        return {"status": "no_data", "message": "No WOs with est_hrs found"}

    results = {}

    # By sign type
    by_type = df.groupby("sign_type").agg(
        wo_count=("wo_number", "count"),
        avg_variance_pct=("variance_pct", "mean"),
        median_variance_pct=("variance_pct", "median"),
        over_count=("over_under", lambda x: (x == "OVER").sum()),
        under_count=("over_under", lambda x: (x == "UNDER").sum()),
    ).round(1).sort_values("wo_count", ascending=False)
    results["by_sign_type"] = by_type

    # By estimator
    by_est = df.groupby("estimator").agg(
        wo_count=("wo_number", "count"),
        avg_variance_pct=("variance_pct", "mean"),
        median_variance_pct=("variance_pct", "median"),
        total_est_hrs=("total_est_hrs", "sum"),
        total_actual_hrs=("total_actual_hrs", "sum"),
    ).round(1).sort_values("wo_count", ascending=False)
    by_est["overall_variance_pct"] = (
        (by_est["total_actual_hrs"] - by_est["total_est_hrs"]) / by_est["total_est_hrs"] * 100
    ).round(1)
    results["by_estimator"] = by_est

    # Worst sign types (consistently over)
    worst = by_type[by_type["avg_variance_pct"] > 15].sort_values("avg_variance_pct", ascending=False)
    results["worst_sign_types"] = worst

    # Detail data
    results["detail"] = df
    results["total_wos"] = len(df)
    results["avg_variance"] = df["variance_pct"].mean().round(1)

    return results


# ---------------------------------------------------------------------------
# Module B: Shadow Burden Model
# ---------------------------------------------------------------------------


def shadow_burden(conn: sqlite3.Connection,
                  shop_overhead_monthly: float | None = None,
                  billable_hrs_monthly: float | None = None) -> pd.DataFrame:
    """Compare ERP burden vs calculated burden.

    If shop_overhead_monthly and billable_hrs_monthly are provided,
    calculates shadow burden rate. Otherwise shows ERP burden only.
    """
    query = """
    SELECT
        wo_number,
        sign_type,
        estimator,
        date_completed,
        total_labor_cost,
        total_burden_cost,
        total_cost,
        quoted_price,
        billing,
        gross_margin,
        gm_pct
    FROM work_orders
    WHERE total_burden_cost IS NOT NULL AND total_labor_cost IS NOT NULL
        AND total_labor_cost > 0
    ORDER BY date_completed DESC
    """
    df = pd.read_sql_query(query, conn)
    if df.empty:
        return df

    df["erp_burden_rate"] = (df["total_burden_cost"] / df["total_labor_cost"]).round(3)

    if shop_overhead_monthly and billable_hrs_monthly:
        overhead_rate = shop_overhead_monthly / billable_hrs_monthly
        # Get actual hours per WO from labor_summary
        hrs_query = """
        SELECT wo_number, SUM(actual_hrs) as actual_hrs
        FROM labor_summary
        GROUP BY wo_number
        """
        hrs_df = pd.read_sql_query(hrs_query, conn)
        df = df.merge(hrs_df, on="wo_number", how="left")
        df["shadow_burden"] = (df["actual_hrs"] * overhead_rate).round(2)
        df["burden_leak"] = (df["total_burden_cost"] - df["shadow_burden"]).round(2)
        df["shadow_overhead_rate"] = overhead_rate
    else:
        log.warning("  Shadow Burden: No overhead data provided — showing ERP burden only")
        log.warning("  Provide --shop-overhead and --billable-hrs for full analysis")

    return df


# ---------------------------------------------------------------------------
# Module C: Dead Stock Report
# ---------------------------------------------------------------------------


def dead_stock(conn: sqlite3.Connection, days_threshold: int = 365) -> pd.DataFrame:
    """Items with qty > 0 but not issued in threshold period."""
    query = """
    SELECT
        i.part_number,
        i.description,
        i.inventory_type,
        i.qty_on_hand,
        i.uom,
        i.acctg_cost,
        i.warehouse_location,
        i.qty_on_hand * COALESCE(i.acctg_cost, 0) as tied_up_capital
    FROM inventory i
    WHERE i.qty_on_hand > 0
    ORDER BY tied_up_capital DESC
    """
    df = pd.read_sql_query(query, conn)
    # Note: last_issued_date not available in current inventory data
    # Will be enrichable from Phase 2 inventory transaction history
    return df


# ---------------------------------------------------------------------------
# Module D: Win/Loss Ratio (Quote Conversion)
# ---------------------------------------------------------------------------


def quote_conversion(conn: sqlite3.Connection) -> dict:
    """Quote conversion stats. BLOCKED until Phase 2 Quote Status Report."""
    # Check if quotes table exists and has data
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM quotes")
        count = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        count = 0

    if count == 0:
        return {
            "status": "blocked",
            "message": "Quote data not yet available. Phase 2 must scrape "
                       "Quote Status Report (ID 1441869) which includes "
                       "Won/Lost/Void/Cancelled quotes.",
            "action_needed": "Run tracer_bullet.py then scrape_informer.py",
        }

    # When data is available:
    query = """
    SELECT status, COUNT(*) as count, SUM(quoted_total) as total_value
    FROM quotes
    GROUP BY status
    """
    df = pd.read_sql_query(query, conn)
    total = df["count"].sum()
    won = df[df["status"] == "Won"]["count"].sum() if "Won" in df["status"].values else 0

    return {
        "status": "ok",
        "close_rate": round(won / total, 3) if total > 0 else 0,
        "by_status": df.to_dict("records"),
        "total_quotes": total,
    }


# ---------------------------------------------------------------------------
# Module E: True Job Profitability
# ---------------------------------------------------------------------------


def job_profitability(conn: sqlite3.Connection, year: int | None = None) -> pd.DataFrame:
    """Full cost picture per WO: labor + material + outplant + burden vs revenue."""
    year_filter = f"AND substr(w.date_completed, 1, 4) = '{year}'" if year else ""

    query = f"""
    SELECT
        w.wo_number,
        w.customer_id,
        w.customer_name,
        w.sign_type,
        w.estimator,
        w.date_completed,
        w.total_labor_cost,
        w.total_burden_cost,
        w.total_material_cost,
        w.total_outplant_cost,
        w.total_use_tax,
        w.total_cost,
        w.quoted_price,
        w.sale_price,
        w.billing,
        w.gross_margin,
        w.gm_pct,
        COALESCE(w.billing, w.quoted_price, w.sale_price) as revenue
    FROM work_orders w
    WHERE w.total_cost IS NOT NULL AND w.total_cost > 0
        {year_filter}
    ORDER BY w.gross_margin ASC
    """
    df = pd.read_sql_query(query, conn)
    if df.empty:
        return df

    df["true_margin"] = (df["revenue"] - df["total_cost"]).round(2)
    df["true_margin_pct"] = (
        (df["true_margin"] / df["revenue"] * 100).round(1)
        .where(df["revenue"] > 0)
    )
    return df


def customer_profitability(conn: sqlite3.Connection, year: int | None = None) -> pd.DataFrame:
    """Roll up job profitability to customer level."""
    df = job_profitability(conn, year)
    if df.empty:
        return df

    by_cust = df.groupby(["customer_id", "customer_name"]).agg(
        wo_count=("wo_number", "count"),
        total_revenue=("revenue", "sum"),
        total_cost=("total_cost", "sum"),
        total_margin=("true_margin", "sum"),
        avg_margin_pct=("true_margin_pct", "mean"),
        total_labor=("total_labor_cost", "sum"),
        total_material=("total_material_cost", "sum"),
    ).round(2).sort_values("total_revenue", ascending=False)

    by_cust["margin_pct"] = (by_cust["total_margin"] / by_cust["total_revenue"] * 100).round(1)
    return by_cust.reset_index()


# ---------------------------------------------------------------------------
# Module F: Root Cause Decomposition
# ---------------------------------------------------------------------------


def efficiency_decomposition(conn: sqlite3.Connection, year1: int, year2: int) -> pd.DataFrame:
    """Break efficiency change between two years into components by department."""
    query = """
    SELECT
        ls.work_dept,
        substr(w.date_completed, 1, 4) as year,
        w.sign_type,
        COUNT(DISTINCT w.wo_number) as wo_count,
        SUM(ls.actual_hrs) as total_hrs,
        SUM(ls.job_cost) as total_cost,
        AVG(ls.actual_hrs) as avg_hrs_per_wo
    FROM labor_summary ls
    JOIN work_orders w ON ls.wo_number = w.wo_number
    WHERE substr(w.date_completed, 1, 4) IN (?, ?)
        AND ls.actual_hrs > 0
    GROUP BY ls.work_dept, year, w.sign_type
    """
    df = pd.read_sql_query(query, conn, params=[str(year1), str(year2)])
    if df.empty:
        return df

    # Pivot to compare years
    y1 = df[df["year"] == str(year1)].copy()
    y2 = df[df["year"] == str(year2)].copy()

    # Department-level summary
    dept_summary = df.groupby(["work_dept", "year"]).agg(
        wo_count=("wo_count", "sum"),
        total_hrs=("total_hrs", "sum"),
        total_cost=("total_cost", "sum"),
    ).reset_index()

    pivot = dept_summary.pivot(index="work_dept", columns="year", values=["wo_count", "total_hrs"])
    pivot.columns = [f"{col[0]}_{col[1]}" for col in pivot.columns]

    # Calculate hrs/WO for each year
    for y in [str(year1), str(year2)]:
        if f"total_hrs_{y}" in pivot.columns and f"wo_count_{y}" in pivot.columns:
            pivot[f"hrs_per_wo_{y}"] = (pivot[f"total_hrs_{y}"] / pivot[f"wo_count_{y}"]).round(2)

    col1 = f"hrs_per_wo_{year1}"
    col2 = f"hrs_per_wo_{year2}"
    if col1 in pivot.columns and col2 in pivot.columns:
        pivot["change_pct"] = ((pivot[col2] - pivot[col1]) / pivot[col1] * 100).round(1)
        pivot["trend"] = pivot["change_pct"].apply(
            lambda x: "IMPROVING" if x < -5 else ("LOSING EFF" if x > 5 else "STABLE")
        )

    return pivot.reset_index()


# ---------------------------------------------------------------------------
# Module G: Material Cost Tracking
# ---------------------------------------------------------------------------


def material_cost_trend(conn: sqlite3.Connection, sign_type: str | None = None) -> pd.DataFrame:
    """Track material costs over time by sign type."""
    sign_filter = f"AND w.sign_type = '{sign_type}'" if sign_type else ""

    query = f"""
    SELECT
        substr(w.date_completed, 1, 4) as year,
        w.sign_type,
        COUNT(DISTINCT m.wo_number) as wo_count,
        SUM(m.job_cost) as total_material_cost,
        AVG(m.job_cost) as avg_material_cost,
        COUNT(*) as line_count
    FROM material_transactions m
    JOIN work_orders w ON m.wo_number = w.wo_number
    WHERE w.date_completed IS NOT NULL
        AND m.job_cost IS NOT NULL
        {sign_filter}
    GROUP BY year, w.sign_type
    HAVING wo_count >= 3
    ORDER BY year, w.sign_type
    """
    return pd.read_sql_query(query, conn)


def material_as_pct_of_cost(conn: sqlite3.Connection) -> pd.DataFrame:
    """Material cost as % of total job cost by sign type."""
    query = """
    SELECT
        w.sign_type,
        COUNT(*) as wo_count,
        AVG(w.total_material_cost) as avg_material_cost,
        AVG(w.total_cost) as avg_total_cost,
        AVG(CASE WHEN w.total_cost > 0
            THEN w.total_material_cost * 100.0 / w.total_cost
            ELSE NULL END) as material_pct_of_cost
    FROM work_orders w
    WHERE w.total_cost > 0 AND w.total_material_cost IS NOT NULL
        AND w.sign_type IS NOT NULL
    GROUP BY w.sign_type
    HAVING wo_count >= 5
    ORDER BY material_pct_of_cost DESC
    """
    df = pd.read_sql_query(query, conn)
    df = df.round(2)
    return df


# ---------------------------------------------------------------------------
# Module H: Capacity Model
# ---------------------------------------------------------------------------


def capacity_analysis(conn: sqlite3.Connection, year: int | None = None) -> pd.DataFrame:
    """Available vs utilized capacity by department."""
    year_val = year or datetime.now().year
    year_filter = f"AND substr(w.date_completed, 1, 4) = '{year_val}'"

    query = f"""
    SELECT
        ls.work_dept,
        COUNT(DISTINCT ld.employee_name) as active_employees,
        SUM(ls.actual_hrs) as utilized_hrs,
        SUM(ls.est_hrs) as estimated_hrs,
        COUNT(DISTINCT ls.wo_number) as wo_count
    FROM labor_summary ls
    LEFT JOIN labor_detail ld ON ls.wo_number = ld.wo_number AND ls.work_dept = ld.work_dept
    JOIN work_orders w ON ls.wo_number = w.wo_number
    WHERE ls.actual_hrs > 0
        {year_filter}
    GROUP BY ls.work_dept
    ORDER BY utilized_hrs DESC
    """
    df = pd.read_sql_query(query, conn)
    if df.empty:
        return df

    # Available = active_employees * 2080 hrs/yr
    df["available_hrs"] = df["active_employees"] * 2080
    df["utilization_pct"] = (df["utilized_hrs"] / df["available_hrs"] * 100).round(1)
    df["slack_hrs"] = (df["available_hrs"] - df["utilized_hrs"]).round(0)

    return df


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


def generate_report(conn: sqlite3.Connection, year: int | None = None) -> str:
    """Generate full decision intelligence report as markdown."""
    lines = []
    lines.append(f"# Eagle Sign Decision Intelligence Report")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Year filter: {year or 'All time'}")
    lines.append("")

    # Module A
    lines.append("## A. Estimating Accuracy")
    results = estimating_accuracy_summary(conn, year)
    if results.get("status") == "no_data":
        lines.append("No work orders with estimated hours found.")
    else:
        lines.append(f"Total WOs analyzed: {results['total_wos']:,}")
        lines.append(f"Average variance: {results['avg_variance']}%")
        lines.append("")

        lines.append("### By Estimator")
        if "by_estimator" in results:
            lines.append(results["by_estimator"].to_markdown())
        lines.append("")

        lines.append("### By Sign Type (worst overruns)")
        if "worst_sign_types" in results and not results["worst_sign_types"].empty:
            lines.append(results["worst_sign_types"].head(10).to_markdown())
        else:
            lines.append("No sign types consistently over-estimated by >15%.")
        lines.append("")

    # Module B
    lines.append("## B. Shadow Burden Model")
    burden_df = shadow_burden(conn)
    if not burden_df.empty:
        avg_burden_rate = burden_df["erp_burden_rate"].mean()
        lines.append(f"Average ERP burden rate: {avg_burden_rate:.2f}x labor cost")
        lines.append(f"WOs analyzed: {len(burden_df):,}")
        lines.append("")
        # Top 10 highest burden rates
        top_burden = burden_df.nlargest(10, "erp_burden_rate")[
            ["wo_number", "sign_type", "total_labor_cost", "total_burden_cost", "erp_burden_rate"]
        ]
        lines.append("### Highest Burden Rate WOs")
        lines.append(top_burden.to_markdown(index=False))
    else:
        lines.append("No burden data available.")
    lines.append("")

    # Module C
    lines.append("## C. Dead Stock / Inventory")
    stock_df = dead_stock(conn)
    if not stock_df.empty:
        total_capital = stock_df["tied_up_capital"].sum()
        lines.append(f"Items with stock on hand: {len(stock_df):,}")
        lines.append(f"Total tied-up capital: ${total_capital:,.2f}")
        lines.append("")
        lines.append("### Top 20 by Tied-Up Capital")
        lines.append(stock_df.head(20).to_markdown(index=False))
    else:
        lines.append("No inventory data available.")
    lines.append("")

    # Module D
    lines.append("## D. Win/Loss Ratio")
    quote_data = quote_conversion(conn)
    if quote_data["status"] == "blocked":
        lines.append(f"**BLOCKED**: {quote_data['message']}")
    else:
        lines.append(f"Close rate: {quote_data['close_rate']:.1%}")
        lines.append(f"Total quotes: {quote_data['total_quotes']:,}")
    lines.append("")

    # Module E
    lines.append("## E. True Job Profitability")
    prof_df = job_profitability(conn, year)
    if not prof_df.empty:
        lines.append(f"WOs analyzed: {len(prof_df):,}")
        lines.append(f"Average margin: {prof_df['true_margin_pct'].mean():.1f}%")
        lines.append("")

        # Worst jobs
        worst = prof_df.nsmallest(10, "true_margin")[
            ["wo_number", "customer_name", "sign_type", "revenue", "total_cost", "true_margin", "true_margin_pct"]
        ]
        lines.append("### 10 Worst Margin Jobs")
        lines.append(worst.to_markdown(index=False))
        lines.append("")

        # Customer profitability
        cust_df = customer_profitability(conn, year)
        if not cust_df.empty:
            lines.append("### Top 20 Customers by Revenue")
            lines.append(cust_df.head(20).to_markdown(index=False))
            lines.append("")

            lines.append("### Bottom 10 Customers by Margin %")
            bottom = cust_df[cust_df["wo_count"] >= 3].nsmallest(10, "margin_pct")
            lines.append(bottom.to_markdown(index=False))
    else:
        lines.append("No profitability data available.")
    lines.append("")

    # Module F
    lines.append("## F. Efficiency Decomposition")
    # Compare last 2 full years
    curr_year = datetime.now().year
    eff_df = efficiency_decomposition(conn, curr_year - 2, curr_year - 1)
    if not eff_df.empty:
        lines.append(f"Comparing {curr_year - 2} vs {curr_year - 1} (hrs/WO by department)")
        lines.append(eff_df.to_markdown(index=False))
    else:
        lines.append("Insufficient data for decomposition.")
    lines.append("")

    # Module G
    lines.append("## G. Material Cost Analysis")
    mat_pct = material_as_pct_of_cost(conn)
    if not mat_pct.empty:
        lines.append("### Material as % of Total Cost by Sign Type")
        lines.append(mat_pct.to_markdown(index=False))
    else:
        lines.append("No material cost data available.")
    lines.append("")

    # Module H
    lines.append("## H. Capacity Model")
    cap_df = capacity_analysis(conn, year)
    if not cap_df.empty:
        lines.append(f"Year: {year or datetime.now().year}")
        lines.append(cap_df.to_markdown(index=False))
    else:
        lines.append("No capacity data available.")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Phase 6: Decision Intelligence Engine")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--module", type=str, help="Run single module (A-H)")
    parser.add_argument("--year", type=int, help="Filter to specific year")
    parser.add_argument("--format", choices=["markdown", "csv"], default="markdown")
    parser.add_argument("--output-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--shop-overhead", type=float, help="Monthly shop overhead for burden model")
    parser.add_argument("--billable-hrs", type=float, help="Monthly billable hours for burden model")
    args = parser.parse_args()

    if not args.db.exists():
        log.error(f"Database not found: {args.db}")
        log.error("Run build_warehouse.py first.")
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    conn = get_conn(args.db)

    log.info("=" * 60)
    log.info("DECISION INTELLIGENCE ENGINE")
    log.info("=" * 60)
    log.info(f"  Database: {args.db}")
    log.info(f"  Year filter: {args.year or 'All time'}")
    log.info(f"  Output: {args.output_dir}")
    log.info("")

    if args.module:
        # Run single module
        module = args.module.upper()
        log.info(f"Running module {module}...")

        if module == "A":
            results = estimating_accuracy_summary(conn, args.year)
            if results.get("by_estimator") is not None:
                print("\n=== By Estimator ===")
                print(results["by_estimator"].to_string())
                print(f"\n=== By Sign Type (worst) ===")
                if not results["worst_sign_types"].empty:
                    print(results["worst_sign_types"].to_string())
        elif module == "B":
            df = shadow_burden(conn, args.shop_overhead, args.billable_hrs)
            if not df.empty:
                print(f"Average ERP burden rate: {df['erp_burden_rate'].mean():.3f}")
                print(df.head(20).to_string())
        elif module == "C":
            df = dead_stock(conn)
            print(f"Items with stock: {len(df)}")
            print(f"Tied-up capital: ${df['tied_up_capital'].sum():,.2f}")
            print(df.head(20).to_string())
        elif module == "D":
            result = quote_conversion(conn)
            print(json.dumps(result, indent=2))
        elif module == "E":
            df = job_profitability(conn, args.year)
            print(f"WOs: {len(df)}, Avg margin: {df['true_margin_pct'].mean():.1f}%")
            print(df.head(20).to_string())
        elif module == "F":
            curr = datetime.now().year
            df = efficiency_decomposition(conn, curr - 2, curr - 1)
            print(df.to_string())
        elif module == "G":
            df = material_as_pct_of_cost(conn)
            print(df.to_string())
        elif module == "H":
            df = capacity_analysis(conn, args.year)
            print(df.to_string())
        else:
            log.error(f"Unknown module: {module}. Use A-H.")
    else:
        # Run all modules and generate full report
        log.info("Generating full report...")
        report = generate_report(conn, args.year)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = args.output_dir / f"decision_report_{timestamp}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        log.info(f"Report written: {report_path}")
        print(report)

    conn.close()


if __name__ == "__main__":
    main()
