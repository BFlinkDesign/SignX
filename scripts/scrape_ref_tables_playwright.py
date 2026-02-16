"""Scrape 33 MVI reference code listing tables using Playwright (system Chrome).

The reference tables are rendered inside nested MVI framesets that a simple
requests-based scraper can't reach. This script uses headless Chrome to:
  1. Login to KeyedIn ERP (POST to LOGIN.START)
  2. Navigate to each APPLOAD?APP={endpoint}
  3. Wait for the APP frame to load
  4. Extract the data table rows from the second <table>
  5. Save as CSV, overwriting broken 1-row files

Usage:
    python scrape_ref_tables_playwright.py              # All 33 tables
    python scrape_ref_tables_playwright.py STATES.LIST  # Single table
"""
import csv
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ENV_FILE = Path(r"C:\Scripts\keyedin-capture\.env")
OUTPUT_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\csv_exports")

load_dotenv(ENV_FILE)
USERNAME = os.environ["KEYEDIN_USERNAME"]
PASSWORD = os.environ["KEYEDIN_PASSWORD"]

ERP_BASE = "https://eaglesign.keyedinsign.com"
MVI_BASE = f"{ERP_BASE}/cgi-bin/mvi.exe"

REFERENCE_TABLES = [
    "SALES.TAXES.LIST",
    "STATES.LIST",
    "WORK.CODE.LIST",
    "SIGN.TEMPLATE.LISTING",
    "SHOW.INV.TYPES",
    "SALES.CODES.LIST",
    "SIGN.TYPE.CODES.LISTING",
    "SHOW.UM.CODES",
    "COUNTRY.LIST",
    "EST.QUOTE.STATUS.CODE.LIST",
    "WORK.DEPT.LIST",
    "QUOTE.SALES.STAGE.CODE.LISTING",
    "TERRITORY.CODES.LIST",
    "EXTRA.CHARGES.LIST",
    "ORDER.CLASSES.LIST",
    "SHOW.ADJUST.CODE",
    "SALESPERSONS.LIST",
    "PRICE.CODES.LIST",
    "SHOW.BUYERS",
    "SHOW.OP.STATUS",
    "ACCOUNT.TYPE.CODE.LISTING",
    "REASON.CODES.LIST",
    "SHOW.ISSUE.REASON.CODES",
    "CALL.METHOD.CODES.LISTING",
    "PRICE.CLASS.CODE.LIST",
    "PROJECT.MILESTONE.CODES.LISTING",
    "CALL.TYPE.CODES.LISTING",
    "LEAD.SOURCE.EVENT.LISTING",
    "SERVICE.CALL.STATUS.CODE.LISTING",
    "ORDER.TYPES.LIST",
    "SHOW.ENGR.STATUS.CODES",
    "PROJECT.STATUS.CODES.LISTING",
    "PROJECT.TYPE.CODES.LISTING",
]


def login(page):
    """Login to KeyedIn ERP via form POST."""
    print("[AUTH] Navigating to login page...")
    page.goto(f"{MVI_BASE}/LOGIN.START", wait_until="networkidle", timeout=30000)
    page.fill('input[name="USERNAME"]', USERNAME)
    page.fill('input[name="PASSWORD"]', PASSWORD)
    page.click('input[name="btnLogin"]')
    page.wait_for_load_state("networkidle", timeout=30000)
    # Verify login succeeded
    if "DASHBOARD" in page.url.upper() or "LOGIN" not in page.url.upper():
        print("[AUTH] Login successful!")
    else:
        print("[AUTH] WARNING: Login may have failed, continuing anyway...")


