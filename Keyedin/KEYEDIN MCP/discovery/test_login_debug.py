from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    page = browser.new_page()
    
    print("Going to login page...")
    page.goto('http://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/LOGIN.START')
    page.wait_for_load_state('networkidle')
    
    print("Current URL:", page.url)
    print("\nLooking for login form fields...")
    
    # Try to find and fill the form
    try:
        page.fill('input[name="USERNAME"]', 'BradyF')
        print("✓ Filled USERNAME")
    except Exception as e:
        print(f"✗ Could not fill USERNAME: {e}")
    
    try:
        page.fill('input[name="PASSWORD"]', '[REDACTED]')
        print("✓ Filled PASSWORD")
    except Exception as e:
        print(f"✗ Could not fill PASSWORD: {e}")
    
    input("Check the browser - are fields filled? Press Enter to click submit...")
    
    try:
        page.click('input[type="submit"]')
        print("✓ Clicked submit")
    except Exception as e:
        print(f"✗ Could not click submit: {e}")
    
    print("Waiting for navigation...")
    time.sleep(5)
    
    print("\nAfter login attempt:")
    print("Current URL:", page.url)
    print("\nDoes URL contain LOGIN?", "LOGIN" in page.url)
    
    input("Press Enter to close...")
    browser.close()