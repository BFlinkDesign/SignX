from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import os
from pathlib import Path

print('=' * 80)
print('Automated HAR Capture for KeyedIn Informer')
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

# Setup Chrome with performance logging
options = Options()
options.set_capability('goog:loggingPrefs', {'performance': 'ALL', 'browser': 'ALL'})
options.add_argument('--disable-blink-features=AutomationControlled')

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

all_requests = []

try:
    print('\n Step 1: Auto-login...')
    driver.get('https://eaglesign.keyedinsign.com/')
    time.sleep(2)
    
    # Login
    username_field = driver.find_element(By.ID, 'USERNAME')
    password_field = driver.find_element(By.ID, 'PASSWORD')
    username_field.send_keys(username)
    password_field.send_keys(password)
    password_field.send_keys(Keys.RETURN)
    
    time.sleep(5)
    print(f'   Current URL: {driver.current_url}')
    
    # Try to click on Production menu if we can find it
    print('\n Step 2: Attempting to navigate to Work Order report...')
    
    # Look for Production link or Work Order link
    try:
        # Give it a moment for page to load
        time.sleep(3)
        
        # Try to find menu items
        links = driver.find_elements(By.TAG_NAME, 'a')
        print(f'   Found {len(links)} links on page')
        
        # Look for Production or Work Order links
        for link in links:
            text = link.text.strip().lower()
            if 'production' in text or 'work order' in text:
                print(f'   Found menu item: {link.text}')
                try:
                    link.click()
                    time.sleep(2)
                    break
                except:
                    pass
    except Exception as e:
        print(f'   Could not auto-navigate: {e}')
    
    print('\n PLEASE MANUALLY NAVIGATE TO:')
    print('   Production  (BI) - Work Order Listing')
    print('   (Or any other work order report)')
    print()
    print(' Waiting 30 seconds for you to navigate...')
    print('   (Script will continue capturing in background)')
    
    time.sleep(30)
    
    print('\n Step 3: Capturing all network traffic...')
    
    # Get performance logs
    logs = driver.get_log('performance')
    
    print(f'   Processing {len(logs)} log entries...')
    
    # Parse all network requests
    for log in logs:
        try:
            message = json.loads(log['message'])
            log_method = message.get('message', {}).get('method', '')
            
            # Capture both requests and responses
            if 'Network.request' in log_method or 'Network.response' in log_method:
                params = message.get('message', {}).get('params', {})
                
                if 'request' in params:
                    req = params['request']
                    url = req.get('url', '')
                    
                    if 'eaglesign.keyedinsign.com' in url:
                        all_requests.append({
                            'timestamp': log.get('timestamp', 0),
                            'method': req.get('method', ''),
                            'url': url,
                            'headers': req.get('headers', {}),
                            'postData': req.get('postData', {}).get('text', None)
                        })
        except:
            pass
    
    print(f'    Captured {len(all_requests)} requests')
    
    # Filter for Informer API calls
    informer_calls = []
    for req in all_requests:
        url = req['url']
        if ':8443' in url and not any(ext in url.lower() 
           for ext in ['.js', '.css', '.png', '.jpg', '.gif', '.woff', '.ttf', '.svg']):
            informer_calls.append(req)
    
    print(f'    Found {len(informer_calls)} Informer API calls')
    
    # Show unique endpoints
    print('\n Unique Informer Endpoints:\n')
    seen_urls = set()
    for call in informer_calls:
        url_base = call['url'].split('?')[0]
        if url_base not in seen_urls:
            seen_urls.add(url_base)
            print(f'   {call["method"]:6s} {url_base}')
            if call.get('postData'):
                print(f'          POST: {call["postData"][:100]}...')
    
    # Save HAR-like format
    har_data = {
        'log': {
            'version': '1.2',
            'creator': {'name': 'KeyedIn Scraper', 'version': '1.0'},
            'entries': []
        }
    }
    
    for req in all_requests:
        entry = {
            'request': {
                'method': req['method'],
                'url': req['url'],
                'headers': [{'name': k, 'value': v} for k, v in req.get('headers', {}).items()],
                'postData': {'text': req.get('postData')} if req.get('postData') else None
            },
            'response': {'status': 0}  # We don't capture responses in this version
        }
        har_data['log']['entries'].append(entry)
    
    # Save HAR file
    with open('keyedin_network.har', 'w') as f:
        json.dump(har_data, f, indent=2)
    
    print(f'\n Saved HAR file: keyedin_network.har')
    
    # Save filtered API calls
    with open('informer_api_calls_extracted.json', 'w') as f:
        json.dump({
            'total_requests': len(all_requests),
            'informer_calls': informer_calls,
            'unique_endpoints': list(seen_urls)
        }, f, indent=2)
    
    print(f' Saved API calls: informer_api_calls_extracted.json')
    
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

print('\n' + '=' * 80)
print('Next: Run parse_har.py to analyze the captured traffic!')
print('=' * 80)
