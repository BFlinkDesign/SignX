"""Quick test: verify template-based pagination works for pages 1-3."""

import json
import re
import sys
from pathlib import Path

import requests
import urllib3

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gwt_parser import extract_rows, extract_total_count, extract_view_token

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

INFORMER_BASE = "https://eaglesign.keyedinsign.com:8443"
INFORMER_PATH = "/eaglesign/informer"
MODULE_BASE = f"{INFORMER_BASE}{INFORMER_PATH}/"
GWT_PERMUTATION = "6823F3E0DFFF554BC1A7951AA98B182D"

SESSION_FILE = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\informer_session.json")
CMD_REQUEST = Path(
    r"C:\Scripts\keyedin-capture\reports\report_quote_status_report_cmd_request.txt"
)
PAGINATION_TEMPLATE = Path(r"C:\Scripts\keyedin-capture\reports\reqid655_request.txt")

CAPTURED_AUTH_TOKEN = "6728f894-940d-4611-85e7-a40d225d58eb"
CAPTURED_CLIENT_ID = "cf4f5ce2-8fb2-456e-b23f-3755434cfdf0"
TEMPLATE_VIEW_TOKEN = "80ab7e6b-92d4-4650-a4f4-40f4b7d25c8a"
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
    jsessionid = data["jsessionid"]
    auth_token = data["auth_token"]
    client_id = data["client_id"]
    print(f"Session: auth_token={auth_token[:16]}...")

    s = requests.Session()
    s.verify = False
    s.cookies.set("JSESSIONID", jsessionid)

    headers = {
        "Content-Type": "text/x-gwt-rpc; charset=UTF-8",
        "X-GWT-Permutation": GWT_PERMUTATION,
        "X-GWT-Module-Base": MODULE_BASE,
    }

    # Step 1: RunReportCommand
    print("\n" + "=" * 60)
    print("STEP 1: RunReportCommand")
    print("=" * 60)

    cmd_payload = CMD_REQUEST.read_text(encoding="utf-8").strip()
    cmd_payload = cmd_payload.replace(CAPTURED_AUTH_TOKEN, auth_token)
    cmd_payload = cmd_payload.replace(CAPTURED_CLIENT_ID, client_id)

    url = f"{INFORMER_BASE}{INFORMER_PATH}/commandService?authToken={auth_token}&clientId={client_id}"
    resp = s.post(url, data=cmd_payload.encode("utf-8"), headers=headers, timeout=120)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")

    if not resp.text.startswith("//OK"):
        print(f"  ERROR: {resp.text[:300]}")
        sys.exit(1)

    view_token = extract_view_token(resp.text)
    total = extract_total_count(resp.text)
    print(f"  ViewToken: {view_token}")
    print(f"  Total: {total}")

    rows1 = extract_rows(resp.text, REPORT_FIELDS)
    print(f"  Page 1 rows: {len(rows1)}")
    if rows1:
        print(f"  First row: quoteno={rows1[0].get('quoteno')}, company={rows1[0].get('company')}")
        print(f"  Last row:  quoteno={rows1[-1].get('quoteno')}, company={rows1[-1].get('company')}")

    # Step 2: Template-based pagination for pages 2-3
    template_raw = PAGINATION_TEMPLATE.read_text(encoding="utf-8").strip()
    template_parts = template_raw.split("|")
    print(f"\n  Template: {len(template_parts)} parts")
    print(f"  Template ViewToken: {template_parts[9][:16]}...")
    print(f"  Template offset: {template_parts[OFFSET_POSITION]}")

    view_url = f"{INFORMER_BASE}{INFORMER_PATH}/rpc/protected/ViewRPCService?authToken={auth_token}&clientId={client_id}"

    for page in [2, 3, 4]:
        offset = (page - 1) * 25
        parts = template_parts.copy()
        parts[9] = view_token
        parts[OFFSET_POSITION] = str(offset)
        payload = "|".join(parts)

        print(f"\n{'=' * 60}")
        print(f"PAGE {page} (offset={offset})")
        print(f"{'=' * 60}")

        resp = s.post(view_url, data=payload.encode("utf-8"), headers=headers, timeout=120)
        print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")

        if resp.text.startswith("//OK"):
            rows = extract_rows(resp.text, REPORT_FIELDS)
            print(f"  Rows: {len(rows)}")
            if rows:
                print(f"  First: quoteno={rows[0].get('quoteno')}, company={rows[0].get('company')}")
                print(f"  Last:  quoteno={rows[-1].get('quoteno')}, company={rows[-1].get('company')}")
        elif resp.text.startswith("//EX"):
            err_match = re.search(r'"([^"]+)"', resp.text)
            err = err_match.group(1) if err_match else resp.text[:200]
            print(f"  ERROR: {err}")
        else:
            print(f"  Response: {resp.text[:300]}")

    print(f"\n{'=' * 60}")
    print("TEST COMPLETE")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