def extract_table_from_app_frame(page, endpoint):
    """Navigate to APPLOAD and extract data from the APP frame's data table.

    Returns (header_row, data_rows) where each is a list of strings.
    Returns ([], []) on failure.
    """
    appload_url = f"{MVI_BASE}/APPLOAD?APP={endpoint}"
    page.goto(appload_url, wait_until="networkidle", timeout=30000)

    # Find the APP frame
    app_frame = None
    for frame in page.frames:
        if frame.name == "APP":
            app_frame = frame
            break

    if app_frame is None:
        print(f"    No APP frame found")
        return [], []

    # Wait a moment for content to fully render
    time.sleep(1)

    # Check "Show All Codes" checkbox if it exists (reveals inactive records)
    show_all = app_frame.query_selector("#SHOW_ALL_CODES")
    if show_all and not show_all.is_checked():
        show_all.check()
        try:
            app_frame.evaluate("document.forms[0].submit()")
            time.sleep(2)
            page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(1)
            # Re-find the APP frame after form submit
            app_frame = None
            for frame in page.frames:
                if frame.name == "APP":
                    app_frame = frame
                    break
            if app_frame is None:
                print(f"    Lost APP frame after SHOW_ALL submit")
                return [], []
            print(f"    [SHOW_ALL] Enabled — including inactive records")
        except Exception as e:
            print(f"    [SHOW_ALL] Submit failed: {e}, using default view")

    # Get all tables in the APP frame
    tables = app_frame.query_selector_all("table")
    if len(tables) < 2:
        # Some endpoints might have only one table (or data in the first)
        # Try the last table available
        if not tables:
            print(f"    No tables found in APP frame")
            return [], []
        data_table = tables[-1]
    else:
        # Data is in the second table (index 1); first is the title
        data_table = tables[1]

    rows = data_table.query_selector_all("tr")
    if not rows:
        print(f"    Data table has no rows")
        return [], []

    header = []
    data = []
    # Track whether we've seen the header keywords row (some tables have
    # a sub-category label row before the actual column headers)
    seen_label_row = False

    for row in rows:
        cells = row.query_selector_all("td, th")
        if not cells:
            continue

        # Extract cell text and classes
        cell_texts = []
        cell_classes = []
        for cell in cells:
            text = cell.inner_text().strip()
            cell_texts.append(text)
            cell_classes.append(cell.get_attribute("class") or "")

        # Skip empty rows and spacer rows (all cells empty or just whitespace)
        non_empty = [t for t in cell_texts if t and t.strip()]
        if not non_empty:
            continue

        first_class = cell_classes[0]

        # --- Pattern 1: Header row detected by itemLabel class ---
        if "itemLabel" in first_class and not header:
            if cell_texts[0] == "" and len(cell_texts) > 1:
                header = cell_texts[1:]
            else:
                header = cell_texts
            continue

        # --- Pattern 2: Data rows with itemDataC selector column ---
        if "itemDataC" in first_class and len(cell_texts) > 1:
            if not header:
                # Infer header from previous non-empty row wasn't detected
                # This shouldn't normally happen but guard against it
                header = [f"Col{i}" for i in range(len(cell_texts) - 1)]
            data.append(cell_texts[1:])
            continue

        # --- Pattern 3: oddTableRow data rows (no itemDataC) ---
        if "oddTableRow" in first_class:
            if not header:
                header = [f"Col{i}" for i in range(len(cell_texts) - 1)]
            # First cell is empty selector column
            if cell_texts[0] == "" and len(cell_texts) > 1:
                data.append(cell_texts[1:])
            else:
                data.append(cell_texts)
            continue

        # --- Fallback: If we already have a header and data rows, this is
        # a non-oddTableRow data row (alternating row without class) ---
        if header and data:
            if cell_texts[0] == "" and len(cell_texts) > 1:
                data.append(cell_texts[1:])
            else:
                data.append(cell_texts)
            continue

        # --- Detect header heuristically for tables without itemLabel ---
        # If we haven't found a header yet and this row has multiple
        # non-empty cells that look like column names (short text, no digits
        # in first chars), treat it as header. Skip single-cell category rows.
        if not header and len(non_empty) >= 2:
            if cell_texts[0] == "" and len(cell_texts) > 1:
                header = cell_texts[1:]
            else:
                header = cell_texts
            continue

        # Skip single-cell category/sub-header rows (e.g., "Reason")
        if not header and len(non_empty) == 1:
            seen_label_row = True
            continue

    return header, data


def save_csv(endpoint, header, data, output_dir):
    """Save extracted table as CSV, preserving naming convention."""
    safe_name = endpoint.replace(".", "_")
    filepath = output_dir / f"ref_{safe_name}.csv"

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if header:
            writer.writerow(header)
        for row in data:
            writer.writerow(row)

    return filepath


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Determine which tables to scrape
    if len(sys.argv) > 1:
        targets = [sys.argv[1]]
    else:
        targets = REFERENCE_TABLES

    print(f"MVI Reference Table Scraper (Playwright)")
    print(f"Targets: {len(targets)} tables")
    print(f"Output: {OUTPUT_DIR}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        login(page)

        success = 0
        empty = 0
        failed = 0

        for i, endpoint in enumerate(targets, 1):
            safe_name = endpoint.replace(".", "_")
            print(f"  [{i}/{len(targets)}] {endpoint}...")

            try:
                header, data = extract_table_from_app_frame(page, endpoint)
            except PlaywrightTimeout:
                print(f"    TIMEOUT loading page")
                failed += 1
                continue
            except Exception as e:
                print(f"    ERROR: {type(e).__name__}: {e}")
                failed += 1
                continue

            if not data:
                if header:
                    # Table loaded but genuinely has 0 data rows
                    print(f"    Genuinely empty (header: {header})")
                    filepath = save_csv(endpoint, header, [], OUTPUT_DIR)
                    print(f"    Saved {filepath.name}: 0 data rows (empty table)")
                    empty += 1
                else:
                    print(f"    FAILED: No header or data extracted")
                    failed += 1
                continue

            # Validate before overwriting
            if len(data) < 1:
                print(f"    SKIP: Only {len(data)} rows, not overwriting")
                failed += 1
                continue

            filepath = save_csv(endpoint, header, data, OUTPUT_DIR)
            size_kb = filepath.stat().st_size / 1024
            print(f"    Saved {filepath.name}: {len(data)} data rows, {size_kb:.1f}KB")
            success += 1

            time.sleep(1)  # Rate limit

        browser.close()

    print(f"\nDone: {success} success, {empty} genuinely empty, {failed} failed")


if __name__ == "__main__":
    main()
