"""Debug: check what fields extract_rows actually returns."""

import json
import sys
from pathlib import Path

import requests
import urllib3

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gwt_parser import (
    discover_field_names,
    extract_rows,
    extract_total_count,
    extract_view_token,
    parse_gwt_response,
)

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

    s = requests.Session()
    s.verify = False
    s.cookies.set("JSESSIONID", jsessionid)

    headers = {
        "Content-Type": "text/x-gwt-rpc; charset=UTF-8",
        "X-GWT-Permutation": GWT_PERMUTATION,
        "X-GWT-Module-Base": MODULE_BASE,
    }

    # RunReportCommand for page 1
    cmd_payload = CMD_REQUEST.read_text(encoding="utf-8").strip()
    cmd_payload = cmd_payload.replace(CAPTURED_AUTH_TOKEN, auth_token)
    cmd_payload = cmd_payload.replace(CAPTURED_CLIENT_ID, client_id)

    url = f"{INFORMER_BASE}{INFORMER_PATH}/commandService?authToken={auth_token}&clientId={client_id}"
    resp = s.post(url, data=cmd_payload.encode("utf-8"), headers=headers, timeout=120)

    print("=== PAGE 1 (RunReportCommand) ===")
    print(f"Response length: {len(resp.text)}")

    # Discover field names
    discovered = discover_field_names(resp.text)
    print(f"Discovered fields ({len(discovered)}): {discovered}")

    # Try extracting with discovered fields
    rows_discovered = extract_rows(resp.text, discovered)
    print(f"Rows with discovered fields: {len(rows_discovered)}")
    if rows_discovered:
        r = rows_discovered[0]
        print(f"First row keys: {list(r.keys())[:10]}")
        print(f"First row values (first 5):")
        for k, v in list(r.items())[:5]:
            print(f"  {k}: {v!r}")

    # Try extracting with predefined fields
    rows_predefined = extract_rows(resp.text, REPORT_FIELDS)
    print(f"\nRows with REPORT_FIELDS: {len(rows_predefined)}")
    if rows_predefined:
        r = rows_predefined[0]
        non_none = {k: v for k, v in r.items() if v is not None}
        print(f"Non-None fields: {len(non_none)} / {len(r)}")
        for k, v in list(non_none.items())[:5]:
            print(f"  {k}: {v!r}")

    # Now test page 2
    template_raw = PAGINATION_TEMPLATE.read_text(encoding="utf-8").strip()
    template_parts = template_raw.split("|")
    view_token = extract_view_token(resp.text)

    parts = template_parts.copy()
    parts[9] = view_token
    parts[OFFSET_POSITION] = "25"
    payload = "|".join(parts)

    view_url = f"{INFORMER_BASE}{INFORMER_PATH}/rpc/protected/ViewRPCService?authToken={auth_token}&clientId={client_id}"
    resp2 = s.post(view_url, data=payload.encode("utf-8"), headers=headers, timeout=120)

    print(f"\n=== PAGE 2 (template pagination) ===")
    print(f"Response length: {len(resp2.text)}")

    discovered2 = discover_field_names(resp2.text)
    print(f"Discovered fields ({len(discovered2)}): {discovered2}")

    rows2_disc = extract_rows(resp2.text, discovered2)
    print(f"Rows with discovered fields: {len(rows2_disc)}")
    if rows2_disc:
        r = rows2_disc[0]
        print(f"First row keys: {list(r.keys())[:10]}")
        print(f"First row values (first 5):")
        for k, v in list(r.items())[:5]:
            print(f"  {k}: {v!r}")

    rows2_pre = extract_rows(resp2.text, REPORT_FIELDS)
    print(f"\nRows with REPORT_FIELDS: {len(rows2_pre)}")
    if rows2_pre:
        r = rows2_pre[0]
        non_none = {k: v for k, v in r.items() if v is not None}
        print(f"Non-None fields: {len(non_none)} / {len(r)}")
        for k, v in list(non_none.items())[:5]:
            print(f"  {k}: {v!r}")


if __name__ == "__main__":
    main()
