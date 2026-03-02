"""Capture GWT RPC payloads for all 30 Informer BI reports.

Uses Playwright to:
  1. Login to KeyedIn ERP via SSO
  2. Navigate to the Informer reports listing
  3. Launch each report and intercept ViewRPCService + commandService POSTs
  4. Fill required date parameters with wide range (2000-2099)
  5. Save request payloads, response bodies, and discovered field names

Report categories:
  - LAUNCHABLE: Click Launch link, then Launch Report button -> ViewRPCService fires
  - EXPORT_ONLY: No Launch link (e.g., "Customer Listing Export") -> skipped
  - AUTO_RUN: Auto-runs on launch, no Launch Report button needed

Usage:
    python capture_all_reports.py                   # all reports, headed
    python capture_all_reports.py --headless         # all reports, headless
    python capture_all_reports.py --report "Cash Receipts"
    python capture_all_reports.py --skip-existing
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from playwright.sync_api import (
    BrowserContext,
    Page,
    Request,
    Response,
    sync_playwright,
)

# Use the proper RTL Row analysis from gwt_parser (not a heuristic)
from gwt_parser import discover_field_names as gwt_discover_field_names

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENV_FILE = Path(r"C:\Scripts\keyedin-capture\.env")
REPORTS_DIR = Path(r"C:\Scripts\keyedin-capture\reports")
MANIFEST_FILE = REPORTS_DIR / "field_names_manifest.json"

ERP_LOGIN_URL = "http://eaglesign.keyedinsign.com/"
INFORMER_BASE = "https://eaglesign.keyedinsign.com:8443"
INFORMER_HTML = f"{INFORMER_BASE}/eaglesign/Informer.html"

REPORTS: list[dict[str, Any]] = [
    {"id": 1441842, "name": "AR Invoice Details"},
    {"id": 1441843, "name": "AR Invoice Listing"},
    {"id": 1441844, "name": "AR Open Invoices"},
    {"id": 1441849, "name": "Cash Receipts"},
    {"id": 1441850, "name": "Customer Listing"},
    {"id": 1441851, "name": "Customer Listing Export"},
    {"id": 1441852, "name": "Customer Location Listing"},
    {"id": 1441853, "name": "Customer Location Listing Export"},
    {"id": 1441854, "name": "Inventory List"},
    {"id": 1441855, "name": "Inventory List Export"},
    {"id": 1441856, "name": "Inventory Transaction History"},
    {"id": 1441857, "name": "Invoice Register"},
    {"id": 1441859, "name": "Open Sales Order Backlog"},
    {"id": 1441860, "name": "Open Sales Orders"},
    {"id": 1441861, "name": "Open Work Orders"},
    {"id": 1441862, "name": "Planned Part Activity"},
    {"id": 1441865, "name": "Purchase History"},
    {"id": 1441866, "name": "Purchase Order Detail"},
    {"id": 1441868, "name": "Purchased Part Variance"},
    {"id": 1441869, "name": "Quote Status Report"},
    {"id": 1441870, "name": "Sales Cost Detail Report"},
    {"id": 1441872, "name": "Sales Order Bookings By Line Date"},
    {"id": 1441873, "name": "Sales Order Bookings By SO Date"},
    {"id": 1441874, "name": "Sales Order Detail"},
    {"id": 1441875, "name": "Sales Order Status by Customer"},
    {"id": 1441877, "name": "Sales Summary by Customer"},
    {"id": 1441878, "name": "Sales Summary by Product Type"},
    {"id": 1441883, "name": "Vendor Listing"},
    {"id": 1441884, "name": "Vendor Listing Export"},
    {"id": 1441887, "name": "Work Order Listing"},
]

# Report categories based on UI reconnaissance (2026-02-02).
# EXPORT_ONLY: no Launch link on reports home, requires Export flow.
# AUTO_RUN: auto-runs on launch, no "Launch Report" button in dialog.
EXPORT_ONLY_REPORTS = {
    "Customer Listing Export",
    "Customer Location Listing Export",
    "Inventory List Export",
    "Vendor Listing Export",
}
AUTO_RUN_REPORTS = {
    "AR Open Invoices",
    "Open Sales Orders",
    "Open Work Orders",
}
# Reports that need required date fields filled before Launch Report.
REQUIRED_PARAM_REPORTS = {
    "AR Invoice Details",
    "AR Invoice Listing",
    "Inventory Transaction History",
    "Purchase History",
    "Purchase Order Detail",
    "Purchased Part Variance",
    "Quote Status Report",
    "Sales Cost Detail Report",
    "Sales Order Detail",
    "Sales Order Status by Customer",
}

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def safe_filename(name: str) -> str:
    """Convert a report name to a filesystem-safe lowercase slug.

    Args:
        name: Human-readable report name.

    Returns:
        Slug suitable for use in filenames.
    """
    return re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_").lower()



@dataclass
class CaptureResult:
    """Result of capturing a single report's RPC exchange."""

    report_name: str
    report_id: int
    success: bool = False
    skipped: bool = False
    error: str = ""
    request_file: Path | None = None
    response_file: Path | None = None
    field_names: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Login + SSO
