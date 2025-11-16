import json
import requests
from bs4 import BeautifulSoup

print('=' * 80)
print('Testing Work Order Endpoints')
print('=' * 80)

# Load session cookies
with open('keyedin_chrome_session.json', 'r') as f:
    cookies_list = json.load(f)

session = requests.Session()
for cookie in cookies_list:
    session.cookies.set(
        name=cookie['name'],
        value=cookie['value'],
        domain=cookie.get('domain', ''),
        path=cookie.get('path', '/')
    )

base_url = 'https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe'

# Key work order processes from menu
work_order_processes = [
    'WO.INQUIRY',           # (BI) - Work Order Listing
    'WO.HISTORY',           # Work Order Cost History
    'WO.COMPLETION.INQUIRY', # Work Order Completion Listing
    'WO.GROUP.ANALYSIS',    # Work Order Group Analysis
    'FIRST.ISSUE',          # Work Order Issue
]

for process in work_order_processes:
    print(f'\n Testing: {process}')
    url = f'{base_url}/{process}'
    
    try:
        r = session.get(url, timeout=10)
        print(f'   Status: {r.status_code}')
        print(f'   Length: {len(r.text)} bytes')
        
        # Save response
        filename = f'{process}.html'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(r.text)
        print(f'    Saved: {filename}')
        
        # Check if it's an error page
        if 'Error Occurred' in r.text or 'not defined in the VOC' in r.text:
            print(f'    Error page returned')
            continue
        
        # Parse for data
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Look for iframes (KeyedIn often loads content via iframe)
        iframes = soup.find_all('iframe')
        if iframes:
            print(f'     Contains {len(iframes)} iframe(s):')
            for iframe in iframes:
                src = iframe.get('src', '')
                if src:
                    print(f'       {src}')
        
        # Look for forms
        forms = soup.find_all('form')
        if forms:
            print(f'    Contains {len(forms)} form(s)')
        
        # Look for tables
        tables = soup.find_all('table')
        if tables:
            print(f'    Contains {len(tables)} table(s)')
        
        # Show first 300 chars
        if len(r.text) > 100:
            print(f'\n   Preview:')
            print(f'   {r.text[:300]}...')
        
    except Exception as e:
        print(f'    Error: {e}')

print('\n' + '=' * 80)
print('Check saved HTML files for work order data!')
print('=' * 80)
