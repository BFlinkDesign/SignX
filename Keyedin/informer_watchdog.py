#!/usr/bin/env python3
"""
Informer Port 8443 Watchdog — monitors for recovery and auto-extracts.

Discovery: The KeyedIn Informer BI system runs a multi-tenant Jetty cluster:
  Ports 8440-8442 (LIVE): [other tenants — redacted]
  Port 8443 (DOWN): eaglesign

The eaglesign instance on port 8443 crashed. This script:
1. Polls port 8443 every 30 seconds
2. When it comes back, authenticates via GWT-RPC
3. Navigates to each report's DATA tab
4. Exports complete CSV for all 30 reports
"""

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

CDP_URL = os.environ.get("CDP_URL", "http://localhost:29229")
USERNAME = os.environ.get("KEYEDIN_USERNAME", "")
PASSWORD = os.environ.get("KEYEDIN_PASSWORD", "")
BASE = "https://eaglesign.keyedinsign.com"
INFORMER_URL = f"{BASE}:8443/eaglesign/informer/"
OUTPUT_DIR = Path(__file__).parent / "extraction_output" / "informer_exports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_IDS = [
    1441842, 1441843, 1441844, 1441849, 1441850, 1441851, 1441852,
    1441853, 1441854, 1441855, 1441856, 1441857, 1441859, 1441860,
    1441861, 1441862, 1441865, 1441866, 1441868, 1441869, 1441870,
    1441872, 1441873, 1441874, 1441875, 1441877, 1441878, 1441883,
    1441884, 1441887,
]


async def check_port(port: int = 8443) -> bool:
    """Non-blocking port check."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                "eaglesign.keyedinsign.com", port, ssl=False
            ),
            timeout=3,
        )
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


async def extract_all_reports(page):
    """Navigate to each report's DATA tab and export CSV."""
    results = []
    for report_id in REPORT_IDS:
        try:
            url = f"{INFORMER_URL}#action=ReportRun&reportId={report_id}"
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            # Click DATA tab if present
            data_tab = page.locator("text=Data").first
            if await data_tab.count() > 0:
                await data_tab.click()
                await asyncio.sleep(3)

            # Try Export → CSV
            export_btn = page.locator("text=Export").first
            if await export_btn.count() > 0:
                await export_btn.click()
                await asyncio.sleep(1)
                csv_btn = page.locator("text=CSV").first
                if await csv_btn.count() > 0:
                    async with page.expect_download(timeout=60000) as dl_info:
                        await csv_btn.click()
                    download = await dl_info.value
                    path = OUTPUT_DIR / f"report_{report_id}.csv"
                    await download.save_as(str(path))
                    size = path.stat().st_size
                    results.append({"id": report_id, "size": size, "status": "ok"})
                    print(f"  ✓ Report {report_id}: {size:,} bytes")
                    continue

            # Fallback: capture page content
            content = await page.content()
            fallback_path = OUTPUT_DIR / f"report_{report_id}.html"
            fallback_path.write_text(content, encoding="utf-8")
            results.append({"id": report_id, "size": len(content), "status": "html_fallback"})
            print(f"  ⚠ Report {report_id}: HTML fallback ({len(content)} bytes)")

        except Exception as e:
            results.append({"id": report_id, "error": str(e), "status": "error"})
            print(f"  ✗ Report {report_id}: {e}")

    return results


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-interval", type=int, default=30)
    parser.add_argument("--max-checks", type=int, default=0, help="0=unlimited")
    parser.add_argument("--extract-now", action="store_true",
                        help="Skip waiting, try extraction immediately")
    args = parser.parse_args()

    if not args.extract_now:
        print(f"Monitoring port 8443 every {args.check_interval}s...")
        print("Live ports: 8440-8442 (other tenants — redacted)")
        print()

        checks = 0
        while True:
            checks += 1
            if args.max_checks and checks > args.max_checks:
                print(f"Max checks ({args.max_checks}) reached. Exiting.")
                return

            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            alive = await check_port(8443)
            if alive:
                print(f"[{ts}] PORT 8443 IS BACK! Starting extraction...")
                break
            else:
                if checks % 10 == 0:
                    # Also check live ports to confirm cluster is healthy
                    p40 = await check_port(8440)
                    p41 = await check_port(8441)
                    p42 = await check_port(8442)
                    print(f"[{ts}] 8443=DOWN (check #{checks}) | "
                          f"8440={'UP' if p40 else 'DOWN'} "
                          f"8441={'UP' if p41 else 'DOWN'} "
                          f"8442={'UP' if p42 else 'DOWN'}")
                else:
                    print(f"[{ts}] Port 8443: DOWN (check #{checks})")

            await asyncio.sleep(args.check_interval)

    # Port is up — connect and extract
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(CDP_URL)
    if not browser.contexts:
        print("ERROR: No browser contexts found — is Chrome running?")
        await pw.stop()
        return
    ctx = browser.contexts[0]
    page = await ctx.new_page()

    # Navigate to Informer
    try:
        await page.goto(INFORMER_URL, wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(3)
        print(f"Informer loaded: {page.url}")
    except Exception as e:
        print(f"Failed to load Informer: {e}")
        await pw.stop()
        return

    # Check if we need to authenticate
    content = await page.content()
    if "login" in content.lower() and "username" in content.lower():
        print("Authentication required...")
        # The SSO flow from ERP should handle this if we have active ERP session
        # Try direct Informer login
        try:
            username_field = page.locator('input[name="username"], input[name="j_username"]')
            if await username_field.count() > 0:
                await username_field.fill(USERNAME)
                password_field = page.locator('input[name="password"], input[name="j_password"]')
                await password_field.fill(PASSWORD)
                await page.locator('button[type="submit"], input[type="submit"]').click()
                await asyncio.sleep(3)
        except Exception as e:
            print(f"Auth error: {e}")

    # Extract all reports
    print(f"\nExtracting {len(REPORT_IDS)} reports...")
    results = await extract_all_reports(page)

    # Summary
    ok = sum(1 for r in results if r.get("status") == "ok")
    total_bytes = sum(r.get("size", 0) for r in results if r.get("status") == "ok")
    print(f"\nDone: {ok}/{len(REPORT_IDS)} reports exported, {total_bytes:,} bytes total")

    import json
    with open(OUTPUT_DIR / "extraction_manifest.json", "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": results,
            "ok_count": ok,
            "total_bytes": total_bytes,
        }, f, indent=2)

    await page.close()
    await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