# ---------------------------------------------------------------------------


def login_and_sso(page: Page, username: str, password: str) -> bool:
    """Perform ERP login and follow SSO to Informer.

    Args:
        page: Playwright Page instance.
        username: KeyedIn ERP username.
        password: KeyedIn ERP password.

    Returns:
        True if JSESSIONID cookie was obtained after SSO.
    """
    sso_urls: list[str] = []

    def _on_request(request: Request) -> None:
        if "8443" in request.url:
            sso_urls.append(request.url)

    page.on("request", _on_request)

    # Step 1: Load ERP login page.
    log.info("Loading ERP login page: %s", ERP_LOGIN_URL)
    page.goto(ERP_LOGIN_URL, timeout=30_000)
    page.wait_for_load_state("networkidle")
    log.info("  URL after load: %s", page.url)

    # Step 2: Fill credentials and submit.
    log.info("Filling credentials and submitting login form...")
    page.fill("input[name=USERNAME]", username)
    page.fill("input[name=PASSWORD]", password)
    page.click("input[name=btnLogin]")
    time.sleep(3)
    page.wait_for_load_state("networkidle", timeout=30_000)
    log.info("  URL after login: %s", page.url)

    # Debug: screenshot and dump after login.
    page.screenshot(path=str(Path(r"C:\Scripts\signx-warehouse\warehouse\raw") / "debug_erp_after_login.png"))
    log.info("  ERP after-login screenshot saved")

    # Dump all frames and their URLs.
    all_frames = page.frames
    for i, f in enumerate(all_frames):
        log.info("  Frame[%d]: %s", i, f.url[:120])

    # Dump intercepted 8443 URLs so far.
    if sso_urls:
        log.info("  Intercepted 8443 URLs: %s", sso_urls[:5])

    # Step 3: Find SSO link to Informer.
    log.info("Searching for Informer SSO link...")
    sso_link: str | None = page.evaluate(
        """() => {
            const links = document.querySelectorAll('a');
            for (const a of links) {
                const href = a.href || '';
                if (href.includes('8443')) return href;
            }
            const frames = document.querySelectorAll('iframe');
            for (const f of frames) {
                const src = f.src || '';
                if (src.includes('8443')) return src;
            }
            return null;
        }"""
    )

    if not sso_link:
        # Fallback: try clicking menu items that mention reports/informer.
        log.info("No direct SSO link found, searching menu items...")
        menu_items: list[dict[str, Any]] = page.evaluate(
            """() => {
                const items = [];
                const elements = document.querySelectorAll('a, span, div, td');
                for (const el of elements) {
                    const text = (el.textContent || '').trim().toLowerCase();
                    if (text.includes('informer') || text.includes('bi report')
                        || text.includes('reports')) {
                        items.push({
                            tag: el.tagName,
                            text: (el.textContent || '').trim().substring(0, 50),
                            href: el.href || null,
                        });
                    }
                }
                return items.slice(0, 10);
            }"""
        )
        for item in menu_items:
            if item.get("href"):
                text = item["text"]
                log.info("  Clicking menu item: '%s'", text)
                try:
                    page.click(f"text='{text}'", timeout=5_000)
                    time.sleep(2)
                    page.wait_for_load_state("networkidle", timeout=10_000)
                except Exception as exc:
                    log.warning("  Click failed: %s", exc)

    # Resolve SSO URL.
    actual_sso = sso_link
    if not actual_sso:
        for u in sso_urls:
            if "sso" in u.lower() or "8443" in u:
                actual_sso = u
                break

    if actual_sso:
        log.info("Following SSO link: %s", actual_sso[:100])
        page.goto(actual_sso, timeout=30_000, wait_until="networkidle")
    else:
        log.info("Trying direct Informer URL: %s/eaglesign/sso", INFORMER_BASE)
        page.goto(
            f"{INFORMER_BASE}/eaglesign/sso",
            timeout=30_000,
            wait_until="networkidle",
        )

    time.sleep(2)
    log.info("  URL after SSO: %s", page.url)

    # Verify JSESSIONID.
    cookies = page.context.cookies()
    for c in cookies:
        if c["name"] == "JSESSIONID":
            log.info("  JSESSIONID obtained: %s...", c["value"][:16])
            return True

    log.error("JSESSIONID cookie not found after SSO.")
    return False


