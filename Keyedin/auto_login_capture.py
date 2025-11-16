from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import sys
import json
import os
from pathlib import Path

print('=' * 80)
print('Auto-Login + Manual Navigation + API Capture')
print('=' * 80)

# Load credentials
env_file = Path(__file__).parent / '.env.keyedin'
with open(env_file) as f:
    for line in f:
        if line.strip() and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k] = v.strip()

username = os.getenv('KEYEDIN_USERNAME')
password = os.getenv('KEYEDIN_PASSWORD')

options = Options()
options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

try:
    print('\n Auto-logging in...')
    driver.get('https://eaglesign.keyedinsign.com/')
    time.sleep(2)
    
    # Fill credentials
    username_field = driver.find_element(By.ID, 'USERNAME')
    password_field = driver.find_element(By.ID, 'PASSWORD')
    
    username_field.send_keys(username)
    password_field.send_keys(password)
    
    # Press Enter to login
    password_field.send_keys(Keys.RETURN)
    
    print('   Logging in...')
    time.sleep(5)
    
    print(f'   Current URL: {driver.current_url}')
    
    if 'LOGIN.START' not in driver.current_url:
        print('    Login successful!')
    else:
        print('     Still on login page, but continuing...')
    
    print('\n NOW YOU NAVIGATE:')
    print('   1. Go to: Production  (BI) - Work Order Listing')
    print('   2. Wait for the report to FULLY load')
    print('   3. Come back here and press Enter')
    print()
    input('After report loads, press Enter to capture traffic...')
    
    print('\n Waiting 2 seconds for final requests...')
    time.sleep(2)
    
    print('\n Capturing network traffic...')
    
    current_url = driver.current_url
    print(f'   Final URL: {current_url}')
    
    logs = driver.get_log('performance')
    print(f'   Processing {len(logs)} log entries...')
    
    # Capture all Informer/eaglesign requests
    all_requests = []
    api_calls = []
    
    for log in logs:
        try:
            message = json.loads(log['message'])
            method = message.get('message', {}).get('method', '')
            
            if 'Network.request' in method:
                params = message.get('message', {}).get('params', {})
                req = params.get('request', {})
                url = req.get('url', '')
                
                if 'eaglesign.keyedinsign.com' in url:
                    all_requests.append({
                        'url': url,
                        'method': req.get('method', ''),
                        'postData': req.get('postData', None)
                    })
                    
                    # Potential data APIs (not static resources)
                    if ':8443' in url and not any(ext in url.lower() 
                       for ext in ['.js', '.css', '.png', '.jpg', '.gif', '.woff', '.ttf']):
                        api_calls.append({
                            'url': url,
                            'method': req.get('method', ''),
                            'postData': req.get('postData', None)
                        })
        except:
            pass
    
    print(f'\n Captured {len(all_requests)} requests ({len(api_calls)} potential APIs)')
    
    # Show unique API URLs
    print(f'\n API Endpoints Found:')
    seen = set()
    for call in api_calls:
        url_base = call['url'].split('?')[0]
        if url_base not in seen:
            seen.add(url_base)
            method = call['method']
            print(f'   {method:6s} {url_base}')
            if call.get('postData'):
                print(f'          POST: {call["postData"][:80]}...')
    
    # Save everything
    with open('captured_all_requests.json', 'w') as f:
        json.dump(all_requests, f, indent=2)
    
    with open('captured_api_calls.json', 'w') as f:
        json.dump(api_calls, f, indent=2)
    
    print(f'\n Saved to:')
    print(f'   captured_all_requests.json ({len(all_requests)} requests)')
    print(f'   captured_api_calls.json ({len(api_calls)} APIs)')
    
    print('\n Done! Press Enter to close browser...')
    input()

except Exception as e:
    print(f'\n Error: {e}')
    import traceback
    traceback.print_exc()
    input('Press Enter to close...')

finally:
    try:
        driver.quit()
    except:
        pass
    print('\n Browser closed')
