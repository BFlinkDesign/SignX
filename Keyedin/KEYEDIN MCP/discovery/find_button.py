from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('http://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/LOGIN.START')
    page.wait_for_load_state('networkidle')
    
    html = page.content()
    
    # Find the Sign In button
    import re
    buttons = re.findall(r'<button[^>]*>.*?</button>|<input[^>]*type=["\'](?:submit|button)[^>]*>', html, re.DOTALL | re.I)
    
    print("=== FOUND BUTTONS ===")
    for btn in buttons:
        print(btn[:200])
        print("---")
    
    browser.close()