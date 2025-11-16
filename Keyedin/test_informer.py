import json
import requests
from bs4 import BeautifulSoup

print('=' * 80)
print('Accessing KeyedIn Informer Portal')
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

# The Informer SSO URL pattern from menu
# HTTPS://EAGLESIGN.KEYEDINSIGN.COM:8443/eaglesign/sso?u=BRADYF&t=<session>&initialAction.action=ReportRun&remoteId=7831576

# Try the Informer base URL
informer_base = 'https://eaglesign.keyedinsign.com:8443/eaglesign'

endpoints = [
    '/Informer.html',
    '/Home.html',
    '/ReportList.html',
    '/sso',
]

for endpoint in endpoints:
    url = f'{informer_base}{endpoint}'
    print(f'\n Testing: {endpoint}')
    
    try:
        r = session.get(url, timeout=10, verify=True)
        print(f'   Status: {r.status_code}')
        print(f'   Final URL: {r.url}')
        print(f'   Length: {len(r.text)} bytes')
        
        # Save response
        filename = endpoint.replace('/', '_').replace('.html', '') + '_response.html'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(r.text)
        print(f'    Saved: {filename}')
        
        # Look for report links
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Find links with 'work' or 'order' in them
        links = soup.find_all('a', href=True)
        work_links = [l for l in links if 'work' in l.get_text().lower() or 'order' in l.get_text().lower()]
        
        if work_links:
            print(f'    Found {len(work_links)} work-related links:')
            for link in work_links[:5]:
                print(f'       {link.get_text().strip()[:50]}  {link["href"][:80]}')
        
        # Show preview
        print(f'\n   Preview (first 400 chars):')
        print(f'   {r.text[:400]}')
        
    except Exception as e:
        print(f'    Error: {e}')

print('\n' + '=' * 80)
print('Summary: Check saved files to see Informer interface')
print('=' * 80)
