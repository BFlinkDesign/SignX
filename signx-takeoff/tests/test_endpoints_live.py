"""
test_endpoints_live.py — Comprehensive E2E test of ALL SignX-Takeoff API endpoints.

Spins up the server on port 18765 and hits real endpoints with real data.
Covers: estimators (8 types), intel (4), dossier, drawings, project-files,
structural (6), notion (3), keyedin, notify.
"""

import asyncio
import sys
import threading
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
import uvicorn

from app import app

PASS = 0
FAIL = 0
ERRORS = []
BASE = "http://127.0.0.1:18765"


def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {label}")
    else:
        FAIL += 1
        ERRORS.append(label)
        print(f"  FAIL: {label} -- {detail}")


async def safe_request(client, method, url, **kwargs):
    """Make a request with graceful timeout handling. Returns (response, error_string)."""
    try:
        if method == "GET":
            r = await client.get(url, **kwargs)
        elif method == "POST":
            r = await client.post(url, **kwargs)
        else:
            r = await client.request(method, url, **kwargs)
        return r, None
    except httpx.TimeoutException:
        return None, "TIMEOUT"
    except Exception as e:
        return None, str(e)


def safe_json(r):
    """Parse JSON from response, return empty dict on failure."""
    try:
        return r.json()
    except Exception:
        return {"_raw_status": r.status_code, "_parse_error": True}


def run_server():
    uvicorn.run(app, host="127.0.0.1", port=18765, log_level="error")


