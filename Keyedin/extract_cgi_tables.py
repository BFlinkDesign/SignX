#!/usr/bin/env python3
"""
Extract actual table data from all 240 CGI functions.
Uses Playwright frame-level evaluation to access data inside framesets.
"""

import asyncio
import csv
import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CGI_BASE = "https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe"
CDP_URL = os.environ.get("CDP_URL", "http://localhost:29229")
USERNAME = os.environ.get("KEYEDIN_USERNAME", "")
PASSWORD = os.environ.get("KEYEDIN_PASSWORD", "")

OUTPUT_DIR = Path(__file__).parent / "extraction_output" / "cgi_tables"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Functions that have actual data tables embedded (from analysis)
# Including ALL 240 for completeness
ALL_240 = [
    "#PROJECT.ATTACHMENTS", "#PROJECT.CONTACTS", "#PROJECT.DETAILS",
    "#PROJECT.LISTING", "#PROJECT.LOCATIONS", "#PROJECT.MILESTONE.TRACKING",
    "#PROJECT.NOTES", "#PROJECT.POS", "#PROJECT.PROPOSALS",
    "#PROJECT.QUOTES", "#PROJECT.SALES.ORDERS", "#PROJECT.SHIPMENTS",
    "#PROJECT.VENDORS", "#PROJECT.WORK.ORDERS",
    "ACCOUNT.TYPE.CODE.LISTING", "ADJUST", "ALLOCATE", "AP.DETAIL",
    "ASSEMBLY.MAINT", "BILL.COMPARE", "BILL.TO", "BIN.ITEM.REQ",
    "BOM", "BOM.DELETE", "BUYERS",
    "CALL.METHOD.CODES.LISTING", "CALL.TYPE.CODES.LISTING",
    "CHANGE.PASSWORD", "CHANGE.SC.ACCOUNT", "CHECK.AVAIL",
    "CHECK.ISSUE", "CHG.VALUE", "CLEAR.ME",
    "COMPLETE.BILL", "COMPLETE.GROUP", "COMPLETE.RT",
    "COMPLETE.TOOL.LIST", "COMPLETE.WC.WU", "COMPLETE.WU",
    "CONVERT.QUOTE.TO.MFG", "COPY.BILL", "COST.INQ", "COST.POST",
    "COUNTRY.LIST", "CRM.ATTACHMENTS.DELETE", "CRM.CONTACT.MGT",
    "CRM.NOTES.REPORT", "CRM.SOLUTIONS.LISTING",
    "CUST.PRICE.MAINT", "CUST.PROD", "CUST.PROD.EXPORT", "CUST.SUM",
    "CUSTOMERS", "DAILY.SHIP.REPORT", "DAY.SALES",
    "EMP.EFF", "EMP.HOURS.BY.DATE", "EMP.HOURS.BY.OP",
    "EMP.HOURS.BY.PAY.PERIOD", "EST.BATCH.INACTIVE",
    "EST.CHANGE.ACCTID", "EST.CREATE.SO", "EST.PROP.DELETE",
    "EST.PROP.PRINT", "EST.PROP.REPRINT", "EST.PROP.RESET.DATE",
    "EST.PROPOSAL.STATUS", "EST.QUOTE.COPY", "EST.QUOTE.ENTRY",
    "EST.QUOTE.PRINT", "EST.QUOTE.STATUS", "EST.QUOTE.STATUS.CODE.LIST",
    "EST.RESET.EXP.DATE", "EST.SIGN.TEMPLATE.MAINT",
    "EST.TEMPLATE.PRINT", "EXPORT.WIP.SUMMARY",
    "EXPORT.WO.LABOR.ANALYSIS", "EXTRA.CHARGES.LIST",
    "FIRST.ISSUE", "GM.BY.INV", "GM.BY.INV.EXPORT", "GM.BY.PROD",
    "GM.DET.PROD.PART", "GM.PROJECT", "IMPORT.BOM",
    "IMPORT.CRM.NEW", "IMPORT.PARTS", "IMPORT.ROUTING",
    "IMPORT.SIGN.TEMPLATE", "ISSUE", "IT.HISTORY", "ITEM.MASTER.LIST",
    "JOB.COST.DEPT.SUMMARY", "JOB.COST.SUMMARY.LIMITED",
    "KILL.WO.RELEASE", "LABOR.TASK.BY.DEPARTMENT",
    "LANDLORD.MALL.TC.LISTING", "LEAD.SOURCE.EVENT.LISTING",
    "LIST.AP.DET", "LIST.PLAN", "LOOK.PLAN", "LOOK.SO", "LSO",
    "MATL.ISSUED", "MATL.RECEIVED", "MRP.CALC",
    "MY.PROFILE.MAINT", "OBSOLETE", "OPEN.SO",
    "ORDER.CLASSES.LIST", "ORDER.ENTRY", "ORDER.TYPES.LIST",
    "PART.COST.LIST", "PART.COSTS", "PART.PRICE.LIST",
    "PART.PRICES", "PARTS.MRP", "PLAN.BOM", "PLAN.MAINT",
    "PLAN.ROUTE", "PM.INSURANCE.LISTING",
    "PO.ACTION.RELEASE", "PO.ACTIONS", "PO.CHANGE", "PO.CLOSE",
    "PO.INQUIRY", "PO.RECEIPTS", "PO.REQ.DELETE", "PO.REQ.RELEASE",
    "PREPLAN.REPORT", "PRICE.CLASS.CODE.LIST", "PRICE.CODES.LIST",
    "PRINT.RT", "PROD.CALENDAR", "PROD.CUST", "PROD.SUM",
    "PROJECT.MILESTONE.CODES.LISTING", "PROJECT.STATUS.CODES.LISTING",
    "PROJECT.TYPE.CODES.LISTING", "PUR.COMMIT", "PUR.HISTORY",
    "PUR.PART.VAR", "PUR.PO.DEL.ANALYSIS", "PUR.PO.SCHED.ANALYSIS",
    "PUR.PO.VAR.ANALYSIS", "PUR.PRINT", "PURCHASE",
    "QUOTE.ENTRY.LIMITED", "QUOTE.LISTING", "QUOTE.MASS.COPY",
    "QUOTE.MASS.DELETE", "QUOTE.MASS.UPDATE", "QUOTE.PIPELINE.REPORT",
    "QUOTE.SALES.DIFFS", "QUOTE.SALES.STAGE.CODE.LISTING",
    "QV.PRINT", "RAW.MATL.MAINT", "REASON.CODES.LIST",
    "REPORT.VIEW.INDEX", "RESOURCE.INQUIRY", "RESOURCE.LIST",
    "ROUTING.MAINT", "SA.BY.STATE", "SALES.CODES.LIST",
    "SALES.TAXES.LIST", "SALES.TERRITORY", "SALESPERSONS.LIST",
    "SERVICE.CALL.STATUS.CODE.LISTING", "SERVICE.CALL.STATUS.REPORT",
    "SHIP.TO", "SHIPLISTS", "SHIPMENTS", "SHIPMENTS.TRACKING",
    "SHOW.ACTIVITY", "SHOW.ADJUST.CODE", "SHOW.BUYERS",
    "SHOW.ENGR.STATUS.CODES", "SHOW.INV.TYPES",
    "SHOW.ISSUE.REASON.CODES", "SHOW.MRP", "SHOW.OP.STATUS",
    "SHOW.PART.PRICES", "SHOW.PO", "SHOW.PS", "SHOW.UM.CODES",
    "SHOW.WO.COMMENTS", "SHOW.WO.MATL", "SHOW.WO.OPS",
    "SHOW.WO.PRICE.CALC", "SIGN.TEMPLATE.LISTING",
    "SIGN.TYPE.CODES.LISTING", "SLSPER.PROD", "SLSPER.PROD.EXPORT",
    "SO.COMMIT", "SO.CONTRACT", "SO.PRINT", "SS.VALUE",
    "STATES.LIST", "STOCK", "STOCK.STATUS", "SUM.BILL",
    "SUM.DEPT.EFF", "SUM.WC.EFF", "TAX.BY.TYPE.REPORT",
    "TERRITORY.CODES.LIST", "TRANSFER", "USAGE.ANAL.FILE",
    "USER.LOGOFF", "VENDORS", "VIEW.TRANSMITTED.FORMS",
    "VM.INQUIRY", "WIP.RECEIPTS", "WIP.RETRO", "WO.CHANGE",
    "WO.COMMENTS.MAINT", "WO.COMPLETION.INQUIRY",
    "WO.GROUP.ANALYSIS", "WO.HISTORY", "WO.INQUIRY",
    "WO.OP.STATUS", "WO.OPEN", "WO.OPEN.PO", "WO.PRICE.CALC",
    "WO.PRINT", "WO.PRODUCTION.SUMMARY", "WO.ROUTING.MAINT",
    "WO.STATUS.BILL", "WO.STATUS.GLTRANS", "WO.STATUS.LABR",
    "WO.STATUS.LDTL", "WO.STATUS.LDTL.LIMITED", "WO.STATUS.MATDIR",
    "WO.STATUS.MATL", "WO.STATUS.OUTP", "WO.STATUS.SUM",
    "WO.TO.START", "WORK.CODE.LIST", "WORK.DEPT.LIST",
    "WORK.DEPT.LOAD", "WSA.PURCHASE.REPORT",
]

