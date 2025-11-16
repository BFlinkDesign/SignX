from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import sys
import json

print('=' * 80)
print('Capturing Informer Portal Network Traffic')
print('=' * 80)

options = Options()
options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

try:
    # Go to main KeyedIn, login, then navigate to Informer
    driver.get('https://eaglesign.keyedinsign.com/')
    
    print('\n LOGIN MANUALLY')
    print('   Then click on any WORK ORDER REPORT')
    print('   (e.g., Production > Work Order Listing)')
    print()
    print('After the report loads, press Enter here to capture traffic...')
    
    sys.stdin.readline()
    
    print('\n Extracting Informer API calls...')
    
    logs = driver.get_log('performance')
    
    # Parse for Informer API calls
    api_calls = []
    
    for log in logs:
        try:
            message = json.loads(log['message'])
            method = message.get('message', {}).get('method', '')
            
            if 'Network.request' in method:
                params = message.get('message', {}).get('params', {})
                req = params.get('request', {})
                url = req.get('url', '')
                
                # Filter for Informer API calls
                if 'eaglesign.keyedinsign.com:8443' in url and any(kw in url.lower() 
                   for kw in ['api', 'data', 'report', 'query', 'datasource', 'informer']):
                    api_calls.append({
                        'url': url,
                        'method': req.get('method', ''),
                        'postData': req.get('postData', None)
                    })
        except:
            pass
    
    # Deduplicate
    unique_apis = {}
    for call in api_calls:
        url = call['url']
        if url not in unique_apis:
            unique_apis[url] = call
    
    print(f'\n Found {len(unique_apis)} unique Informer API calls:\n')
    
    for url, call in unique_apis.items():
        print(f' {call["method"]:6s} {url}')
        if call['postData']:
            print(f'   POST data: {call["postData"][:100]}')
    
    # Save to file
    with open('informer_api_calls.json', 'w') as f:
        json.dump(list(unique_apis.values()), f, indent=2)
    
    print(f'\n Saved to: informer_api_calls.json')
    
    # Get current page source
    with open('informer_report_page.html', 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print(f' Saved page: informer_report_page.html')
    
    print('\nPress Enter to close...')
    sys.stdin.readline()

except Exception as e:
    print(f'\n Error: {e}')
    import traceback
    traceback.print_exc()

finally:
    driver.quit()
    print('\n Done')
