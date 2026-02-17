"""Temp query: WO 9719 contract + Central Iowa Trails search."""
import duckdb

con = duckdb.connect("C:/Scripts/signx-warehouse/warehouse/signx.duckdb", read_only=True)


def fmt_sale(v):
    return f"${v:,.2f}" if v else "N/A"


# WO 9719 contract info
print("=== WO 9719 Contract ===")
c = con.execute("""
    SELECT work_order, customer_name, sign_type, sale_price, description
    FROM so_contracts WHERE work_order LIKE '9719%'
""").fetchall()
for row in c:
    print(f"  WO: {row[0]}  Cust: {row[1]}  Type: {row[2]}  Sale: {fmt_sale(row[3])}  Desc: {row[4]}")

print()

# Central Iowa Trails - Ankeny comparable
print("=== Central Iowa Trails Search ===")
r = con.execute("""
    SELECT work_order, customer_name, sign_type, sale_price, description
    FROM so_contracts
    WHERE LOWER(customer_name) LIKE '%central iowa%'
       OR LOWER(customer_name) LIKE '%trail%'
       OR LOWER(description) LIKE '%central iowa%'
       OR LOWER(description) LIKE '%trail%'
    ORDER BY work_order DESC
    LIMIT 20
""").fetchall()
if r:
    for row in r:
        print(f"  WO: {row[0]:12s}  Cust: {(row[1] or ''):35s}  Type: {(row[2] or ''):8s}  Sale: {fmt_sale(row[3]):>12s}  Desc: {row[4]}")
else:
    print("  No matches for 'central iowa' or 'trail'")

print()

# Also pull WO 9719.2 labor summary (already got it, but with contract context)
print("=== WO 9719.2 Labor (Cost Summary D) ===")
r2 = con.execute("""
    SELECT work_code, description, est_hours, actual_hours, variance_hours,
           est_cost, job_cost, cost_variance
    FROM so_contract_labor
    WHERE wo_number = '9719.2'
    ORDER BY work_code
""").fetchall()
tot_est = tot_act = tot_est_cost = tot_job_cost = 0
print(f"  {'Code':>6s} {'Description':30s} {'Est':>7s} {'Actual':>7s} {'Var':>7s}  {'Est$':>9s} {'Actual$':>9s} {'Var$':>9s}")
for row in r2:
    est_c = row[5] or 0
    job_c = row[6] or 0
    cost_v = row[7] or 0
    print(f"  {row[0]:>6s} {(row[1] or ''):30s} {row[2]:7.2f} {row[3]:7.2f} {row[4]:7.2f}  {est_c:9.2f} {job_c:9.2f} {cost_v:9.2f}")
    tot_est += row[2]
    tot_act += row[3]
    tot_est_cost += est_c
    tot_job_cost += job_c
print(f"  {'':>6s} {'TOTAL':30s} {tot_est:7.2f} {tot_act:7.2f} {tot_act-tot_est:7.2f}  {tot_est_cost:9.2f} {tot_job_cost:9.2f} {tot_job_cost-tot_est_cost:9.2f}")

con.close()
