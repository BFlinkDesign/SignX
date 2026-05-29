#!/usr/bin/env python3
"""
Run all 18 CGI BI reports and extract their output data.
These use RUN_REPORT through the ERP (port 443), not Informer (port 8443).

Each report has a form with parameters → "Run Report" → BI_OUTPUT iframe with data.
"""

import asyncio
import csv as csv_mod
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CGI_BASE = "https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe"
CDP_URL = os.environ.get("CDP_URL", "http://localhost:29229")

OUTPUT_DIR = Path(__file__).parent / "extraction_output" / "bi_report_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# BI report functions that have RUN_REPORT capability
BI_REPORTS = [
    "CUST.PROD",
    "CUST.PROD.EXPORT",
    "CUST.SUM",
    "EMP.EFF",
    "EST.PROPOSAL.STATUS",
    "GM.BY.INV",
    "GM.BY.INV.EXPORT",
    "GM.BY.PROD",
    "GM.DET.PROD.PART",
    "GM.PROJECT",
    "PROD.CUST",
    "PROD.SUM",
    "QUOTE.PIPELINE.REPORT",
    "QV.PRINT",
    "SLSPER.PROD",
    "SLSPER.PROD.EXPORT",
    "SUM.DEPT.EFF",
    "SUM.WC.EFF",
]

# Also extract data from listing functions with embedded data
LISTING_FUNCTIONS = [
    "ACCOUNT.TYPE.CODE.LISTING",
    "CALL.METHOD.CODES.LISTING",
    "CALL.TYPE.CODES.LISTING",
    "COUNTRY.LIST",
    "CRM.SOLUTIONS.LISTING",
    "EST.QUOTE.STATUS.CODE.LIST",
    "EXTRA.CHARGES.LIST",
    "LANDLORD.MALL.TC.LISTING",
    "LEAD.SOURCE.EVENT.LISTING",
    "ORDER.CLASSES.LIST",
    "ORDER.TYPES.LIST",
    "PM.INSURANCE.LISTING",
    "PRICE.CLASS.CODE.LIST",
    "PRICE.CODES.LIST",
    "PROJECT.MILESTONE.CODES.LISTING",
    "PROJECT.STATUS.CODES.LISTING",
    "PROJECT.TYPE.CODES.LISTING",
    "QUOTE.SALES.STAGE.CODE.LISTING",
    "REASON.CODES.LIST",
    "SALES.CODES.LIST",
    "SALES.TAXES.LIST",
    "SALESPERSONS.LIST",
    "SERVICE.CALL.STATUS.CODE.LISTING",
    "SHOW.ACTIVITY",
    "SHOW.ADJUST.CODE",
    "SHOW.BUYERS",
    "SHOW.ENGR.STATUS.CODES",
    "SHOW.INV.TYPES",
    "SHOW.ISSUE.REASON.CODES",
    "SHOW.MRP",
    "SHOW.OP.STATUS",
    "SHOW.PART.PRICES",
    "SHOW.UM.CODES",
    "SIGN.TEMPLATE.LISTING",
    "SIGN.TYPE.CODES.LISTING",
    "STATES.LIST",
    "TERRITORY.CODES.LIST",
    "WORK.CODE.LIST",
    "WORK.DEPT.LIST",
]


async def extract_table_data(page, code: str) -> dict:
    """Extract table data from a CGI page using JS evaluation."""
    tables = await page.evaluate("""
        () => {
            const results = [];
            const allDocs = [document];
            
            // Include all iframes
            document.querySelectorAll('iframe').forEach(iframe => {
                try {
                    if (iframe.contentDocument) allDocs.push(iframe.contentDocument);
                } catch(e) {}
            });
            
            for (const doc of allDocs) {
                doc.querySelectorAll('table').forEach((table, tableIdx) => {
                    const headers = [];
                    const rows = [];
                    
                    // Get headers
                    table.querySelectorAll('thead th, thead td, tr:first-child th').forEach(th => {
                        headers.push(th.textContent.trim());
                    });
                    
                    // If no thead, try first row
                    if (headers.length === 0) {
                        const firstRow = table.querySelector('tr');
                        if (firstRow) {
                            firstRow.querySelectorAll('th, td').forEach(cell => {
                                const text = cell.textContent.trim();
                                if (text && !text.includes('\\n')) {
                                    headers.push(text);
                                }
                            });
                        }
                    }
                    
                    // Get data rows
                    const trs = table.querySelectorAll('tr');
                    const startIdx = headers.length > 0 ? 1 : 0;
                    for (let i = startIdx; i < trs.length; i++) {
                        const cells = [];
                        trs[i].querySelectorAll('td').forEach(td => {
                            // Get text, but also check for input values
                            const input = td.querySelector('input, select');
                            if (input) {
                                cells.push(input.value || td.textContent.trim());
                            } else {
                                cells.push(td.textContent.trim());
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
                            colCount: Math.max(...rows.map(r => r.length), headers.length)
                        });
                    }
                });
            }
            return results;
        }
    """)
    return tables


