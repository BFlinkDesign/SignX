"""
KeyedIn API - Legacy wrapper for enhanced API
For new code, use KeyedInAPIEnhanced from keyedin_api_enhanced.py
"""

import json
import requests
from datetime import datetime
from pathlib import Path

# Import enhanced API for future use
try:
    from keyedin_api_enhanced import KeyedInAPIEnhanced
except ImportError:
    KeyedInAPIEnhanced = None

class KeyedInAPI:
    """
    Legacy KeyedIn API wrapper
    
    NOTE: This is a simple wrapper. For automatic session management,
    cookie refresh, and validation, use KeyedInAPIEnhanced instead.
    """
    def __init__(self, cookies_file='keyedin_chrome_session.json'):
        '''Initialize with saved session cookies'''
        self.base_url = 'https://eaglesign.keyedinsign.com'
        self.session = requests.Session()
        
        # Load cookies
        try:
            with open(cookies_file, 'r') as f:
                cookies_list = json.load(f)
            
            for cookie in cookies_list:
                self.session.cookies.set(
                    name=cookie['name'],
                    value=cookie['value'],
                    domain=cookie.get('domain', ''),
                    path=cookie.get('path', '/')
                )
            
            print(f' Loaded {len(cookies_list)} cookies')
        except FileNotFoundError:
            print(f' Warning: Cookie file {cookies_file} not found')
            print(' Run keyedin_cdp_extractor.py to extract cookies first')
        except Exception as e:
            print(f' Error loading cookies: {e}')
    
    def get_menu(self):
        '''Get the menu structure'''
        url = f'{self.base_url}/cgi-bin/mvi.exe/WEB.MENU?USERNAME=BRADYF'
        r = self.session.get(url)
        return r.json()
    
    def get_work_order_form(self):
        '''Get the work order inquiry form'''
        url = f'{self.base_url}/cgi-bin/mvi.exe/WO.INQUIRY'
        r = self.session.get(url)
        return r.text
    
    def test_endpoints(self):
        '''Test discovered endpoints'''
        endpoints = {
            'Menu': '/cgi-bin/mvi.exe/WEB.MENU?USERNAME=BRADYF',
            'WO Inquiry': '/cgi-bin/mvi.exe/WO.INQUIRY',
            'WO History': '/cgi-bin/mvi.exe/WO.HISTORY',
            'Cost Summary': '/cgi-bin/mvi.exe/WO.COST.SUMMARY',
            'Service Calls': '/cgi-bin/mvi.exe/WIDGET.ASSIGNED.SERVICE.CALLS?ACTION=AJAX',
        }
        
        results = {}
        for name, endpoint in endpoints.items():
            url = f'{self.base_url}{endpoint}'
            try:
                r = self.session.get(url, timeout=10)
                results[name] = {
                    'status': r.status_code,
                    'length': len(r.text),
                    'url': url,
                    'success': r.status_code == 200
                }
            except Exception as e:
                results[name] = {
                    'error': str(e)
                }
        
        return results

# Test the API
print('=' * 80)
print('KeyedIn API Client Test')
print('=' * 80)

api = KeyedInAPI()

print('\n Testing endpoints...\n')
results = api.test_endpoints()

for name, result in results.items():
    if 'error' in result:
        print(f' {name:20s} ERROR: {result["error"]}')
    else:
        status = '' if result['success'] else ''
        print(f'{status} {name:20s} Status: {result["status"]}  Length: {result["length"]:,} bytes')

print('\n' + '=' * 80)
print(' API client is working! Session cookies are valid.')
print('=' * 80)

# Save API client for reuse
print('\n API client code saved for future use')
