from selenium import webdriver
from selenium.webdriver.edge.options import Options
import time
import json
import sys

print('Manual Login  Cookie Extraction')
print('=' * 80)

options = Options()
driver = webdriver.Edge(options=options)

try:
    driver.get('https://eaglesign.keyedinsign.com/')
    
    print('\n Please LOGIN MANUALLY in the browser window')
    print('   Username: BradyF')
    print('   Password: (use KEYEDIN_PASSWORD env var)')
    print()
    print('After logging in, come back here and press Enter...')
    
    # Wait for manual input
    sys.stdin.readline()
    
    # Extract cookies
    cookies = driver.get_cookies()
    
    print(f'\n Extracted {len(cookies)} cookies:')
    for cookie in cookies:
        value_preview = cookie['value'][:30] if len(cookie['value']) > 30 else cookie['value']
        print(f'   {cookie["name"]:30s} = {value_preview}...')
    
    # Save cookies
    with open('keyedin_session.json', 'w') as f:
        json.dump(cookies, f, indent=2)
    
    print(f'\n Saved cookies to: keyedin_session.json')
    
    # Get current URL to confirm login
    print(f'\n Current URL: {driver.current_url}')
    
    # Save the logged-in page
    with open('logged_in_page.html', 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print(' Saved page source to: logged_in_page.html')
    
    print('\n Success! Now we can use these cookies for API requests.')
    print('\nPress Enter to close browser...')
    sys.stdin.readline()

except Exception as e:
    print(f'\n Error: {e}')
    import traceback
    traceback.print_exc()

finally:
    driver.quit()
    print('\n Browser closed')
