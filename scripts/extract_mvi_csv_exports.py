"""Bulk extract all MVI CSV exports and reference code listings from KeyedIn ERP.

6 CSV export endpoints (looped yearly 2005-2026) plus 33 reference code listing
tables. Outputs to warehouse/raw/csv_exports/ with checkpoint-based resume.

Usage:
    python extract_mvi_csv_exports.py download          # All 6 CSV endpoints
    python extract_mvi_csv_exports.py download --resume  # Skip done+errored jobs
    python extract_mvi_csv_exports.py refs              # 33 reference tables
    python extract_mvi_csv_exports.py merge             # Combine yearly CSVs
    python extract_mvi_csv_exports.py all               # Everything
    python extract_mvi_csv_exports.py all --resume      # Resume everything
    python extract_mvi_csv_exports.py download --endpoint EMP.HOURS.BY.DATE
    python extract_mvi_csv_exports.py download --year 2024
"""

import csv
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ENV_FILE = Path(r"C:\Scripts\keyedin-capture\.env")
OUTPUT_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\csv_exports")
CHECKPOINT_FILE = OUTPUT_DIR / "extraction_progress.json"

ERP_BASE = "https://eaglesign.keyedinsign.com"
MVI_BASE = f"{ERP_BASE}/cgi-bin/mvi.exe"

load_dotenv(ENV_FILE)
USERNAME = os.environ.get("KEYEDIN_USERNAME", "")
PASSWORD = os.environ.get("KEYEDIN_PASSWORD", "")

RATE_LIMIT_SECONDS = 3
POLL_INTERVAL_SECONDS = 3
POLL_TIMEOUT_SECONDS = 120
REQUEST_TIMEOUT_SECONDS = 180
MAX_RETRIES = 3
RETRY_BACKOFF = [30, 60, 120]  # Seconds between retries on ReadTimeout
START_YEAR = 2005
END_YEAR = 2026
CURRENT_DATE = datetime.now().strftime("%m/%d/%y")

# ---------------------------------------------------------------------------
# 6 CSV Export Endpoint Configurations
# ---------------------------------------------------------------------------
EXPORT_ENDPOINTS = [
    {
        "name": "EMP.HOURS.BY.DATE",
        "process": "EMP.HOURS.BY.DATE",
        "tip_frame": "LAB776.ENTRY",
        "run_suffix": ".EXPORT.RUN",
        "logkey": "LAB776E",
        "csv_filename": "BRADYF_EMP.HOURS.BY.DATE.CSV",
        "form_params": {
            "DIVNO": "20",
            "DISPLAY_WHERE": "E",
        },
    },
    {
        "name": "EXPORT.WO.LABOR.ANALYSIS",
        "process": "EXPORT.WO.LABOR.ANALYSIS",
        "tip_frame": "WOC280.ENTRY",
        "run_suffix": ".RUN",
        "logkey": "WOC280E",
        "csv_filename": "BRADYF.LABOR.TRANS.CSV",
        "form_params": {
            "DIVNO": "20",
            "DATE_TYPE": "DUE",
            "INCLUDE_SERVICE": "N",
        },
    },
    {
        "name": "GM.BY.INV.EXPORT",
        "process": "GM.BY.INV.EXPORT",
        "tip_frame": "SOP791.ENTRY",
        "run_suffix": ".RUN",
        "logkey": "SOP791E",
        "csv_filename": "BRADYF_GM_INVOICE.CSV",
        "form_params": {
            "DIVNO": "20",
            "REPORT_TYPE": "D",
        },
    },
    {
        "name": "SLSPER.PROD.EXPORT",
        "process": "SLSPER.PROD.EXPORT",
        "tip_frame": "SOP722.ENTRY",
        "run_suffix": ".RUN",
        "logkey": "SOP722E",
        "csv_filename": "BRADYF_GM_SALESPERSON.CSV",
        "form_params": {
            "DIVNO": "20",
        },
    },
    {
        "name": "EXPORT.WIP.SUMMARY",
        "process": "EXPORT.WIP.SUMMARY",
        "tip_frame": "WOC202.ENTRY",
        "run_suffix": ".RUN",
        "logkey": "WOC202E",
        "csv_filename": "BRADYF.WIP.SUMMARY.CSV",
        "form_params": {
            "DIVNO": "20",
            "ZERO_TRANS": "N",
        },
        "wip_types": ["C", "O"],  # Special: two passes per year
    },
    {
        "name": "CUST.PROD.EXPORT",
        "process": "CUST.PROD.EXPORT",
        "tip_frame": "SOP710E.ENTRY",
        "run_suffix": ".RUN",
        "logkey": "SOP710E",
        "csv_filename": "BRADYF_SALES_CUST_PROD.CSV",
        "form_params": {
            "DIVNO": "20",
        },
    },
]