TABLE_EXTRACT_JS = """
() => {
    const results = [];
    document.querySelectorAll('table').forEach((table, tableIdx) => {
        const headers = [];
        const rows = [];

        // Get headers from thead
        table.querySelectorAll('thead th, thead td').forEach(th => {
            headers.push(th.textContent.trim());
        });

        // If no thead, try first row with th
        if (headers.length === 0) {
            const firstRow = table.querySelector('tr');
            if (firstRow) {
                const ths = firstRow.querySelectorAll('th');
                if (ths.length > 0) {
                    ths.forEach(th => headers.push(th.textContent.trim()));
                }
            }
        }

        // Get all data rows
        const trs = table.querySelectorAll('tr');
        const startIdx = headers.length > 0 ? 1 : 0;
        for (let i = startIdx; i < trs.length; i++) {
            const cells = [];
            trs[i].querySelectorAll('td').forEach(td => {
                const input = td.querySelector('input[type="text"], input[type="hidden"], select');
                if (input && input.value) {
                    cells.push(input.value);
                } else {
                    cells.push(td.textContent.trim().replace(/\\s+/g, ' '));
                }
            });
            if (cells.length > 0 && cells.some(c => c.length > 0)) {
                rows.push(cells);
            }
        }

        if (rows.length > 0) {
            results.push({
                tableIndex: tableIdx,
                headers: headers,
                rows: rows,
                rowCount: rows.length,
            });
        }
    });
    return results;
}
"""