# ---------------------------------------------------------------------------
# Navigate to reports home
# ---------------------------------------------------------------------------


def navigate_to_reports_home(page: Page) -> None:
    """Ensure the page is on the Informer reports listing.

    Args:
        page: Playwright Page, already authenticated via SSO.
    """
    current = page.url
    if "Informer.html" not in current:
        log.info("Navigating to Informer reports home: %s", INFORMER_HTML)
        page.goto(INFORMER_HTML, timeout=30_000, wait_until="networkidle")
    else:
        log.info("Already on Informer page: %s", current)

    # Wait for the GWT app to render the reports table.
    # The reports listing contains a table or div with report titles.
    time.sleep(3)
    page.wait_for_load_state("networkidle", timeout=30_000)
    log.info("Reports home loaded. URL: %s", page.url)


# ---------------------------------------------------------------------------
# Launch helpers
# ---------------------------------------------------------------------------


def _click_launch_link(page: Page, report_name: str) -> bool:
    """Try to click the Launch link for a report on the current page.

    Uses 3 strategies: row-based Playwright locator, JS row walk, index-based.

    Returns:
        True if a Launch link was clicked.
    """
    # Strategy 1: Row-based Playwright locator.
    try:
        name_locator = page.locator(f"text='{report_name}'").first
        name_locator.wait_for(state="visible", timeout=5_000)
        row = name_locator.locator("xpath=ancestor::tr[1]")
        launch_link = row.locator("text=Launch").first
        launch_link.click(timeout=5_000)
        log.info("    Clicked Launch (strategy 1: row-based)")
        return True
    except Exception:
        pass

    # Strategy 2: JS row walk.
    try:
        clicked = page.evaluate(
            """(reportName) => {
                const allElements = document.querySelectorAll('td, div, span');
                for (const el of allElements) {
                    const text = (el.textContent || '').trim();
                    if (text === reportName || text.includes(reportName)) {
                        let row = el.closest('tr') || el.parentElement;
                        if (row) {
                            const links = row.querySelectorAll('a');
                            for (const a of links) {
                                if ((a.textContent || '').trim() === 'Launch') {
                                    a.click();
                                    return true;
                                }
                            }
                        }
                    }
                }
                return false;
            }""",
            report_name,
        )
        if clicked:
            log.info("    Clicked Launch (strategy 2: JS row walk)")
            return True
    except Exception:
        pass

    # Strategy 3: Index-based matching.
    try:
        all_launches = page.locator("text=Launch").all()
        visible_names: list[str] = page.evaluate(
            """() => {
                const names = [];
                const cells = document.querySelectorAll(
                    'td, div.reportTitle, span.reportTitle'
                );
                for (const c of cells) {
                    const t = (c.textContent || '').trim();
                    if (t.length > 3 && t.length < 80) names.push(t);
                }
                return names;
            }"""
        )
        for idx, vn in enumerate(visible_names):
            if report_name in vn or vn in report_name:
                if idx < len(all_launches):
                    all_launches[idx].click(timeout=5_000)
                    log.info("    Clicked Launch (strategy 3: index %d)", idx)
                    return True
    except Exception:
        pass

    return False


