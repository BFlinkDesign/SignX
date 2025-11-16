#!/usr/bin/env python3
"""
KeyedIn Investigation Tool – v5 (Full Auto-Navigation & Mapping)
----------------------------------------------------------------
This version:
  1. Logs in automatically using provided credentials (`--user`/`--pass`).
  2. Navigates to each main section:
       • Job Cost
       • Report Administration
       • Estimating and Proposals
       • Sales Order Entry
  3. In each section, captures:
       • Link text and href mappings
       • Table headers (if present)
       • Input/select field names
  4. Builds a selector map (`navigation_map`) recording text, CSS selector, and URL (if link)
  5. Saves discovered mapping and field data to `keyedin_navigation_map.json` for reuse.
  6. Takes screenshots of each section.

Usage:
  python keyedin_investigator_v5.py --user myUser --pass myPass

Prerequisites:
  • Chrome launched with `--remote-debugging-port=9222`
  • Playwright installed and `playwright install`
"""
import asyncio
import json
import sys
import time
import shutil
import urllib.request
import urllib.error
from pathlib import Path
from argparse import ArgumentParser
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
REMOTE_PORT = 9222
CDP_URL = f"http://127.0.0.1:{REMOTE_PORT}"
LOGIN_URL = "https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/LOGIN.START"
OUTPUT_MAP = Path("keyedin_navigation_map.json")
SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

# ----------------------------------------------------------------------
# CLI Parsing
# ----------------------------------------------------------------------
def parse_args():
    p = ArgumentParser(description="KeyedIn Auto-Navigation & Mapping v5")
    p.add_argument("--user", required=True, help="KeyedIn username")
    p.add_argument("--pass", dest="password", required=True, help="KeyedIn password")
    return p.parse_args()

# ----------------------------------------------------------------------
# Helper to launch or reuse Chrome debugging
# ----------------------------------------------------------------------
def ensure_chrome_debugging():
    chrome = shutil.which("chrome.exe") or shutil.which("chrome")
    if not chrome:
        print("❌ chrome.exe not found in PATH.")
        sys.exit(1)
    try:
        urllib.request.urlopen(f"{CDP_URL}/json", timeout=2)
    except urllib.error.URLError:
        print("🔄 Launching Chrome with remote debugging…")
        profile = Path.home()/".keyedin_debug"
        profile.mkdir(exist_ok=True)
        subprocess.Popen([
            chrome,
            f"--remote-debugging-port={REMOTE_PORT}",
            f"--user-data-dir={str(profile)}",
            LOGIN_URL
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)

# ----------------------------------------------------------------------
# Main Investigator
# ----------------------------------------------------------------------
class KeyedInInvestigator:
    def __init__(self, page: Page):
        self.page = page
        # navigation_map will store per-section link and selector data
        self.navigation_map = {
            'timestamp': datetime.now().isoformat(),
            'credentials': False,
            'sections': {}
        }

    async def login(self, user: str, password: str):
        await self.page.goto(LOGIN_URL)
        await self.page.fill('input[name="Username"]', user)
        await self.page.fill('input[name="Password"]', password)
        await self.page.click('input[type=submit], button:has-text("Sign In")')
        await self.page.wait_for_selector('a:has-text("Job Cost")', timeout=60000)
        self.navigation_map['credentials'] = True
        print("✅ Logged in successfully.")

    async def map_section(self, section_name: str):
        print(f"\n🔍 Mapping section: {section_name}")
        # Click section link
        await self.page.click(f'a:has-text("{section_name}")')
        await self.page.wait_for_timeout(2000)
        # Gather all links
        links = await self.page.query_selector_all('a')
        link_data = []
        for a in links:
            txt = (await a.text_content() or "").strip()
            if not txt: continue
            href = await a.get_attribute('href')
            selector = await a.evaluate("el => el.tagName + (el.id?('#'+el.id):el.className?'.'+el.className.split(' ').join('.'):'')")
            link_data.append({'text': txt, 'href': href, 'selector': selector})
        # Gather headers
        headers = await self.page.locator('th').all_inner_texts()
        headers = [h.strip() for h in headers if h.strip()]
        # Gather input/select fields
        fields = await self.page.eval_on_selector_all(
            'input[type=text], input[type=number], select',
            'els=>els.map(el=>el.name||el.id).filter(Boolean)'
        )
        # Screenshot
        path = SCREENSHOT_DIR / f"{section_name.lower().replace(' ','_')}.png"
        await self.page.screenshot(path=path)
        self.navigation_map['sections'][section_name] = {
            'links': link_data,
            'headers': headers,
            'fields': fields,
            'screenshot': str(path)
        }
        print(f"  • {len(link_data)} links, {len(headers)} headers, {len(fields)} fields recorded.")

    async def run(self, user: str, password: str):
        # 1. Login
        await self.login(user, password)
        # 2. Sections to map
        for sec in ["Job Cost", "Report Administration", "Estimating and Proposals", "Sales Order Entry"]:
            await self.map_section(sec)
        # 3. Save map
        OUTPUT_MAP.write_text(json.dumps(self.navigation_map, indent=2))
        print(f"\n✅ Navigation map saved to {OUTPUT_MAP.resolve()}")

# ----------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------
async def main():
    args = parse_args()
    ensure_chrome_debugging()
    pw = await async_playwright().start()
    browser: Browser = await pw.chromium.connect_over_cdp(CDP_URL)
    # find the KeyedIn page
    page = None
    for ctx in browser.contexts:
        for p in ctx.pages:
            if LOGIN_URL.split('/cgi')[0] in p.url:
                page = p
                break
        if page: break
    if not page:
        page = await browser.new_page()
    inv = KeyedInInvestigator(page)
    await inv.run(args.user, args.password)
    await browser.close()
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
