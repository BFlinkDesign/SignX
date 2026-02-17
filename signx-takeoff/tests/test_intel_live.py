"""
test_intel_live.py — Live validation of customer_intel.py against real warehouse data.

Run: python tests/test_intel_live.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from customer_intel import (
    find_similar_jobs,
    get_customer_profile,
    get_market_intel,
    warehouse_stats,
)

PASS = 0
FAIL = 0


def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {label}")
    else:
        FAIL += 1
        print(f"  FAIL: {label} — {detail}")


print("=" * 70)
print("CUSTOMER INTELLIGENCE — LIVE DATA VALIDATION")
print("=" * 70)

# ── 1. Warehouse loads ────────────────────────────────────────────────────

print("\n--- Warehouse Stats ---")
stats = warehouse_stats()
check("Warehouse loaded", stats["loaded"])
check("27K+ jobs", stats["total_jobs"] >= 27000, f"got {stats['total_jobs']}")
check("Revenue > $50M", stats["total_revenue"] > 50_000_000, f"got ${stats['total_revenue']:,.0f}")
check("3000+ customers", stats["unique_customers"] >= 3000, f"got {stats['unique_customers']}")

# ── 2. Known customer profiles ───────────────────────────────────────────

print("\n--- Customer Profile: CAT SCALE (biggest customer) ---")
p = get_customer_profile("CAT SCALE")
check("Profile found", p is not None)
if p:
    check("2000+ jobs", p.total_jobs >= 2000, f"got {p.total_jobs}")
    check("Revenue > $20M", p.total_revenue > 20_000_000, f"got ${p.total_revenue:,.0f}")
    check("Key Account", p.relationship_label == "Key Account", f"got {p.relationship_label}")
    check("Top type is POLLIT", p.top_sign_type == "POLLIT", f"got {p.top_sign_type}")
    check("Has insights", len(p.insights) > 0, f"got {len(p.insights)}")
    check("Has locations", len(p.locations) > 0, f"got {len(p.locations)}")
    check("Has recent jobs", len(p.recent_jobs) > 0)
    check("GM% in range 30-60", 30 <= p.avg_gm_pct <= 60, f"got {p.avg_gm_pct}")

print("\n--- Customer Profile: TACO JOHN'S OF IOWA ---")
p2 = get_customer_profile("TACO JOHN'S OF IOWA")
check("Profile found", p2 is not None)
if p2:
    check("400+ jobs", p2.total_jobs >= 400, f"got {p2.total_jobs}")
    check("Has sign type breakdown", len(p2.sign_type_breakdown) > 0)

# ── 3. Fuzzy matching ────────────────────────────────────────────────────

print("\n--- Fuzzy Customer Matching ---")
fuzzy_tests = [
    ("Cat Scale", "CAT SCALE"),
    ("cat scale", "CAT SCALE"),
    ("Taco Johns", "TACO JOHN"),
    ("Availa", "AVAILA"),
    ("Git N Go", "GIT N GO"),
    ("Iowa Events", "IOWA EVENTS"),
    ("Van Meter", "VAN METER"),
    ("Charley", "CHARLEY"),
]
for query, expected_contains in fuzzy_tests:
    result = get_customer_profile(query)
    if result:
        found_name = result.customer_name.upper()
        match = expected_contains.upper() in found_name
        check(
            f'"{query}" -> {result.customer_name}',
            match,
            f"expected to contain '{expected_contains}'",
        )
    else:
        check(f'"{query}" found', False, "returned None")

# ── 4. Similar jobs ──────────────────────────────────────────────────────

print("\n--- Similar Jobs: MONUMENT at ~$6K ---")
similar = find_similar_jobs("MONUMENT", revenue_estimate=6000, max_results=5)
check("Found similar jobs", len(similar) > 0, f"got {len(similar)}")
if similar:
    check("All have WO numbers", all(s.work_order for s in similar))
    check("All have billing > 0", all(s.billing > 0 for s in similar))
    check("Sorted by similarity", similar[0].similarity_score >= similar[-1].similarity_score)
    # Revenue should be reasonably close to $6K
    revenues = [s.billing for s in similar]
    check(
        "Revenue range reasonable",
        min(revenues) < 20000,
        f"closest revenue: ${min(revenues):,.0f}",
    )
    for s in similar[:3]:
        print(f"    WO {s.work_order} | {s.customer[:30]} | {s.sign_type} | ${s.billing:,.0f} | {s.gm_pct}% | sim={s.similarity_score}")

print("\n--- Similar Jobs: CHANNEL_LETTER at ~$3.5K ---")
similar_cl = find_similar_jobs("CHANNEL_LETTER", revenue_estimate=3500, max_results=5)
check("Found CL similar jobs", len(similar_cl) > 0, f"got {len(similar_cl)}")
if similar_cl:
    for s in similar_cl[:3]:
        print(f"    WO {s.work_order} | {s.customer[:30]} | {s.sign_type} | ${s.billing:,.0f} | {s.gm_pct}% | sim={s.similarity_score}")

# ── 5. Market intel ──────────────────────────────────────────────────────

print("\n--- Market Intel: PYLON ---")
mkt = get_market_intel("PYLON")
check("Market data found", mkt is not None)
if mkt:
    check("2000+ pylon jobs", mkt.total_jobs >= 2000, f"got {mkt.total_jobs}")
    check("Avg revenue > $5K", mkt.avg_revenue > 5000, f"got ${mkt.avg_revenue:,.0f}")
    check("Has top customers", len(mkt.top_customers) > 0)
    print(f"    Jobs: {mkt.total_jobs} | Avg: ${mkt.avg_revenue:,.0f} | Med: ${mkt.median_revenue:,.0f} | GM: {mkt.avg_gm_pct}%")
    print(f"    P25-P75: ${mkt.p25_revenue:,.0f} - ${mkt.p75_revenue:,.0f}")

print("\n--- Market Intel: CHANNEL_LETTER ---")
mkt_cl = get_market_intel("CHANNEL_LETTER")
check("CL market data found", mkt_cl is not None)
if mkt_cl:
    check("2000+ CL jobs", mkt_cl.total_jobs >= 2000, f"got {mkt_cl.total_jobs}")
    print(f"    Jobs: {mkt_cl.total_jobs} | Avg: ${mkt_cl.avg_revenue:,.0f} | Med: ${mkt_cl.median_revenue:,.0f} | GM: {mkt_cl.avg_gm_pct}%")

print("\n--- Market Intel: MONUMENT ---")
mkt_mon = get_market_intel("MONUMENT")
check("Monument market data found", mkt_mon is not None)
if mkt_mon:
    print(f"    Jobs: {mkt_mon.total_jobs} | Avg: ${mkt_mon.avg_revenue:,.0f} | Med: ${mkt_mon.median_revenue:,.0f} | GM: {mkt_mon.avg_gm_pct}%")

# ── 6. Edge cases ────────────────────────────────────────────────────────

print("\n--- Edge Cases ---")
check("Empty string returns None", get_customer_profile("") is None)
check("Gibberish returns None", get_customer_profile("xyzzyplugh99") is None)
check("Single char returns None", get_customer_profile("X") is None)
check("Similar for unknown type returns empty", len(find_similar_jobs("SPACESHIP")) == 0)
check("Market for unknown type returns None", get_market_intel("SPACESHIP") is None)

# ── Summary ──────────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
if FAIL == 0:
    print("ALL TESTS PASSED")
else:
    print(f"!!! {FAIL} FAILURES — FIX BEFORE PROCEEDING !!!")
print("=" * 70)