def _try_page2_launch(page: Page, report_name: str) -> bool:
    """Check for pagination and try to find the report on page 2.

    Returns:
        True if the Launch link was found and clicked on page 2.
    """
    log.info("    Report not found on page 1, checking for pagination...")
    try:
        # Look for a "Next" link or page 2 link in the GWT table.
        next_clicked = page.evaluate(
            """() => {
                // Look for Next, >, >>, page 2, or pagination links.
                const candidates = document.querySelectorAll('a, div, span, button');
                for (const el of candidates) {
                    const text = (el.textContent || '').trim();
                    if (text === 'Next' || text === '>' || text === '>>'
                        || text === '2' || text === 'Page 2') {
                        // Make sure it looks like a pagination control (small text).
                        if (text.length <= 6) {
                            el.click();
                            return true;
                        }
                    }
                }
                return false;
            }"""
        )
        if next_clicked:
            log.info("    Navigated to page 2")
            time.sleep(3)
            page.wait_for_load_state("networkidle", timeout=15_000)
            return _click_launch_link(page, report_name)
    except Exception as exc:
        log.warning("    Pagination attempt failed: %s", exc)

    return False


def _fill_required_date_fields(page: Page) -> None:
    """Fill required date fields in the parameter dialog with a wide range.

    Uses 01/01/2000 for start dates and 12/31/2099 for end dates.
    """
    log.info("    Filling required date fields...")
    try:
        # Find all visible input fields in the parameter dialog.
        filled = page.evaluate(
            """() => {
                const inputs = document.querySelectorAll(
                    'input[type="text"], input:not([type])'
                );
                let count = 0;
                for (const inp of inputs) {
                    // Skip hidden inputs.
                    if (inp.offsetParent === null) continue;
                    // Check if this looks like a date field (placeholder, label, nearby text).
                    const label = inp.closest('tr, div');
                    const labelText = label ? label.textContent.toLowerCase() : '';
                    const isDate = (
                        labelText.includes('date') || labelText.includes('from')
                        || labelText.includes('start') || labelText.includes('end')
                        || labelText.includes('begin') || labelText.includes('to')
                        || inp.placeholder.toLowerCase().includes('date')
                        || inp.placeholder.toLowerCase().includes('mm/')
                    );
                    if (!isDate) continue;

                    // Determine if this is a start or end date.
                    const isEnd = (
                        labelText.includes('end') || labelText.includes(' to')
                        || labelText.includes('through')
                    );

                    // Clear and fill the field.
                    inp.focus();
                    inp.value = '';
                    const nativeSet = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value'
                    ).set;
                    nativeSet.call(inp, isEnd ? '12/31/2099' : '01/01/2000');
                    inp.dispatchEvent(new Event('input', {bubbles: true}));
                    inp.dispatchEvent(new Event('change', {bubbles: true}));
                    inp.dispatchEvent(new Event('blur', {bubbles: true}));
                    count++;
                }
                return count;
            }"""
        )
        log.info("    Filled %d date field(s)", filled)
        time.sleep(1)
    except Exception as exc:
        log.warning("    Date field fill failed: %s", exc)