async def authenticate(page) -> bool:
    """Authenticate to KeyedIn ERP."""
    try:
        await page.goto(f"{CGI_BASE}/APPLOAD?APP=COUNTRY.LIST",
                        wait_until="domcontentloaded", timeout=20000)
    except Exception:
        pass
    await asyncio.sleep(3)

    all_text = ""
    for frame in page.frames:
        try:
            all_text += await frame.content()
        except Exception:
            pass
    try:
        all_text += await page.content()
    except Exception:
        pass

    if any(m in all_text for m in ["Eagle Sign", "Country Code", "dataSIGN"]):
        return True

    for attempt in range(5):
        try:
            try:
                await page.goto(f"{CGI_BASE}/LOGIN.START",
                                wait_until="domcontentloaded", timeout=20000)
            except Exception:
                pass
            await asyncio.sleep(2)

            target = page
            for frame in page.frames:
                try:
                    fc = await frame.content()
                    if "USERNAME" in fc and "PASSWORD" in fc:
                        target = frame
                        break
                except Exception:
                    pass

            ufield = target.locator('input[name="USERNAME"]')
            pfield = target.locator('input[name="PASSWORD"]')
            if await ufield.count() > 0:
                await ufield.fill(USERNAME)
                await pfield.fill(PASSWORD)
                submit = target.locator('input[type="submit"], button[type="submit"]')
                if await submit.count() > 0:
                    await submit.first.click()
                else:
                    await pfield.press("Enter")
                await asyncio.sleep(3)

            post = ""
            for frame in page.frames:
                try:
                    post += await frame.content()
                except Exception:
                    pass
            if "EXCEEDED YOUR LICENSE QUOTA" in post.upper():
                print(f"  License quota — waiting 30s (attempt {attempt+1})")
                await asyncio.sleep(30)
                continue
            if "LOGIN.START" not in page.url:
                return True
        except Exception as e:
            print(f"  Auth attempt {attempt+1}: {e}")
            await asyncio.sleep(5)
    return False


