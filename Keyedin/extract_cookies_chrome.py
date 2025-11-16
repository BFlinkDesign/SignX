from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import sys

print('=' * 80)
print('KeyedIn Session - Chrome with DevTools')
print('=' * 80)

options = Options()
# Uncomment to see more details:
# options.add_argument('--auto-open-devtools-for-tabs')

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

try:
    driver.get('https://eaglesign.keyedinsign.com/')
    
    print('\n Please LOGIN MANUALLY in Chrome')
    print('   Username: BradyF')
    print('   Password: [REDACTED]')
    print()
    print(' TIP: Press F12 to open Chrome DevTools')
    print('   - Go to Network tab to see all requests')
    print('   - Go to Application  Cookies to see session data')
    print()
    print('After logging in successfully, come back here and press Enter...')
    
    sys.stdin.readline()
    
    # Extract cookies
    cookies = driver.get_cookies()
    
    print(f'\n Extracted {len(cookies)} cookies:')
    for cookie in cookies:
        value = cookie['value'][:40] if len(cookie['value']) > 40 else cookie['value']
        print(f'   {cookie["name"]:30s} = {value}')
    
    # Save cookies
    with open('keyedin_chrome_session.json', 'w') as f:
        json.dump(cookies, f, indent=2)
    
    print(f'\n Saved to: keyedin_chrome_session.json')
    print(f' Current URL: {driver.current_url}')
    
    # Save page
    with open('chrome_logged_in.html', 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print(f' Saved page: chrome_logged_in.html')
    
    print('\n Success! Press Enter to close Chrome...')
    sys.stdin.readline()

except Exception as e:
    print(f'\n Error: {e}')
    import traceback
    traceback.print_exc()

finally:
    driver.quit()
    print('\n Chrome closed')