def _click_launch_report_button(page: Page) -> None:
    """Click the 'Launch Report' button in the parameter dialog.

    Handles the GWT PushButton with two instances (hidden + visible).
    Uses multiple strategies: Playwright locator click, then coordinate-based
    click if the locator click doesn't trigger GWT's internal handler.
    """
    # GWT PushButton widgets require specific event sequences.  We try
    # multiple CDP-level approaches since GWT may ignore some event paths.
    try:
        btns = page.locator("div.gwt-PushButton", has_text="Launch Report")
        btn_count = btns.count()
        log.info("    Found %d 'Launch Report' GWT PushButtons", btn_count)

        for i in range(btn_count):
            btn = btns.nth(i)
            if not btn.is_visible():
                continue

            box = btn.bounding_box()
            log.info(
                "    Visible PushButton nth=%d box=%s",
                i,
                f"({box['x']:.0f},{box['y']:.0f},{box['width']:.0f}x{box['height']:.0f})" if box else "None",
            )

            # Approach 1: Full mousedown → mouseup → click sequence at
            # coordinates (GWT PushButton listens to mousedown/mouseup).
            if box:
                cx = box["x"] + box["width"] / 2
                cy = box["y"] + box["height"] / 2
                page.mouse.move(cx, cy)
                time.sleep(0.1)
                page.mouse.down()
                time.sleep(0.1)
                page.mouse.up()
                log.info("    Approach 1: mousedown+up at (%.0f, %.0f)", cx, cy)
                time.sleep(2)
                return

    except Exception as exc:
        log.warning("    PushButton approach 1 failed: %s", exc)

    # Approach 2: Find the inner face element of the PushButton and click it.
    # GWT PushButton has structure: div.gwt-PushButton > div > div (up-face/down-face).
    try:
        clicked = page.evaluate(
            """() => {
                const btns = document.querySelectorAll('div.gwt-PushButton');
                for (const btn of btns) {
                    if (btn.offsetParent === null) continue;
                    if (!btn.textContent.trim().includes('Launch Report')) continue;
                    // Find the inner face element
                    const face = btn.querySelector('.gwt-PushButton-up-face, .html-face')
                                 || btn.firstElementChild || btn;
                    // Simulate full mouse event sequence on the face element
                    const rect = face.getBoundingClientRect();
                    const opts = {
                        bubbles: true, cancelable: true, view: window,
                        clientX: rect.left + rect.width/2,
                        clientY: rect.top + rect.height/2
                    };
                    face.dispatchEvent(new MouseEvent('mouseover', opts));
                    face.dispatchEvent(new MouseEvent('mousedown', opts));
                    face.dispatchEvent(new MouseEvent('mouseup', opts));
                    face.dispatchEvent(new MouseEvent('click', opts));
                    return true;
                }
                return false;
            }"""
        )
        if clicked:
            log.info("    Approach 2: JS face-element event dispatch")
            time.sleep(2)
            return
    except Exception as exc:
        log.warning("    Approach 2 failed: %s", exc)

    # Approach 3: Playwright dispatch_event (CDP DOM.dispatchEvent path).
    try:
        btns = page.locator("div.gwt-PushButton", has_text="Launch Report")
        for i in range(btns.count()):
            btn = btns.nth(i)
            if btn.is_visible():
                btn.dispatch_event("click")
                log.info("    Approach 3: dispatch_event('click') nth=%d", i)
                time.sleep(2)
                return
    except Exception as exc:
        log.warning("    Approach 3 failed: %s", exc)

    # Approach 4: Standard text matching for other button labels.
    for btn_text in ["Launch Report", "Run", "Execute", "OK", "Submit"]:
        try:
            btn = page.locator(f"text='{btn_text}'").first
            btn.wait_for(state="visible", timeout=2_000)
            btn.click(timeout=3_000)
            log.info("    Approach 4: text-match click '%s'", btn_text)
            return
        except Exception:
            continue

    log.warning("    Could not find any Launch Report / Run / Execute button")


# ---------------------------------------------------------------------------
# Capture a single report
# ---------------------------------------------------------------------------


