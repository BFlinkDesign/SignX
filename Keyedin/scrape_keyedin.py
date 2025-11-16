import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd

class KeyedInScraper:
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
        
        print(f' Initialized with {len(cookies_list)} cookies')
    
    def get_menu_structure(self):
        '''Get full menu including all work order reports'''
        url = f'{self.base_url}/cgi-bin/mvi.exe/WEB.MENU?USERNAME=BRADYF'
        r = self.session.get(url)
        return r.json()
    
    def find_work_order_endpoints(self):
        '''Extract all work order related endpoints from menu'''
        menu_data = self.get_menu_structure()
        
        def search_menu(items, path=''):
            endpoints = []
            for item in items:
                label = item.get('text', '')
                process = item.get('process', '')
                ext_url = item.get('extURL', '')
                
                if any(kw in label.lower() for kw in ['work order', 'job cost', 'production']):
                    endpoints.append({
                        'path': path,
                        'label': label,
                        'process': process,
                        'extURL': ext_url
                    })
                
                submenu = item.get('submenu', [])
                if submenu:
                    new_path = f'{path} > {label}' if path else label
                    endpoints.extend(search_menu(submenu, new_path))
            
            return endpoints
        
        return search_menu(menu_data.get('menu', []))
    
    def get_widgets_data(self):
        '''Get dashboard widget data (assigned work, tasks, etc.)'''
        widgets = {
            'service_calls': '/cgi-bin/mvi.exe/WIDGET.ASSIGNED.SERVICE.CALLS?ACTION=AJAX',
            'tasks': '/cgi-bin/mvi.exe/WIDGET.CRM.TASKS?ACTION=AJAX',
            'milestones': '/cgi-bin/mvi.exe/WIDGET.ASSIGNED.MILESTONES?ACTION=AJAX',
        }
        
        results = {}
        for name, endpoint in widgets.items():
            url = f'{self.base_url}{endpoint}'
            r = self.session.get(url)
            results[name] = self.parse_widget_html(r.text)
        
        return results
    
    def parse_widget_html(self, html):
        '''Parse widget HTML table into structured data'''
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        
        if not table:
            return []
        
        rows = table.find_all('tr')
        if len(rows) < 2:
            return []
        
        # Get headers
        header_row = rows[0]
        headers = [th.get_text(strip=True) for th in header_row.find_all('td')]
        
        # Get data rows
        data = []
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) == 1:  # "No items" message
                continue
            
            row_data = {}
            for i, cell in enumerate(cells):
                if i < len(headers):
                    row_data[headers[i]] = cell.get_text(strip=True)
            
            if row_data:
                data.append(row_data)
        
        return data

# Run the scraper
print('=' * 80)
print('KeyedIn Work Order Scraper')
print('=' * 80)

scraper = KeyedInScraper()

print('\n Finding work order endpoints...')
endpoints = scraper.find_work_order_endpoints()
print(f'   Found {len(endpoints)} work order endpoints')

print('\n Work Order Related Endpoints:\n')
for ep in endpoints[:15]:
    print(f'   {ep["label"]:50s}  {ep["process"]}')

print('\n Getting widget data...')
widgets = scraper.get_widgets_data()

print('\n Dashboard Widgets:')
for name, data in widgets.items():
    print(f'   {name:20s}: {len(data)} items')
    if data:
        print(f'      Sample: {data[0]}')

# Save results
output = {
    'timestamp': datetime.now().isoformat(),
    'endpoints': endpoints,
    'widget_data': widgets
}

with open('keyedin_work_orders.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f'\n Saved results to: keyedin_work_orders.json')

print('\n' + '=' * 80)
print(' Scraper complete!')
print('=' * 80)
print('\nNext steps:')
print('1. Review keyedin_work_orders.json for available endpoints')
print('2. We can now build specific scrapers for each work order type')
print('3. Or access the Informer portal for BI reports')
