#!/usr/bin/env python3
"""
KeyedIn Export Endpoint Tester
Tests all 6 export endpoints, 5 import endpoints, and 3 untested CGI endpoints.
Saves results to export-test-results/ directory.
"""
import http.cookiejar
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

BASE_URL = "https://eaglesign.keyedinsign.com"
CGI_BASE = f"{BASE_URL}/cgi-bin/mvi.exe"
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "export-test-results")

# Credentials from existing repo scripts
USERNAME = "BradyF"
PASSWORD = "Eagle@605!"

EXPORT_ENDPOINTS = [
    "CUST.PROD.EXPORT",
    "GM.BY.INV.EXPORT",
    "SLSPER.PROD.EXPORT",
    "USAGE.ANAL.FILE",
    "EXPORT.WO.LABOR.ANALYSIS",
    "EXPORT.WIP.SUMMARY",
]

IMPORT_ENDPOINTS = [
    "IMPORT.PARTS",
    "IMPORT.BOM",
    "IMPORT.ROUTING",
    "IMPORT.CRM.NEW",
    "IMPORT.SIGN.TEMPLATE",
]

# 3 untested CGI endpoints that should return data (read-only)
SPOT_CHECK_ENDPOINTS = [
    "WO.STATUS.MATL",       # Costing - Material
    "WO.STATUS.LABR",       # Costing - Labor
    "QUOTE.PIPELINE.REPORT", # Quote pipeline
]