def capture_single_report(
    page: Page,
    report: dict[str, Any],
    skip_existing: bool = False,
) -> CaptureResult:
    """Launch a report, intercept the commandService RPC, and save payloads.

    Args:
        page: Playwright Page on the Informer reports listing.
        report: Dict with ``id`` and ``name`` keys.
        skip_existing: If True, skip reports with existing payload files.

    Returns:
        CaptureResult describing what happened.
    """
    report_id: int = report["id"]
    report_name: str = report["name"]
    slug = safe_filename(report_name)

    result = CaptureResult(report_name=report_name, report_id=report_id)

    # Prefer ViewRPCService payloads (actual browser flow), fall back to commandService.
    view_request_file = REPORTS_DIR / f"report_{slug}_view_request.txt"
    view_response_file = REPORTS_DIR / f"report_{slug}_view_response.txt"
    cmd_request_file = REPORTS_DIR / f"report_{slug}_cmd_request.txt"
    cmd_response_file = REPORTS_DIR / f"report_{slug}_cmd_response.txt"

    if skip_existing and (
        view_request_file.exists()
        or cmd_request_file.exists()
    ):
        log.info("  [SKIP] %s -- payload files already exist", report_name)
        result.skipped = True
        return result

    # Storage for intercepted payloads (ViewRPCService preferred, commandService fallback).
    captured_view: dict[str, str] = {}
    captured_cmd: dict[str, str] = {}
    captured_view_response: list[str] = []
    captured_cmd_response: list[str] = []

    def on_request(request: Request) -> None:
        """Intercept ViewRPCService and commandService POST requests."""
        if request.method != "POST":
            return
        url = request.url
        if "ViewRPCService" in url and not captured_view:
            captured_view["url"] = url
            captured_view["payload"] = request.post_data or ""
            log.info("    Intercepted ViewRPCService request: %s (%d bytes)",
                     url, len(captured_view["payload"]))
        elif "commandService" in url and not captured_cmd:
            captured_cmd["url"] = url
            captured_cmd["payload"] = request.post_data or ""
            log.info("    Intercepted commandService request: %s", url)

    def on_response(response: Response) -> None:
        """Intercept ViewRPCService and commandService responses."""
        if response.request.method != "POST":
            return
        url = response.url
        try:
            if "ViewRPCService" in url and not captured_view_response:
                body = response.text()
                captured_view_response.append(body)
                log.info("    Intercepted ViewRPCService response (%d bytes)", len(body))
            elif "commandService" in url and not captured_cmd_response:
                body = response.text()
                captured_cmd_response.append(body)
                log.info("    Intercepted commandService response (%d bytes)", len(body))
        except Exception as exc:
            log.warning("    Failed to read response body: %s", exc)

    page.on("request", on_request)
    page.on("response", on_response)

    # Auto-accept JS alert dialogs (validation errors like "You must specify a value").
    dialog_messages: list[str] = []

    def _on_dialog(dialog) -> None:
        msg = dialog.message
        dialog_messages.append(msg)
        log.info("    Dialog accepted: %s", msg[:100])
        try:
            dialog.accept()
        except Exception:
            pass  # Dialog may already be dismissed

    page.on("dialog", _on_dialog)

    try:
        # ---------------------------------------------------------------
        # Step 1: Navigate to the report with launch=false.
        # This opens the report view without auto-launching the template.
        # ---------------------------------------------------------------
        report_url = (
            f"{INFORMER_HTML}#action=ReportRun"
            f"&reportId={report_id}&launch=false"
        )
        log.info("    Navigating to: ...reportId=%d&launch=false", report_id)
        page.goto(report_url, wait_until="commit", timeout=30_000)
        time.sleep(3)
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass

        # ---------------------------------------------------------------
        # Step 2: Click the "Data" tab to trigger ViewRPCService|getData.
        # The Data tab shows raw grid data and fires the RPC we need.
        # Try multiple strategies to find it.
        # ---------------------------------------------------------------
        has_rpc = lambda: captured_view or captured_cmd  # noqa: E731

        # Strategy A: Find element with text "Data" that looks like a tab.
        data_tab_clicked = page.evaluate("""() => {
            // Look for GWT tab bar items, labels, or divs with "Data" text
            const candidates = document.querySelectorAll(
                '.gwt-TabBarItem, .gwt-Label, .gwt-HTML, a, div, span, td'
            );
            for (const el of candidates) {
                const ownText = el.childNodes.length <= 2
                    ? Array.from(el.childNodes)
                        .filter(n => n.nodeType === 3)
                        .map(n => n.textContent.trim())
                        .join('')
                    : '';
                const text = (el.textContent || '').trim();
                // Match elements whose own text (not children) is "Data"
                if (ownText === 'Data' || (text === 'Data' && el.children.length === 0)) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        el.click();
                        return 'Clicked: <' + el.tagName + '> class=' + (el.className || '').substring(0, 60) + ' @ ' + Math.round(rect.x) + ',' + Math.round(rect.y);
                    }
                }
            }
            return null;
        }""")

        if data_tab_clicked:
            log.info("    Data tab clicked: %s", data_tab_clicked)
        else:
            log.warning("    Data tab not found via JS. Trying Playwright locator...")
            # Strategy B: Playwright text locator
            try:
                data_loc = page.locator("text='Data'").first
                data_loc.wait_for(state="visible", timeout=5_000)
                data_loc.click(timeout=5_000)
                log.info("    Data tab clicked via Playwright locator")
                data_tab_clicked = "playwright"
            except Exception:
                log.warning("    Data tab not found via locator either")

            if not data_tab_clicked:
                # Strategy C: Screenshot + dump elements for debugging
                page.screenshot(
                    path=str(REPORTS_DIR / f"debug_{slug}_no_data_tab.png")
                )
                all_text = page.evaluate("""() => {
                    const items = [];
                    const all = document.querySelectorAll('*');
                    for (const el of all) {
                        const t = (el.textContent || '').trim();
                        if (t.length > 0 && t.length < 30) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0 && el.children.length === 0) {
                                items.push(t);
                            }
                        }
                    }
                    return [...new Set(items)].slice(0, 50);
                }""")
                log.info("    Visible leaf text on page: %s", all_text[:500])

        # ---------------------------------------------------------------
        # Step 2b: Wait for RPC to fire after Data tab click.
        # ---------------------------------------------------------------
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and not has_rpc():
            time.sleep(0.5)

        # If a validation dialog appeared and no RPC fired, this is a
        # required-param report. Fill date fields and retry.
        if not has_rpc() and dialog_messages:
            log.info("    Validation dialog detected — filling required params...")
            time.sleep(2)
            try:
                page.wait_for_load_state("networkidle", timeout=10_000)
            except Exception:
                pass
            _fill_required_date_fields(page)
            _click_launch_report_button(page)
            deadline2 = time.monotonic() + 30
            while time.monotonic() < deadline2 and not has_rpc():
                time.sleep(0.5)
        elif not has_rpc():
            # Extra wait for slow reports.
            extra_deadline = time.monotonic() + 25
            while time.monotonic() < extra_deadline and not has_rpc():
                time.sleep(0.5)

        if not has_rpc():
            result.error = (
                f"Timed out waiting for RPC request (report: '{report_name}')"
            )
            log.error("  [FAIL] %s -- %s", report_name, result.error)
            return result

        # ---------------------------------------------------------------
        # Step 3: Wait for response and save payloads.
        # ---------------------------------------------------------------
        resp_deadline = time.monotonic() + 30
        while time.monotonic() < resp_deadline and not (
            captured_view_response or captured_cmd_response
        ):
            time.sleep(0.5)

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # Save ViewRPCService payloads (preferred).
        if captured_view:
            view_request_file.write_text(
                captured_view.get("payload", ""), encoding="utf-8"
            )
            result.request_file = view_request_file
            log.info("    Saved request  -> %s", view_request_file.name)

        if captured_view_response:
            resp_text = captured_view_response[0]
            view_response_file.write_text(resp_text, encoding="utf-8")
            result.response_file = view_response_file
            log.info("    Saved response -> %s", view_response_file.name)
        else:
            resp_text = ""

        # Also save commandService payloads if captured.
        if captured_cmd:
            cmd_request_file.write_text(
                captured_cmd.get("payload", ""), encoding="utf-8"
            )
            log.info("    Saved cmd request  -> %s", cmd_request_file.name)
        if captured_cmd_response:
            cmd_response_file.write_text(
                captured_cmd_response[0], encoding="utf-8"
            )
            log.info("    Saved cmd response -> %s", cmd_response_file.name)

        # Use best available response for field discovery.
        if not resp_text and captured_cmd_response:
            resp_text = captured_cmd_response[0]

        # Discover field names from the response.
        if resp_text:
            try:
                fields = gwt_discover_field_names(resp_text)
                result.field_names = fields
                log.info("    Discovered %d field names", len(fields))
            except Exception as exc:
                log.warning("    Field discovery failed: %s", exc)

        result.success = True
        log.info("  [OK] %s", report_name)

    except Exception as exc:
        result.error = str(exc)
        log.error("  [FAIL] %s -- %s", report_name, exc)
    finally:
        # Remove listeners to avoid duplicate captures on next report.
        try:
            page.remove_listener("dialog", _on_dialog)
        except Exception:
            pass
        page.remove_listener("request", on_request)
        page.remove_listener("response", on_response)

    return result


