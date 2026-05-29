#!/usr/bin/env python3
"""
Informer Report CSV Export Automation.

Uses Playwright browser automation to export all 30 Informer reports as CSV
files via the Export Results UI. This bypasses GWT-RPC serialization
complexity by using the browser's native export functionality.

Requirements:
  - Playwright: pip install playwright && playwright install chromium
  - Chrome running with CDP: --remote-debugging-port=29229
  - Active Informer session (login first via ERP SSO)

Usage:
  python export_informer_reports.py [--output-dir DIR] [--report-ids ID,ID,...]
"""

import argparse
import asyncio
import glob
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

# Report IDs
ALL_REPORT_IDS = [
    1441842, 1441843, 1441844, 1441849, 1441850, 1441851, 1441852,
    1441853, 1441854, 1441855, 1441856, 1441857, 1441859, 1441860,
    1441861, 1441862, 1441865, 1441866, 1441868, 1441869, 1441870,
    1441872, 1441873, 1441874, 1441875, 1441877, 1441878, 1441883,
    1441884, 1441887,
]

USERNAME = os.environ.get("KEYEDIN_USERNAME", "")
PASSWORD = os.environ.get("KEYEDIN_PASSWORD", "")
if not USERNAME or not PASSWORD:
    raise SystemExit("Set KEYEDIN_USERNAME and KEYEDIN_PASSWORD env vars")
CDP_URL = os.environ.get("CDP_URL", "http://localhost:29229")

INFORMER_BASE = "https://eaglesign.keyedinsign.com:8443/eaglesign"
INFORMER_URL = f"{INFORMER_BASE}/Informer.html?locale=en_US"
ERP_LOGIN_URL = "https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/LOGIN.START"
SSO_URL = f"{INFORMER_BASE}/sso?u={USERNAME.upper()}"


def get_artifact_files():
    """Get current Playwright artifact files for download detection."""
    files = {}
    for d in glob.glob("/tmp/playwright-artifacts-*/"):
        try:
            for f in os.listdir(d):
                fp = os.path.join(d, f)
                if os.path.isfile(fp) and os.path.getsize(fp) > 100:
                    files[fp] = os.path.getmtime(fp)
        except OSError:
            pass
    return files


async def login_to_informer(page):
    """Authenticate via ERP login → SSO → Informer."""
    print("Logging in via ERP → SSO flow...")
    await page.goto(ERP_LOGIN_URL, timeout=60000)
    await asyncio.sleep(3)
    await page.fill('input[name="USERNAME"]', USERNAME)
    await page.fill('input[name="PASSWORD"]', PASSWORD)
    await page.evaluate('document.getElementById("SECURE").value = "true"')
    await page.evaluate("document.forms[0].submit()")
    await asyncio.sleep(8)

    await page.goto(SSO_URL, timeout=60000)
    await asyncio.sleep(8)

    await page.goto(INFORMER_URL, timeout=60000)
    await asyncio.sleep(8)

    body = await page.evaluate("() => document.body.innerText.substring(0, 200)")
    if "Brady Flink" in body:
        print("Logged in as Brady Flink")
        return True

    print(f"Login check: {body[:80]}")
    return False