def create_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def authenticate(cookie_jar, opener):
    """Authenticate and return True if successful."""
    login_data = urllib.parse.urlencode({
        "USERNAME": USERNAME,
        "PASSWORD": PASSWORD,
        "SECURE": "TRUE",
    }).encode("utf-8")

    print(f"[AUTH] POST {BASE_URL} ...")
    start = time.time()
    try:
        req = urllib.request.Request(BASE_URL, data=login_data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        resp = opener.open(req, timeout=30)
        elapsed = int((time.time() - start) * 1000)
        status = resp.getcode()
        body = resp.read(2000).decode("utf-8", errors="replace")
        print(f"[AUTH] Status: {status}, Time: {elapsed}ms, Body length: {len(body)}")

        # Check cookies
        cookies = {c.name: c.value for c in cookie_jar}
        print(f"[AUTH] Cookies: {list(cookies.keys())}")
        if "SESSIONID" in cookies or "ASP.NET_SessionId" in cookies:
            print("[AUTH] SUCCESS - session cookie obtained")
            return True, elapsed, cookies
        else:
            print("[AUTH] WARNING - no session cookie found, checking body...")
            if "login" in body.lower() or "password" in body.lower():
                print("[AUTH] FAILED - still on login page")
                return False, elapsed, cookies
            return True, elapsed, cookies
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        print(f"[AUTH] ERROR: {e} ({elapsed}ms)")
        return False, elapsed, {}

def verify_session(opener):
    """Verify session by hitting a known-working endpoint."""
    url = f"{CGI_BASE}/WEB.MENU?USERNAME={USERNAME}"
    print(f"[VERIFY] GET {url} ...")
    start = time.time()
    try:
        resp = opener.open(url, timeout=30)
        elapsed = int((time.time() - start) * 1000)
        body = resp.read(1000).decode("utf-8", errors="replace")
        print(f"[VERIFY] Status: {resp.getcode()}, Size: {len(body)}, Time: {elapsed}ms")
        if "menuItem" in body or "menuHeader" in body:
            print("[VERIFY] SUCCESS - menu data returned, session is live")
            return True
        else:
            print("[VERIFY] WARNING - unexpected response content")
            return False
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        print(f"[VERIFY] ERROR: {e} ({elapsed}ms)")
        return False

def test_endpoint(opener, endpoint_name, method="GET", save_file=True):
    """Test a single endpoint. Returns result dict."""
    url = f"{CGI_BASE}/{endpoint_name}"
    result = {
        "endpoint": endpoint_name,
        "url": url,
        "method": method,
        "status": None,
        "content_type": None,
        "response_type": None,
        "body_preview": "",
        "body_length": 0,
        "form_fields": [],
        "error": None,
        "time_ms": 0,
        "saved_file": None,
    }

    print(f"\n[TEST] {method} {url} ...")
    start = time.time()
    try:
        if method == "POST":
            req = urllib.request.Request(url, data=b"", method="POST")
        else:
            req = urllib.request.Request(url)

        resp = opener.open(req, timeout=30)
        elapsed = int((time.time() - start) * 1000)
        result["time_ms"] = elapsed
        result["status"] = resp.getcode()
        result["content_type"] = resp.headers.get("Content-Type", "unknown")

        body = resp.read()
        result["body_length"] = len(body)

        # Determine response type
        ct = result["content_type"].lower()
        body_text = body.decode("utf-8", errors="replace")
        result["body_preview"] = body_text[:500]

        if "text/csv" in ct or "application/csv" in ct or "application/octet-stream" in ct:
            result["response_type"] = "FILE_DOWNLOAD"
        elif "application/vnd" in ct or "application/excel" in ct:
            result["response_type"] = "FILE_DOWNLOAD"
        elif "<form" in body_text.lower() or "<input" in body_text.lower():
            result["response_type"] = "FORM_REQUIRING_PARAMS"
            # Extract form fields
            result["form_fields"] = extract_form_fields(body_text)
        elif "error" in body_text.lower() and ("not defined" in body_text.lower() or "error code" in body_text.lower()):
            result["response_type"] = "ERROR"
            result["error"] = body_text[:300]
        elif len(body_text.strip()) < 50:
            result["response_type"] = "EMPTY_OR_MINIMAL"
        else:
            result["response_type"] = "DATA_RESPONSE"

        # Check for redirect to login
        if "login" in body_text.lower() and "password" in body_text.lower() and "username" in body_text.lower():
            result["response_type"] = "REDIRECT_TO_LOGIN"

        # Save file if it looks like downloadable data
        if save_file and result["response_type"] in ("FILE_DOWNLOAD", "DATA_RESPONSE"):
            ext = "csv" if "csv" in ct else "html" if "html" in ct else "txt"
            fname = f"{endpoint_name.replace('.', '_')}.{ext}"
            fpath = os.path.join(RESULTS_DIR, fname)
            with open(fpath, "wb") as f:
                f.write(body)
            result["saved_file"] = fname
            print(f"[TEST] Saved to {fname}")

        # Always save the raw response for analysis
        raw_fname = f"{endpoint_name.replace('.', '_')}_raw.html"
        raw_fpath = os.path.join(RESULTS_DIR, raw_fname)
        with open(raw_fpath, "wb") as f:
            f.write(body)

        print(f"[TEST] Status: {result['status']}, Type: {result['response_type']}, "
              f"Size: {result['body_length']}, CT: {result['content_type']}, Time: {elapsed}ms")

    except urllib.error.HTTPError as e:
        elapsed = int((time.time() - start) * 1000)
        result["time_ms"] = elapsed
        result["status"] = e.code
        result["error"] = str(e)
        result["response_type"] = "ERROR"
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        result["body_preview"] = body[:500]
        print(f"[TEST] HTTP ERROR {e.code}: {e} ({elapsed}ms)")

    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        result["time_ms"] = elapsed
        result["error"] = str(e)
        result["response_type"] = "ERROR"
        print(f"[TEST] ERROR: {e} ({elapsed}ms)")

    return result

def extract_form_fields(html):
    """Simple form field extraction without external dependencies."""
    fields = []
    html_lower = html.lower()

    # Find input fields
    i = 0
    while True:
        idx = html_lower.find("<input", i)
        if idx == -1:
            break
        end = html.find(">", idx)
        if end == -1:
            break
        tag = html[idx:end + 1]

        name = extract_attr(tag, "name")
        ftype = extract_attr(tag, "type") or "text"
        value = extract_attr(tag, "value") or ""
        size = extract_attr(tag, "size") or ""

        if name:
            fields.append({
                "name": name,
                "type": ftype,
                "value": value,
                "size": size,
            })
        i = end + 1

    # Find select fields
    i = 0
    while True:
        idx = html_lower.find("<select", i)
        if idx == -1:
            break
        end = html.find(">", idx)
        if end == -1:
            break
        tag = html[idx:end + 1]
        name = extract_attr(tag, "name")

        # Get options
        select_end = html_lower.find("</select>", idx)
        if select_end == -1:
            select_end = len(html)
        select_html = html[idx:select_end]
        options = extract_options(select_html)

        if name:
            fields.append({
                "name": name,
                "type": "select",
                "options": options,
            })
        i = (select_end if select_end < len(html) else end) + 1

    # Find textarea fields
    i = 0
    while True:
        idx = html_lower.find("<textarea", i)
        if idx == -1:
            break
        end = html.find(">", idx)
        if end == -1:
            break
        tag = html[idx:end + 1]
        name = extract_attr(tag, "name")
        if name:
            fields.append({"name": name, "type": "textarea"})
        i = end + 1

    return fields

def extract_attr(tag, attr_name):
    """Extract attribute value from an HTML tag."""
    tag_lower = tag.lower()
    patterns = [f'{attr_name}="', f"{attr_name}='", f"{attr_name}="]
    for pat in patterns:
        idx = tag_lower.find(pat)
        if idx == -1:
            continue
        start = idx + len(pat)
        if pat.endswith('"'):
            end = tag.find('"', start)
        elif pat.endswith("'"):
            end = tag.find("'", start)
        else:
            end = start
            while end < len(tag) and tag[end] not in (' ', '>', '/'):
                end += 1
        if end == -1:
            end = len(tag)
        return tag[start:end]
    return None

def extract_options(select_html):
    """Extract option values from a select element."""
    options = []
    lower = select_html.lower()
    i = 0
    while True:
        idx = lower.find("<option", i)
        if idx == -1:
            break
        tag_end = select_html.find(">", idx)
        if tag_end == -1:
            break
        tag = select_html[idx:tag_end + 1]
        value = extract_attr(tag, "value")

        # Get option text
        text_end = lower.find("</option>", tag_end)
        if text_end == -1:
            text_end = lower.find("<option", tag_end + 1)
            if text_end == -1:
                text_end = len(select_html)
        text = select_html[tag_end + 1:text_end].strip()

        options.append({"value": value or "", "text": text[:80]})
        i = tag_end + 1
    return options

def main():
    print("=" * 80)
    print(f"KeyedIn Export Endpoint Tester — {datetime.now().isoformat()}")
    print("=" * 80)

    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Set up cookie-based HTTP client
    ctx = create_ssl_context()
    cookie_jar = http.cookiejar.CookieJar()
    https_handler = urllib.request.HTTPSHandler(context=ctx)
    cookie_handler = urllib.request.HTTPCookieProcessor(cookie_jar)
    opener = urllib.request.build_opener(https_handler, cookie_handler)

    # Step 1: Authenticate
    print("\n--- STEP 1: AUTHENTICATE ---")
    auth_ok = False
    auth_time = 0
    auth_cookies = {}
    for attempt in range(1, 4):
        print(f"\nAttempt {attempt}/3:")
        auth_ok, auth_time, auth_cookies = authenticate(cookie_jar, opener)
        if auth_ok:
            break
        print(f"Auth failed on attempt {attempt}, retrying...")
        time.sleep(2)

    if not auth_ok:
        print("\n[FATAL] Authentication failed after 3 attempts. Aborting.")
        # Write failure report
        with open(os.path.join(RESULTS_DIR, "AUTH_FAILED.txt"), "w") as f:
            f.write(f"Authentication failed at {datetime.now().isoformat()}\n")
            f.write(f"Cookies received: {auth_cookies}\n")
        return

    # Verify session
    print("\n--- VERIFY SESSION ---")
    if not verify_session(opener):
        print("[WARNING] Session verification returned unexpected data, continuing anyway...")

    all_results = []

    # Step 2: Test export endpoints
    print("\n\n--- STEP 2: TEST EXPORT ENDPOINTS ---")
    for ep in EXPORT_ENDPOINTS:
        result = test_endpoint(opener, ep, method="GET")
        # If GET returns a form or empty, try POST
        if result["response_type"] in ("FORM_REQUIRING_PARAMS", "EMPTY_OR_MINIMAL"):
            print(f"  GET returned {result['response_type']}, trying POST...")
            post_result = test_endpoint(opener, ep, method="POST")
            if post_result["response_type"] not in ("FORM_REQUIRING_PARAMS", "EMPTY_OR_MINIMAL"):
                result = post_result
                result["method"] = "POST (fallback)"
        # Check for session death
        if result["response_type"] == "REDIRECT_TO_LOGIN":
            print("[WARNING] Session died, re-authenticating...")
            auth_ok, _, _ = authenticate(cookie_jar, opener)
            if auth_ok:
                result = test_endpoint(opener, ep, method="GET")
        all_results.append(("EXPORT", result))

    # Step 3: Test import endpoints (GET only)
    print("\n\n--- STEP 3: RECON IMPORT ENDPOINTS ---")
    for ep in IMPORT_ENDPOINTS:
        result = test_endpoint(opener, ep, method="GET", save_file=False)
        if result["response_type"] == "REDIRECT_TO_LOGIN":
            print("[WARNING] Session died, re-authenticating...")
            auth_ok, _, _ = authenticate(cookie_jar, opener)
            if auth_ok:
                result = test_endpoint(opener, ep, method="GET", save_file=False)
        all_results.append(("IMPORT", result))

    # Step 4: Spot-check 3 untested endpoints
    print("\n\n--- STEP 4: SPOT-CHECK UNTESTED ENDPOINTS ---")
    for ep in SPOT_CHECK_ENDPOINTS:
        result = test_endpoint(opener, ep, method="GET")
        if result["response_type"] == "REDIRECT_TO_LOGIN":
            print("[WARNING] Session died, re-authenticating...")
            auth_ok, _, _ = authenticate(cookie_jar, opener)
            if auth_ok:
                result = test_endpoint(opener, ep, method="GET")
        all_results.append(("SPOT_CHECK", result))

    # Save raw results as JSON
    json_path = os.path.join(RESULTS_DIR, "all_results.json")
    with open(json_path, "w") as f:
        json.dump([{"category": cat, **res} for cat, res in all_results], f, indent=2)
    print(f"\n\nRaw results saved to {json_path}")

    # Print summary
    print("\n\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"{'Category':<12} {'Endpoint':<28} {'Status':<6} {'Type':<24} {'Size':<8} {'Time'}")
    print("-" * 90)
    for cat, r in all_results:
        print(f"{cat:<12} {r['endpoint']:<28} {r['status'] or 'ERR':<6} "
              f"{r['response_type'] or 'UNKNOWN':<24} {r['body_length']:<8} {r['time_ms']}ms")

if __name__ == "__main__":
    main()