async def extract_from_frames(page, code: str) -> dict:
    """Extract table data from ALL frames of a CGI page."""
    all_tables = []
    all_pre = []
    all_form_fields = []
    all_select_options = []

    for frame in page.frames:
        try:
            # Extract tables via JS within each frame
            tables = await frame.evaluate(TABLE_EXTRACT_JS)
            for t in tables:
                t["frame_url"] = frame.url[:200]
            all_tables.extend(tables)
        except Exception:
            pass

        try:
            fc = await frame.content()

            # Extract <pre> blocks
            pres = re.findall(r'<pre[^>]*>(.*?)</pre>', fc, re.DOTALL | re.IGNORECASE)
            all_pre.extend(pres)

            # Extract form input names and values
            for m in re.finditer(
                r'<input[^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']',
                fc, re.IGNORECASE
            ):
                all_form_fields.append({"name": m.group(1), "value": m.group(2)})

            # Extract select options with values
            for sel_m in re.finditer(
                r'<select[^>]*name=["\']([^"\']+)["\'][^>]*>(.*?)</select>',
                fc, re.DOTALL | re.IGNORECASE
            ):
                sel_name = sel_m.group(1)
                options = re.findall(
                    r'<option[^>]*value=["\']([^"\']*)["\'][^>]*>(.*?)</option>',
                    sel_m.group(2), re.IGNORECASE
                )
                if options:
                    all_select_options.append({
                        "name": sel_name,
                        "options": [{"value": v, "text": t.strip()} for v, t in options],
                    })
        except Exception:
            pass

    return {
        "tables": all_tables,
        "pre_blocks": all_pre,
        "form_fields": all_form_fields,
        "select_options": all_select_options,
    }


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--start", type=int, default=0, help="Start index")
    args = parser.parse_args()

    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(CDP_URL)
    if not browser.contexts:
        print("ERROR: No browser contexts found — is Chrome running?")
        await pw.stop()
        sys.exit(1)
    ctx = browser.contexts[0]
    page = await ctx.new_page()
    print("Connected to Chrome via CDP")

    ok = await authenticate(page)
    if not ok:
        print("Authentication FAILED")
        await pw.stop()
        sys.exit(1)
    print("Authenticated ✓\n")

    checkpoint_file = OUTPUT_DIR / ".checkpoint.json"
    done_codes = set()
    if args.resume and checkpoint_file.exists():
        with open(checkpoint_file) as f:
            done_codes = set(json.load(f))
        print(f"Resuming: {len(done_codes)} already done")

    all_results = {}
    total = len(ALL_240)
    data_functions = 0

    for i, code in enumerate(ALL_240):
        if i < args.start:
            continue
        if code in done_codes:
            continue

        safe = code.replace("#", "HASH_").replace(":", "_")

        if code.startswith("#"):
            url = f"https://eaglesign.keyedinsign.com/{code}"
        else:
            url = f"{CGI_BASE}/APPLOAD?APP={code}"

        try:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            except Exception:
                pass
            await asyncio.sleep(1.5)

            # Check for session loss
            main_content = ""
            try:
                main_content = await page.content()
            except Exception:
                pass
            if "LOGIN.START" in main_content and "USERNAME" in main_content and "PASSWORD" in main_content:
                print(f"  Session lost at {code} — re-authenticating...")
                ok = await authenticate(page)
                if not ok:
                    print("FATAL: Cannot re-authenticate")
                    break
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                except Exception:
                    pass
                await asyncio.sleep(1.5)

            # Extract data from all frames
            result = await extract_from_frames(page, code)

            total_rows = sum(t.get("rowCount", 0) for t in result["tables"])
            has_data = total_rows > 0 or len(result["pre_blocks"]) > 0

            if has_data:
                data_functions += 1

                # Save tables as CSV
                for ti, table in enumerate(result["tables"]):
                    csv_file = OUTPUT_DIR / f"{safe}_table{ti}.csv"
                    with open(csv_file, "w", newline="") as f:
                        writer = csv.writer(f)
                        if table["headers"]:
                            writer.writerow(table["headers"])
                        for row in table["rows"]:
                            writer.writerow(row)

                # Save pre blocks
                if result["pre_blocks"]:
                    pre_file = OUTPUT_DIR / f"{safe}_pre.txt"
                    pre_file.write_text("\n---\n".join(result["pre_blocks"]),
                                        encoding="utf-8")

                # Save form fields + select options
                if result["form_fields"] or result["select_options"]:
                    meta_file = OUTPUT_DIR / f"{safe}_metadata.json"
                    with open(meta_file, "w") as f:
                        json.dump({
                            "form_fields": result["form_fields"],
                            "select_options": result["select_options"],
                        }, f, indent=2)

            icon = "📊" if has_data else "⚪"
            detail = (f"{len(result['tables'])} tables, {total_rows} rows, "
                      f"{len(result['pre_blocks'])} pre, "
                      f"{len(result['form_fields'])} fields, "
                      f"{len(result['select_options'])} selects")
            print(f"[{i+1}/{total}] {icon} {code}: {detail}")

            all_results[code] = {
                "tables": len(result["tables"]),
                "total_rows": total_rows,
                "pre_blocks": len(result["pre_blocks"]),
                "form_fields": len(result["form_fields"]),
                "select_options": len(result["select_options"]),
                "has_data": has_data,
            }

            done_codes.add(code)
            if len(done_codes) % 10 == 0:
                with open(checkpoint_file, "w") as f:
                    json.dump(list(done_codes), f)

        except Exception as e:
            print(f"[{i+1}/{total}] ❌ {code}: {e}")
            all_results[code] = {"error": str(e)}

    # Save checkpoint
    with open(checkpoint_file, "w") as f:
        json.dump(list(done_codes), f)

    # Save results
    with open(OUTPUT_DIR / "table_extraction_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_probed": len(all_results),
            "with_data": data_functions,
            "results": all_results,
        }, f, indent=2)

    # Stats
    total_files = sum(1 for f in OUTPUT_DIR.glob("*") if f.is_file()
                      and not f.name.startswith("."))
    total_bytes = sum(f.stat().st_size for f in OUTPUT_DIR.glob("*")
                      if f.is_file() and not f.name.startswith("."))
    print(f"\n{'='*60}")
    print(f"COMPLETE: {len(all_results)} functions, {data_functions} with data")
    print(f"Files: {total_files}, Size: {total_bytes:,} bytes ({total_bytes/1024/1024:.1f} MB)")

    await page.close()
    await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
