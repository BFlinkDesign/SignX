from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

print('=' * 80)
print('Simple Manual HAR Capture')
print('=' * 80)

options = Options()
options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

try:
    driver.get('https://eaglesign.keyedinsign.com/')
    
    print('\n LOGIN AND NAVIGATE NOW:')
    print('   1. Login manually')
    print('   2. Navigate to: Production  (BI) - Work Order Listing')
    print('   3. Wait for report to fully load')
    print('   4. Press Enter here when done')
    print()
    input('Press Enter after report loads...')
    
    print('\n Capturing network traffic...')
    
    logs = driver.get_log('performance')
    print(f'   Processing {len(logs)} log entries...')
    
    # Extract all requests
    all_requests = []
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
                        'method': req.get('method', ''),
                        'url': url,
                        'postData': req.get('postData', {}).get('text', None)
                    })
        except:
            pass
    
    # Filter Informer calls
    informer_calls = [r for r in all_requests if ':8443' in r['url'] 
                      and not any(ext in r['url'].lower() 
                      for ext in ['.js', '.css', '.png', '.jpg', '.gif', '.woff', '.ttf', '.svg'])]
    
    print(f'\n Captured {len(all_requests)} total requests')
    print(f' Found {len(informer_calls)} Informer API calls\n')
    
    # Show unique endpoints
    seen = set()
    for call in informer_calls:
        base = call['url'].split('?')[0]
        if base not in seen:
            seen.add(base)
            print(f'   {call["method"]:6s} {base}')
            if call.get('postData'):
                print(f'          POST: {call["postData"][:80]}...')
    
    # Save everything
    with open('keyedin_network.har', 'w') as f:
        json.dump({'log': {'entries': all_requests}}, f, indent=2)
    
    with open('informer_api_calls.json', 'w') as f:
        json.dump({'informer_calls': informer_calls, 'unique_endpoints': list(seen)}, f, indent=2)
    
    print(f'\n Saved:')
    print(f'   keyedin_network.har')
    print(f'   informer_api_calls.json')
    
    input('\nPress Enter to close...')

except Exception as e:
    print(f'\n Error: {e}')
    input('Press Enter to close...')

finally:
    driver.quit()
    print('\n Done!')
