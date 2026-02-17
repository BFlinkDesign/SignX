import duckdb
db = duckdb.connect(r'C:\Scripts\signx-warehouse\warehouse\signx.duckdb')

print("=== Sign Types by Volume & Revenue ===\n")
rows = db.sql("""
    SELECT sign_type, 
           COUNT(*) as jobs,
           ROUND(SUM(billing),0) as total_revenue,
           ROUND(AVG(billing),0) as avg_revenue,
           ROUND(AVG(gm_percent),1) as avg_gm
    FROM so_contracts 
    WHERE sign_type IS NOT NULL 
      AND billing > 0
      AND work_order NOT LIKE 'SC%'
    GROUP BY sign_type 
    ORDER BY total_revenue DESC
""").fetchall()

print(f"{'Type':<20} {'Jobs':>6} {'Total Rev':>12} {'Avg Rev':>10} {'Avg GM%':>8}")
print("-" * 60)
for r in rows:
    print(f"{r[0]:<20} {r[1]:>6} ${r[2]:>11,.0f} ${r[3]:>9,.0f} {r[4]:>7.1f}%")

print(f"\n{'TOTAL':<20} {sum(r[1] for r in rows):>6} ${sum(r[2] for r in rows):>11,.0f}")