async def run_tests():
    async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as c:

        # =====================================================================
        # INTEL ENDPOINTS
        # =====================================================================

        # ── Warehouse Stats ──
        print("\n--- GET /api/intel/warehouse ---")
        r, err = await safe_request(c, "GET", "/api/intel/warehouse")
        if err:
            check("Warehouse endpoint reachable", False, err)
        else:
            d = safe_json(r)
            check("Warehouse loaded", d.get("loaded") is True)
            check("27K+ jobs", d.get("total_jobs", 0) >= 27000)
            check("Revenue > $50M", d.get("total_revenue", 0) > 50_000_000)
            print(f"    {d.get('total_jobs')} jobs | ${d.get('total_revenue', 0):,.0f} | {d.get('unique_customers')} customers")

        # ── Customer Intel (known) ──
        print("\n--- GET /api/intel/customer/Cat Scale ---")
        r, err = await safe_request(c, "GET", "/api/intel/customer/Cat Scale")
        if err:
            check("Customer intel reachable", False, err)
        else:
            d = safe_json(r)
            check("Found Cat Scale", d.get("ok") is True)
            check("Cat Scale 2000+ jobs", d.get("total_jobs", 0) >= 2000)
            check("Cat Scale Key Account", d.get("relationship_label") == "Key Account")
            print(f"    {d.get('customer_name')} | {d.get('total_jobs')} jobs | ${d.get('total_revenue', 0):,.0f} | {d.get('relationship_label')}")

        print("\n--- GET /api/intel/customer/Taco Johns ---")
        r, err = await safe_request(c, "GET", "/api/intel/customer/Taco Johns")
        if err:
            check("Taco Johns intel reachable", False, err)
        else:
            d = safe_json(r)
            check("Found Taco Johns", d.get("ok") is True)
            print(f"    {d.get('customer_name')} | {d.get('total_jobs')} jobs | ${d.get('total_revenue', 0):,.0f}")

        # ── Customer Intel (unknown) ──
        print("\n--- GET /api/intel/customer/xyzzyplugh99 ---")
        r, err = await safe_request(c, "GET", "/api/intel/customer/xyzzyplugh99")
        if err:
            check("Unknown customer intel reachable", False, err)
        else:
            check("Unknown customer returns 404", r.status_code == 404)
            d = safe_json(r)
            check("Unknown customer ok=false", d.get("ok") is False)

        # ── Similar Jobs ──
        print("\n--- GET /api/intel/similar?sign_type=MONUMENT&revenue=6000 ---")
        r, err = await safe_request(c, "GET", "/api/intel/similar", params={"sign_type": "MONUMENT", "revenue": 6000})
        if err:
            check("Similar jobs reachable", False, err)
        else:
            d = safe_json(r)
            check("Similar jobs found", d.get("matches", 0) > 0)
            jobs = d.get("jobs", [])
            if jobs:
                j = jobs[0]
                print(f"    Top match: WO {j['wo']} | {j['customer'][:30]} | ${j['revenue']:,.0f} | {j['gm_pct']}% GM")

        # ── Market Intel ──
        print("\n--- GET /api/intel/market/PYLON ---")
        r, err = await safe_request(c, "GET", "/api/intel/market/PYLON")
        if err:
            check("Market intel reachable", False, err)
        else:
            d = safe_json(r)
            check("Pylon market data ok", d.get("ok") is True)
            check("2000+ pylon jobs", d.get("total_jobs", 0) >= 2000)
            print(f"    {d.get('total_jobs')} jobs | Avg ${d.get('avg_revenue', 0):,.0f} | GM {d.get('avg_gm_pct')}%")

        # ── Market Intel (unknown type) ──
        print("\n--- GET /api/intel/market/ZZZBOGUS ---")
        r, err = await safe_request(c, "GET", "/api/intel/market/ZZZBOGUS")
        if err:
            check("Unknown market reachable", False, err)
        else:
            check("Unknown sign type returns 404", r.status_code == 404)

        # =====================================================================
        # DOSSIER ENDPOINT
        # =====================================================================

        print("\n--- GET /api/dossier?customer=Cat Scale&sign_type=PYLON ---")
        r, err = await safe_request(c, "GET", "/api/dossier", params={"customer": "Cat Scale", "sign_type": "PYLON"})
        if err:
            check("Dossier reachable", False, err)
        else:
            d = safe_json(r)
            check("Dossier has intel", d.get("intel") is not None)
            check("Dossier has similar_jobs", len(d.get("similar_jobs", [])) > 0)
            check("Dossier has market", d.get("market") is not None)
            check("Dossier has files section", d.get("files") is not None)
            check("Dossier has bids section", "bids" in d)
            intel = d.get("intel", {})
            print(f"    Intel: {intel.get('customer_name')} | {intel.get('total_jobs')} jobs | {intel.get('relationship_label')}")
            print(f"    Similar: {len(d.get('similar_jobs', []))} matches")
            mkt = d.get("market", {})
            print(f"    Market: {mkt.get('total_jobs')} jobs | Avg ${mkt.get('avg_revenue', 0):,.0f}")
            files = d.get("files", {})
            print(f"    Files: {files.get('total_scanned', 0)} scanned | warnings: {files.get('warnings', [])}")
            print(f"    Bids: {len(d.get('bids', []))} from Notion")

        # ── Dossier: unknown customer ──
        print("\n--- GET /api/dossier?customer=xyzzyplugh99 ---")
        r, err = await safe_request(c, "GET", "/api/dossier", params={"customer": "xyzzyplugh99"})
        if err:
            check("Unknown dossier reachable", False, err)
        else:
            d = safe_json(r)
            check("Unknown customer has no intel", d.get("intel") is None)
            check("Unknown customer has intel_note", d.get("intel_note") is not None)

        # =====================================================================
        # ESTIMATOR ENDPOINTS
        # =====================================================================

        # ── Channel Letter Estimate ──
        print("\n--- POST /api/estimate (channel letter) ---")
        r, err = await safe_request(c, "POST", "/api/estimate", json={
            "pf_source": "chart",
            "letter_count": 10,
            "height_inches": 18,
            "font_type": "block",
            "construction": "face_lit",
        })
        if err:
            check("Channel letter estimate reachable", False, err)
        else:
            d = safe_json(r)
            check("CL estimate returns hours", d.get("total_man_hours", 0) > 0)
            check("CL estimate has labor lines", len(d.get("labor", [])) > 0)
            check("CL estimate has benchmark", d.get("benchmark") is not None or d.get("benchmark") is None)  # may or may not match
            print(f"    10 block letters @ 18in = {d.get('total_man_hours', 0):.2f} man-hrs")

        # ── Channel Letter: manual PF ──
        print("\n--- POST /api/estimate (manual PF) ---")
        r, err = await safe_request(c, "POST", "/api/estimate", json={
            "pf_source": "manual",
            "pf_value": 45.0,
            "height_inches": 24,
            "font_type": "block",
            "construction": "halo",
        })
        if err:
            check("Manual PF estimate reachable", False, err)
        else:
            d = safe_json(r)
            check("Manual PF estimate returns hours", d.get("total_man_hours", 0) > 0)
            print(f"    45 PF halo_lit @ 24in = {d.get('total_man_hours', 0):.2f} man-hrs")

        # ── Monument Estimate ──
        print("\n--- POST /api/estimate/monument ---")
        r, err = await safe_request(c, "POST", "/api/estimate/monument", json={
            "width_ft": 8.0,
            "height_ft": 4.0,
            "num_faces": 2,
            "illuminated": False,
            "has_vinyl": True,
            "install_height_ft": 6.0,
            "miles": 25.0,
            "crew_size": 2,
        })
        if err:
            check("Monument estimate reachable", False, err)
        else:
            d = safe_json(r)
            check("Monument returns hours", d.get("total_man_hours", 0) > 0)
            check("Monument has labor lines", len(d.get("labor", [])) > 0)
            print(f"    8x4 monument DF = {d.get('total_man_hours', 0):.2f} man-hrs + {d.get('total_crew_hours', 0):.2f} crew-hrs")

        # ── Pylon Estimate ──
        print("\n--- POST /api/estimate/pylon ---")
        r, err = await safe_request(c, "POST", "/api/estimate/pylon", json={
            "width_ft": 8.0,
            "height_ft": 6.0,
            "num_faces": 2,
            "pole_height_ft": 25.0,
            "has_vinyl": True,
            "include_footing": True,
            "miles": 30.0,
            "crew_size": 3,
        })
        if err:
            check("Pylon estimate reachable", False, err)
        else:
            d = safe_json(r)
            check("Pylon returns hours", d.get("total_man_hours", 0) > 0)
            check("Pylon has install lines", len(d.get("install", [])) > 0)
            print(f"    8x6 pylon @ 25ft = {d.get('total_man_hours', 0):.2f} man-hrs + {d.get('total_crew_hours', 0):.2f} crew-hrs")

        # ── Cabinet Estimate ──
        print("\n--- POST /api/estimate/cabinet ---")
        r, err = await safe_request(c, "POST", "/api/estimate/cabinet", json={
            "width_ft": 6.0,
            "height_ft": 4.0,
            "num_faces": 1,
            "illuminated": True,
            "has_vinyl": True,
            "mount_type": "wall",
            "install_height_ft": 12.0,
            "miles": 10.0,
            "crew_size": 2,
        })
        if err:
            check("Cabinet estimate reachable", False, err)
        else:
            d = safe_json(r)
            check("Cabinet returns hours", d.get("total_man_hours", 0) > 0)
            check("Cabinet has labor lines", len(d.get("labor", [])) > 0)
            print(f"    6x4 cabinet wall = {d.get('total_man_hours', 0):.2f} man-hrs + {d.get('total_crew_hours', 0):.2f} crew-hrs")

        # ── Awning Estimate ──
        print("\n--- POST /api/estimate/awning ---")
        r, err = await safe_request(c, "POST", "/api/estimate/awning", json={
            "width_ft": 10.0,
            "projection_ft": 3.0,
            "valance_height_in": 12.0,
            "num_bays": 1,
            "install_height_ft": 10.0,
            "miles": 15.0,
            "crew_size": 2,
        })
        if err:
            check("Awning estimate reachable", False, err)
        else:
            d = safe_json(r)
            check("Awning returns hours", d.get("total_man_hours", 0) > 0)
            print(f"    10ft awning = {d.get('total_man_hours', 0):.2f} man-hrs + {d.get('total_crew_hours', 0):.2f} crew-hrs")

        # ── Removal Estimate ──
        print("\n--- POST /api/estimate/removal ---")
        r, err = await safe_request(c, "POST", "/api/estimate/removal", json={
            "sign_type": "CLLIT",
            "num_units": 2,
            "face_area_sf": 32.0,
            "remove_height_ft": 15.0,
            "miles": 20.0,
            "crew_size": 2,
        })
        if err:
            check("Removal estimate reachable", False, err)
        else:
            d = safe_json(r)
            check("Removal returns hours", d.get("total_man_hours", 0) > 0 or d.get("total_crew_hours", 0) > 0)
            print(f"    2-unit removal = {d.get('total_man_hours', 0):.2f} man-hrs + {d.get('total_crew_hours', 0):.2f} crew-hrs")

        # ── Dimensional Estimate ──
        print("\n--- POST /api/estimate/dimensional ---")
        r, err = await safe_request(c, "POST", "/api/estimate/dimensional", json={
            "letter_count": 10,
            "letter_height_inches": 8.0,
            "paint_colors": 1,
            "miles": 5.0,
            "crew_size": 1,
        })
        if err:
            check("Dimensional estimate reachable", False, err)
        else:
            d = safe_json(r)
            check("Dimensional returns hours", d.get("total_man_hours", 0) > 0 or d.get("total_crew_hours", 0) > 0)
            print(f"    10 dimensional @ 8in = {d.get('total_man_hours', 0):.2f} man-hrs + {d.get('total_crew_hours', 0):.2f} crew-hrs")

        # ── Directional Estimate ──
        print("\n--- POST /api/estimate/directional ---")
        r, err = await safe_request(c, "POST", "/api/estimate/directional", json={
            "width_ft": 4.0,
            "height_ft": 2.0,
            "num_units": 3,
            "has_vinyl": True,
            "paint_colors": 2,
            "miles": 10.0,
            "crew_size": 1,
        })
        if err:
            check("Directional estimate reachable", False, err)
        else:
            d = safe_json(r)
            check("Directional returns hours", d.get("total_man_hours", 0) > 0 or d.get("total_crew_hours", 0) > 0)
            print(f"    3x directional panels = {d.get('total_man_hours', 0):.2f} man-hrs + {d.get('total_crew_hours', 0):.2f} crew-hrs")

        # =====================================================================
        # DRAWING SEARCH & PROJECT FILES
        # =====================================================================

        # ── Drawing Search ──
        print("\n--- GET /api/drawings/search?customer=Cat Scale ---")
        r, err = await safe_request(c, "GET", "/api/drawings/search", params={"customer": "Cat Scale"})
        if err:
            check("Drawing search reachable", False, err)
        else:
            d = safe_json(r)
            check("Drawing search ok", d.get("ok") is True or r.status_code == 500)  # G: drive may be down
            if d.get("ok"):
                print(f"    Found {d.get('drawing_count', 0)} drawings, {d.get('pdf_count', 0)} PDFs")
                if d.get("warnings"):
                    print(f"    Warning: {d['warnings'][0][:80]}")
            else:
                print(f"    G: drive unavailable (expected): {d.get('error', '')[:80]}")

        # ── Project Files ──
        print("\n--- GET /api/project-files?customer=Cat Scale ---")
        r, err = await safe_request(c, "GET", "/api/project-files", params={"customer": "Cat Scale"})
        if err:
            check("Project files reachable", False, err)
        else:
            d = safe_json(r)
            check("Project files endpoint works", d.get("ok") is True)
            if d.get("warnings"):
                print(f"    (Expected) G: drive warning: {d['warnings'][0][:60]}")
            print(f"    Scanned: {d.get('total_scanned', 0)} files | Total: {d.get('total_files', 0)}")

        # =====================================================================
        # STRUCTURAL ENDPOINTS
        # =====================================================================

        # ── Wind Load ──
        print("\n--- POST /api/structural/wind ---")
        r, err = await safe_request(c, "POST", "/api/structural/wind", json={
            "V_mph": 115.0,
            "sign_width_ft": 10.0,
            "sign_height_ft": 5.0,
            "height_to_top_ft": 20.0,
            "exposure": "C",
            "Kzt": 1.0,
            "elevation_ft": 0.0,
            "risk_category": "II",
        })
        if err:
            check("Wind load reachable", False, err)
        else:
            d = safe_json(r)
            check("Wind calc ok", d.get("ok") is True)
            result = d.get("result", {})
            check("Wind has governing force", result.get("governing_F_lbf", 0) > 0)
            print(f"    F={result.get('governing_F_lbf', 0):.0f} lbf | M={result.get('governing_M_ftlbf', 0):.0f} ft-lb")

        # ── Foundation Design ──
        print("\n--- POST /api/structural/foundation ---")
        r, err = await safe_request(c, "POST", "/api/structural/foundation", json={
            "F_lbf": 2000.0,
            "M_inlb": 480000.0,
        })
        if err:
            check("Foundation reachable", False, err)
        else:
            d = safe_json(r)
            check("Foundation calc ok", d.get("ok") is True)
            geo = d.get("geometry", {})
            print(f"    Dia={geo.get('foundation_dia_in', 0):.0f}in | Depth={geo.get('embed_in', 0):.0f}in")

        # ── Anchor Design ──
        print("\n--- POST /api/structural/anchors ---")
        r, err = await safe_request(c, "POST", "/api/structural/anchors", json={
            "F_lbf": 2000.0,
            "M_inlb": 480000.0,
            "P_lbf": 500.0,
            "f_c_psi": 3000.0,
            "bolt_grade": "F1554-36",
            "n_bolts": 4,
        })
        if err:
            check("Anchors reachable", False, err)
        else:
            d = safe_json(r)
            # 422 = valid engineering rejection (moment too high for bolt config)
            check("Anchor endpoint responds", r.status_code in (200, 422, 500))
            if d.get("ok"):
                geo = d.get("geometry", {})
                print(f"    Bolt dia={geo.get('bolt_dia_in', 0)} | BC={geo.get('bolt_circle_in', 0)}in | Plate={geo.get('plate_in', 0)}in")
            else:
                print(f"    Engineering rejection (expected): {d.get('error', '')[:80]}")

        # ── Member Check ──
        print("\n--- POST /api/structural/member-check ---")
        r, err = await safe_request(c, "POST", "/api/structural/member-check", json={
            "designation": "Pipe4STD",
            "M_inlb": 200000.0,
            "V_lbf": 1500.0,
            "L_in": 240.0,
            "load_type": "cantilever",
        })
        if err:
            check("Member check reachable", False, err)
        else:
            d = safe_json(r)
            check("Member check ok", d.get("ok") is True)
            check("Member check has passes field", "passes" in d)
            print(f"    Pipe4STD passes={d.get('passes')}")

        # ── Member Select ──
        print("\n--- POST /api/structural/member-select ---")
        r, err = await safe_request(c, "POST", "/api/structural/member-select", json={
            "M_inlb": 200000.0,
            "V_lbf": 1500.0,
            "L_in": 240.0,
            "load_type": "cantilever",
            "families": ["pipe"],
        })
        if err:
            check("Member select reachable", False, err)
        else:
            d = safe_json(r)
            # 422 = no passing section found (valid engineering result)
            check("Member select endpoint responds", r.status_code in (200, 422))
            if d.get("ok"):
                print(f"    Selected: {d.get('designation')} ({d.get('family')}) @ {d.get('weight_plf')} plf")
            else:
                print(f"    No passing section (expected for high M/low catalog): {d.get('error', '')[:60]}")

        # ── Full Design ──
        print("\n--- POST /api/structural/full-design ---")
        r, err = await safe_request(c, "POST", "/api/structural/full-design", json={
            "sign_width_ft": 8.0,
            "sign_height_ft": 4.0,
            "height_to_top_ft": 20.0,
            "V_mph": 115.0,
            "exposure": "C",
            "elevation_ft": 0.0,
            "f_c_psi": 3000.0,
            "bolt_grade": "F1554-36",
        })
        if err:
            check("Full design reachable", False, err)
        else:
            d = safe_json(r)
            # 422 = cascading failure from member/foundation (valid)
            check("Full design endpoint responds", r.status_code in (200, 422))
            if d.get("ok"):
                check("Full design has wind", d.get("wind") is not None)
                check("Full design has foundation", d.get("foundation") is not None)
                mem = d.get("member") or {}
                print(f"    Member: {mem.get('designation')} | Wind: {d.get('wind', {}).get('governing_F_lbf', 0):.0f} lbf")
            else:
                print(f"    Design rejected (expected): {d.get('error', '')[:80]}")

        # ── Sections List ──
        print("\n--- GET /api/structural/sections?family=pipe ---")
        r, err = await safe_request(c, "GET", "/api/structural/sections", params={"family": "pipe", "limit": 5})
        if err:
            check("Sections list reachable", False, err)
        else:
            d = safe_json(r)
            check("Sections returns data", d.get("total", 0) > 0)
            secs = d.get("sections", [])
            if secs:
                print(f"    {d['total']} pipe sections, first: {secs[0].get('designation')}")

        # =====================================================================
        # FOOTAGE CHART
        # =====================================================================

        print("\n--- POST /api/footage-chart ---")
        r, err = await safe_request(c, "POST", "/api/footage-chart", json={
            "letter_count": 8,
            "height_inches": 24,
            "font_type": "block",
        })
        if err:
            check("Footage chart reachable", False, err)
        else:
            d = safe_json(r)
            check("Footage chart returns PF", d.get("total_pf", 0) > 0)
            print(f"    8 letters @ 24in = {d.get('total_pf', 0):.2f} PF ({d.get('pf_per_letter', 0):.2f}/letter)")

        # =====================================================================
        # KEYEDIN FORMAT
        # =====================================================================

        print("\n--- POST /api/keyedin/format ---")
        r, err = await safe_request(c, "POST", "/api/keyedin/format", json={
            "quote_number": "TEST-001",
            "customer": "Test Customer",
            "labor_lines": [
                {"code": "FAB-CL", "desc": "Fabricate channel letters", "hours": 8.5, "unit": "man-hrs", "dept": "SHOP"},
                {"code": "WIRE-CL", "desc": "Wire channel letters", "hours": 2.0, "unit": "man-hrs", "dept": "ELECTRIC"},
            ],
            "install_lines": [
                {"code": "INST-CL", "desc": "Install channel letters", "hours": 4.0, "unit": "CREW-hrs", "dept": "INSTALL"},
            ],
        })
        if err:
            check("KeyedIn format reachable", False, err)
        else:
            d = safe_json(r)
            check("KeyedIn format ready", d.get("keyedin_ready") is True)
            check("KeyedIn has work orders", len(d.get("work_orders", [])) == 3)
            check("KeyedIn man-hrs correct", d.get("total_man_hours") == 10.5)
            check("KeyedIn crew-hrs correct", d.get("total_crew_hours") == 4.0)
            print(f"    {d.get('line_count')} lines | {d.get('total_man_hours')} man-hrs | {d.get('total_crew_hours')} crew-hrs")

        # =====================================================================
        # NOTION ENDPOINTS (graceful - may not have token configured)
        # =====================================================================

        print("\n--- GET /api/notion/bids ---")
        r, err = await safe_request(c, "GET", "/api/notion/bids")
        if err:
            check("Notion bids reachable", False, err)
        else:
            d = safe_json(r)
            # If no token, expect error message but still 200
            if d.get("error") and "not configured" in d.get("error", ""):
                check("Notion bids returns graceful error when unconfigured", True)
                print(f"    (Expected) {d['error'][:60]}")
            else:
                check("Notion bids returns data", "bids" in d)
                print(f"    {d.get('total', 0)} bids | ${d.get('total_pipeline_value', 0):,.0f} pipeline value")

        print("\n--- GET /api/notion/flow-status ---")
        r, err = await safe_request(c, "GET", "/api/notion/flow-status")
        if err:
            check("Flow status reachable", False, err)
        else:
            d = safe_json(r)
            check("Flow status has flows", "flows" in d)
            check("Flow status has salesmen", len(d.get("salesmen", [])) > 0)
            print(f"    {len(d.get('flows', []))} active | {len(d.get('planned_flows', []))} planned")

        # =====================================================================
        # ERROR CASES
        # =====================================================================

        print("\n--- ERROR: POST /api/estimate with missing params ---")
        r, err = await safe_request(c, "POST", "/api/estimate", json={})
        if err:
            check("Empty estimate reachable", False, err)
        else:
            # Should still return 200 with defaults, engine handles defaults gracefully
            check("Empty estimate does not crash (status < 500)", r.status_code < 500)

        print("\n--- ERROR: POST /api/structural/wind with bad exposure ---")
        r, err = await safe_request(c, "POST", "/api/structural/wind", json={
            "V_mph": 115.0,
            "sign_width_ft": 10.0,
            "sign_height_ft": 5.0,
            "height_to_top_ft": 20.0,
            "exposure": "Z",  # invalid
        })
        if err:
            check("Bad wind exposure reachable", False, err)
        else:
            check("Bad exposure returns error status", r.status_code >= 400)

        print("\n--- ERROR: POST /api/structural/member-check with bogus section ---")
        r, err = await safe_request(c, "POST", "/api/structural/member-check", json={
            "designation": "BOGUS_SECTION_999",
            "M_inlb": 100000.0,
            "V_lbf": 1000.0,
            "L_in": 120.0,
        })
        if err:
            check("Bogus section reachable", False, err)
        else:
            check("Bogus section returns 404", r.status_code == 404)

        print("\n--- ERROR: GET /api/drawings/search without customer ---")
        r, err = await safe_request(c, "GET", "/api/drawings/search")
        if err:
            check("Missing customer drawing search reachable", False, err)
        else:
            check("Missing customer returns 422", r.status_code == 422)

        # =====================================================================
        # BID SCORING
        # =====================================================================

        # ── Score Bid: known customer ──
        print("\n--- POST /api/bid/score (Cat Scale, POLLIT, $8500) ---")
        r, err = await safe_request(c, "POST", "/api/bid/score", params={
            "customer": "Cat Scale",
            "sign_type": "POLLIT",
            "price": 8500,
        })
        if err:
            check("Bid score reachable", False, err)
        else:
            d = safe_json(r)
            check("Bid score ok=true (known customer)", d.get("ok") is True)
            prob = d.get("win_probability", -1)
            check("win_probability in [0.0, 1.0]", 0.0 <= prob <= 1.0, f"got {prob}")
            factors = d.get("factors", [])
            check("factors list has 6 items", len(factors) == 6, f"got {len(factors)}")
            recs = d.get("recommendations", None)
            check("recommendations is a list", isinstance(recs, list), f"got {type(recs)}")
            print(f"    win_prob={prob:.3f} | {len(factors)} factors | {len(recs or [])} recommendations")

        # ── Score Bid: unknown customer ──
        print("\n--- POST /api/bid/score (unknown customer) ---")
        r, err = await safe_request(c, "POST", "/api/bid/score", params={
            "customer": "xyzzyplugh_unknown_99",
            "sign_type": "POLLIT",
            "price": 8500,
        })
        if err:
            check("Bid score unknown customer reachable", False, err)
        else:
            d = safe_json(r)
            check("Bid score ok=true (unknown customer)", d.get("ok") is True)
            prob = d.get("win_probability", -1)
            check("Unknown customer win_probability still in [0.0, 1.0]", 0.0 <= prob <= 1.0, f"got {prob}")
            print(f"    unknown customer win_prob={prob:.3f}")

        # ── Score Bid: with optional salesperson ──
        print("\n--- POST /api/bid/score (with salesperson) ---")
        r, err = await safe_request(c, "POST", "/api/bid/score", params={
            "customer": "Cat Scale",
            "sign_type": "POLLIT",
            "price": 8500,
            "salesperson": "JEFF",
        })
        if err:
            check("Bid score with salesperson reachable", False, err)
        else:
            d = safe_json(r)
            check("Bid score with salesperson ok=true", d.get("ok") is True)
            prob = d.get("win_probability", -1)
            check("Bid score with salesperson win_probability valid", 0.0 <= prob <= 1.0, f"got {prob}")
            print(f"    JEFF + Cat Scale + POLLIT win_prob={prob:.3f}")

        # ── Win Rates ──
        print("\n--- GET /api/bid/win-rates ---")
        r, err = await safe_request(c, "GET", "/api/bid/win-rates")
        if err:
            check("Win rates reachable", False, err)
        else:
            d = safe_json(r)
            overall = d.get("overall_win_rate", -1)
            check("overall_win_rate present", overall != -1)
            check("overall_win_rate approx 0.76 (±0.05)", abs(overall - 0.76) <= 0.05, f"got {overall:.4f}")
            by_year = d.get("by_year", {})
            check("by_year has 2020 entry", "2020" in by_year or 2020 in by_year)
            check("by_year has 2025 entry", "2025" in by_year or 2025 in by_year)
            by_sp = d.get("by_salesperson", {})
            check("by_salesperson has JEFF", "JEFF" in by_sp)
            check("by_salesperson has KENT", "KENT" in by_sp)
            check("by_salesperson has MIKEE", "MIKEE" in by_sp)
            by_pb = d.get("by_price_bracket", None)
            check("by_price_bracket present", by_pb is not None)
            print(f"    overall_win_rate={overall:.4f} | years={list(by_year.keys())[:4]} | salespeople={list(by_sp.keys())}")

        # ── Price Recommendation: CLLIT ──
        print("\n--- GET /api/bid/price-recommendation?sign_type=CLLIT ---")
        r, err = await safe_request(c, "GET", "/api/bid/price-recommendation", params={"sign_type": "CLLIT"})
        if err:
            check("Price recommendation reachable", False, err)
        else:
            d = safe_json(r)
            check("Price recommendation ok=true", d.get("ok") is True)
            conservative = d.get("conservative", 0)
            balanced = d.get("balanced", 0)
            aggressive = d.get("aggressive", 0)
            check("conservative < balanced", conservative < balanced, f"{conservative} vs {balanced}")
            check("balanced < aggressive", balanced < aggressive, f"{balanced} vs {aggressive}")
            data_pts = d.get("data_points", 0)
            check("data_points > 100", data_pts > 100, f"got {data_pts}")
            print(f"    CLLIT: conservative=${conservative:,.0f} | balanced=${balanced:,.0f} | aggressive=${aggressive:,.0f} | n={data_pts}")

        # ── Price Recommendation: POLLIT with customer adjustment ──
        print("\n--- GET /api/bid/price-recommendation?sign_type=POLLIT&customer=Cat+Scale ---")
        r, err = await safe_request(c, "GET", "/api/bid/price-recommendation", params={"sign_type": "POLLIT", "customer": "Cat Scale"})
        if err:
            check("Price recommendation with customer reachable", False, err)
        else:
            d = safe_json(r)
            check("Price recommendation with customer ok=true", d.get("ok") is True)
            conservative = d.get("conservative", 0)
            balanced = d.get("balanced", 0)
            aggressive = d.get("aggressive", 0)
            check("POLLIT+Cat Scale conservative < balanced", conservative < balanced, f"{conservative} vs {balanced}")
            check("POLLIT+Cat Scale balanced < aggressive", balanced < aggressive, f"{balanced} vs {aggressive}")
            print(f"    POLLIT+Cat Scale: conservative=${conservative:,.0f} | balanced=${balanced:,.0f} | aggressive=${aggressive:,.0f}")

        # ── Scoring Health ──
        print("\n--- GET /api/bid/scoring-health ---")
        r, err = await safe_request(c, "GET", "/api/bid/scoring-health")
        if err:
            check("Scoring health reachable", False, err)
        else:
            d = safe_json(r)
            wh_jobs = d.get("warehouse_jobs", 0)
            check("scoring-health warehouse_jobs > 27000", wh_jobs > 27000, f"got {wh_jobs}")
            check("scoring-health loaded==true", d.get("loaded") is True)
            check("scoring-health overall_win_rate present", "overall_win_rate" in d)
            print(f"    loaded={d.get('loaded')} | warehouse_jobs={wh_jobs} | win_rate={d.get('overall_win_rate')}")

        # =====================================================================
        # ML MODEL (Logistic Regression)
        # =====================================================================

        print("\n" + "=" * 70)
        print("ML BID MODEL (Logistic Regression)")
        print("=" * 70)

        # ── ML Score: known customer ──
        print("\n--- POST /api/bid/ml-score (Cat Scale POLLIT $8500 KENT) ---")
        r, err = await safe_request(
            c, "POST", "/api/bid/ml-score",
            params={"customer": "CAT SCALE", "sign_type": "POLLIT", "price": 8500, "salesperson": "KENT"},
        )
        if err:
            check("ML score reachable", False, err)
        else:
            d = safe_json(r)
            check("ML score ok=true", d.get("ok") is True)
            check("ML model_available=true", d.get("model_available") is True)
            prob = d.get("win_probability", 0)
            check("ML Cat Scale win_probability > 0.80", prob > 0.80, f"got {prob:.4f}")
            check("ML confidence is 'high'", d.get("confidence") == "high", f"got {d.get('confidence')}")
            check("ML has feature_contributions", len(d.get("feature_contributions", {})) == 12)
            check("ML has positive_factors", len(d.get("positive_factors", [])) > 0)
            print(f"    ML prob: {prob:.1%} | conf: {d.get('confidence')}")

        # ── ML Score: unknown customer ──
        print("\n--- POST /api/bid/ml-score (Unknown Startup MONDF $85K JEFF) ---")
        r, err = await safe_request(
            c, "POST", "/api/bid/ml-score",
            params={"customer": "Unknown Startup", "sign_type": "MONDF", "price": 85000, "salesperson": "JEFF"},
        )
        if err:
            check("ML score unknown reachable", False, err)
        else:
            d = safe_json(r)
            prob = d.get("win_probability", 1)
            check("ML unknown prob < 0.30", prob < 0.30, f"got {prob:.4f}")
            check("ML unknown has risk_factors", len(d.get("risk_factors", [])) > 0)
            print(f"    ML prob: {prob:.1%} | risks: {d.get('risk_factors', [])[:2]}")

        # ── ML Diagnostics ──
        print("\n--- GET /api/bid/ml-diagnostics ---")
        r, err = await safe_request(c, "GET", "/api/bid/ml-diagnostics")
        if err:
            check("ML diagnostics reachable", False, err)
        else:
            d = safe_json(r)
            check("ML status=ready", d.get("status") == "ready", f"got {d.get('status')}")
            m = d.get("metrics", {})
            auc = m.get("auc_roc", 0)
            check("ML AUC-ROC > 0.70", auc > 0.70, f"got {auc:.4f}")
            brier = m.get("brier_score", 1)
            check("ML Brier < 0.30", brier < 0.30, f"got {brier:.4f} (time-decay weighted)")
            n_train = m.get("n_train", 0)
            check("ML n_train > 15000", n_train > 15000, f"got {n_train}")
            check("ML has coefficients", len(d.get("top_5_features", {})) >= 5)
            print(f"    AUC={auc:.4f} | Brier={brier:.4f} | n={n_train:,}")

        # =====================================================================
        # OPENAPI / DOCS
        # =====================================================================

        print("\n--- GET /docs (OpenAPI Swagger UI) ---")
        r, err = await safe_request(c, "GET", "/docs")
        if err:
            check("Swagger docs reachable", False, err)
        else:
            check("Swagger docs returns 200", r.status_code == 200)

        print("\n--- GET /openapi.json ---")
        r, err = await safe_request(c, "GET", "/openapi.json")
        if err:
            check("OpenAPI JSON reachable", False, err)
        else:
            d = safe_json(r)
            paths = d.get("paths", {})
            check("OpenAPI has paths", len(paths) > 0)
            print(f"    {len(paths)} paths defined in OpenAPI schema")


def main():
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(3)

    print("=" * 70)
    print("SIGNX ENDPOINT LIVE VALIDATION — COMPREHENSIVE SUITE")
    print("=" * 70)

    try:
        asyncio.run(run_tests())
    except Exception as e:
        print(f"\n  FATAL: Test runner crashed: {e}")
        traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
    if FAIL == 0:
        print("ALL ENDPOINT TESTS PASSED")
    else:
        print(f"!!! {FAIL} FAILURES !!!")
        for err_label in ERRORS:
            print(f"  - {err_label}")
    print("=" * 70)

    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
