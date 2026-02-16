"""Quick test: extract 5 pages (125 rows) to verify pipeline."""

import csv
import json
import logging
import re
import sys
import time
from pathlib import Path

import requests
import urllib3

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gwt_parser import (
    discover_field_names,
    extract_rows,
    extract_total_count,
    extract_view_token,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s")
log = logging.getLogger(__name__)

INFORMER_BASE = "https://eaglesign.keyedinsign.com:8443"
INFORMER_PATH = "/eaglesign/informer"
MODULE_BASE = f"{INFORMER_BASE}{INFORMER_PATH}/"
GWT_PERMUTATION = "6823F3E0DFFF554BC1A7951AA98B182D"

SESSION_FILE = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\informer_session.json")
CMD_REQUEST = Path(r"C:\Scripts\keyedin-capture\reports\report_quote_status_report_cmd_request.txt")
PAGINATION_TEMPLATE = Path(r"C:\Scripts\keyedin-capture\reports\reqid655_request.txt")

CAPTURED_AUTH_TOKEN = "6728f894-940d-4611-85e7-a40d225d58eb"
CAPTURED_CLIENT_ID = "cf4f5ce2-8fb2-456e-b23f-3755434cfdf0"
OFFSET_POSITION = 2968

REPORT_FIELDS = [
    "quoteno", "salesperson", "qtDate", "defaultShip", "expDate",
    "acctid", "company", "specInst", "extPrice", "salesStage2",
    "statusCode&Description", "currStatusDate2", "statusTime_2", "wono",
    "inactiveMsg", "currStatus", "quoteStatusCodes_assoc_descr",
    "salesStage", "quoteSalesStage_assoc_descr", "qtyOrdered",
    "salesTotal", "sellingPrice", "classifyAsLoss", "inactive",
    "inactive2", "specInst2", "currStatusDate", "descr",
]


def main():
    data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    s = requests.Session()
    s.verify = False
    s.cookies.set("JSESSIONID", data["jsessionid"])
    auth_token, client_id = data["auth_token"], data["client_id"]

    headers = {
        "Content-Type": "text/x-gwt-rpc; charset=UTF-8",
        "X-GWT-Permutation": GWT_PERMUTATION,
        "X-GWT-Module-Base": MODULE_BASE,
    }

    # Step 1: RunReportCommand for ViewToken
    cmd_payload = CMD_REQUEST.read_text(encoding="utf-8").strip()
    cmd_payload = cmd_payload.replace(CAPTURED_AUTH_TOKEN, auth_token)
    cmd_payload = cmd_payload.replace(CAPTURED_CLIENT_ID, client_id)

    url = f"{INFORMER_BASE}{INFORMER_PATH}/commandService?authToken={auth_token}&clientId={client_id}"
    resp = s.post(url, data=cmd_payload.encode("utf-8"), headers=headers, timeout=120)
    assert resp.text.startswith("//OK"), f"RunReportCommand failed: {resp.text[:200]}"

    view_token = extract_view_token(resp.text)
    total = extract_total_count(resp.text)
    log.info("ViewToken: %s, Total: %d", view_token, total)

    # Step 2: Template pagination for pages 1-5
    template_parts = PAGINATION_TEMPLATE.read_text(encoding="utf-8").strip().split("|")
    view_url = f"{INFORMER_BASE}{INFORMER_PATH}/rpc/protected/ViewRPCService?authToken={auth_token}&clientId={client_id}"

    all_rows = []
    field_names = REPORT_FIELDS

    for page in range(1, 6):
        offset = (page - 1) * 25
        parts = template_parts.copy()
        parts[9] = view_token
        parts[OFFSET_POSITION] = str(offset)
        payload = "|".join(parts)

        resp = s.post(view_url, data=payload.encode("utf-8"), headers=headers, timeout=120)
        assert resp.text.startswith("//OK"), f"Page {page} failed: {resp.text[:200]}"

        if page == 1:
            discovered = discover_field_names(resp.text)
            clean = [f for f in discovered if not re.match(r"^\d+$", f) and "/" not in f and "." not in f]
            log.info("Discovered %d clean fields: %s", len(clean), clean)

        rows = extract_rows(resp.text, field_names)
        all_rows.extend(rows)
        log.info("Page %d (offset=%d): %d rows, total=%d", page, offset, len(rows), len(all_rows))

    # Show sample data
    log.info("\n=== SAMPLE DATA (first 3 rows) ===")
    for i, row in enumerate(all_rows[:3]):
        non_none = {k: v for k, v in row.items() if v is not None}
        log.info("Row %d (%d fields): %s", i, len(non_none), dict(list(non_none.items())[:6]))

    # Write test CSV
    test_csv = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\quote_status_test.csv")
    with test_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=field_names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)
    log.info("Test CSV: %s (%d rows)", test_csv, len(all_rows))


if __name__ == "__main__":
    main()