async def export_one_report(page, report_id, output_dir):
    """Navigate to report, click Export Results → CSV → Export."""

    # Close any open dialog
    await page.evaluate("""() => {
        const popups = document.querySelectorAll('.gwt-PopupPanel');
        for (const p of popups) p.style.display = 'none';
    }""")
    await asyncio.sleep(1)

    # Navigate to report with auto-launch
    hash_url = f"#action=ReportRun&reportId={report_id}&launch=true"
    await page.evaluate(f'window.location.hash = "{hash_url}";')
    await asyncio.sleep(12)

    # Check state and try Launch Report if needed
    body = await page.evaluate("() => document.body.innerText.substring(0, 1000)")
    if "No items listed" in body or "Launch Report" in body:
        try:
            launch_btns = page.locator('div:text-is("Launch Report")')
            for i in range(await launch_btns.count()):
                box = await launch_btns.nth(i).bounding_box()
                if box and box["y"] > 250 and box["width"] < 200:
                    await launch_btns.nth(i).click()
                    await asyncio.sleep(15)
                    break
        except Exception:
            pass

    # Get report name
    report_name = await page.evaluate("""() => {
        const links = document.querySelectorAll('a');
        let name = '';
        for (const a of links) {
            const t = a.textContent.trim();
            if (t.length > 3 && t.length < 60 && !t.includes('Logged in')) name = t;
        }
        return name || 'unknown';
    }""")

    # Click Export Results
    try:
        er = page.locator('div:text-is("Export Results")')
        await er.first.click(timeout=5000)
    except Exception:
        return {"status": "error", "error": "No Export Results button", "name": report_name}
    await asyncio.sleep(3)

    # Record files before export for download detection
    before_files = get_artifact_files()

    # Check dialog state
    dialog_text = await page.evaluate("() => document.body.innerText")

    if "Comma-Separated Values" in dialog_text and "Output Filename" not in dialog_text:
        # Format selection page → click CSV option by text locator
        csv_option = page.locator('text="Comma-Separated Values"')
        try:
            await csv_option.first.click(timeout=5000)
        except Exception:
            await page.mouse.click(265, 205)
        await asyncio.sleep(3)

    # Verify on CSV settings page
    dialog_text2 = await page.evaluate("() => document.body.innerText")
    if "Output Filename" not in dialog_text2:
        return {"status": "error", "error": "Not on CSV settings page", "name": report_name}

    # Click Export button
    try:
        export_btns = page.locator('div:text-is("Export")')
        clicked = False
        for i in range(await export_btns.count()):
            box = await export_btns.nth(i).bounding_box()
            if box and box["y"] > 350:
                await export_btns.nth(i).click()
                clicked = True
                break
        if not clicked:
            return {"status": "error", "error": "Export button not found", "name": report_name}
    except Exception as e:
        return {"status": "error", "error": f"Export click failed: {e}", "name": report_name}

    # Wait for download
    await asyncio.sleep(25)

    # Check for new artifact files
    after_files = get_artifact_files()
    new_files = {k: v for k, v in after_files.items() if k not in before_files}

    if new_files:
        newest = max(new_files, key=new_files.get)
        safe_name = re.sub(r'[/\\:*?"<>|]', "_", report_name)[:40]
        dst = os.path.join(output_dir, f"report_{report_id}_{safe_name}.csv")
        shutil.copy2(newest, dst)
        size = os.path.getsize(dst)
        with open(dst, encoding="utf-8", errors="replace") as f:
            lines = sum(1 for _ in f)
        return {
            "status": "success",
            "name": report_name,
            "file": dst,
            "size": size,
            "lines": lines,
        }

    return {"status": "error", "error": "No download detected", "name": report_name}


async def run_exports(report_ids, output_dir):
    """Main export loop."""
    os.makedirs(output_dir, exist_ok=True)
    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]
        page = context.pages[0]

        # Check if logged in
        await page.goto(INFORMER_URL, timeout=120000)
        await asyncio.sleep(8)
        body = await page.evaluate("() => document.body.innerText.substring(0, 200)")

        if "Brady Flink" not in body:
            if not await login_to_informer(page):
                print("ERROR: Could not log in")
                return results

        success_count = 0
        for i, rid in enumerate(report_ids):
            # Skip already exported
            existing = [
                f
                for f in os.listdir(output_dir)
                if f.startswith(f"report_{rid}_") and os.path.getsize(os.path.join(output_dir, f)) > 100
            ]
            if existing:
                print(f"[{i + 1}/{len(report_ids)}] {rid}: already exported ({existing[0]})")
                success_count += 1
                continue

            print(f"[{i + 1}/{len(report_ids)}] {rid}...", end=" ", flush=True)

            try:
                result = await asyncio.wait_for(
                    export_one_report(page, rid, output_dir),
                    timeout=120,
                )
            except asyncio.TimeoutError:
                result = {"status": "error", "error": "Timeout"}
            except Exception as e:
                result = {"status": "error", "error": str(e)[:80]}

            results[str(rid)] = result

            if result["status"] == "success":
                success_count += 1
                print(f'OK {result["name"]}: {result["size"]:,}b, {result["lines"]}L')
            else:
                print(f'FAIL {result.get("name", "?")}: {result.get("error", "?")}')

        print(f"\n{'=' * 40}")
        print(f"Exported: {success_count}/{len(report_ids)}")
        total_size = sum(
            r.get("size", 0)
            for r in results.values()
            if r.get("status") == "success"
        )
        print(f"Total size: {total_size:,} bytes ({total_size / 1024 / 1024:.1f} MB)")

        failed = [
            (k, v) for k, v in results.items() if v.get("status") != "success"
        ]
        if failed:
            print(f"\nFailed ({len(failed)}):")
            for k, v in failed:
                print(f"  {k}: {v.get('error', '?')}")

    # Save results manifest
    with open(os.path.join(output_dir, "export_manifest.json"), "w") as f:
        json.dump(results, f, indent=2)

    return results


def main():
    parser = argparse.ArgumentParser(description="Export Informer reports to CSV")
    parser.add_argument(
        "--output-dir",
        default="probe_results/deep_probe/exports",
        help="Output directory for CSV files",
    )
    parser.add_argument(
        "--report-ids",
        default=None,
        help="Comma-separated report IDs (default: all 30)",
    )
    args = parser.parse_args()

    if args.report_ids:
        ids = [int(x.strip()) for x in args.report_ids.split(",")]
    else:
        ids = ALL_REPORT_IDS

    asyncio.run(run_exports(ids, args.output_dir))


if __name__ == "__main__":
    main()
