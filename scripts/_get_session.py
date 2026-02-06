"""Get fresh Informer session credentials via Playwright browser automation.

Uses headless Chromium to:
  1. Login to KeyedIn ERP
  2. Find and follow SSO to Informer
  3. Extract auth tokens via getActiveSession RPC
  4. Save to informer_session.json
"""

import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ENV_FILE = Path(r"C:\Scripts\keyedin-capture\.env")
SESSION_FILE = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\informer_session.json")

INFORMER_BASE = "https://eaglesign.keyedinsign.com:8443"
MODULE_BASE = f"{INFORMER_BASE}/eaglesign/informer/"
GWT_PERMUTATION = "6823F3E0DFFF554BC1A7951AA98B182D"
AUTH_POLICY = "51B059033C002274BD4151F7D17FC702"


def main():
    load_dotenv(ENV_FILE)
    username = os.environ.get("KEYEDIN_USERNAME")
    password = os.environ.get("KEYEDIN_PASSWORD")

    if not username or not password:
        print("ERROR: Missing KEYEDIN_USERNAME or KEYEDIN_PASSWORD in .env")
        return

    print(f"Username: {username}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--ignore-certificate-errors"])
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        # Capture any requests to 8443 (SSO URLs)
        sso_urls = []

        def on_request(request):
            if "8443" in request.url:
                sso_urls.append(request.url)

        page.on("request", on_request)

        # Step 1: Load ERP login page
        print("\n1. Loading ERP login page...")
        page.goto("http://eaglesign.keyedinsign.com/", timeout=30000)
        page.wait_for_load_state("networkidle")
        print(f"   URL: {page.url}")

        # Step 2: Fill credentials and submit
        print("2. Logging in...")
        page.fill("input[name=USERNAME]", username)
        page.fill("input[name=PASSWORD]", password)

        # The button is type=button so we need to use JS click or find the submit handler
        # Try clicking the button and wait for navigation
        page.click("input[name=btnLogin]")
        time.sleep(3)  # Wait for any JS redirects
        page.wait_for_load_state("networkidle", timeout=30000)
        print(f"   URL after login: {page.url}")

        # Check if we're on the main app
        title = page.title()
        print(f"   Title: {title}")

        # Step 3: Look for Informer/SSO in the loaded page
        print("3. Looking for Informer SSO link...")

        # Try to find SSO link in the page
        sso_link = page.evaluate(
            """() => {
            const links = document.querySelectorAll('a');
            for (const a of links) {
                const href = a.href || '';
                if (href.includes('8443') || href.toLowerCase().includes('informer')
                    || href.toLowerCase().includes('sso')) {
                    return href;
                }
            }
            // Check for SSO in iframes
            const frames = document.querySelectorAll('iframe');
            for (const f of frames) {
                const src = f.src || '';
                if (src.includes('8443') || src.toLowerCase().includes('informer')) {
                    return src;
                }
            }
            return null;
        }"""
        )

        if sso_link:
            print(f"   Found SSO link: {sso_link[:80]}")
        else:
            print("   No SSO link in current page.")
            # Try clicking on BI Reports / Informer menu items
            menu_items = page.evaluate(
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
                            onclick: el.getAttribute('onclick') || null
                        });
                    }
                }
                return items.slice(0, 10);
            }"""
            )
            print(f"   Menu items with 'reports/informer': {json.dumps(menu_items, indent=4)}")

            # Try clicking on report-related items
            for item in menu_items:
                if item.get("onclick") or item.get("href"):
                    text = item["text"]
                    print(f"   Clicking: '{text}'")
                    try:
                        page.click(f"text='{text}'", timeout=5000)
                        time.sleep(2)
                        page.wait_for_load_state("networkidle", timeout=10000)
                        print(f"   URL: {page.url}")
                    except Exception as e:
                        print(f"   Click failed: {e}")

        # Check if we captured any 8443 URLs
        if sso_urls:
            print(f"\n   Captured 8443 URLs: {sso_urls[:5]}")

        # Step 4: Navigate to Informer via the discovered SSO link
        actual_sso = sso_link
        if not actual_sso:
            # Fall back to any captured 8443 URL with sso
            for u in sso_urls:
                if "sso" in u.lower():
                    actual_sso = u
                    break

        if actual_sso:
            print(f"\n4. Following SSO link: {actual_sso[:80]}...")
            page.goto(actual_sso, timeout=30000, wait_until="networkidle")
            print(f"   URL after SSO: {page.url}")
        else:
            print("\n4. No SSO link found. Trying direct Informer URL...")
            page.goto(
                f"{INFORMER_BASE}/eaglesign/sso", timeout=30000, wait_until="networkidle"
            )
            print(f"   URL: {page.url}")

        # Step 5: Wait for Informer to load and check for auth
        time.sleep(2)
        print(f"\n5. Current URL: {page.url}")

        # Get cookies
        cookies = context.cookies()
        jsessionid = None
        for c in cookies:
            if c["name"] == "JSESSIONID":
                jsessionid = c["value"]
                print(f"   JSESSIONID: {jsessionid}")

        if not jsessionid:
            print("   ERROR: No JSESSIONID found")
            browser.close()
            return

        # Step 6: Call getActiveSession via fetch
        print("\n6. Calling getActiveSession...")
        payload = (
            f"7|0|5|{MODULE_BASE}|{AUTH_POLICY}|"
            "com.entrinsik.informer.core.client.service.AuthenticationRPCService|"
            "getActiveSession|Z|1|2|3|4|1|5|1|"
        )

        resp_text = page.evaluate(
            """async (payload) => {
            try {
                const resp = await fetch('/eaglesign/informer/rpc/AuthenticationRPCService', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'text/x-gwt-rpc; charset=UTF-8',
                        'X-GWT-Permutation': '"""
            + GWT_PERMUTATION
            + """',
                        'X-GWT-Module-Base': '"""
            + MODULE_BASE
            + """'
                    },
                    body: payload
                });
                return await resp.text();
            } catch(e) {
                return 'FETCH_ERROR: ' + e.message;
            }
        }""",
            payload,
        )

        print(f"   Response: {resp_text[:300]}")

        if resp_text.startswith("//OK"):
            uuids = re.findall(
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                resp_text,
            )
            if len(uuids) >= 2:
                auth_token = uuids[0]
                client_id = uuids[1]
                print(f"   auth_token: {auth_token}")
                print(f"   client_id : {client_id}")

                session_data = {
                    "jsessionid": jsessionid,
                    "auth_token": auth_token,
                    "client_id": client_id,
                }
                SESSION_FILE.write_text(
                    json.dumps(session_data, indent=2), encoding="utf-8"
                )
                print(f"\n   SESSION SAVED to {SESSION_FILE}")
            else:
                print(f"   Only {len(uuids)} UUIDs found: {uuids}")
        else:
            print("   getActiveSession failed -- session not authenticated")
            print("   The SSO did not properly authenticate.")
            print()
            print("   Manual fallback: Open Chrome, login to KeyedIn ERP,")
            print("   navigate to Informer, then from DevTools console run:")
            print("   document.cookie")
            print("   And from any network request URL, copy authToken and clientId")

        # Take a screenshot for debugging
        page.screenshot(path=str(Path(r"C:\Scripts\signx-warehouse\warehouse\raw\informer_login_debug.png")))
        print("\n   Debug screenshot saved.")

        browser.close()


if __name__ == "__main__":
    main()
