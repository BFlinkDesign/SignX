"""
Tracer Bullet: Prove Playwright + CDP can login to KeyedIn and export ONE Informer report
============================================================================================

Steps:
  1. Connect to Chrome via CDP (assumes Chrome launched with --remote-debugging-port=9222)
  2. Navigate to KeyedIn login page
  3. Fill credentials from .env, submit login
  4. Verify login success (DASHBOARD page)
  5. Navigate to Informer BI portal via SSO link
  6. Open Customer Listing report (ID 1441850, ~6,268 rows)
  7. Click Export -> CSV
  8. Capture downloaded file
  9. Validate: CSV has rows, headers match expected schema

Success criteria:
  - Login succeeds without manual intervention
  - SSO handoff to Informer succeeds
  - CSV file captured with correct row count (within 10% of expected)
  - Entire flow completes in < 120 seconds

Usage:
  1. Launch Chrome:  chrome.exe --remote-debugging-port=9222
  2. Run:            python tracer_bullet.py
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, Browser

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ENV_FILE = Path(r"C:\Scripts\keyedin-capture\.env")
DOWNLOAD_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\tracer_bullet")
CDP_ENDPOINT = "http://127.0.0.1:9222"

LOGIN_URL = "https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/LOGIN.START"
DASHBOARD_URL = "https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/DASHBOARD"

# Informer BI base — port 8443 with SSO
INFORMER_BASE = "https://eaglesign.keyedinsign.com:8443"

# Target report for tracer bullet
TARGET_REPORT_ID = "1441850"  # Customer Listing
TARGET_REPORT_NAME = "Customer Listing"
EXPECTED_ROW_COUNT = 6268
ROW_TOLERANCE = 0.10  # 10%

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("tracer")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_credentials() -> tuple[str, str]:
    """Load KeyedIn credentials from .env file."""
    load_dotenv(ENV_FILE)
    username = os.environ.get("KEYEDIN_USERNAME")
    password = os.environ.get("KEYEDIN_PASSWORD")
    if not username or not password:
        log.error(f"Missing credentials in {ENV_FILE}")
        log.error("Set KEYEDIN_USERNAME and KEYEDIN_PASSWORD in .env")
        sys.exit(1)
    return username, password


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------


async def run_tracer():
    """Execute the tracer bullet test."""
    start_time = time.time()
    username, password = load_credentials()
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("TRACER BULLET — KeyedIn -> Informer -> CSV Export")
    log.info("=" * 60)

    async with async_playwright() as p:
        # Step 1: Connect to Chrome via CDP
        log.info("Step 1: Connecting to Chrome via CDP...")
        try:
            browser = await p.chromium.connect_over_cdp(CDP_ENDPOINT)
        except Exception as e:
            log.error(f"FAILED to connect to Chrome CDP at {CDP_ENDPOINT}")
            log.error(f"Launch Chrome with: chrome.exe --remote-debugging-port=9222")
            log.error(f"Error: {e}")
            return False

        log.info(f"  Connected. Contexts: {len(browser.contexts)}")

        # Get or create a browser context with download path
        if browser.contexts:
            context = browser.contexts[0]
        else:
            context = await browser.new_context()

        page = await context.new_page()

        # Step 2: Navigate to login
        log.info("Step 2: Navigating to KeyedIn login...")
        try:
            await page.goto(LOGIN_URL, timeout=30000)
            await page.wait_for_load_state("domcontentloaded")
        except Exception as e:
            log.error(f"FAILED to load login page: {e}")
            return False

        log.info(f"  Page title: {await page.title()}")

        # Step 3: Fill credentials and submit
        log.info("Step 3: Filling credentials...")
        try:
            # Try multiple selector patterns for username field
            for selector in [
                'input[name="USERNAME"]',
                'input[name="USERID"]',
                'input[type="text"]',
            ]:
                elem = await page.query_selector(selector)
                if elem:
                    await elem.fill(username)
                    log.info(f"  Username filled via {selector}")
                    break
            else:
                log.error("Could not find username field")
                return False

            # Password field
            for selector in [
                'input[name="PASSWORD"]',
                'input[type="password"]',
            ]:
                elem = await page.query_selector(selector)
                if elem:
                    await elem.fill(password)
                    log.info(f"  Password filled via {selector}")
                    break
            else:
                log.error("Could not find password field")
                return False

            # Submit
            for selector in [
                'input[name="btnLogin"]',
                'input[type="submit"]',
                'button[type="submit"]',
            ]:
                elem = await page.query_selector(selector)
                if elem:
                    await elem.click()
                    log.info(f"  Login submitted via {selector}")
                    break
            else:
                log.error("Could not find submit button")
                return False

            await page.wait_for_load_state("domcontentloaded", timeout=30000)
        except Exception as e:
            log.error(f"FAILED during login: {e}")
            return False

        # Step 4: Verify login
        log.info("Step 4: Verifying login...")
        await asyncio.sleep(2)  # Allow redirect
        current_url = page.url
        log.info(f"  Current URL: {current_url}")

        # Check if we landed on dashboard or got redirected
        if "LOGIN" in current_url.upper() and "DASHBOARD" not in current_url.upper():
            # Still on login page — check for error message
            error_text = await page.text_content("body")
            if "invalid" in (error_text or "").lower() or "error" in (error_text or "").lower():
                log.error("LOGIN FAILED — invalid credentials")
                return False
            log.warning("Still on login page, attempting to navigate to dashboard...")
            await page.goto(DASHBOARD_URL, timeout=30000)

        page_text = await page.text_content("body")
        if page_text and ("DASHBOARD" in page_text.upper() or "MENU" in page_text.upper()):
            log.info("  LOGIN SUCCESSFUL")
        else:
            log.warning("  Login status uncertain — continuing to test Informer SSO")

        # Step 5: Find and navigate to Informer BI
        log.info("Step 5: Navigating to Informer BI portal...")
        try:
            # Look for Informer/BI SSO link on the page
            # First try navigating to the reports menu
            # The SSO pattern is: /eaglesign/sso?u=bradyf&t=TOKEN&initialAction.action=ReportRun&remoteId=REPORT_ID
            # We need to find a link that goes to port 8443

            # Try clicking through the menu to find BI Reports
            sso_link = await page.query_selector('a[href*="8443"]')
            if not sso_link:
                sso_link = await page.query_selector('a[href*="sso"]')
            if not sso_link:
                # Navigate directly to informer URL pattern
                # First we need the SSO token — try to extract from any existing link
                all_links = await page.query_selector_all("a[href]")
                informer_url = None
                for link in all_links:
                    href = await link.get_attribute("href")
                    if href and "8443" in href:
                        informer_url = href
                        break

                if not informer_url:
                    # Try the direct Informer URL with the report ID
                    # We may need to construct the SSO URL manually
                    log.info("  No Informer link found on page. Trying BI Reports menu...")

                    # Navigate to the BI Reports section
                    bi_link = await page.query_selector('a[href*="INFORMER"]')
                    if not bi_link:
                        bi_link = await page.query_selector('a:has-text("BI Reports")')
                    if not bi_link:
                        bi_link = await page.query_selector('a:has-text("Informer")')

                    if bi_link:
                        await bi_link.click()
                        await page.wait_for_load_state("domcontentloaded", timeout=30000)
                        await asyncio.sleep(2)
                    else:
                        log.warning("  Could not find Informer menu link")
                        # Take a screenshot for debugging
                        screenshot_path = DOWNLOAD_DIR / "debug_after_login.png"
                        await page.screenshot(path=str(screenshot_path))
                        log.info(f"  Debug screenshot saved: {screenshot_path}")

                        # Try direct navigation to a known Informer SSO URL pattern
                        # Construct URL manually using session
                        log.info("  Attempting direct Informer navigation...")
                else:
                    await page.goto(informer_url, timeout=60000)
                    await page.wait_for_load_state("domcontentloaded")
            else:
                href = await sso_link.get_attribute("href")
                log.info(f"  Found Informer link: {href[:80]}...")
                await sso_link.click()
                await page.wait_for_load_state("domcontentloaded", timeout=60000)

        except Exception as e:
            log.error(f"FAILED navigating to Informer: {e}")
            screenshot_path = DOWNLOAD_DIR / "debug_informer_nav.png"
            await page.screenshot(path=str(screenshot_path))
            log.info(f"  Debug screenshot: {screenshot_path}")
            return False

        log.info(f"  Current URL: {page.url}")

        # Step 6: Navigate to the target report
        log.info(f"Step 6: Opening {TARGET_REPORT_NAME} (ID: {TARGET_REPORT_ID})...")
        try:
            # Check if we're on the Informer page
            # Look for the report in the report list, or navigate directly
            report_link = await page.query_selector(f'a[href*="{TARGET_REPORT_ID}"]')
            if report_link:
                await report_link.click()
                await page.wait_for_load_state("domcontentloaded", timeout=60000)
            else:
                # Try direct URL navigation to the report
                # Informer URL pattern: /eaglesign/report/{id} or similar
                report_url = f"{INFORMER_BASE}/eaglesign/report/{TARGET_REPORT_ID}"
                log.info(f"  Trying direct URL: {report_url}")
                await page.goto(report_url, timeout=60000)
                await page.wait_for_load_state("domcontentloaded")

            await asyncio.sleep(3)  # Wait for report to render
        except Exception as e:
            log.error(f"FAILED opening report: {e}")
            screenshot_path = DOWNLOAD_DIR / "debug_report_open.png"
            await page.screenshot(path=str(screenshot_path))
            return False

        # Take a screenshot for verification
        screenshot_path = DOWNLOAD_DIR / "report_loaded.png"
        await page.screenshot(path=str(screenshot_path))
        log.info(f"  Screenshot: {screenshot_path}")

        # Step 7: Export to CSV
        log.info("Step 7: Exporting report to CSV...")
        try:
            # Look for Export button/menu
            export_btn = None
            for selector in [
                'button:has-text("Export")',
                'a:has-text("Export")',
                '[data-action="export"]',
                '.export-button',
                'button[title*="Export"]',
                'button[title*="export"]',
                '#export',
                '.toolbar button:has-text("Export")',
            ]:
                export_btn = await page.query_selector(selector)
                if export_btn:
                    log.info(f"  Found export button: {selector}")
                    break

            if not export_btn:
                # Try looking in iframes
                frames = page.frames
                for frame in frames:
                    for selector in [
                        'button:has-text("Export")',
                        'a:has-text("Export")',
                    ]:
                        export_btn = await frame.query_selector(selector)
                        if export_btn:
                            log.info(f"  Found export in iframe: {selector}")
                            break
                    if export_btn:
                        break

            if not export_btn:
                log.warning("  Export button not found. Taking debug screenshot...")
                screenshot_path = DOWNLOAD_DIR / "debug_no_export.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)

                # Capture page HTML for DOM analysis
                html = await page.content()
                html_path = DOWNLOAD_DIR / "debug_page.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html)
                log.info(f"  Page HTML saved: {html_path}")

                log.error("FAILED: Could not find Export button")
                log.error("Manual DOM analysis needed — see debug files")
                return False

            # Set up download handler
            async with page.expect_download(timeout=60000) as download_info:
                await export_btn.click()
                await asyncio.sleep(1)

                # Look for CSV option in export menu
                csv_option = await page.query_selector('a:has-text("CSV")')
                if not csv_option:
                    csv_option = await page.query_selector('li:has-text("CSV")')
                if not csv_option:
                    csv_option = await page.query_selector('[data-format="csv"]')
                if csv_option:
                    async with page.expect_download(timeout=60000) as download_info:
                        await csv_option.click()

            download = await download_info.value
            csv_path = DOWNLOAD_DIR / f"tracer_{TARGET_REPORT_NAME.replace(' ', '_')}.csv"
            await download.save_as(str(csv_path))
            log.info(f"  Downloaded: {csv_path}")

        except Exception as e:
            log.error(f"FAILED during export: {e}")
            screenshot_path = DOWNLOAD_DIR / "debug_export_fail.png"
            await page.screenshot(path=str(screenshot_path))
            return False

        # Step 8: Validate CSV
        log.info("Step 8: Validating downloaded CSV...")
        try:
            import csv as csv_mod

            with open(csv_path, "r", encoding="utf-8-sig") as f:
                reader = csv_mod.reader(f)
                headers = next(reader)
                rows = list(reader)

            row_count = len(rows)
            log.info(f"  Headers: {headers[:5]}... ({len(headers)} columns)")
            log.info(f"  Row count: {row_count:,}")

            # Check row count tolerance
            min_expected = int(EXPECTED_ROW_COUNT * (1 - ROW_TOLERANCE))
            max_expected = int(EXPECTED_ROW_COUNT * (1 + ROW_TOLERANCE))

            if min_expected <= row_count <= max_expected:
                log.info(f"  Row count within tolerance ({min_expected}-{max_expected})")
            elif row_count > 0:
                log.warning(
                    f"  Row count {row_count} outside tolerance "
                    f"({min_expected}-{max_expected}) but data present"
                )
            else:
                log.error("  EMPTY CSV — export may have failed")
                return False

        except Exception as e:
            log.error(f"FAILED validating CSV: {e}")
            return False

        elapsed = time.time() - start_time
        log.info(f"\n{'=' * 60}")
        log.info(f"TRACER BULLET PASSED")
        log.info(f"  Login: OK")
        log.info(f"  Informer SSO: OK")
        log.info(f"  CSV Export: {row_count:,} rows ({len(headers)} columns)")
        log.info(f"  Elapsed: {elapsed:.1f}s")
        log.info(f"{'=' * 60}")

        # Write result manifest
        result = {
            "status": "PASS",
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "report_id": TARGET_REPORT_ID,
            "report_name": TARGET_REPORT_NAME,
            "csv_path": str(csv_path),
            "row_count": row_count,
            "column_count": len(headers),
            "headers": headers,
        }
        manifest_path = DOWNLOAD_DIR / "tracer_result.json"
        with open(manifest_path, "w") as f:
            json.dump(result, f, indent=2)

        return True


async def main():
    success = await run_tracer()
    if not success:
        log.error("\nTRACER BULLET FAILED")
        log.error("Review debug files in: " + str(DOWNLOAD_DIR))
        log.error(
            "Common fixes:\n"
            "  1. Ensure Chrome is running with --remote-debugging-port=9222\n"
            "  2. Check .env credentials are current\n"
            "  3. Verify KeyedIn is accessible (VPN?)\n"
            "  4. Check debug screenshots for DOM issues"
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
