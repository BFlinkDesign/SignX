from playwright.sync_api import sync_playwright 
import getpass 
import time 
 
print("KeyedIn Automation") 
print("=" * 40) 
username = input("Enter username: ") 
password = getpass.getpass("Enter password: ") 
 
with sync_playwright() as p: 
    browser = p.chromium.launch(headless=False) 
    page = browser.new_page() 
    print("Opening KeyedIn...") 
    page.goto("https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/LOGIN.START") 
    page.wait_for_load_state("networkidle") 
    time.sleep(2) 
    print("Attempting login...") 
    try: 
        page.fill('input[type="text"]', username) 
        page.fill('input[type="password"]', password) 
        page.click('input[type="submit"]') 
        print("Login submitted!") 
    except Exception as e: 
        print(f"Error: {e}") 
    input("\nPress Enter to close browser...") 
    browser.close() 
