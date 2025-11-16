#!/usr/bin/env python3
"""
KeyedIn Manual Login + Automatic Mapping
-----------------------------------------
This approach:
1. Opens Chrome and navigates to login page
2. Waits for YOU to manually log in
3. Then automatically maps all sections

More reliable than auto-login when dealing with:
- Complex login flows
- Multi-factor authentication
- License agreements
- Session timeouts
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime
import requests
from playwright.async_api import async_playwright

REMOTE_PORT = 9222
CDP_URL = f"http://127.0.0.1:{REMOTE_PORT}"
LOGIN_URL = "https://eaglesign.keyedinsign.com"
OUTPUT_FILE = Path("keyedin_sections_mapped.json")
SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


async def wait_for_manual_login(page):
    """Wait for user to manually log in."""
    print("\n" + "="*60)
    print("🔐 MANUAL LOGIN REQUIRED")
    print("="*60)
    print("1. Log into KeyedIn in the Chrome window")
    print("2. Navigate past any license screens")  
    print("3. When you see the MAIN MENU, press Enter here")
    print("="*60)
    
    input("\nPress Enter when ready >>> ")
    
    # Verify we're logged in
    try:
        await page.wait_for_selector('a:has-text("Job Cost"), a:has-text("Estimating")', timeout=5000)
        print("✅ Login confirmed!")
        return True
    except:
        print("❌ Main menu not detected. Please ensure you're logged in.")
        return False


async def map_all_sections(page):
    """Map all available sections."""
    results = {
        'timestamp': datetime.now().isoformat(),
        'sections': {},
        'main_menu_links': []
    }
    
    # First, capture all main menu links
    print("\n📋 Capturing main menu structure...")
    all_links = await page.locator('a').all()
    
    for link in all_links:
        try:
            text = (await link.text_content() or "").strip()
            href = await link.get_attribute('href') or ""
            if text and len(text) < 50:  # Avoid very long text
                results['main_menu_links'].append({
                    'text': text,
                    'href': href
                })
        except:
            continue
    
    print(f"  • Found {len(results['main_menu_links'])} menu items")
    
    # Map specific sections
    target_sections = [
        "Job Cost",
        "Estimating",
        "Sales Order", 
        "Report Administration",
        "Inventory",
        "Purchasing"
    ]
    
    for section_name in target_sections:
        print(f"\n🔍 Mapping {section_name}...")
        
        # Find best match for section
        section_link = None
        for link_data in results['main_menu_links']:
            if section_name.lower() in link_data['text'].lower():
                section_link = link_data['text']
                break
        
        if not section_link:
            print(f"  ⚠️ {section_name} not found in menu")
            continue
            
        try:
            # Click the section
            await page.click(f'a:has-text("{section_link}")')
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            
            # Gather data
            section_data = {
                'subsections': [],
                'fields': [],
                'tables': []
            }
            
            # Get subsection links
            sub_links = await page.locator('a').all()
            for link in sub_links[:50]:
                try:
                    text = (await link.text_content() or "").strip()
                    if text and text != section_link:
                        section_data['subsections'].append(text)
                except:
                    continue
            
            # Get form fields
            fields = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('input, select, textarea'))
                    .map(el => ({
                        type: el.type || el.tagName,
                        name: el.name || el.id || 'unnamed',
                        label: el.placeholder || el.getAttribute('aria-label') || ''
                    }))
                    .filter(f => f.name !== 'unnamed');
            }''')
            section_data['fields'] = fields[:30]
            
            # Screenshot
            screenshot_path = SCREENSHOT_DIR / f"{section_name.lower().replace(' ', '_')}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            
            results['sections'][section_name] = section_data
            print(f"  ✓ Mapped: {len(section_data['subsections'])} subsections, {len(section_data['fields'])} fields")
            
            # Go back to main menu
            if await page.locator('a:has-text("Main Menu"), a:has-text("Home")').count() > 0:
                await page.click('a:has-text("Main Menu"), a:has-text("Home")')
                await page.wait_for_timeout(2000)
            
        except Exception as e:
            print(f"  ❌ Error mapping {section_name}: {str(e)[:50]}")
            results['sections'][section_name] = {'error': str(e)}
    
    return results


async def main():
    # Get CDP endpoint
    try:
        resp = requests.get(f"{CDP_URL}/json/version")
        cdp_ws = resp.json().get('webSocketDebuggerUrl', CDP_URL)
    except:
        cdp_ws = CDP_URL
        
    print(f"🔌 Connecting to Chrome at {cdp_ws}")
    
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(cdp_ws)
        
        # Find or create page
        page = None
        for context in browser.contexts:
            if context.pages:
                page = context.pages[0]
                break
                
        if not page:
            page = await browser.new_page()
            await page.goto(LOGIN_URL)
        
        # Wait for manual login
        if await wait_for_manual_login(page):
            # Map sections
            results = await map_all_sections(page)
            
            # Save results
            OUTPUT_FILE.write_text(json.dumps(results, indent=2))
            print(f"\n✅ Results saved to {OUTPUT_FILE}")
            print(f"\n📊 Summary:")
            print(f"  • Main menu items: {len(results['main_menu_links'])}")
            print(f"  • Sections mapped: {len(results['sections'])}")
            print(f"  • Screenshots saved in: {SCREENSHOT_DIR}")
        
        # Keep browser open
        print("\n💡 Browser left open for further exploration")


if __name__ == "__main__":
    # First ensure Chrome is running
    import subprocess
    import shutil
    import time
    
    chrome = shutil.which("chrome.exe") or shutil.which("chrome")
    if chrome:
        try:
            requests.get(f"{CDP_URL}/json", timeout=1)
        except:
            print("🚀 Launching Chrome with debugging...")
            subprocess.Popen([
                chrome,
                f"--remote-debugging-port={REMOTE_PORT}",
                "--new-window",
                LOGIN_URL
            ])
            time.sleep(5)
    
    asyncio.run(main())
