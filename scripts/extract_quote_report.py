"""Extract full Quote Status Report (18,854 rows) from KeyedIn Informer.

Uses template-based pagination discovered via browser capture:
- RunReportCommand returns page 1 data + ViewToken
- Subsequent pages use a getData template (reqid655) with offset changes
- Only the ViewToken UUID (pos 9) and offset (pos 2968) need replacement
"""

import csv
import json
import logging
import re
import sys
import time
from pathlib import Path

import requests
import urllib3

# Sibling module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gwt_parser import (
    discover_field_names,
    extract_rows,
    extract_total_count,
    extract_view_token,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INFORMER_BASE = "https://eaglesign.keyedinsign.com:8443"
INFORMER_PATH = "/eaglesign/informer"
MODULE_BASE = f"{INFORMER_BASE}{INFORMER_PATH}/"
GWT_PERMUTATION = "6823F3E0DFFF554BC1A7951AA98B182D"

SESSION_FILE = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\informer_session.json")
CMD_REQUEST = Path(
    r"C:\Scripts\keyedin-capture\reports\report_quote_status_report_cmd_request.txt"
)
PAGINATION_TEMPLATE = Path(
    r"C:\Scripts\keyedin-capture\reports\reqid655_request.txt"
)
OUTPUT_CSV = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\quote_status_report.csv")

# Auth tokens in the original cmd_request template
CAPTURED_AUTH_TOKEN = "6728f894-940d-4611-85e7-a40d225d58eb"
CAPTURED_CLIENT_ID = "cf4f5ce2-8fb2-456e-b23f-3755434cfdf0"

# ViewToken UUID in the pagination template (from reqid655)
TEMPLATE_VIEW_TOKEN = "80ab7e6b-92d4-4650-a4f4-40f4b7d25c8a"

# Offset position in the pipe-delimited pagination template (0-indexed)
OFFSET_POSITION = 2968

PAGE_SIZE = 25

REPORT_FIELDS = [
    "quoteno",
    "salesperson",
    "qtDate",
    "defaultShip",
    "expDate",
    "acctid",
    "company",
    "specInst",
    "extPrice",
    "salesStage2",
    "statusCode&Description",
    "currStatusDate2",
    "statusTime_2",
    "wono",
    "inactiveMsg",
    "currStatus",
    "quoteStatusCodes_assoc_descr",
    "salesStage",
    "quoteSalesStage_assoc_descr",
    "qtyOrdered",
    "salesTotal",
    "sellingPrice",
    "classifyAsLoss",
    "inactive",
    "inactive2",
    "specInst2",
    "currStatusDate",
    "descr",
]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def make_session(jsessionid: str) -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.cookies.set("JSESSIONID", jsessionid)
    return s


def send_command(session, payload, auth_token, client_id):
    url = f"{INFORMER_BASE}{INFORMER_PATH}/commandService"
    url += f"?authToken={auth_token}&clientId={client_id}"
    headers = {
        "Content-Type": "text/x-gwt-rpc; charset=UTF-8",
        "X-GWT-Permutation": GWT_PERMUTATION,
        "X-GWT-Module-Base": MODULE_BASE,
    }
    return session.post(url, data=payload.encode("utf-8"), headers=headers, timeout=120)


def send_view_rpc(session, payload, auth_token, client_id):
    url = f"{INFORMER_BASE}{INFORMER_PATH}/rpc/protected/ViewRPCService"
    url += f"?authToken={auth_token}&clientId={client_id}"
    headers = {
        "Content-Type": "text/x-gwt-rpc; charset=UTF-8",
        "X-GWT-Permutation": GWT_PERMUTATION,
        "X-GWT-Module-Base": MODULE_BASE,
    }
    return session.post(url, data=payload.encode("utf-8"), headers=headers, timeout=120)


# ---------------------------------------------------------------------------
# Pagination template
# ---------------------------------------------------------------------------


def build_page_payload(template_parts: list[str], view_token: str, offset: int) -> str:
    """Build a pagination payload from the template by replacing ViewToken and offset."""
    parts = template_parts.copy()
    # Position 9 in pipe-delimited = string index 7 in GWT string table = ViewToken UUID
    parts[9] = view_token
    # Position 2968 = offset value
    parts[OFFSET_POSITION] = str(offset)
    return "|".join(parts)


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------


