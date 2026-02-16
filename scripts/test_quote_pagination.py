"""
Test: Quote Status Report pagination via getData
=================================================
Key finding: browser uses SINGLE params (not arrays!) for getData.

The browser's actual getData format (from reqid=636):
  7|0|13|...|getData|ViewToken|LoadOptions|{uuid}|HashMap|en_US|
  ArrayList|Order|name|NullValue|
  1|2|3|4|2|5|6|5|7|6|8|0|0|0|0|25|9|10|1|11|1|12|0|0|13|0|0|

This uses getData(ViewToken, LoadOptions) not getData(ViewToken[], LoadOptions[]).
"""

import json
import re
import sys
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

INFORMER_BASE = "https://eaglesign.keyedinsign.com:8443"
INFORMER_PATH = "/eaglesign/informer"
MODULE_BASE = f"{INFORMER_BASE}{INFORMER_PATH}/"
GWT_PERMUTATION = "6823F3E0DFFF554BC1A7951AA98B182D"

POLICY_KEYS = {
    "view": "327E0F303D0CA463050DC31340CFE01D",
    "command": "81D82B6C6154989542DE45F20CEB3EF0",
}

SESSION_FILE = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\informer_session.json")
CMD_REQUEST = Path(
    r"C:\Scripts\keyedin-capture\reports\report_quote_status_report_cmd_request.txt"
)

CAPTURED_AUTH_TOKEN = "6728f894-940d-4611-85e7-a40d225d58eb"
CAPTURED_CLIENT_ID = "cf4f5ce2-8fb2-456e-b23f-3755434cfdf0"


def build_gwt_payload(strings: list[str], refs: list) -> str:
    parts = ["7", "0", str(len(strings))]
    parts.extend(strings)
    parts.extend(str(r) for r in refs)
    return "|".join(parts) + "|"


def send_rpc(session, service_key, payload, auth_token, client_id):
    endpoints = {
        "view": f"{INFORMER_PATH}/rpc/protected/ViewRPCService",
        "command": f"{INFORMER_PATH}/commandService",
    }
    url = f"{INFORMER_BASE}{endpoints[service_key]}"
    if auth_token:
        url += f"?authToken={auth_token}&clientId={client_id}"

    headers = {
        "Content-Type": "text/x-gwt-rpc; charset=UTF-8",
        "X-GWT-Permutation": GWT_PERMUTATION,
        "X-GWT-Module-Base": MODULE_BASE,
    }

    resp = session.post(url, data=payload.encode("utf-8"), headers=headers, timeout=120)
    return resp


def extract_view_token(response_text):
    """Extract ViewToken UUID from GWT response."""
    uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    idx = response_text.find("ViewToken/3777265110")
    if idx >= 0:
        match = re.search(uuid_pattern, response_text[idx:])
        if match:
            return match.group(0)
    return None


def build_getdata_browser_format(view_token, offset=0, limit=25):
    """Exact browser format: getData(ViewToken, LoadOptions) with single params.

    Matches reqid=636 from browser capture:
    1|2|3|4|2|5|6|5|7|6|8|0|0|0|0|25|9|10|1|11|1|12|0|0|13|0|0|
    """
    return build_gwt_payload(
        strings=[
            MODULE_BASE,                                                          # 1
            POLICY_KEYS["view"],                                                  # 2
            "com.entrinsik.informer.core.client.service.ViewRPCService",          # 3
            "getData",                                                            # 4
            "com.entrinsik.gwt.data.shared.ViewToken/3777265110",                 # 5
            "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",               # 6
            view_token,                                                           # 7
            "java.util.HashMap/1797211028",                                       # 8
            "en_US",                                                              # 9
            "java.util.ArrayList/4159755760",                                     # 10
            "com.entrinsik.gwt.data.shared.Order/1651361273",                     # 11
            "name",                                                               # 12
            "com.entrinsik.gwt.data.shared.values.NullValue/2880996259",          # 13
        ],
        refs=[
            1, 2, 3, 4,         # header
            2, 5, 6,            # 2 params: ViewToken, LoadOptions (SINGLE, not array)
            5, 7,               # ViewToken(uuid)
            6, 8, 0,            # LoadOptions, HashMap(0 entries)
            0, 0,               # null criteria, null projections
            offset, limit,      # offset, limit
            9,                  # "en_US" locale
            10, 1,              # ArrayList(1 order)
            11, 1,              # Order(ascending=1)
            12,                 # "name" field
            0, 0,               # trailing nulls in Order
            13, 0, 0,           # NullValue, trailing
        ],
    )


def build_getdata_no_order(view_token, offset=0, limit=25):
    """getData without ordering — null orders instead of ArrayList."""
    return build_gwt_payload(
        strings=[
            MODULE_BASE,                                                          # 1
            POLICY_KEYS["view"],                                                  # 2
            "com.entrinsik.informer.core.client.service.ViewRPCService",          # 3
            "getData",                                                            # 4
            "com.entrinsik.gwt.data.shared.ViewToken/3777265110",                 # 5
            "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",               # 6
            view_token,                                                           # 7
            "java.util.HashMap/1797211028",                                       # 8
            "en_US",                                                              # 9
            "com.entrinsik.gwt.data.shared.values.NullValue/2880996259",          # 10
        ],
        refs=[
            1, 2, 3, 4,         # header
            2, 5, 6,            # 2 params: ViewToken, LoadOptions
            5, 7,               # ViewToken(uuid)
            6, 8, 0,            # LoadOptions, HashMap(0)
            0, 0,               # null criteria, null projections
            offset, limit,      # offset, limit
            9,                  # "en_US" locale
            0,                  # null orders (no ArrayList)
            0, 0,               # trailing nulls
            10, 0, 0,           # NullValue, trailing
        ],
    )


