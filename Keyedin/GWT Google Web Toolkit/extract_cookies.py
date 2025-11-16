"""
KeyedIn Session Cookie Extractor
=================================
Opens Chrome, lets you log in manually, then extracts session cookies.

Usage:
    python extract_cookies.py
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import sys

def extract_cookies():
    """Open browser, wait for manual login, extract cookies"""
    
    print("=" * 80)
    print("KEYEDIN SESSION COOKIE EXTRACTOR")
    print("=" * 80)
    print()
    
    # Setup Chrome
    options = Options()
    # Run visible so user can log in
    # options.add_argument('--headless')  # Disabled for manual login
    
    print("🌐 Opening Chrome browser...")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    try:
        # Navigate to KeyedIn login
        keyedin_url = "https://eaglesign.keyedinsign.com:8443/eaglesign/"
        print(f"📍 Navigating to: {keyedin_url}")
        driver.get(keyedin_url)
        
        print()
        print("=" * 80)
        print("🔐 PLEASE LOG IN TO KEYEDIN IN THE BROWSER WINDOW")
        print("=" * 80)
        print()
        print("Instructions:")
        print("  1. Complete the login process in the browser")
        print("  2. Wait until you see the KeyedIn dashboard")
        print("  3. Then come back here and press Enter")
        print()
        
        input("Press Enter after you've successfully logged in...")
        
        # Give it a moment to settle
        time.sleep(2)
        
        # Extract cookies
        print("\n🍪 Extracting session cookies...")
        cookies = driver.get_cookies()
        
        if not cookies:
            print("✗ No cookies found! Login may have failed.")
            sys.exit(1)
        
        # Save cookies to file
        output_file = "session_cookies.json"
        with open(output_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        
        print(f"✓ Saved {len(cookies)} cookies to {output_file}")
        print()
        print("Cookie names:")
        for cookie in cookies:
            print(f"  - {cookie['name']}")
        
        print()
        print("=" * 80)
        print("✓ SESSION COOKIES EXTRACTED SUCCESSFULLY")
        print("=" * 80)
        print()
        print(f"Next step: python keyedin_complete_extraction.py --session-file {output_file}")
        
    finally:
        print("\n🔒 Closing browser...")
        driver.quit()


if __name__ == "__main__":
    extract_cookies()