# ---------------------------------------------------------------------------
# 33 Reference Code Listing Tables
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Network / Auth
# ---------------------------------------------------------------------------

def create_session() -> requests.Session:
    """Authenticate to KeyedIn ERP and return a requests Session."""
    s = requests.Session()
    s.verify = False
    s.headers.update(
        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"}
    )
    print("[AUTH] Getting initial session cookies...")
    s.get(f"{ERP_BASE}/", allow_redirects=True, timeout=30)
    print(f"[AUTH] Logging in as {USERNAME}...")
    resp = s.post(
        f"{MVI_BASE}/LOGIN.START",
        data={"USERNAME": USERNAME, "PASSWORD": PASSWORD, "btnLogin": "Login"},
        allow_redirects=True,
        timeout=30,
    )
    if "DASHBOARD" in resp.text.upper() or resp.status_code == 200:
        print("[AUTH] Login successful!")
    else:
        print("[AUTH] WARNING: Login may have failed")
    s.cookies.set("user", USERNAME.upper(), domain="eaglesign.keyedinsign.com")
    s.cookies.set("secure", "FALSE", domain="eaglesign.keyedinsign.com")
    return s


def is_session_expired(resp: requests.Response) -> bool:
    """Check if server response indicates session expired."""
    if resp.status_code == 302:
        location = resp.headers.get("Location", "")
        if "LOGIN" in location.upper():
            return True
    if resp.status_code == 200 and "LOGIN.START" in resp.text.upper():
        return True
    return False


def safe_request(session, method, url, max_retries=1, **kwargs):
    """Make a request with re-auth on session expiry and retry on timeout."""
    kwargs.setdefault("timeout", REQUEST_TIMEOUT_SECONDS)
    kwargs.setdefault("allow_redirects", True)

    resp = None
    for attempt in range(MAX_RETRIES):
        try:
            if method == "GET":
                resp = session.get(url, **kwargs)
            else:
                resp = session.post(url, **kwargs)
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            if attempt < MAX_RETRIES - 1:
                backoff = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                print(f"    [RETRY] {type(e).__name__} on attempt {attempt + 1}/{MAX_RETRIES}, "
                      f"waiting {backoff}s...")
                time.sleep(backoff)
                # Re-auth in case session went stale during timeout
                print("[AUTH] Re-authenticating after timeout...")
                session = create_session()
                continue
            else:
                print(f"    [RETRY] {type(e).__name__}: all {MAX_RETRIES} attempts exhausted for {url}")
                raise
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                backoff = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                print(f"    [RETRY] {type(e).__name__} on attempt {attempt + 1}/{MAX_RETRIES}, "
                      f"waiting {backoff}s...")
                time.sleep(backoff)
                continue
            raise

        if is_session_expired(resp) and attempt < MAX_RETRIES - 1:
            print("[AUTH] Session expired, re-authenticating...")
            session = create_session()
            continue

        if is_session_expired(resp):
            print(f"[AUTH] WARNING: All {MAX_RETRIES} attempts failed for {url}")
        return resp, session

    return resp, session


# ---------------------------------------------------------------------------
# Checkpoint Management
# ---------------------------------------------------------------------------

