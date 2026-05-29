#!/usr/bin/env python3
"""
Probe ALL 240 CGI functions + Informer DATA tabs.
Zero gaps. Every function classified and saved.

Usage:
    python probe_all_240.py                  # Probe all 240 CGI functions
    python probe_all_240.py --informer       # Also probe Informer DATA tabs
    python probe_all_240.py --resume         # Resume from last checkpoint
"""

import asyncio
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

USERNAME = os.environ.get("KEYEDIN_USERNAME", "BradyF")
PASSWORD = os.environ.get("KEYEDIN_PASSWORD", os.environ.get("KEYEDIN_PASSWORD", ""))
CDP_URL = os.environ.get("CDP_URL", "http://localhost:29229")

ERP_BASE = "https://eaglesign.keyedinsign.com"
CGI_BASE = f"{ERP_BASE}/cgi-bin/mvi.exe"
INFORMER_BASE = "https://eaglesign.keyedinsign.com:8443/eaglesign"

OUTPUT_DIR = Path(__file__).parent / "extraction_output"
CGI_DIR = OUTPUT_DIR / "cgi_full_probe"
INFORMER_DIR = OUTPUT_DIR / "informer_data"
CHECKPOINT_FILE = OUTPUT_DIR / ".probe_checkpoint.json"
RESULTS_FILE = OUTPUT_DIR / "full_240_probe_results.json"