async def run_bi_report(page, code: str) -> dict:
    """Navigate to a BI report, click Run Report, and extract output."""
    url = f"{CGI_BASE}/APPLOAD?APP={code}"
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
    except Exception:
        pass
    await asyncio.sleep(2)

    # Look for and click "Run Report" button
    run_clicked = False
    for frame in [page] + list(page.frames):
        try:
            run_btn = frame.locator('input[name="RUN_REPORT"], input[value*="Run Report"], button:text("Run Report")')
            if await run_btn.count() > 0:
                await run_btn.first.click()
                run_clicked = True
                break
        except Exception:
            pass

    if run_clicked:
        await asyncio.sleep(5)  # Wait for report to generate

    # Extract all table data from the result
    tables = await extract_table_data(page, code)

    # Also check for <pre> content (some reports output pre-formatted text)
    pre_content = []
    for frame in [page] + list(page.frames):
        try:
            fc = await frame.content()
            pres = re.findall(r'<pre[^>]*>(.*?)</pre>', fc, re.DOTALL | re.IGNORECASE)
            pre_content.extend(pres)
        except Exception:
            pass

    return {
        "code": code,
        "run_clicked": run_clicked,
        "tables": tables,
        "pre_content": pre_content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def extract_listing(page, code: str) -> dict:
    """Extract embedded table data from listing functions."""
    url = f"{CGI_BASE}/APPLOAD?APP={code}"

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
    except Exception:
        pass
    await asyncio.sleep(2)

    tables = await extract_table_data(page, code)

    return {
        "code": code,
        "tables": tables,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def authenticate(page) -> bool:
    """Authenticate to KeyedIn ERP."""
    USERNAME = os.environ.get("KEYEDIN_USERNAME", "")
    PASSWORD = os.environ.get("KEYEDIN_PASSWORD", "")

    # Check if already authenticated by navigating to a known page
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

    # Need to login
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
                print(f"  License quota exceeded — waiting 30s (attempt {attempt+1})")
                await asyncio.sleep(30)
                continue
            if "LOGIN.START" not in page.url:
                return True
        except Exception as e:
            print(f"  Auth attempt {attempt+1} failed: {e}")
            await asyncio.sleep(5)
    return False


async def main():
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
        print("Authentication FAILED — aborting")
        await pw.stop()
        sys.exit(1)

    print("Authenticated ✓\n")

    all_results = {}

    # Extract BI reports
    print(f"{'='*60}")
    print(f"RUNNING {len(BI_REPORTS)} BI REPORTS")
    print(f"{'='*60}\n")

    for i, code in enumerate(BI_REPORTS):
        try:
            result = await run_bi_report(page, code)
            total_rows = sum(t.get("rowCount", 0) for t in result["tables"])
            total_tables = len(result["tables"])

            # Save JSON data
            out_file = OUTPUT_DIR / f"{code}_bi_data.json"
            with open(out_file, "w") as f:
                json.dump(result, f, indent=2)

            # Save CSV for each table
            for ti, table in enumerate(result["tables"]):
                csv_file = OUTPUT_DIR / f"{code}_table{ti}.csv"
                with open(csv_file, "w", newline="") as f:
                    writer = csv_mod.writer(f)
                    if table["headers"]:
                        writer.writerow(table["headers"])
                    for row in table["rows"]:
                        writer.writerow(row)

            # Save pre content
            if result["pre_content"]:
                pre_file = OUTPUT_DIR / f"{code}_pre.txt"
                pre_file.write_text("\n".join(result["pre_content"]), encoding="utf-8")

            run_icon = "▶" if result["run_clicked"] else "⚪"
            print(f"[{i+1}/{len(BI_REPORTS)}] {run_icon} {code}: "
                  f"{total_tables} tables, {total_rows} rows, "
                  f"{len(result['pre_content'])} pre blocks")

            all_results[code] = {
                "type": "bi_report",
                "tables": total_tables,
                "rows": total_rows,
                "pre_blocks": len(result["pre_content"]),
            }

        except Exception as e:
            print(f"[{i+1}/{len(BI_REPORTS)}] ❌ {code}: {e}")
            all_results[code] = {"type": "bi_report", "error": str(e)}

    # Extract listing data
    print(f"\n{'='*60}")
    print(f"EXTRACTING {len(LISTING_FUNCTIONS)} LISTING FUNCTIONS")
    print(f"{'='*60}\n")

    for i, code in enumerate(LISTING_FUNCTIONS):
        try:
            result = await extract_listing(page, code)
            total_rows = sum(t.get("rowCount", 0) for t in result["tables"])
            total_tables = len(result["tables"])

            # Save JSON
            out_file = OUTPUT_DIR / f"{code}_listing_data.json"
            with open(out_file, "w") as f:
                json.dump(result, f, indent=2)

            # Save CSV for each table
            for ti, table in enumerate(result["tables"]):
                csv_file = OUTPUT_DIR / f"{code}_table{ti}.csv"
                with open(csv_file, "w", newline="") as f:
                    writer = csv_mod.writer(f)
                    if table["headers"]:
                        writer.writerow(table["headers"])
                    for row in table["rows"]:
                        writer.writerow(row)

            print(f"[{i+1}/{len(LISTING_FUNCTIONS)}] 📊 {code}: "
                  f"{total_tables} tables, {total_rows} rows")

            all_results[code] = {
                "type": "listing",
                "tables": total_tables,
                "rows": total_rows,
            }

        except Exception as e:
            print(f"[{i+1}/{len(LISTING_FUNCTIONS)}] ❌ {code}: {e}")
            all_results[code] = {"type": "listing", "error": str(e)}

    # Save summary
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_functions": len(all_results),
        "results": all_results,
    }
    with open(OUTPUT_DIR / "extraction_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Final stats
    total_files = sum(1 for f in OUTPUT_DIR.glob("*") if f.is_file())
    total_bytes = sum(f.stat().st_size for f in OUTPUT_DIR.glob("*") if f.is_file())
    print(f"\n{'='*60}")
    print("EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Files: {total_files}")
    print(f"Total data: {total_bytes:,} bytes ({total_bytes/1024/1024:.1f} MB)")

    await page.close()
    await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
