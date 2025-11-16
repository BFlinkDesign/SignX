import json
import requests

print('=' * 80)
print('KeyedIn Session Cleanup')
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

# Try to logout
logout_url = 'https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/LOGOUT'

print('\n Attempting to logout from existing sessions...')

try:
    r = session.get(logout_url, timeout=10)
    print(f'   Status: {r.status_code}')
    print(f'   URL: {r.url}')
    
    if 'LOGIN' in r.url or r.status_code == 200:
        print('    Logout successful')
    
except Exception as e:
    print(f'   Error: {e}')

print('\n Waiting 10 seconds for license to free up...')
import time
time.sleep(10)

print('\n Done! Now try logging in again.')
