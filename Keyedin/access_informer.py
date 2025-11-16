import json
import requests
from bs4 import BeautifulSoup
import re

class KeyedInInformerAPI:
    def __init__(self, cookies_file='keyedin_chrome_session.json'):
        self.base_url = 'https://eaglesign.keyedinsign.com:8443/eaglesign'
        self.session = requests.Session()
        
        # Load cookies
        with open(cookies_file, 'r') as f:
            cookies_list = json.load(f)
        
        for cookie in cookies_list:
            self.session.cookies.set(
                name=cookie['name'],
                value=cookie['value'],
                domain=cookie.get('domain', ''),
                path=cookie.get('path', '/')
            )
        
        # Extract session token from cookies
        self.session_token = None
        for cookie in cookies_list:
            if cookie['name'] == 'SESSIONID':
                self.session_token = cookie['value']
                break
        
        print(f' Session token: {self.session_token}')
    
    def access_informer_portal(self):
        '''Access the main Informer interface'''
        url = f'{self.base_url}/Informer.html'
        
        r = self.session.get(url)
        print(f'\n Informer Portal:')
        print(f'   Status: {r.status_code}')
        print(f'   URL: {r.url}')
        
        # Save the page
        with open('informer_portal.html', 'w', encoding='utf-8') as f:
            f.write(r.text)
        
        return r.text
    
    def try_report_list_api(self):
        '''Try to get list of available reports via API'''
        
        # Common Informer API endpoints
        api_endpoints = [
            '/api/reports',
            '/api/datasources',
            '/api/user/reports',
            '/rest/reports',
            '/rest/datasources',
            '/ReportList',
            '/reportlist',
        ]
        
        results = {}
        
        print('\n Testing Informer API endpoints:\n')
        
        for endpoint in api_endpoints:
            url = f'{self.base_url}{endpoint}'
            print(f'Testing: {endpoint}')
            
            try:
                r = self.session.get(url, timeout=10)
                
                result = {
                    'status': r.status_code,
                    'content_type': r.headers.get('Content-Type', ''),
                    'length': len(r.text)
                }
                
                # Try to parse as JSON
                try:
                    data = r.json()
                    result['is_json'] = True
                    result['data_keys'] = list(data.keys()) if isinstance(data, dict) else None
                    print(f'    {r.status_code} - JSON response with keys: {result["data_keys"]}')
                    
                    # Save JSON response
                    filename = endpoint.replace('/', '_') + '.json'
                    with open(filename, 'w') as f:
                        json.dump(data, f, indent=2)
                    print(f'    Saved: {filename}')
                    
                except:
                    result['is_json'] = False
                    print(f'    {r.status_code} - HTML/Text response ({len(r.text)} bytes)')
                
                results[endpoint] = result
                
            except Exception as e:
                results[endpoint] = {'error': str(e)}
                print(f'    Error: {e}')
            
            print()
        
        return results
    
    def try_sso_pattern(self):
        '''Try the SSO URL pattern we found in the menu'''
        
        # Pattern: /sso?u=BRADYF&t=<session>&initialAction.action=...
        
        sso_urls = [
            # Try to access report list
            f'/sso?u=BRADYF&t={self.session_token}&initialAction.action=ReportList',
            # Try the discovered report ID
            f'/sso?u=BRADYF&t={self.session_token}&initialAction.action=ReportRun&remoteId=7831576',
            # Try without initialAction
            f'/sso?u=BRADYF&t={self.session_token}',
        ]
        
        print('\n Testing SSO URL patterns:\n')
        
        for url_path in sso_urls:
            url = f'{self.base_url}{url_path}'
            print(f'Testing: {url_path[:80]}...')
            
            try:
                r = self.session.get(url, timeout=10, allow_redirects=True)
                print(f'   Status: {r.status_code}')
                print(f'   Final URL: {r.url}')
                print(f'   Length: {len(r.text):,} bytes')
                
                # Save response
                filename = f'sso_response_{url_path.split("=")[-1][:20]}.html'
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(r.text)
                print(f'    Saved: {filename}')
                
            except Exception as e:
                print(f'    Error: {e}')
            
            print()

# Run Informer API tests
print('=' * 80)
print('KeyedIn Informer Portal API Access')
print('=' * 80)

api = KeyedInInformerAPI()

# Test main portal
api.access_informer_portal()

# Test API endpoints
api.try_report_list_api()

# Test SSO patterns
api.try_sso_pattern()

print('=' * 80)
print(' Informer portal exploration complete!')
print('Check saved files for report data or report lists.')
print('=' * 80)