def load_checkpoint() -> dict:
    """Load extraction progress from checkpoint file."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_checkpoint(progress: dict):
    """Save extraction progress to checkpoint file."""
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2)


def is_year_done(progress: dict, endpoint_name: str, year_key: str) -> bool:
    """Check if a specific endpoint+year combo is already extracted or permanently failed."""
    ep_progress = progress.get(endpoint_name, {})
    year_data = ep_progress.get(year_key, {})
    return year_data.get("status") in ("done", "error")


def mark_year_done(progress: dict, endpoint_name: str, year_key: str,
                   rows: int, filepath: str):
    """Mark an endpoint+year as complete in checkpoint."""
    if endpoint_name not in progress:
        progress[endpoint_name] = {}
    progress[endpoint_name][year_key] = {
        "status": "done",
        "rows": rows,
        "file": filepath,
        "timestamp": datetime.now().isoformat(),
    }
    save_checkpoint(progress)


def mark_year_error(progress: dict, endpoint_name: str, year_key: str, error: str):
    """Mark an endpoint+year as errored in checkpoint."""
    if endpoint_name not in progress:
        progress[endpoint_name] = {}
    progress[endpoint_name][year_key] = {
        "status": "error",
        "error": error,
        "timestamp": datetime.now().isoformat(),
    }
    save_checkpoint(progress)


# ---------------------------------------------------------------------------
# Date Range Helpers
# ---------------------------------------------------------------------------

def get_date_ranges(year: int) -> list[tuple[str, str]]:
    """Return (start_date, end_date) for a full year in MM/DD/YY format."""
    if year == END_YEAR:
        return [(f"01/01/{year % 100:02d}", CURRENT_DATE)]
    return [(f"01/01/{year % 100:02d}", f"12/31/{year % 100:02d}")]


def get_quarterly_ranges(year: int) -> list[tuple[str, str, str]]:
    """Return quarterly (label, start_date, end_date) for retry splits."""
    yy = f"{year % 100:02d}"
    if year == END_YEAR:
        return [("Q1", f"01/01/{yy}", CURRENT_DATE)]
    return [
        ("Q1", f"01/01/{yy}", f"03/31/{yy}"),
        ("Q2", f"04/01/{yy}", f"06/30/{yy}"),
        ("Q3", f"07/01/{yy}", f"09/30/{yy}"),
        ("Q4", f"10/01/{yy}", f"12/31/{yy}"),
    ]


# ---------------------------------------------------------------------------
# Core Export Functions
# ---------------------------------------------------------------------------

def trigger_export(session, endpoint_cfg: dict, start_date: str, end_date: str,
                   wip_type: str | None = None):
    """Trigger a CSV export via the 2-step MVI pattern.

    Step 1: POST form params to the process endpoint (initializes server state)
    Step 2: GET the .RUN endpoint with same params (triggers background generation)

    Returns (resp, session) tuple.
    """
    process = endpoint_cfg["process"]
    run_suffix = endpoint_cfg["run_suffix"]

    params = dict(endpoint_cfg["form_params"])
    params["START_DATE"] = start_date
    params["END_DATE"] = end_date

    if wip_type:
        params["WIP_TYPE"] = wip_type

    print(f"    [TRIGGER] {process} {start_date}-{end_date}" +
          (f" WIP_TYPE={wip_type}" if wip_type else ""))

    # Step 1: POST to process endpoint (initializes server-side state / MVI_KEY)
    post_url = f"{MVI_BASE}/{process}"
    resp, session = safe_request(session, "POST", post_url, data=params)
    time.sleep(RATE_LIMIT_SECONDS)

    # Step 2: GET the .RUN endpoint to trigger background generation
    # Use requests params= for proper URL encoding of date slashes
    run_url = f"{MVI_BASE}/{process}{run_suffix}"
    resp, session = safe_request(session, "GET", run_url, params=params)
    return resp, session


def poll_view_log(session, logkey: str) -> tuple[bool, requests.Session]:
    """Poll VIEW.LOG until 'ENDED' appears or timeout.

    Returns (success, session).
    """
    url = f"{MVI_BASE}/VIEW.LOG?LOGKEY={logkey}&FIRSTRUN=N"
    start_time = time.time()
    attempts = 0

    while (time.time() - start_time) < POLL_TIMEOUT_SECONDS:
        time.sleep(POLL_INTERVAL_SECONDS)
        attempts += 1
        resp, session = safe_request(session, "GET", url)

        text_upper = resp.text.upper()
        if "ENDED" in text_upper:
            elapsed = time.time() - start_time
            if "ERROR" in text_upper or "FAILED" in text_upper or "ABORTED" in text_upper:
                print(f"    [POLL] Process ended with ERRORS in {elapsed:.0f}s")
                return False, session
            print(f"    [POLL] Completed in {elapsed:.0f}s ({attempts} polls)")
            return True, session

        if attempts % 10 == 0:
            elapsed = time.time() - start_time
            print(f"    [POLL] Still waiting... {elapsed:.0f}s")

    elapsed = time.time() - start_time
    print(f"    [POLL] TIMEOUT after {elapsed:.0f}s ({attempts} polls)")
    return False, session


def download_csv(session, remote_filename: str, local_path: Path) -> tuple[int, requests.Session]:
    """Download a CSV from /attachments/ and save locally.

    Returns (row_count, session).
    """
    url = f"{ERP_BASE}/attachments/{remote_filename}"
    resp, session = safe_request(session, "GET", url)

    if resp.status_code != 200:
        print(f"    [DOWNLOAD] HTTP {resp.status_code} for {remote_filename}")
        return -1, session

    content = resp.text
    if not content.strip():
        print(f"    [DOWNLOAD] Empty response for {remote_filename}")
        return 0, session

    local_path.write_text(content, encoding="utf-8")
    row_count = content.count("\n") - 1  # Subtract header row
    if row_count < 0:
        row_count = 0
    size_kb = local_path.stat().st_size / 1024
    print(f"    [DOWNLOAD] Saved {local_path.name}: {row_count} rows, {size_kb:.1f}KB")
    return row_count, session


def extract_one_period(session, endpoint_cfg: dict, start_date: str, end_date: str,
                       local_path: Path, wip_type: str | None = None) -> tuple[int, requests.Session]:
    """Run full trigger -> poll -> download cycle for one date range.

    Returns (row_count, session). Returns -1 on failure.
    """
    # Step 1: Trigger the export
    resp, session = trigger_export(session, endpoint_cfg, start_date, end_date, wip_type)
    time.sleep(RATE_LIMIT_SECONDS)

    # Step 2: Poll VIEW.LOG
    success, session = poll_view_log(session, endpoint_cfg["logkey"])
    if not success:
        return -1, session

    # Step 3: Download the CSV
    row_count, session = download_csv(session, endpoint_cfg["csv_filename"], local_path)
    time.sleep(RATE_LIMIT_SECONDS)

    return row_count, session


def extract_one_year(session, endpoint_cfg: dict, year: int, progress: dict,
                     wip_type: str | None = None) -> requests.Session:
    """Extract data for one endpoint + one year, with quarterly retry fallback.

    Handles checkpoint check, full-year attempt, quarterly retry, and progress update.
    """
    name = endpoint_cfg["name"]
    year_key = f"{year}" if not wip_type else f"{year}_{wip_type}"
    suffix = f"_{wip_type}" if wip_type else ""

    # Check checkpoint
    if is_year_done(progress, name, year_key):
        return session

    # Check if file already exists
    local_path = OUTPUT_DIR / f"{name}{suffix}_{year}.csv"
    if local_path.exists() and local_path.stat().st_size > 100:
        row_count = local_path.read_text(encoding="utf-8").count("\n") - 1
        if row_count > 0:
            print(f"  [{name}] {year_key}: File exists ({row_count} rows), marking done")
            mark_year_done(progress, name, year_key, row_count, str(local_path))
            return session

    # Full-year attempt
    date_ranges = get_date_ranges(year)
    start_date, end_date = date_ranges[0]

    print(f"\n  [{name}] Year {year_key}: {start_date} - {end_date}")
    row_count, session = extract_one_period(
        session, endpoint_cfg, start_date, end_date, local_path, wip_type
    )

    if row_count >= 0:
        mark_year_done(progress, name, year_key, row_count, str(local_path))
        return session

    # Full year timed out - try quarterly
    print(f"  [{name}] {year_key}: Full year timed out, splitting into quarters...")
    quarters = get_quarterly_ranges(year)
    quarter_files = []
    total_rows = 0
    all_quarters_ok = True

    for q_label, q_start, q_end in quarters:
        q_path = OUTPUT_DIR / f"{name}{suffix}_{year}_{q_label}.csv"

        # Skip quarters already downloaded (resume support)
        if q_path.exists() and q_path.stat().st_size > 100:
            q_rows = max(0, q_path.read_text(encoding="utf-8").count("\n") - 1)
            print(f"  [{name}] {year_key} {q_label}: Quarter file exists ({q_rows} rows), skipping")
            quarter_files.append(q_path)
            total_rows += q_rows
            continue

        print(f"  [{name}] {year_key} {q_label}: {q_start} - {q_end}")

        q_rows, session = extract_one_period(
            session, endpoint_cfg, q_start, q_end, q_path, wip_type
        )

        if q_rows < 0:
            print(f"  [{name}] {year_key} {q_label}: FAILED (timeout)")
            all_quarters_ok = False
            mark_year_error(progress, name, year_key, f"Quarterly {q_label} timeout")
            break

        quarter_files.append(q_path)
        total_rows += q_rows

    if all_quarters_ok and quarter_files:
        # Merge quarter CSVs into the year file
        merge_csv_files(quarter_files, local_path)
        mark_year_done(progress, name, year_key, total_rows, str(local_path))
        # Clean up quarter files
        for qf in quarter_files:
            qf.unlink(missing_ok=True)

    return session


# ---------------------------------------------------------------------------
# Reference Table Scraper
# ---------------------------------------------------------------------------

def scrape_reference_table(session, endpoint: str) -> tuple[list[list[str]], requests.Session]:
    """Scrape a reference code listing table from MVI.

    APPLOAD -> parse frameset -> fetch APP frame -> parse HTML table.
    Returns (rows_including_header, session).
    """
    # Step 1: APPLOAD to get the frameset
    appload_url = f"{MVI_BASE}/APPLOAD?APP={endpoint}"
    resp, session = safe_request(session, "GET", appload_url)

    if resp.status_code != 200:
        print(f"    [REF] APPLOAD failed for {endpoint}: HTTP {resp.status_code}")
        return [], session

    html = resp.text

    # Step 2: Extract APP frame URL from frameset
    # Look for frame src pointing to the actual content
    frame_match = re.search(
        r'<frame[^>]+src=["\']([^"\']*)["\'][^>]*name=["\']APP["\']',
        html, re.IGNORECASE
    )
    if not frame_match:
        # Try reverse order: name before src
        frame_match = re.search(
            r'<frame[^>]+name=["\']APP["\'][^>]*src=["\']([^"\']*)["\']',
            html, re.IGNORECASE
        )
    if not frame_match:
        # Maybe the content is directly in the response (no frameset)
        app_html = html
    else:
        frame_url = frame_match.group(1)
        if not frame_url.startswith("http"):
            if frame_url.startswith("/"):
                frame_url = f"{ERP_BASE}{frame_url}"
            else:
                frame_url = f"{MVI_BASE}/{frame_url}"

        resp, session = safe_request(session, "GET", frame_url)
        app_html = resp.text

    time.sleep(1)

    # Step 3: Parse HTML table
    rows = parse_html_table(app_html)
    return rows, session


def parse_html_table(html: str) -> list[list[str]]:
    """Parse the first HTML table into a list of rows (list of cell values)."""
    rows = []

    # Find <table> blocks
    table_match = re.search(r"<table[^>]*>(.*?)</table>", html, re.DOTALL | re.IGNORECASE)
    if not table_match:
        return rows

    table_html = table_match.group(1)

    # Extract rows
    row_matches = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, re.DOTALL | re.IGNORECASE)
    for row_html in row_matches:
        cells = re.findall(
            r"<t[hd][^>]*>(.*?)</t[hd]>", row_html, re.DOTALL | re.IGNORECASE
        )
        # Strip HTML tags and whitespace from each cell
        clean_cells = []
        for cell in cells:
            text = re.sub(r"<[^>]+>", "", cell)
            text = text.strip()
            # Collapse whitespace
            text = re.sub(r"\s+", " ", text)
            clean_cells.append(text)
        if clean_cells:
            rows.append(clean_cells)

    return rows


def extract_all_reference_tables(session) -> requests.Session:
    """Scrape all 33 reference code listing tables."""
    print(f"\n{'='*60}")
    print(f"[REFS] Extracting {len(REFERENCE_TABLES)} reference tables")
    print(f"{'='*60}")

    total_rows = 0
    success = 0
    errors = 0

    for i, endpoint in enumerate(REFERENCE_TABLES, 1):
        safe_name = endpoint.replace(".", "_")
        local_path = OUTPUT_DIR / f"ref_{safe_name}.csv"

        # Skip if already exists
        if local_path.exists() and local_path.stat().st_size > 50:
            existing_rows = local_path.read_text(encoding="utf-8").count("\n")
            print(f"  [{i}/{len(REFERENCE_TABLES)}] {endpoint}: exists ({existing_rows} rows), skipping")
            success += 1
            total_rows += existing_rows
            continue

        print(f"  [{i}/{len(REFERENCE_TABLES)}] {endpoint}...")
        rows, session = scrape_reference_table(session, endpoint)

        if not rows:
            print(f"    No data found for {endpoint}")
            errors += 1
            continue

        # Write CSV
        with open(local_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)

        data_rows = len(rows) - 1 if len(rows) > 1 else len(rows)
        size_kb = local_path.stat().st_size / 1024
        print(f"    Saved ref_{safe_name}.csv: {data_rows} data rows, {size_kb:.1f}KB")
        success += 1
        total_rows += data_rows

        time.sleep(RATE_LIMIT_SECONDS)

    print(f"\n[REFS] Done: {success} tables, {errors} errors, {total_rows} total rows")
    return session


# ---------------------------------------------------------------------------
# Merge Yearly CSVs
# ---------------------------------------------------------------------------

def merge_csv_files(source_files: list[Path], dest_path: Path):
    """Merge multiple CSV files into one, keeping only the first header."""
    first = True
    with open(dest_path, "w", newline="", encoding="utf-8") as out:
        for src in source_files:
            if not src.exists():
                continue
            with open(src, encoding="utf-8") as f:
                for line_num, line in enumerate(f):
                    if line_num == 0 and not first:
                        continue  # Skip header on subsequent files
                    out.write(line)
            first = False


def merge_all_endpoints():
    """Merge yearly CSVs into _ALL.csv for each endpoint."""
    print(f"\n{'='*60}")
    print("[MERGE] Combining yearly CSVs into _ALL files")
    print(f"{'='*60}")

    for ep in EXPORT_ENDPOINTS:
        name = ep["name"]
        wip_types = ep.get("wip_types")

        if wip_types:
            for wt in wip_types:
                suffix = f"_{wt}"
                _merge_endpoint_files(name, suffix)
        else:
            _merge_endpoint_files(name, "")


def _merge_endpoint_files(name: str, suffix: str):
    """Merge all yearly files for one endpoint+suffix combo."""
    pattern = f"{name}{suffix}_*.csv"
    year_files = sorted(
        [f for f in OUTPUT_DIR.glob(pattern)
         if re.match(rf".*_\d{{4}}\.csv$", f.name)],
        key=lambda p: p.name,
    )

    if not year_files:
        print(f"  [{name}{suffix}] No yearly files found")
        return

    all_path = OUTPUT_DIR / f"{name}{suffix}_ALL.csv"
    merge_csv_files(year_files, all_path)

    # Count total rows
    total_rows = 0
    with open(all_path, encoding="utf-8") as f:
        total_rows = sum(1 for _ in f) - 1  # Subtract header

    size_mb = all_path.stat().st_size / (1024 * 1024)
    print(f"  [{name}{suffix}] Merged {len(year_files)} files -> {all_path.name}: "
          f"{total_rows} rows, {size_mb:.2f}MB")

    # Report gaps
    expected_years = set(range(START_YEAR, END_YEAR + 1))
    found_years = set()
    for f in year_files:
        m = re.search(r"_(\d{4})\.csv$", f.name)
        if m:
            found_years.add(int(m.group(1)))
    missing = expected_years - found_years
    if missing:
        print(f"    GAPS: Missing years {sorted(missing)}")


# ---------------------------------------------------------------------------
# Summary Report
# ---------------------------------------------------------------------------

def print_summary():
    """Print extraction summary from checkpoint data."""
    progress = load_checkpoint()

    print(f"\n{'='*60}")
    print("EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"{'Endpoint':<35} {'Years':>6} {'Rows':>10} {'Errors':>7}")
    print("-" * 60)

    for ep in EXPORT_ENDPOINTS:
        name = ep["name"]
        ep_data = progress.get(name, {})
        done_count = sum(1 for v in ep_data.values() if v.get("status") == "done")
        total_rows = sum(v.get("rows", 0) for v in ep_data.values() if v.get("status") == "done")
        error_count = sum(1 for v in ep_data.values() if v.get("status") == "error")
        print(f"  {name:<33} {done_count:>6} {total_rows:>10} {error_count:>7}")

    # Reference tables
    ref_count = len(list(OUTPUT_DIR.glob("ref_*.csv")))
    ref_rows = 0
    for f in OUTPUT_DIR.glob("ref_*.csv"):
        ref_rows += f.read_text(encoding="utf-8").count("\n")
    print(f"\n  {'Reference Tables':<33} {ref_count:>6} {ref_rows:>10}")

    # ALL files
    print(f"\n  Merged _ALL files:")
    for f in sorted(OUTPUT_DIR.glob("*_ALL.csv")):
        rows = f.read_text(encoding="utf-8").count("\n") - 1
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"    {f.name}: {rows} rows, {size_mb:.2f}MB")


# ---------------------------------------------------------------------------
# Main Download Loop
# ---------------------------------------------------------------------------

def download_all_exports(session, filter_endpoint: str | None = None,
                         filter_year: int | None = None) -> requests.Session:
    """Download all CSV exports for all endpoints and years."""
    progress = load_checkpoint()

    endpoints = EXPORT_ENDPOINTS
    if filter_endpoint:
        endpoints = [ep for ep in endpoints if ep["name"] == filter_endpoint]
        if not endpoints:
            print(f"ERROR: Unknown endpoint '{filter_endpoint}'")
            print(f"Available: {', '.join(ep['name'] for ep in EXPORT_ENDPOINTS)}")
            sys.exit(1)

    years = list(range(START_YEAR, END_YEAR + 1))
    if filter_year:
        years = [filter_year]

    total_jobs = 0
    for ep in endpoints:
        wip_types = ep.get("wip_types")
        if wip_types:
            total_jobs += len(years) * len(wip_types)
        else:
            total_jobs += len(years)

    print(f"\n{'='*60}")
    print(f"[DOWNLOAD] {len(endpoints)} endpoints x {len(years)} years = {total_jobs} jobs")
    print(f"[DOWNLOAD] Output: {OUTPUT_DIR}")
    print(f"{'='*60}")

    completed = 0
    skipped = 0
    failed = 0
    for ep in endpoints:
        wip_types = ep.get("wip_types")
        job_list = []
        if wip_types:
            for wt in wip_types:
                for year in years:
                    job_list.append((year, wt))
        else:
            for year in years:
                job_list.append((year, None))

        for year, wt in job_list:
            name = ep["name"]
            year_key = f"{year}" if not wt else f"{year}_{wt}"
            try:
                session = extract_one_year(session, ep, year, progress, wip_type=wt)
            except Exception as e:
                failed += 1
                error_msg = f"{type(e).__name__}: {e}"
                print(f"\n  [FAILED] {name} {year_key}: {error_msg}")
                print(f"  [FAILED] Logging failure and continuing to next job...\n")
                mark_year_error(progress, name, year_key, error_msg)
                # Re-auth for next job
                try:
                    session = create_session()
                except Exception:
                    print("  [AUTH] Re-auth failed, will retry on next job")
            completed += 1
            if completed % 10 == 0:
                print(f"\n  --- Progress: {completed}/{total_jobs} jobs "
                      f"({failed} failed) ---\n")

    print(f"\n[DOWNLOAD] Complete: {completed}/{total_jobs} jobs, "
          f"{failed} failed")
    return session


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def main():
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    if not USERNAME or not PASSWORD:
        print(f"ERROR: Set KEYEDIN_USERNAME and KEYEDIN_PASSWORD in {ENV_FILE}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Parse CLI args
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    filter_endpoint = None
    filter_year = None
    resume_mode = False

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--endpoint" and i + 1 < len(args):
            filter_endpoint = args[i + 1]
            i += 2
        elif args[i] == "--year" and i + 1 < len(args):
            filter_year = int(args[i + 1])
            i += 2
        elif args[i] == "--resume":
            resume_mode = True
            i += 1
        else:
            i += 1

    print(f"KeyedIn MVI CSV Export Extractor")
    print(f"Mode: {mode}")
    if resume_mode:
        print(f"Resume: ON (skipping completed + errored jobs)")
    if filter_endpoint:
        print(f"Endpoint filter: {filter_endpoint}")
    if filter_year:
        print(f"Year filter: {filter_year}")
    print(f"Output: {OUTPUT_DIR}")
    print()

    # In resume mode, scan existing files to rebuild checkpoint for any
    # files that exist on disk but aren't in the checkpoint yet.
    if resume_mode:
        progress = load_checkpoint()
        existing_count = 0
        for csv_file in OUTPUT_DIR.glob("*.csv"):
            if csv_file.name.startswith("ref_") or "_ALL" in csv_file.name:
                continue
            # Parse endpoint name, optional suffix, and year from filename
            m = re.match(r"^(.+?)(?:_([A-Z]))_(\d{4})\.csv$", csv_file.name)
            if not m:
                m2 = re.match(r"^(.+?)_(\d{4})\.csv$", csv_file.name)
                if m2:
                    ep_name, yr = m2.group(1), m2.group(2)
                    year_key = yr
                else:
                    continue
            else:
                ep_name = m.group(1)
                year_key = f"{m.group(3)}_{m.group(2)}"

            if not is_year_done(progress, ep_name, year_key):
                row_count = csv_file.read_text(encoding="utf-8").count("\n") - 1
                if row_count > 0:
                    mark_year_done(progress, ep_name, year_key, row_count, str(csv_file))
                    existing_count += 1

        if existing_count > 0:
            print(f"[RESUME] Recovered {existing_count} completed jobs from existing files")
        # Count remaining work
        total_possible = 0
        already_done = 0
        for ep in EXPORT_ENDPOINTS:
            wip_types = ep.get("wip_types")
            years_list = list(range(START_YEAR, END_YEAR + 1))
            if wip_types:
                for wt in wip_types:
                    for yr in years_list:
                        total_possible += 1
                        yk = f"{yr}_{wt}"
                        ep_data = progress.get(ep["name"], {}).get(yk, {})
                        if ep_data.get("status") in ("done", "error"):
                            already_done += 1
            else:
                for yr in years_list:
                    total_possible += 1
                    yk = str(yr)
                    ep_data = progress.get(ep["name"], {}).get(yk, {})
                    if ep_data.get("status") in ("done", "error"):
                        already_done += 1
        print(f"[RESUME] {already_done}/{total_possible} jobs already done/errored, "
              f"{total_possible - already_done} remaining\n")

    session = None

    if mode in ("all", "download"):
        session = create_session()
        session = download_all_exports(session, filter_endpoint, filter_year)

    if mode in ("all", "refs"):
        if session is None:
            session = create_session()
        session = extract_all_reference_tables(session)

    if mode in ("all", "merge"):
        merge_all_endpoints()

    if mode == "summary":
        print_summary()
        return

    print_summary()


if __name__ == "__main__":
    main()