def main():
    # Load session
    data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    jsessionid = data["jsessionid"]
    auth_token = data["auth_token"]
    client_id = data["client_id"]
    log.info("Session loaded: auth_token=%s...", auth_token[:16])

    s = make_session(jsessionid)

    # Load pagination template
    template_raw = PAGINATION_TEMPLATE.read_text(encoding="utf-8").strip()
    template_parts = template_raw.split("|")
    log.info(
        "Pagination template loaded: %d parts, ViewToken=%s",
        len(template_parts),
        template_parts[9][:16] + "...",
    )

    # Step 1: Run the report command to get page 1 + ViewToken
    log.info("=" * 60)
    log.info("STEP 1: RunReportCommand (page 1)")
    log.info("=" * 60)

    cmd_payload = CMD_REQUEST.read_text(encoding="utf-8").strip()
    cmd_payload = cmd_payload.replace(CAPTURED_AUTH_TOKEN, auth_token)
    cmd_payload = cmd_payload.replace(CAPTURED_CLIENT_ID, client_id)

    resp = send_command(s, cmd_payload, auth_token, client_id)
    if not resp.text.startswith("//OK"):
        log.error("RunReportCommand failed: %s", resp.text[:300])
        sys.exit(1)

    view_token = extract_view_token(resp.text)
    total_count = extract_total_count(resp.text)
    log.info("ViewToken: %s", view_token)
    log.info("Total rows: %d", total_count)

    if not view_token:
        log.error("No ViewToken in RunReportCommand response")
        sys.exit(1)

    all_rows: list[dict] = []

    # Step 2: Use template-based getData for ALL pages (including page 1)
    # RunReportCommand response has different structure that misaligns field mapping,
    # so we use the getData template uniformly for consistent parsing.
    if total_count <= 0:
        total_count = 18854  # fallback
    total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
    log.info("=" * 60)
    log.info("STEP 2: Paginating %d pages (total %d rows)", total_pages, total_count)
    log.info("=" * 60)

    # Discover field names from page 1 getData response
    field_names: list[str] = []
    errors = 0
    for page in range(1, total_pages + 1):
        offset = (page - 1) * PAGE_SIZE
        payload = build_page_payload(template_parts, view_token, offset)

        try:
            resp = send_view_rpc(s, payload, auth_token, client_id)
        except requests.RequestException as e:
            log.error("Page %d: request failed: %s", page, e)
            errors += 1
            if errors > 5:
                log.error("Too many errors, stopping")
                break
            time.sleep(2)
            continue

        if not resp.text.startswith("//OK"):
            err_match = re.search(r'"([^"]+)"', resp.text)
            err = err_match.group(1) if err_match else resp.text[:200]
            log.error("Page %d (offset=%d): %s", page, offset, err)
            errors += 1
            if errors > 5:
                log.error("Too many consecutive errors, stopping")
                break
            time.sleep(1)
            continue

        # On page 1, discover fields and use REPORT_FIELDS as canonical order
        if page == 1 and not field_names:
            discovered = discover_field_names(resp.text)
            # Filter out GWT type artifacts (numeric strings, java types)
            discovered_clean = [
                f for f in discovered
                if not re.match(r"^\d+$", f) and "/" not in f and "." not in f
            ]
            # Use REPORT_FIELDS if they cover most discovered fields,
            # otherwise fall back to discovered
            covered = sum(1 for f in discovered_clean if f in REPORT_FIELDS)
            if covered >= len(discovered_clean) * 0.5:
                field_names = REPORT_FIELDS
                log.info("Using predefined REPORT_FIELDS (%d fields)", len(field_names))
            else:
                field_names = discovered_clean
                log.info("Using discovered fields (%d): %s", len(field_names), field_names)

        try:
            rows = extract_rows(resp.text, field_names)
        except Exception as e:
            log.error("Page %d: parse error: %s", page, e)
            errors += 1
            continue

        all_rows.extend(rows)
        errors = 0  # reset on success

        if page % 50 == 0 or page == total_pages or page == 1:
            log.info(
                "Progress: page %d/%d, %d rows collected (%.1f%%)",
                page,
                total_pages,
                len(all_rows),
                len(all_rows) / total_count * 100,
            )

        # Gentle throttle to avoid hammering the server
        if page % 10 == 0:
            time.sleep(0.5)

    # Step 3: Write CSV
    log.info("=" * 60)
    log.info("STEP 3: Writing CSV (%d rows)", len(all_rows))
    log.info("=" * 60)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    csv_fields = field_names if field_names else REPORT_FIELDS
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    log.info("CSV written to %s", OUTPUT_CSV)
    log.info("Total rows: %d / %d expected", len(all_rows), total_count)

    if len(all_rows) < total_count * 0.95:
        log.warning(
            "Only %.1f%% of rows extracted - check errors above",
            len(all_rows) / total_count * 100,
        )


if __name__ == "__main__":
    main()
