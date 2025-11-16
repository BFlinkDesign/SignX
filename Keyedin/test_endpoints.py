import json
import requests
from bs4 import BeautifulSoup

print('=' * 80)
print('Testing Discovered KeyedIn Endpoints')
print('=' * 80)

# Load cookies from Chrome session
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

print(f'\n Loaded {len(cookies_list)} cookies')

# Test the discovered endpoints
endpoints = [
    '/cgi-bin/mvi.exe/WEB.MENU?USERNAME=BRADYF',
    '/cgi-bin/mvi.exe/WIDGET.ASSIGNED.SERVICE.CALLS?ACTION=AJAX',
    '/cgi-bin/mvi.exe/WIDGET.CRM.TASKS?ACTION=AJAX',
    '/cgi-bin/mvi.exe/WIDGET.ASSIGNED.MILESTONES?ACTION=AJAX',
    '/cgi-bin/mvi.exe/WIDGET.FYI?ACTION=AJAX',
]

base_url = 'https://eaglesign.keyedinsign.com'

for endpoint in endpoints:
    print(f'\n Testing: {endpoint}')
    url = f'{base_url}{endpoint}'
    
    try:
        r = session.get(url, timeout=10)
        print(f'   Status: {r.status_code}')
        print(f'   Length: {len(r.text)} bytes')
        
        # Save response
        filename = endpoint.split('/')[-1].split('?')[0] + '.html'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(r.text)
        print(f'    Saved: {filename}')
        
        # Try to parse as JSON first
        try:
            data = r.json()
            print(f'    JSON response with {len(data)} keys')
            print(f'   Keys: {list(data.keys())[:5]}')
            
            # Save JSON version
            json_file = filename.replace('.html', '.json')
            with open(json_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f'    Saved JSON: {json_file}')
            
        except:
            # Try HTML parsing
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Look for work order links
            links = soup.find_all('a', href=True)
            if links:
                work_links = [l for l in links if any(kw in l.get_text().lower() 
                              for kw in ['work', 'order', 'service', 'job'])]
                if work_links:
                    print(f'    Found {len(work_links)} work-related links:')
                    for link in work_links[:5]:
                        print(f'       {link.get_text().strip()[:50]}  {link["href"]}')
            
            # Show first 500 chars
            print(f'\n   Preview:')
            print(f'   {r.text[:500]}')
    
    except Exception as e:
        print(f'    Error: {e}')

print('\n' + '=' * 80)
print('Check the saved files for work order data!')
print('=' * 80)