def return_to_reports_home(page: Page) -> None:
    """Navigate back to the Informer reports listing after capturing a report.

    Tries breadcrumb navigation first, then falls back to direct URL.

    Args:
        page: Playwright Page instance.
    """
    try:
        # Try clicking a "Reports Home" or "Home" breadcrumb/link.
        for link_text in ["Reports Home", "Home", "Reports", "Back"]:
            try:
                link = page.locator(f"text='{link_text}'").first
                if link.is_visible(timeout=2_000):
                    link.click(timeout=5_000)
                    time.sleep(2)
                    page.wait_for_load_state("networkidle", timeout=15_000)
                    log.info("    Navigated back via '%s' link", link_text)
                    return
            except Exception:
                continue
    except Exception:
        pass

    # Fallback: navigate directly.
    log.info("    Falling back to direct navigation to reports home")
    page.goto(INFORMER_HTML, timeout=30_000, wait_until="networkidle")
    time.sleep(2)


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def run(
    report_filter: str | None = None,
    headless: bool = False,
    skip_existing: bool = False,
) -> None:
    """Run the full capture workflow.

    Args:
        report_filter: If set, only capture the report with this name.
        headless: Run the browser in headless mode.
        skip_existing: Skip reports that already have saved payload files.
    """
    load_dotenv(ENV_FILE)
    username = os.environ.get("KEYEDIN_USERNAME", "")
    password = os.environ.get("KEYEDIN_PASSWORD", "")

    if not username or not password:
        log.error("Missing KEYEDIN_USERNAME or KEYEDIN_PASSWORD in %s", ENV_FILE)
        sys.exit(1)

    # Filter reports if requested.
    targets = REPORTS
    if report_filter:
        targets = [r for r in REPORTS if r["name"] == report_filter]
        if not targets:
            # Fuzzy match.
            lower_filter = report_filter.lower()
            targets = [r for r in REPORTS if lower_filter in r["name"].lower()]
        if not targets:
            log.error("No report matches filter: '%s'", report_filter)
            sys.exit(1)
        log.info("Filtered to %d report(s)", len(targets))

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    results: list[CaptureResult] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=headless,
            args=["--ignore-certificate-errors"],
        )
        context: BrowserContext = browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1400, "height": 900},
        )
        page: Page = context.new_page()

        # Login + SSO.
        if not login_and_sso(page, username, password):
            log.error("Login/SSO failed. Aborting.")
            page.screenshot(path=str(REPORTS_DIR / "login_failure_debug.png"))
            browser.close()
            sys.exit(1)

        # Navigate to reports home.
        navigate_to_reports_home(page)

        # Capture each report.
        for i, report in enumerate(targets, start=1):
            log.info(
                "\n[%d/%d] Processing: %s (id=%d)",
                i,
                len(targets),
                report["name"],
                report["id"],
            )

            try:
                result = capture_single_report(
                    page, report, skip_existing=skip_existing
                )
                results.append(result)
            except Exception as exc:
                log.error("  Unhandled error for %s: %s", report["name"], exc)
                results.append(
                    CaptureResult(
                        report_name=report["name"],
                        report_id=report["id"],
                        error=str(exc),
                    )
                )

            # No need to navigate home — each report uses direct URL.

        browser.close()

    # -----------------------------------------------------------------------
    # Save field names manifest
    # -----------------------------------------------------------------------
    manifest: dict[str, list[str]] = {}
    if MANIFEST_FILE.exists():
        try:
            manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    for res in results:
        if res.success and res.field_names:
            manifest[str(res.report_id)] = res.field_names

    if manifest:
        MANIFEST_FILE.write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )
        log.info("\nField names manifest saved to %s", MANIFEST_FILE)

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    captured = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)

    log.info("\n" + "=" * 60)
    log.info("CAPTURE SUMMARY")
    log.info("=" * 60)
    log.info("  Total:    %d", len(results))
    log.info("  Captured: %d", captured)
    log.info("  Failed:   %d", failed)
    log.info("  Skipped:  %d", skipped)

    if failed:
        log.info("\nFailed reports:")
        for r in results:
            if not r.success and not r.skipped:
                log.info("  - %s: %s", r.report_name, r.error)

    log.info("=" * 60)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        description="Capture GWT RPC RunReportCommand payloads for Informer reports.",
    )
    parser.add_argument(
        "--report",
        type=str,
        default=None,
        help="Capture only the report matching this name (partial match OK).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode (default: headed for debugging).",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=False,
        help="Skip reports whose payload files already exist on disk.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    args = parse_args()
    run(
        report_filter=args.report,
        headless=args.headless,
        skip_existing=args.skip_existing,
    )
