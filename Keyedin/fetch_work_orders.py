import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd

class KeyedInWorkOrders:
    def __init__(self, cookies_file='keyedin_chrome_session.json'):
        self.base_url = 'https://eaglesign.keyedinsign.com'
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
    
    def try_work_order_queries(self):
        '''Try different parameter combinations to get work order data'''
        
        base_endpoint = f'{self.base_url}/cgi-bin/mvi.exe/WO.INQUIRY'
        
        # Try different query patterns
        queries = [
            {},  # Empty - might return all
            {'ACTION': 'SEARCH'},
            {'ACTION': 'LIST'},
            {'ACTION': 'AJAX'},
            {'SUBMIT': 'GO'},
            {'SEARCH': 'Y'},
            # Try date ranges
            {'FROM_DATE': '01/01/2024', 'TO_DATE': '12/31/2024'},
            # Try status filters
            {'STATUS': 'OPEN'},
            {'STATUS': 'ALL'},
        ]
        
        results = {}
        
        print('Testing different query parameters...\n')
        
        for i, params in enumerate(queries, 1):
            print(f'{i}. Testing: {params}')
            
            try:
                r = self.session.get(base_endpoint, params=params, timeout=10)
                
                # Check if we got data
                soup = BeautifulSoup(r.text, 'html.parser')
                tables = soup.find_all('table')
                
                # Look for data tables (not just the form)
                data_tables = [t for t in tables if len(t.find_all('tr')) > 2]
                
                result = {
                    'status': r.status_code,
                    'length': len(r.text),
                    'tables': len(data_tables),
                    'url': r.url,
                    'has_form': bool(soup.find('form')),
                    'has_iframe': bool(soup.find('iframe'))
                }
                
                # Check for work order data indicators
                text_lower = r.text.lower()
                result['mentions_work_order'] = 'work order' in text_lower
                result['has_numbers'] = any(char.isdigit() for char in r.text[:500])
                
                results[str(params)] = result
                
                status = '' if data_tables else ''
                print(f'   {status} Status: {r.status_code}, Length: {len(r.text):,}, Tables: {len(data_tables)}')
                
                # Save promising responses
                if data_tables or len(r.text) > 2000:
                    filename = f'wo_query_{i}.html'
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(r.text)
                    print(f'    Saved: {filename}')
                
            except Exception as e:
                results[str(params)] = {'error': str(e)}
                print(f'    Error: {e}')
            
            print()
        
        return results

# Test work order queries
print('=' * 80)
print('KeyedIn Work Order Data Fetcher')
print('=' * 80)

fetcher = KeyedInWorkOrders()

print('\n Attempting to fetch work order data...\n')
results = fetcher.try_work_order_queries()

# Summary
print('=' * 80)
print('Summary:')
print('=' * 80)

successful = [k for k, v in results.items() if v.get('tables', 0) > 0]
if successful:
    print(f'\n Found {len(successful)} queries with data tables!')
    print('Check the saved HTML files for work order data.')
else:
    print('\n All queries returned forms (no data tables)')
    print('This means we need to:')
    print('   1. Use the Informer BI portal instead')
    print('   2. Or find the actual data submission endpoint')

# Save results
with open('wo_query_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f'\n Saved query results to: wo_query_results.json')
