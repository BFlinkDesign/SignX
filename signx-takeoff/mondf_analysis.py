import duckdb
db = duckdb.connect(r'C:\Scripts\signx-warehouse\warehouse\signx.duckdb')

print("=== MONDF Work Code Breakdown ===\n")
rows = db.sql("""
    SELECT l.work_code, l.description,
           COUNT(*) as jobs,
           ROUND(AVG(l.actual_hours),2) as avg_actual,
           ROUND(AVG(l.est_hours),2) as avg_estimated,
           ROUND(AVG(l.actual_hours) - AVG(l.est_hours),2) as avg_variance
    FROM so_contract_labor l
    JOIN so_contracts s ON l.wo_number = s.work_order
    WHERE s.sign_type = 'MONDF'
      AND l.actual_hours > 0
    GROUP BY l.work_code, l.description
    ORDER BY jobs DESC
""").fetchall()

print(f"{'Code':<8} {'Description':<30} {'Jobs':>5} {'AvgAct':>8} {'AvgEst':>8} {'Variance':>9}")
print("-" * 75)
for r in rows:
    print(f"{r[0]:<8} {r[1]:<30} {r[2]:>5} {r[3]:>8.2f} {r[4]:>8.2f} {r[5]:>+9.2f}")
