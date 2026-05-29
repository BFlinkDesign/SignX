"""
KeyedIn Legacy ERP — Automated Recon Test Suite
================================================
Run from ANY internet-connected machine. VPN is NOT required.
(eaglesign.keyedinsign.com is cloud-hosted on AWS, publicly accessible.)

Usage:
    python run_all_tests.py --username BRADYF --password <password>

Or interactive:
    python run_all_tests.py

Saves all results to ./test_output/
"""

import argparse
import json
import os
import socket
import ssl
import sys
import time
import traceback
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "test_output"
BASE_HOST = "eaglesign.keyedinsign.com"
BASE_URL = f"https://{BASE_HOST}"
CGI_BASE = f"{BASE_URL}/cgi-bin/mvi.exe"
INFORMER_BASE = f"https://{BASE_HOST}:8443/eaglesign"

# Disable SSL verification for internal/legacy servers
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def setup():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Target: {BASE_HOST}")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 70)


def save_result(filename, content):
    path = OUTPUT_DIR / filename
    path.write_text(content, encoding="utf-8")
    print(f"  -> Saved: {path}")


def save_json(filename, data):
    path = OUTPUT_DIR / filename
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    print(f"  -> Saved: {path}")


# ==========================================================================
# TEST 1: NETWORK LOCATION
# ==========================================================================
def test_1_network():
    print("\n" + "=" * 70)
    print("TEST 1: NETWORK LOCATION")
    print("=" * 70)

    results = {"test": "network_location", "timestamp": datetime.now().isoformat()}

    # DNS resolution
    try:
        ip = socket.gethostbyname(BASE_HOST)
        results["ip"] = ip
        print(f"  DNS resolved: {BASE_HOST} -> {ip}")

        octets = ip.split(".")
        is_private = (
            ip.startswith("10.")
            or ip.startswith("192.168.")
            or (ip.startswith("172.") and 16 <= int(octets[1]) <= 31)
            or ip.startswith("127.")
        )

        results["is_private_ip"] = is_private
        if is_private:
            print(f"  *** PRIVATE IP: {ip} ***")
            print("  VERDICT: ON-PREM or VPN-only (server is on Eagle Sign's network)")
            results["verdict"] = "ON-PREM / PRIVATE NETWORK"
        else:
            print(f"  PUBLIC IP: {ip}")
            print("  VERDICT: HOSTED — cloud-accessible, no VPN needed")
            results["verdict"] = "HOSTED / PUBLIC (NO VPN REQUIRED)"

    except socket.gaierror as e:
        results["error"] = str(e)
        results["verdict"] = "DNS_FAILED"
        print(f"  DNS FAILED: {e}")

    # Port checks
    for port in [80, 443, 8443]:
        try:
            sock = socket.create_connection((BASE_HOST, port), timeout=5)
            sock.close()
            results[f"port_{port}"] = "OPEN"
            print(f"  Port {port}: OPEN")
        except Exception as e:
            results[f"port_{port}"] = f"CLOSED ({e})"
            print(f"  Port {port}: CLOSED ({e})")

    save_json("01_network_location.json", results)

    # Also save markdown
    md = f"""# TEST 1: Network Location

**Date:** {datetime.now().isoformat()}
**Target:** {BASE_HOST}

## DNS Resolution
- IP: {results.get('ip', 'FAILED')}
- Private IP: {results.get('is_private_ip', 'N/A')}
- **Verdict: {results.get('verdict', 'UNKNOWN')}**

## Port Status
- Port 80:   {results.get('port_80', 'N/A')}
- Port 443:  {results.get('port_443', 'N/A')}
- Port 8443: {results.get('port_8443', 'N/A')}
"""
    save_result("01_network_location.md", md)
    return results