def build_getdata_quoteno_order(view_token, offset=0, limit=25):
    """getData with ordering by quoteno (a field that exists in quote data)."""
    return build_gwt_payload(
        strings=[
            MODULE_BASE,                                                          # 1
            POLICY_KEYS["view"],                                                  # 2
            "com.entrinsik.informer.core.client.service.ViewRPCService",          # 3
            "getData",                                                            # 4
            "com.entrinsik.gwt.data.shared.ViewToken/3777265110",                 # 5
            "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",               # 6
            view_token,                                                           # 7
            "java.util.HashMap/1797211028",                                       # 8
            "en_US",                                                              # 9
            "java.util.ArrayList/4159755760",                                     # 10
            "com.entrinsik.gwt.data.shared.Order/1651361273",                     # 11
            "quoteno",                                                            # 12
            "com.entrinsik.gwt.data.shared.values.NullValue/2880996259",          # 13
        ],
        refs=[
            1, 2, 3, 4,         # header
            2, 5, 6,            # 2 params: ViewToken, LoadOptions
            5, 7,               # ViewToken(uuid)
            6, 8, 0,            # LoadOptions, HashMap(0)
            0, 0,               # null criteria, null projections
            offset, limit,      # offset, limit
            9,                  # "en_US" locale
            10, 1,              # ArrayList(1 order)
            11, 1,              # Order(ascending=1)
            12,                 # "quoteno" field
            0, 0,               # trailing
            13, 0, 0,           # NullValue, trailing
        ],
    )


def build_getdata_limit_all(view_token):
    """getData with limit=-1 (all rows) — browser format."""
    return build_gwt_payload(
        strings=[
            MODULE_BASE,                                                          # 1
            POLICY_KEYS["view"],                                                  # 2
            "com.entrinsik.informer.core.client.service.ViewRPCService",          # 3
            "getData",                                                            # 4
            "com.entrinsik.gwt.data.shared.ViewToken/3777265110",                 # 5
            "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",               # 6
            view_token,                                                           # 7
            "java.util.HashMap/1797211028",                                       # 8
            "en_US",                                                              # 9
            "java.util.ArrayList/4159755760",                                     # 10
            "com.entrinsik.gwt.data.shared.Order/1651361273",                     # 11
            "name",                                                               # 12
            "com.entrinsik.gwt.data.shared.values.NullValue/2880996259",          # 13
        ],
        refs=[
            1, 2, 3, 4,         # header
            2, 5, 6,            # 2 params
            5, 7,               # ViewToken(uuid)
            6, 8, 0,            # LoadOptions, HashMap(0)
            0, 0,               # null criteria, null projections
            0, -1,              # offset=0, limit=-1 (ALL)
            9,                  # "en_US"
            10, 1,              # ArrayList(1 order)
            11, 1,              # Order(ascending)
            12,                 # "name"
            0, 0,               # trailing
            13, 0, 0,           # NullValue, trailing
        ],
    )


def main():
    data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    jsessionid = data["jsessionid"]
    auth_token = data["auth_token"]
    client_id = data["client_id"]
    print(f"Session: auth_token={auth_token[:20]}...")

    s = requests.Session()
    s.verify = False
    s.cookies.set("JSESSIONID", jsessionid)

    # Step 1: Run the report
    print("\n" + "=" * 60)
    print("STEP 1: RunReportCommand")
    print("=" * 60)

    payload = CMD_REQUEST.read_text(encoding="utf-8").strip()
    payload = payload.replace(CAPTURED_AUTH_TOKEN, auth_token)
    payload = payload.replace(CAPTURED_CLIENT_ID, client_id)

    resp = send_rpc(s, "command", payload, auth_token, client_id)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")

    if not resp.text.startswith("//OK"):
        print(f"  ERROR: {resp.text[:300]}")
        sys.exit(1)

    view_token = extract_view_token(resp.text)
    print(f"  ViewToken: {view_token}")

    # Step 2: Test getData variants
    tests = [
        ("Browser format (name order)", build_getdata_browser_format(view_token, 0, 25)),
        ("No ordering", build_getdata_no_order(view_token, 0, 25)),
        ("Order by quoteno", build_getdata_quoteno_order(view_token, 0, 25)),
        ("Limit=-1 (all rows)", build_getdata_limit_all(view_token)),
        ("Page 2 (offset=25)", build_getdata_browser_format(view_token, 25, 25)),
    ]

    for name, payload in tests:
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print(f"{'='*60}")
        resp = send_rpc(s, "view", payload, auth_token, client_id)
        print(f"  Status: {resp.status_code}")
        print(f"  Length: {len(resp.text)}")

        if resp.text.startswith("//OK"):
            # Check if it has actual data
            if len(resp.text) > 200:
                print(f"  DATA FOUND! ({len(resp.text)} bytes)")
                # Look for ViewPage total count
                nums = re.findall(r"(?<=,)\d{3,}(?=,)", resp.text[:2000])
                print(f"  Large numbers: {nums[:8]}")
                # Show first 300 chars
                print(f"  Preview: {resp.text[:300]}")
            else:
                print(f"  Empty/minimal response")
                print(f"  Full: {resp.text}")
        elif resp.text.startswith("//EX"):
            # Extract error
            err_match = re.search(r'"([^"]+)"', resp.text)
            err = err_match.group(1) if err_match else resp.text[:200]
            print(f"  ERROR: {err}")
        else:
            print(f"  Response: {resp.text[:300]}")

    print(f"\n{'='*60}")
    print("DONE")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
