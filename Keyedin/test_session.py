import json
import requests
from pathlib import Path

print('=' * 80)
print('Testing KeyedIn Session with Extracted Cookies')
print('=' * 80)

# Load the cookies
with open('keyedin_session.json', 'r') as f:
    cookies_list = json.load(f)

# Convert to requests-compatible format
session = requests.Session()
for cookie in cookies_list:
    session.cookies.set(
        name=cookie['name'],
        value=cookie['value'],
        domain=cookie.get('domain', ''),
        path=cookie.get('path', '/')
    )

print(f'\n Loaded {len(cookies_list)} cookies into session')

# Try accessing a protected page
base_url = 'https://eaglesign.keyedinsign.com'

# Test URLs to try
test_urls = [
    '/cgi-bin/mvi.exe/WORKORDER.LIST',
    '/cgi-bin/mvi.exe/SERVICE.CALL.LIST',
    '/cgi-bin/mvi.exe/MAIN',
    '/cgi-bin/mvi.exe/MENU',
]

print('\n Testing access to KeyedIn pages...\n')

for path in test_urls:
    url = f'{base_url}{path}'
    print(f'Testing: {path}')
    
    try:
        r = session.get(url, timeout=10)
        print(f'  Status: {r.status_code}')
        print(f'  Length: {len(r.text)} bytes')
        
        # Check if we're still logged in
        if 'LOGIN' in r.url:
            print(f'   Redirected to login - session expired')
        else:
            print(f'   Authenticated access!')
            print(f'  Final URL: {r.url}')
            
            # Save response
            filename = path.split('/')[-1].replace('.', '_') + '.html'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(r.text)
            print(f'   Saved to: {filename}')
        
        print()
        
    except Exception as e:
        print(f'   Error: {e}\n')

print('=' * 80)
print('Check the saved HTML files to see work order data!')
print('=' * 80)