# ==========================================================================
# TEST 2: AUTHENTICATION
# ==========================================================================
def test_2_auth(username, password):
    print("\n" + "=" * 70)
    print("TEST 2: DIRECT AUTHENTICATION")
    print("=" * 70)

    results = {"test": "authentication", "timestamp": datetime.now().isoformat()}

    # Set up cookie jar
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar),
        urllib.request.HTTPSHandler(context=ssl_ctx),
    )

    # Step 1: GET login page
    print("  Step 1: GET login page...")
    try:
        resp = opener.open(f"{CGI_BASE}/LOGIN.START", timeout=15)
        login_html = resp.read().decode("utf-8", errors="replace")
        results["login_page_status"] = resp.status
        results["login_page_url"] = resp.url
        results["login_page_size"] = len(login_html)
        save_result("02_login_page.html", login_html)
        print(f"    Status: {resp.status}, URL: {resp.url}, Size: {len(login_html)}")

        # Check if this is a Google SSO redirect
        if "accounts.google.com" in resp.url or "accounts.google.com" in login_html:
            results["auth_method"] = "GOOGLE_SSO"
            results["verdict"] = "GOOGLE SSO DETECTED - direct login will not work"
            print("  *** GOOGLE SSO DETECTED ***")
            print("  The login redirects to Google. Direct POST auth will NOT work.")
            print("  Must use Playwright persistent context instead.")
            save_json("02_auth_test.json", results)
            return results, None
        else:
            results["auth_method"] = "DIRECT_FORM"
            print("    Auth method: Direct form (username/password)")

    except Exception as e:
        results["login_page_error"] = str(e)
        print(f"    FAILED: {e}")
        save_json("02_auth_test.json", results)
        return results, None

    # Step 2: POST credentials
    print(f"  Step 2: POST login as {username}...")
    try:
        form_data = urllib.parse.urlencode({
            "USERNAME": username,
            "PASSWORD": password,
            "SECURE": "TRUE",
        }).encode("utf-8")

        req = urllib.request.Request(
            BASE_URL,
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp = opener.open(req, timeout=15)
        post_html = resp.read().decode("utf-8", errors="replace")

        results["post_status"] = resp.status
        results["post_url"] = resp.url
        results["post_size"] = len(post_html)
        save_result("02_post_login_response.html", post_html)

        # Check cookies
        cookies = {}
        for cookie in cookie_jar:
            cookies[cookie.name] = {
                "value": cookie.value[:20] + "..." if len(cookie.value) > 20 else cookie.value,
                "domain": cookie.domain,
                "path": cookie.path,
                "secure": cookie.secure,
                "expires": cookie.expires,
            }
        results["cookies"] = cookies
        results["cookie_count"] = len(cookies)

        has_session = "SESSIONID" in cookies or "ASP.NET_SessionId" in cookies
        results["has_session_cookie"] = has_session

        if has_session:
            print(f"    SUCCESS - Session cookie obtained")
            print(f"    Cookies: {list(cookies.keys())}")
            results["verdict"] = "AUTH_SUCCESS"
        else:
            # Check if login failed (look for error in HTML)
            if "invalid" in post_html.lower() or "error" in post_html.lower() or "failed" in post_html.lower():
                results["verdict"] = "AUTH_FAILED - invalid credentials"
                print("    FAILED - invalid credentials")
            else:
                results["verdict"] = "AUTH_UNCLEAR - no session cookie but no error"
                print("    UNCLEAR - check 02_post_login_response.html")

        # Save full cookie jar for later tests
        cookie_data = []
        for cookie in cookie_jar:
            cookie_data.append({
                "name": cookie.name,
                "value": cookie.value,
                "domain": cookie.domain,
                "path": cookie.path,
            })
        save_json("02_session_cookies.json", cookie_data)

    except Exception as e:
        results["post_error"] = str(e)
        results["verdict"] = f"AUTH_ERROR: {e}"
        print(f"    ERROR: {e}")
        traceback.print_exc()
        save_json("02_auth_test.json", results)
        return results, None

    save_json("02_auth_test.json", results)
    return results, opener if has_session else None


# ==========================================================================
# TEST 3: EXPORT ENDPOINTS
# ==========================================================================
def test_3_exports(opener):
    print("\n" + "=" * 70)
    print("TEST 3: EXPORT ENDPOINTS")
    print("=" * 70)

    if opener is None:
        print("  SKIPPED - no authenticated session")
        save_result("03_export_tests.md", "# TEST 3: SKIPPED - no authenticated session\n")
        return {"test": "exports", "verdict": "SKIPPED"}

    export_endpoints = [
        ("CUST.PROD.EXPORT", "Sales by Customer by Product - Export"),
        ("GM.BY.INV.EXPORT", "Gross Margin by Invoice Export"),
        ("SLSPER.PROD.EXPORT", "GM By Salesperson - Export"),
        ("USAGE.ANAL.FILE", "Part Usage Export"),
        ("EXPORT.WO.LABOR.ANALYSIS", "WO Labor Analysis Export"),
        ("EXPORT.WIP.SUMMARY", "WIP Open or Closed Summary Export"),
    ]

    results = {"test": "export_endpoints", "timestamp": datetime.now().isoformat(), "endpoints": []}

    for process, description in export_endpoints:
        url = f"{CGI_BASE}/{process}"
        print(f"\n  [{process}] {description}")
        print(f"    URL: {url}")

        endpoint_result = {
            "process": process,
            "description": description,
            "url": url,
        }

        try:
            resp = opener.open(url, timeout=30)
            body = resp.read()
            body_text = body.decode("utf-8", errors="replace")

            # Capture headers
            headers = dict(resp.headers)
            endpoint_result["status"] = resp.status
            endpoint_result["content_type"] = headers.get("Content-Type", "unknown")
            endpoint_result["content_disposition"] = headers.get("Content-Disposition", "none")
            endpoint_result["content_length"] = len(body)
            endpoint_result["headers"] = headers

            # Determine response type
            ct = headers.get("Content-Type", "").lower()
            if "csv" in ct or "text/csv" in ct:
                endpoint_result["response_type"] = "CSV_FILE"
                print(f"    CSV FILE! Size: {len(body)} bytes")
            elif "excel" in ct or "spreadsheet" in ct:
                endpoint_result["response_type"] = "EXCEL_FILE"
                print(f"    EXCEL FILE! Size: {len(body)} bytes")
            elif "octet-stream" in ct:
                endpoint_result["response_type"] = "BINARY_DOWNLOAD"
                print(f"    BINARY DOWNLOAD! Size: {len(body)} bytes")
            elif "html" in ct:
                endpoint_result["response_type"] = "HTML_PAGE"
                # Check if it's a form (needs parameters) or data
                if "<form" in body_text.lower() or "<input" in body_text.lower():
                    endpoint_result["response_type"] = "HTML_FORM"
                    print(f"    HTML FORM (needs parameters). Size: {len(body)} bytes")
                elif "<table" in body_text.lower():
                    endpoint_result["response_type"] = "HTML_TABLE"
                    print(f"    HTML TABLE (data in tables). Size: {len(body)} bytes")
                else:
                    print(f"    HTML PAGE. Size: {len(body)} bytes")
            else:
                endpoint_result["response_type"] = f"OTHER ({ct})"
                print(f"    Content-Type: {ct}, Size: {len(body)} bytes")

            # Check for errors in response
            if "error" in body_text.lower() and "not defined in the voc" in body_text.lower():
                endpoint_result["response_type"] = "VOC_ERROR"
                print(f"    VOC ERROR - process not defined")

            # Save first 500 lines of body
            lines = body_text.split("\n")[:500]
            save_result(f"03_export_{process}.txt", "\n".join(lines))

            print(f"    Status: {resp.status}")

        except Exception as e:
            endpoint_result["error"] = str(e)
            endpoint_result["response_type"] = "ERROR"
            print(f"    ERROR: {e}")

        results["endpoints"].append(endpoint_result)
        time.sleep(1)  # Rate limit between requests

    save_json("03_export_tests.json", results)

    # Generate markdown summary
    md_lines = ["# TEST 3: Export Endpoints\n"]
    md_lines.append(f"**Date:** {datetime.now().isoformat()}\n")
    md_lines.append("| Process | Description | Status | Type | Size |")
    md_lines.append("|---------|-------------|--------|------|------|")
    for ep in results["endpoints"]:
        md_lines.append(
            f"| `{ep['process']}` | {ep['description']} | "
            f"{ep.get('status', 'ERR')} | {ep.get('response_type', 'N/A')} | "
            f"{ep.get('content_length', 'N/A')} |"
        )
    save_result("03_export_tests.md", "\n".join(md_lines))

    return results


# ==========================================================================
# TEST 4: INFORMER BI ACCESS
# ==========================================================================
def test_4_informer(opener):
    print("\n" + "=" * 70)
    print("TEST 4: INFORMER BI ACCESS (Port 8443)")
    print("=" * 70)

    if opener is None:
        print("  SKIPPED - no authenticated session")
        save_result("04_informer_tests.md", "# TEST 4: SKIPPED - no authenticated session\n")
        return {"test": "informer", "verdict": "SKIPPED"}

    results = {"test": "informer", "timestamp": datetime.now().isoformat()}

    # Try to access the Informer portal
    informer_url = f"{INFORMER_BASE}/informer/"
    print(f"  Trying: {informer_url}")

    try:
        resp = opener.open(informer_url, timeout=15)
        body = resp.read().decode("utf-8", errors="replace")
        results["informer_status"] = resp.status
        results["informer_url"] = resp.url
        results["informer_size"] = len(body)
        save_result("04_informer_page.html", body)
        print(f"    Status: {resp.status}, Size: {len(body)}")

        # Check if we're authenticated or redirected to login
        if "login" in resp.url.lower() or "sso" in resp.url.lower():
            results["informer_auth"] = "NEEDS_SSO"
            print("    Redirected to login/SSO - need SSO token from main app")
        else:
            results["informer_auth"] = "ACCESSIBLE"
            print("    Informer page loaded")

    except Exception as e:
        results["informer_error"] = str(e)
        print(f"    ERROR: {e}")

    # Try the SSO endpoint pattern (won't work without a fresh token, but documents the flow)
    sso_url = f"{INFORMER_BASE}/sso?u=BRADYF"
    print(f"\n  Trying SSO pattern: {sso_url}")
    try:
        resp = opener.open(sso_url, timeout=10)
        body = resp.read().decode("utf-8", errors="replace")
        results["sso_status"] = resp.status
        save_result("04_sso_response.html", body)
        print(f"    SSO response: {resp.status}, Size: {len(body)}")
    except Exception as e:
        results["sso_error"] = str(e)
        print(f"    SSO error: {e}")

    # Try to find Informer API docs
    api_urls = [
        f"{INFORMER_BASE}/informer/rpc/",
        f"{INFORMER_BASE}/api/",
        f"{INFORMER_BASE}/rest/",
    ]
    for url in api_urls:
        try:
            resp = opener.open(url, timeout=5)
            body = resp.read().decode("utf-8", errors="replace")
            print(f"    {url} -> {resp.status} ({len(body)} bytes)")
            results[f"api_probe_{url}"] = {"status": resp.status, "size": len(body)}
        except Exception as e:
            print(f"    {url} -> {e}")

    save_json("04_informer_tests.json", results)
    save_result("04_informer_tests.md", f"""# TEST 4: Informer BI Access

**Date:** {datetime.now().isoformat()}

## Informer Portal ({informer_url})
- Status: {results.get('informer_status', 'N/A')}
- Auth: {results.get('informer_auth', 'N/A')}
- Size: {results.get('informer_size', 'N/A')} bytes

## SSO Access
- Status: {results.get('sso_status', results.get('sso_error', 'N/A'))}

## Notes
The Informer BI portal requires SSO authentication from the main KeyedIn app.
To access it programmatically, we need to:
1. Log into the main app first (Test 2)
2. Capture the SSO token from the Informer menu links
3. Use the SSO token to authenticate with Informer
""")
    return results


# ==========================================================================
# TEST 5: QUOTE ENTRY READ
# ==========================================================================
def test_5_quote_read(opener, quote_number=None):
    print("\n" + "=" * 70)
    print("TEST 5: QUOTE ENTRY READ")
    print("=" * 70)

    if opener is None:
        print("  SKIPPED - no authenticated session")
        save_result("05_quote_read_test.md", "# TEST 5: SKIPPED - no authenticated session\n")
        return {"test": "quote_read", "verdict": "SKIPPED"}

    results = {"test": "quote_read", "timestamp": datetime.now().isoformat()}

    # First try the quote entry form without a quote number
    print(f"  Step 1: GET EST.QUOTE.ENTRY (no params)...")
    try:
        resp = opener.open(f"{CGI_BASE}/EST.QUOTE.ENTRY", timeout=15)
        body = resp.read().decode("utf-8", errors="replace")
        results["form_status"] = resp.status
        results["form_size"] = len(body)
        save_result("05_quote_entry_form.html", body)
        print(f"    Status: {resp.status}, Size: {len(body)} bytes")

        # Look for form fields
        import re
        inputs = re.findall(r'<input[^>]*name=["\']([^"\']+)["\'][^>]*>', body, re.IGNORECASE)
        selects = re.findall(r'<select[^>]*name=["\']([^"\']+)["\'][^>]*>', body, re.IGNORECASE)
        results["form_fields"] = {"inputs": inputs, "selects": selects}
        if inputs or selects:
            print(f"    Form fields found: {len(inputs)} inputs, {len(selects)} selects")
            for f in inputs[:15]:
                print(f"      input: {f}")
            for f in selects[:5]:
                print(f"      select: {f}")

    except Exception as e:
        results["form_error"] = str(e)
        print(f"    ERROR: {e}")

    # Try QUOTE.ENTRY.DETAILS with quote number if provided
    if quote_number:
        print(f"\n  Step 2: GET QUOTE.ENTRY.DETAILS?QUOTENO={quote_number}...")
        try:
            url = f"{CGI_BASE}/QUOTE.ENTRY.DETAILS?QUOTENO={quote_number}"
            resp = opener.open(url, timeout=15)
            body = resp.read().decode("utf-8", errors="replace")
            results["detail_status"] = resp.status
            results["detail_size"] = len(body)
            save_result("05_quote_detail.html", body)
            print(f"    Status: {resp.status}, Size: {len(body)} bytes")

            # Extract any data from the page
            inputs_with_values = re.findall(
                r'<input[^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\'][^>]*>',
                body, re.IGNORECASE,
            )
            results["detail_fields"] = {name: val for name, val in inputs_with_values}
            if inputs_with_values:
                print(f"    Fields with values: {len(inputs_with_values)}")
                for name, val in inputs_with_values[:20]:
                    print(f"      {name} = {val}")

        except Exception as e:
            results["detail_error"] = str(e)
            print(f"    ERROR: {e}")
    else:
        print("\n  Step 2: SKIPPED - no quote number provided")
        print("    Re-run with: python run_all_tests.py --quote <NUMBER>")

    # Also try the quote status report (read-only, safe)
    print(f"\n  Step 3: GET EST.QUOTE.STATUS (quote listing)...")
    try:
        resp = opener.open(f"{CGI_BASE}/EST.QUOTE.STATUS", timeout=15)
        body = resp.read().decode("utf-8", errors="replace")
        results["status_report_status"] = resp.status
        results["status_report_size"] = len(body)
        save_result("05_quote_status_report.html", body)
        print(f"    Status: {resp.status}, Size: {len(body)} bytes")

        # Count tables and rows
        tables = re.findall(r'<table', body, re.IGNORECASE)
        rows = re.findall(r'<tr', body, re.IGNORECASE)
        results["status_tables"] = len(tables)
        results["status_rows"] = len(rows)
        print(f"    Tables: {len(tables)}, Rows: {len(rows)}")

    except Exception as e:
        results["status_report_error"] = str(e)
        print(f"    ERROR: {e}")

    save_json("05_quote_read_test.json", results)
    return results


# ==========================================================================
# TEST 6: WRITE TEST PLAN (documentation only, no actual writes)
# ==========================================================================
def test_6_write_plan(test5_results):
    print("\n" + "=" * 70)
    print("TEST 6: WRITE TEST PLAN (documentation only)")
    print("=" * 70)

    form_fields = test5_results.get("form_fields", {})

    plan = f"""# TEST 6: Write Test Plan

**Date:** {datetime.now().isoformat()}
**Status:** PLAN ONLY - requires Brady's explicit approval before execution

## Proposed Write Test

### Target
- Endpoint: `POST /cgi-bin/mvi.exe/EST.QUOTE.ENTRY`
- Action: Create or modify a quote line item on a TEST quote

### Prerequisites
1. Brady creates a dedicated TEST quote in KeyedIn (e.g., "TEST-AUTOMATION-001")
2. Brady provides the quote number
3. Brady confirms it's safe to modify this quote

### Form Fields Discovered
{json.dumps(form_fields, indent=2)}

### Proposed Test Steps

1. **GET** the quote entry form to capture any hidden fields (CSRF tokens, session IDs)
2. **GET** QUOTE.ENTRY.DETAILS for the test quote to see current state
3. **POST** to EST.QUOTE.ENTRY with form data:
   - Hidden fields from step 1
   - QUOTENO = (test quote number)
   - ITEM_TYPE = "P" (Part)
   - ITEM_NO = (a known part number)
   - QTY = 1
   - COST = (known cost)
   - MARKUP = 0
4. **GET** QUOTE.ENTRY.DETAILS again to verify the line item was added
5. If successful, **DELETE** the test line item (or document how to)

### Risk Assessment
- LOW risk if using a dedicated test quote
- The same form submission a human user would make
- No database-level writes, only application-level
- Application enforces its own validation rules

### What We Need From Brady
- [ ] A safe test quote number
- [ ] A valid part number to use
- [ ] Explicit "go ahead" to test writes
"""
    save_result("06_write_test_plan.md", plan)
    print("  Write test plan saved (documentation only)")
    return {"test": "write_plan", "verdict": "PLAN_SAVED"}


# ==========================================================================
# MAIN
# ==========================================================================
def main():
    parser = argparse.ArgumentParser(description="KeyedIn Legacy ERP Recon Tests")
    parser.add_argument("--username", default=None, help="KeyedIn username (e.g., BRADYF)")
    parser.add_argument("--password", default=None, help="KeyedIn password")
    parser.add_argument("--quote", default=None, help="Quote number for read test (e.g., 39430)")
    args = parser.parse_args()

    setup()

    # Interactive credential prompt if not provided
    username = args.username
    password = args.password

    if not username:
        username = input("\nKeyedIn username (e.g., BRADYF): ").strip()
    if not password:
        import getpass
        password = getpass.getpass("KeyedIn password: ")

    print(f"\nRunning as: {username}")

    # Run all tests
    all_results = {}

    # Test 1: Network
    all_results["network"] = test_1_network()

    # Test 2: Auth
    auth_results, opener = test_2_auth(username, password)
    all_results["auth"] = auth_results

    # Test 3: Exports (requires auth)
    all_results["exports"] = test_3_exports(opener)

    # Test 4: Informer (requires auth)
    all_results["informer"] = test_4_informer(opener)

    # Test 5: Quote read (requires auth)
    all_results["quote_read"] = test_5_quote_read(opener, args.quote)

    # Test 6: Write plan (documentation)
    all_results["write_plan"] = test_6_write_plan(all_results.get("quote_read", {}))

    # Test 7: REST API probes
    all_results["rest_api"] = test_7_rest_api(opener)

    save_json("ALL_RESULTS.json", all_results)

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Network:  {all_results['network'].get('verdict', 'N/A')}")
    print(f"  Auth:     {all_results['auth'].get('verdict', 'N/A')}")
    print(f"  Exports:  {len([e for e in all_results['exports'].get('endpoints', []) if e.get('status') == 200])} / 6 accessible")
    print(f"  Informer: {all_results['informer'].get('informer_auth', 'N/A')}")
    print(f"  Quote:    {all_results['quote_read'].get('form_status', 'N/A')}")
    print(f"  REST API: {all_results['rest_api'].get('verdict', 'N/A')}")
    print(f"\nAll results saved to: {OUTPUT_DIR}")
    print("Share the test_output/ folder for analysis.")


# ==========================================================================
# TEST 7: REST API PROBES (Informer 5 standard REST endpoints)
# ==========================================================================
def test_7_rest_api(opener):
    """Probe Informer 5 REST API endpoints that have never been tested."""
    print("\n" + "=" * 70)
    print("TEST 7: REST API PROBES (Informer 5)")
    print("=" * 70)

    results = {"test": "rest_api", "timestamp": datetime.now().isoformat(), "endpoints": []}

    rest_paths = [
        ("GET", f"{INFORMER_BASE}/documentation", "Swagger/API docs"),
        ("GET", f"{INFORMER_BASE}/api/datasets", "Datasets listing"),
        ("GET", f"{INFORMER_BASE}/api/reports", "Reports listing"),
        ("GET", f"{INFORMER_BASE}/api/queries", "Queries listing"),
        ("GET", f"{INFORMER_BASE}/api/session", "Current session"),
        ("GET", f"{INFORMER_BASE}/api/users/current", "Current user"),
        ("GET", f"{INFORMER_BASE}/rest", "REST root"),
        ("GET", f"{INFORMER_BASE}/swagger", "Swagger UI"),
        ("GET", f"{INFORMER_BASE}/swagger.json", "Swagger JSON"),
        ("GET", f"{INFORMER_BASE}/v2/api-docs", "OpenAPI v2"),
        ("GET", f"{INFORMER_BASE}/v3/api-docs", "OpenAPI v3"),
    ]

    for method, url, description in rest_paths:
        endpoint_result = {"method": method, "url": url, "description": description}
        print(f"\n  [{method}] {description}")
        print(f"    URL: {url}")

        try:
            req = urllib.request.Request(url)
            resp = opener.open(req, timeout=15)
            body = resp.read().decode("utf-8", errors="replace")
            endpoint_result["status"] = resp.status
            endpoint_result["content_type"] = resp.headers.get("Content-Type", "")
            endpoint_result["size"] = len(body)
            endpoint_result["snippet"] = body[:500]
            print(f"    Status: {resp.status}, Size: {len(body)} bytes")

            if resp.status == 200 and len(body) > 100:
                slug = url.split("/")[-1] or "root"
                save_result(f"07_rest_{slug}.txt", body[:5000])

        except urllib.error.HTTPError as e:
            endpoint_result["status"] = e.code
            try:
                body = e.read().decode("utf-8", errors="replace")
                endpoint_result["error_body"] = body[:500]
            except Exception:
                pass
            print(f"    HTTP {e.code}")
        except Exception as e:
            endpoint_result["error"] = str(e)
            print(f"    ERROR: {e}")

        results["endpoints"].append(endpoint_result)
        time.sleep(0.3)

    # Determine verdict
    successes = [
        e for e in results["endpoints"]
        if e.get("status") == 200 and e.get("size", 0) > 100
    ]
    if successes:
        results["verdict"] = f"REST API FOUND — {len(successes)} endpoints responsive"
    else:
        results["verdict"] = "REST API NOT AVAILABLE — all endpoints returned errors"

    save_json("07_rest_api_tests.json", results)
    return results


if __name__ == "__main__":
    main()