# All 240 function codes (from keyedin-mcp complete network analysis)
ALL_240_CODES = [
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

INFORMER_REPORT_IDS = [
    "1441842", "1441843", "1441844", "1441849", "1441850", "1441851",
    "1441852", "1441853", "1441854", "1441855", "1441856", "1441857",
    "1441859", "1441860", "1441861", "1441862", "1441865", "1441866",
    "1441868", "1441869", "1441870", "1441872", "1441873", "1441874",
    "1441875", "1441877", "1441878", "1441883", "1441884", "1441887",
]


def classify_response(content: str, function_code: str) -> str:
    """Classify CGI response type."""
    cu = content.upper()
    if "NOT AUTHORIZED" in cu:
        return "unauthorized"
    if "LOGIN.START" in cu and "USERNAME" in cu and "PASSWORD" in cu:
        return "login_redirect"
    if "EXCEEDED YOUR LICENSE QUOTA" in cu:
        return "license_quota"
    if "REPORT.IFRAME" in content or "REPORT.VIEW" in content:
        return "bi_report"
    if "<TABLE" in cu:
        tr_count = cu.count("<TR")
        if tr_count > 5:
            return "data_listing"
        if tr_count > 0:
            return "form_with_table"
    if "<FORM" in cu:
        return "form"
    if "<PRE" in cu:
        return "preformatted"
    if len(content.strip()) < 200:
        return "minimal"
    return "other"


def extract_text(html: str) -> str:
    """Strip HTML tags, keep readable text."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&nbsp;", " ").replace("&quot;", '"')
    text = re.sub(r"<[^>]+>", " ", text)
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in text.split("\n")]
    return "\n".join(l for l in lines if l)


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------

class Checkpoint:
    def __init__(self, path: Path):
        self.path = path
        self.data: dict = {}
        if path.exists():
            with open(path) as f:
                self.data = json.load(f)

    def is_done(self, key: str) -> bool:
        return key in self.data

    def mark(self, key: str, result: dict):
        self.data[key] = result
        # Save every 10 items
        if len(self.data) % 10 == 0:
            self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)


# ---------------------------------------------------------------------------
# Main Probe
# ---------------------------------------------------------------------------

async def probe_all_cgi(page, checkpoint: Checkpoint, resume: bool = False):
    """Probe ALL 240 CGI functions via browser. Zero gaps."""
    CGI_DIR.mkdir(parents=True, exist_ok=True)

    total = len(ALL_240_CODES)
    results = {}
    done = 0
    skipped = 0

    for i, code in enumerate(ALL_240_CODES):
        ck = f"cgi_{code}"
        if resume and checkpoint.is_done(ck):
            skipped += 1
            results[code] = checkpoint.data[ck]
            continue

        done += 1
        progress = f"[{i+1}/{total}]"

        # Build URL
        if code.startswith("#"):
            url = f"{ERP_BASE}/{code}"
        else:
            url = f"{CGI_BASE}/APPLOAD?APP={code}"

        try:
            # Navigate
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            except Exception:
                pass  # framesets often abort

            await asyncio.sleep(1.5)

            # Gather content from all frames
            all_parts = []
            try:
                main = await page.content()
                all_parts.append(main)
            except Exception:
                pass

            for frame in page.frames:
                try:
                    fc = await frame.content()
                    all_parts.append(fc)
                except Exception:
                    pass

            content = "\n<!-- FRAME -->\n".join(all_parts) if all_parts else ""

            # Classify
            rtype = classify_response(content, code)

            # Check for session loss mid-probe
            if rtype == "login_redirect":
                print(f"{progress} {code}: SESSION LOST — re-authenticating...")
                ok = await authenticate(page)
                if not ok:
                    print("FATAL: Cannot re-authenticate. Stopping.")
                    break
                # Retry this function
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                except Exception:
                    pass
                await asyncio.sleep(1.5)
                all_parts = []
                try:
                    main = await page.content()
                    all_parts.append(main)
                except Exception:
                    pass
                for frame in page.frames:
                    try:
                        fc = await frame.content()
                        all_parts.append(fc)
                    except Exception:
                        pass
                content = "\n<!-- FRAME -->\n".join(all_parts) if all_parts else ""
                rtype = classify_response(content, code)

            if rtype == "license_quota":
                print(f"{progress} {code}: LICENSE QUOTA — waiting 30s then retrying...")
                await asyncio.sleep(30)
                # Retry same function (up to 3 attempts)
                for retry in range(3):
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    except Exception:
                        pass
                    await asyncio.sleep(1.5)
                    all_parts = []
                    try:
                        main = await page.content()
                        all_parts.append(main)
                    except Exception:
                        pass
                    for frame in page.frames:
                        try:
                            fc = await frame.content()
                            all_parts.append(fc)
                        except Exception:
                            pass
                    content = "\n<!-- FRAME -->\n".join(all_parts) if all_parts else ""
                    rtype = classify_response(content, code)
                    if rtype != "license_quota":
                        break
                    print(f"{progress} {code}: still quota-blocked, retry {retry+1}/3...")
                    await asyncio.sleep(30)
                if rtype == "license_quota":
                    checkpoint.mark(ck, {"status": "license_quota", "timestamp": datetime.now(timezone.utc).isoformat()})
                    results[code] = {"status": "license_quota"}
                    print(f"{progress} {code}: FAILED after 3 retries (license quota)")
                    continue

            # Save HTML
            safe_name = code.replace("#", "HASH_")
            html_file = CGI_DIR / f"{safe_name}.html"
            html_file.write_text(content, encoding="utf-8")

            # Save text extract
            text = extract_text(content)
            if text.strip():
                txt_file = CGI_DIR / f"{safe_name}.txt"
                txt_file.write_text(text, encoding="utf-8")

            # Extract table data if present
            table_rows = 0
            if "<TABLE" in content.upper():
                table_rows = content.upper().count("<TR")

            # Extract form fields
            form_fields = []
            for match in re.finditer(
                r'<input[^>]*name=["\']([^"\']+)["\'][^>]*/?>',
                content, re.IGNORECASE
            ):
                form_fields.append(match.group(1))
            for match in re.finditer(
                r'<select[^>]*name=["\']([^"\']+)["\'][^>]*>',
                content, re.IGNORECASE
            ):
                form_fields.append(match.group(1))

            # Extract links/submenus
            sub_links = []
            for match in re.finditer(
                r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                content, re.IGNORECASE | re.DOTALL
            ):
                href = match.group(1)
                link_text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
                if href and not href.startswith("#") and not href.startswith("javascript:void"):
                    sub_links.append({"href": href, "text": link_text[:100]})

            result = {
                "response_type": rtype,
                "content_length": len(content),
                "table_rows": table_rows,
                "form_fields": form_fields[:30],
                "sub_links_count": len(sub_links),
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            results[code] = result
            checkpoint.mark(ck, result)

            icon = {
                "unauthorized": "🔒",
                "data_listing": "📊",
                "form": "📝",
                "form_with_table": "📋",
                "bi_report": "📈",
                "preformatted": "📄",
                "minimal": "⚪",
                "other": "❓",
            }.get(rtype, "❓")

            print(
                f"{progress} {icon} {code}: {rtype} "
                f"({len(content)} bytes, {table_rows} rows, "
                f"{len(form_fields)} fields)"
            )

        except Exception as e:
            result = {
                "response_type": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            results[code] = result
            checkpoint.mark(ck, result)
            print(f"{progress} ❌ {code}: ERROR — {e}")

    checkpoint.save()

    if skipped > 0:
        print(f"\nResumed: {skipped} already done, {done} newly probed")

    return results


async def authenticate(page) -> bool:
    """Authenticate to KeyedIn ERP."""
    print("Authenticating...")

    # First check if already authenticated
    try:
        await page.goto(
            f"{CGI_BASE}/REPORT.VIEW.INDEX",
            wait_until="domcontentloaded",
            timeout=20000,
        )
    except Exception:
        pass
    await asyncio.sleep(3)

    all_text = ""
    try:
        for frame in page.frames:
            try:
                all_text += await frame.content()
            except Exception:
                pass
        all_text += await page.content()
    except Exception:
        pass

    if any(m in all_text for m in [
        "Eagle Sign", "Report Title", "Click on a report",
        "Selection Criteria", "Add to Favorites",
    ]):
        print("Already authenticated ✓")
        return True

    # Try login
    for attempt in range(10):
        try:
            try:
                await page.goto(
                    f"{CGI_BASE}/LOGIN.START",
                    wait_until="domcontentloaded",
                    timeout=20000,
                )
            except Exception:
                pass
            await asyncio.sleep(2)

            # Find login form in any frame
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

            # Check result
            post_content = ""
            try:
                for frame in page.frames:
                    try:
                        post_content += await frame.content()
                    except Exception:
                        pass
                post_content += await page.content()
            except Exception:
                pass

            if "EXCEEDED YOUR LICENSE QUOTA" in post_content.upper():
                print(f"  License quota exceeded (attempt {attempt+1}/10) — waiting 30s...")
                await asyncio.sleep(30)
                continue

            if any(m in post_content for m in [
                "Eagle Sign", "Report Title", "Selection Criteria",
            ]):
                print("Authentication successful ✓")
                return True

            if "LOGIN.START" not in page.url:
                print("Authentication successful ✓")
                return True

        except Exception as e:
            print(f"  Auth attempt {attempt+1} failed: {e}")
            await asyncio.sleep(5)

    print("Authentication FAILED after 10 attempts")
    return False


async def probe_informer_data_tabs(page, checkpoint: Checkpoint, resume: bool = False):
    """Probe Informer BI — navigate to each report and click DATA tab for full export."""
    INFORMER_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"PROBING INFORMER BI — {len(INFORMER_REPORT_IDS)} reports")
    print(f"{'='*60}\n")

    results = {}

    for i, rid in enumerate(INFORMER_REPORT_IDS):
        ck = f"informer_{rid}"
        if resume and checkpoint.is_done(ck):
            results[rid] = checkpoint.data[ck]
            continue

        progress = f"[{i+1}/{len(INFORMER_REPORT_IDS)}]"

        try:
            # Navigate to report
            url = f"{INFORMER_BASE}/informer/#action=ReportRun&reportId={rid}"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception:
                pass
            await asyncio.sleep(5)

            # Look for DATA tab and click it
            data_tab = page.locator('text="Data"').first
            if await data_tab.count() > 0:
                await data_tab.click()
                await asyncio.sleep(3)

            # Try to get the data content
            content = await page.content()

            # Look for export button
            export_btn = page.locator('text="Export"').first
            has_export = await export_btn.count() > 0

            # Try CSV export if available
            csv_data = None
            if has_export:
                try:
                    # Click Export, then CSV
                    await export_btn.click()
                    await asyncio.sleep(2)

                    csv_btn = page.locator('text="CSV"').first
                    if await csv_btn.count() > 0:
                        # Set up download listener
                        async with page.expect_download(timeout=30000) as download_info:
                            await csv_btn.click()
                        download = await download_info.value
                        save_path = INFORMER_DIR / f"report_{rid}.csv"
                        await download.save_as(str(save_path))
                        csv_data = save_path.read_text(encoding="utf-8", errors="replace")
                        row_count = csv_data.count("\n")
                        print(f"{progress} 📊 Report {rid}: CSV exported ({len(csv_data)} bytes, ~{row_count} rows)")
                except Exception as export_err:
                    print(f"{progress} ⚠️  Report {rid}: Export failed — {export_err}")

            # Save page HTML regardless
            html_file = INFORMER_DIR / f"report_{rid}_page.html"
            html_file.write_text(content, encoding="utf-8")

            # Extract visible table data
            table_data = await page.evaluate("""
                () => {
                    const tables = document.querySelectorAll('table');
                    const results = [];
                    tables.forEach(table => {
                        const rows = [];
                        table.querySelectorAll('tr').forEach(tr => {
                            const cells = [];
                            tr.querySelectorAll('td, th').forEach(cell => {
                                cells.push(cell.textContent.trim());
                            });
                            if (cells.length > 0) rows.push(cells);
                        });
                        if (rows.length > 0) results.push(rows);
                    });
                    return results;
                }
            """)

            result = {
                "report_id": rid,
                "has_data_tab": True,
                "has_export": has_export,
                "csv_exported": csv_data is not None,
                "csv_size": len(csv_data) if csv_data else 0,
                "csv_rows": csv_data.count("\n") if csv_data else 0,
                "page_tables": len(table_data),
                "page_table_rows": sum(len(t) for t in table_data),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            results[rid] = result
            checkpoint.mark(ck, result)

            if csv_data is None:
                print(f"{progress} 📋 Report {rid}: Page captured ({len(content)} bytes, {len(table_data)} tables)")

        except Exception as e:
            result = {
                "report_id": rid,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            results[rid] = result
            checkpoint.mark(ck, result)
            print(f"{progress} ❌ Report {rid}: ERROR — {e}")

    checkpoint.save()
    return results


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Probe ALL 240 CGI functions + Informer")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--informer", action="store_true", help="Also probe Informer DATA tabs")
    parser.add_argument("--informer-only", action="store_true", help="Only probe Informer")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(CDP_URL)
    contexts = browser.contexts
    if not contexts:
        print("ERROR: No browser contexts found")
        sys.exit(1)
    context = contexts[0]
    page = await context.new_page()
    print(f"Connected to Chrome via CDP")

    checkpoint = Checkpoint(CHECKPOINT_FILE)

    # Authenticate
    ok = await authenticate(page)
    if not ok:
        print("Cannot authenticate — aborting")
        await pw.stop()
        sys.exit(1)

    results = {"timestamp": datetime.now(timezone.utc).isoformat()}

    if not args.informer_only:
        # Probe ALL 240 CGI functions
        print(f"\n{'='*60}")
        print(f"PROBING ALL {len(ALL_240_CODES)} CGI FUNCTIONS")
        print(f"{'='*60}\n")

        cgi_results = await probe_all_cgi(page, checkpoint, args.resume)
        results["cgi_functions"] = cgi_results

        # Summary
        types = {}
        for code, r in cgi_results.items():
            t = r.get("response_type", "unknown")
            types[t] = types.get(t, 0) + 1

        print(f"\n{'='*60}")
        print("CGI PROBE SUMMARY")
        print(f"{'='*60}")
        print(f"Total probed: {len(cgi_results)}/{len(ALL_240_CODES)}")
        for t, count in sorted(types.items(), key=lambda x: -x[1]):
            print(f"  {t}: {count}")

        accessible = [c for c, r in cgi_results.items()
                      if r.get("response_type") not in ("unauthorized", "error", "login_redirect", "license_quota", "minimal")]
        print(f"\nACCESSIBLE functions: {len(accessible)}")
        for c in sorted(accessible):
            r = cgi_results[c]
            print(f"  {c}: {r.get('response_type')} ({r.get('content_length', 0)} bytes, {r.get('table_rows', 0)} rows)")

    if args.informer or args.informer_only:
        informer_results = await probe_informer_data_tabs(page, checkpoint, args.resume)
        results["informer_reports"] = informer_results

        print(f"\n{'='*60}")
        print("INFORMER PROBE SUMMARY")
        print(f"{'='*60}")
        exported = sum(1 for r in informer_results.values() if r.get("csv_exported"))
        errored = sum(1 for r in informer_results.values() if "error" in r)
        print(f"Total reports: {len(informer_results)}")
        print(f"CSV exported: {exported}")
        print(f"Errors: {errored}")

    # Save final results
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {RESULTS_FILE}")

    # Close page (not browser)
    await page.close()
    await pw.stop()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
