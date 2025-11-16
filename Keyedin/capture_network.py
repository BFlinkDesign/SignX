from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import sys
import json

print('=' * 80)
print('Auto-Capture KeyedIn Network Traffic')
print('=' * 80)

options = Options()
# Enable DevTools Protocol
options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

# Store captured requests
captured_requests = []

try:
    driver.get('https://eaglesign.keyedinsign.com/')
    
    print('\n LOGIN MANUALLY in Chrome')
    print('   Then navigate around (Work Orders, Reports, etc.)')
    print('   All network traffic is being captured automatically!')
    print()
    print('When done exploring, press Enter to save captured traffic...')
    
    sys.stdin.readline()
    
    print('\n Extracting network traffic from DevTools...')
    
    # Get performance logs (contains all network requests)
    logs = driver.get_log('performance')
    
    print(f'   Found {len(logs)} log entries')
    
    # Parse network requests
    for log in logs:
        try:
            message = json.loads(log['message'])
            method = message.get('message', {}).get('method', '')
            
            # Filter for network requests
            if 'Network.request' in method or 'Network.response' in method:
                params = message.get('message', {}).get('params', {})
                
                if 'request' in params:
                    req = params['request']
                    url = req.get('url', '')
                    method_type = req.get('method', '')
                    
                    # Only capture KeyedIn URLs
                    if 'eaglesign.keyedinsign.com' in url or 'keyedin' in url.lower():
                        captured_requests.append({
                            'url': url,
                            'method': method_type,
                            'headers': req.get('headers', {}),
                            'postData': req.get('postData', None)
                        })
        except:
            pass
    
    # Deduplicate by URL
    unique_urls = {}
    for req in captured_requests:
        url = req['url']
        if url not in unique_urls:
            unique_urls[url] = req
    
    print(f'\n Captured {len(unique_urls)} unique KeyedIn requests:\n')
    
    # Categorize requests
    api_requests = []
    data_requests = []
    other_requests = []
    
    for url, req in unique_urls.items():
        # Skip static resources
        if any(ext in url.lower() for ext in ['.css', '.js', '.png', '.jpg', '.gif', '.ico']):
            continue
        
        method = req['method']
        
        # Highlight important endpoints
        if any(kw in url.lower() for kw in ['api', 'data', 'json', 'informer', 'report', 'work', 'order']):
            api_requests.append((method, url))
            print(f' {method:6s} {url}')
        elif 'cgi-bin' in url:
            data_requests.append((method, url))
            print(f' {method:6s} {url}')
        else:
            other_requests.append((method, url))
            print(f'   {method:6s} {url}')
    
    # Save all captured traffic
    output = {
        'total_requests': len(unique_urls),
        'api_requests': [{'method': m, 'url': u} for m, u in api_requests],
        'data_requests': [{'method': m, 'url': u} for m, u in data_requests],
        'other_requests': [{'method': m, 'url': u} for m, u in other_requests],
        'all_requests': list(unique_urls.values())
    }
    
    with open('keyedin_network_capture.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f'\n Saved all traffic to: keyedin_network_capture.json')
    
    print('\n Summary:')
    print(f'   API/Data endpoints: {len(api_requests)}')
    print(f'   CGI endpoints: {len(data_requests)}')
    print(f'   Other requests: {len(other_requests)}')
    
    if api_requests:
        print('\n Key endpoints to investigate:')
        for method, url in api_requests[:10]:
            print(f'   {method} {url}')
    
    print('\nPress Enter to close Chrome...')
    sys.stdin.readline()

except Exception as e:
    print(f'\n Error: {e}')
    import traceback
    traceback.print_exc()

finally:
    driver.quit()
    print('\n Chrome closed')
