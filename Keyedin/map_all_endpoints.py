#!/usr/bin/env python3
"""
Map ALL KeyedIn Endpoints and Data Sources
Discovers all endpoints that contain work orders, service orders, and cost data
"""

import json
import re
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from keyedin_api_enhanced import KeyedInAPIEnhanced, get_project_root

class KeyedInEndpointMapper:
    """Map all endpoints and data sources"""
    
    def __init__(self):
        self.api = KeyedInAPIEnhanced(auto_refresh=False)
        self.endpoints = {}
        self.work_orders = set()
        self.service_orders = set()
        self.sales_orders = set()
        
    def map_menu_structure(self):
        """Map the complete menu structure to find all endpoints"""
        print("=" * 80)
        print("Mapping Menu Structure")
        print("=" * 80)
        
        try:
            menu = self.api.get_menu()
            
            def extract_endpoints(items, path='', depth=0):
                """Recursively extract all endpoints from menu"""
                endpoints = []
                
                for item in items:
                    item_type = item.get('type', '')
                    text = item.get('text', '')
                    process = item.get('process', '')
                    ext_url = item.get('extURL', '')
                    
                    current_path = f"{path} > {text}" if path else text
                    
                    # Store endpoint information
                    if process:
                        endpoint_info = {
                            'path': current_path,
                            'text': text,
                            'process': process,
                            'extURL': ext_url,
                            'type': item_type,
                            'depth': depth
                        }
                        endpoints.append(endpoint_info)
                        
                        # Categorize endpoints
                        if any(kw in text.lower() for kw in ['work order', 'wo', 'production']):
                            self.endpoints.setdefault('work_orders', []).append(endpoint_info)
                        elif any(kw in text.lower() for kw in ['service', 'service call', 'sc']):
                            self.endpoints.setdefault('service_orders', []).append(endpoint_info)
                        elif any(kw in text.lower() for kw in ['sales order', 'so', 'contract']):
                            self.endpoints.setdefault('sales_orders', []).append(endpoint_info)
                        elif any(kw in text.lower() for kw in ['cost', 'summary', 'report']):
                            self.endpoints.setdefault('cost_reports', []).append(endpoint_info)
                        elif any(kw in text.lower() for kw in ['inquiry', 'list', 'listing']):
                            self.endpoints.setdefault('inquiries', []).append(endpoint_info)
                    
                    # Recurse into submenu
                    submenu = item.get('submenu', [])
                    if submenu:
                        endpoints.extend(extract_endpoints(submenu, current_path, depth + 1))
                
                return endpoints
            
            all_endpoints = extract_endpoints(menu.get('menu', []))
            
            print(f"\nTotal endpoints found: {len(all_endpoints)}")
            print(f"\nCategorized endpoints:")
            for category, items in self.endpoints.items():
                print(f"  {category}: {len(items)} endpoints")
            
            # Save menu map
            output_file = get_project_root() / 'endpoint_map.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'mapped_at': datetime.now().isoformat(),
                    'total_endpoints': len(all_endpoints),
                    'categories': self.endpoints,
                    'all_endpoints': all_endpoints
                }, f, indent=2, default=str)
            
            print(f"\nSaved endpoint map to: {output_file}")
            
            return all_endpoints
            
        except Exception as e:
            print(f"Error mapping menu: {e}")
            return []
    
    def find_listing_endpoints(self):
        """Find endpoints that list work orders, service orders, etc."""
        print("\n" + "=" * 80)
        print("Finding Listing Endpoints")
        print("=" * 80)
        
        listing_endpoints = {
            'work_orders': [],
            'service_orders': [],
            'sales_orders': [],
        }
        
        # Known listing endpoints
        wo_listing_endpoints = [
            '/cgi-bin/mvi.exe/WO.INQUIRY',
            '/cgi-bin/mvi.exe/WORKORDER.LIST',
            '/cgi-bin/mvi.exe/WO.HISTORY',
            '/cgi-bin/mvi.exe/WO.GROUP.ANALYSIS',
            '/cgi-bin/mvi.exe/WO.COMPLETION.INQUIRY',
        ]
        
        sc_listing_endpoints = [
            '/cgi-bin/mvi.exe/SERVICE.CALL.LIST',
            '/cgi-bin/mvi.exe/WIDGET.ASSIGNED.SERVICE.CALLS?ACTION=AJAX',
        ]
        
        so_listing_endpoints = [
            '/cgi-bin/mvi.exe/SO.CONTRACT.RUN',
            '/cgi-bin/mvi.exe/SO.INQUIRY',
        ]
        
        # Test each endpoint
        print("\nTesting Work Order listing endpoints...")
        for endpoint in wo_listing_endpoints:
            try:
                response = self.api.get(endpoint, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    tables = soup.find_all('table')
                    forms = soup.find_all('form')
                    
                    listing_endpoints['work_orders'].append({
                        'endpoint': endpoint,
                        'status': 200,
                        'tables': len(tables),
                        'forms': len(forms),
                        'length': len(response.text)
                    })
                    print(f"  [OK] {endpoint} - {len(tables)} tables, {len(forms)} forms")
            except Exception as e:
                print(f"  [FAIL] {endpoint} - {e}")
        
        print("\nTesting Service Order listing endpoints...")
        for endpoint in sc_listing_endpoints:
            try:
                response = self.api.get(endpoint, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    tables = soup.find_all('table')
                    
                    listing_endpoints['service_orders'].append({
                        'endpoint': endpoint,
                        'status': 200,
                        'tables': len(tables),
                        'length': len(response.text)
                    })
                    print(f"  [OK] {endpoint} - {len(tables)} tables")
            except Exception as e:
                print(f"  [FAIL] {endpoint} - {e}")
        
        print("\nTesting Sales Order listing endpoints...")
        for endpoint in so_listing_endpoints:
            try:
                response = self.api.get(endpoint, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    tables = soup.find_all('table')
                    forms = soup.find_all('form')
                    
                    listing_endpoints['sales_orders'].append({
                        'endpoint': endpoint,
                        'status': 200,
                        'tables': len(tables),
                        'forms': len(forms),
                        'length': len(response.text)
                    })
                    print(f"  [OK] {endpoint} - {len(tables)} tables, {len(forms)} forms")
            except Exception as e:
                print(f"  [FAIL] {endpoint} - {e}")
        
        return listing_endpoints
    
    def extract_all_ids_from_listings(self):
        """Extract all IDs (WO, SO, SC) from listing endpoints"""
        print("\n" + "=" * 80)
        print("Extracting All IDs from Listing Endpoints")
        print("=" * 80)
        
        # Work Orders
        print("\nExtracting Work Order Numbers...")
        wo_endpoints = [
            '/cgi-bin/mvi.exe/WO.INQUIRY',
            '/cgi-bin/mvi.exe/WORKORDER.LIST',
            '/cgi-bin/mvi.exe/WO.HISTORY',
            '/cgi-bin/mvi.exe/WO.GROUP.ANALYSIS',
        ]
        
        for endpoint in wo_endpoints:
            try:
                response = self.api.get(endpoint, timeout=15)
                if response.status_code == 200:
                    wo_nos = self._extract_wo_numbers(response.text)
                    self.work_orders.update(wo_nos)
                    if wo_nos:
                        print(f"  {endpoint}: Found {len(wo_nos)} work orders")
            except Exception as e:
                print(f"  {endpoint}: Error - {e}")
        
        # Service Orders/Calls
        print("\nExtracting Service Order/Call Numbers...")
        sc_endpoints = [
            '/cgi-bin/mvi.exe/SERVICE.CALL.LIST',
            '/cgi-bin/mvi.exe/WIDGET.ASSIGNED.SERVICE.CALLS?ACTION=AJAX',
        ]
        
        for endpoint in sc_endpoints:
            try:
                response = self.api.get(endpoint, timeout=15)
                if response.status_code == 200:
                    sc_nos = self._extract_sc_numbers(response.text)
                    self.service_orders.update(sc_nos)
                    if sc_nos:
                        print(f"  {endpoint}: Found {len(sc_nos)} service calls")
            except Exception as e:
                print(f"  {endpoint}: Error - {e}")
        
        # Sales Orders
        print("\nExtracting Sales Order Numbers...")
        so_endpoints = [
            '/cgi-bin/mvi.exe/SO.CONTRACT.RUN',
            '/cgi-bin/mvi.exe/SO.INQUIRY',
        ]
        
        for endpoint in so_endpoints:
            try:
                response = self.api.get(endpoint, timeout=15)
                if response.status_code == 200:
                    so_nos = self._extract_so_numbers(response.text)
                    self.sales_orders.update(so_nos)
                    if so_nos:
                        print(f"  {endpoint}: Found {len(so_nos)} sales orders")
            except Exception as e:
                print(f"  {endpoint}: Error - {e}")
        
        print(f"\n" + "=" * 80)
        print("ID Extraction Summary")
        print("=" * 80)
        print(f"Work Orders: {len(self.work_orders)}")
        print(f"Service Orders: {len(self.service_orders)}")
        print(f"Sales Orders: {len(self.sales_orders)}")
        
        # Save IDs
        ids_file = get_project_root() / 'all_ids.json'
        with open(ids_file, 'w', encoding='utf-8') as f:
            json.dump({
                'extracted_at': datetime.now().isoformat(),
                'work_orders': sorted(list(self.work_orders), key=lambda x: int(x) if x.isdigit() else 0),
                'service_orders': sorted(list(self.service_orders)),
                'sales_orders': sorted(list(self.sales_orders), key=lambda x: float(x) if '.' in x else float(x + '.0'))
            }, f, indent=2, default=str)
        
        print(f"\nSaved all IDs to: {ids_file}")
        
        return {
            'work_orders': list(self.work_orders),
            'service_orders': list(self.service_orders),
            'sales_orders': list(self.sales_orders)
        }
    
    def _extract_wo_numbers(self, html):
        """Extract work order numbers"""
        wo_numbers = set()
        
        patterns = [
            r'WONO[=\s:]+(\d+)',
            r'WO[#:\s]+(\d+)',
            r'href=["\'][^"\']*WONO=(\d+)',
            r'href=["\'][^"\']*WO\.STATUS[^"\']*WONO=(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            wo_numbers.update(matches)
        
        # Also check tables
        soup = BeautifulSoup(html, 'html.parser')
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                for link in row.find_all('a', href=True):
                    href = link.get('href', '')
                    match = re.search(r'WONO=(\d+)', href, re.IGNORECASE)
                    if match:
                        wo_numbers.add(match.group(1))
                
                cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                for cell in cells:
                    numbers = re.findall(r'\b(\d{4,8})\b', cell)
                    for num in numbers:
                        if not re.match(r'^(19|20)\d{2}', num):
                            wo_numbers.add(num)
        
        return wo_numbers
    
    def _extract_sc_numbers(self, html):
        """Extract service call numbers"""
        sc_numbers = set()
        
        patterns = [
            r'SCNO[=\s:]+(\d+)',
            r'SC[#:\s]+(\d+)',
            r'Service[_\s]?Call[#:\s]+(\d+)',
            r'href=["\'][^"\']*SCNO=(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            sc_numbers.update(matches)
        
        return sc_numbers
    
    def _extract_so_numbers(self, html):
        """Extract sales order numbers"""
        so_numbers = set()
        
        patterns = [
            r'SONO[=\s:]+([\d.]+)',
            r'SO[#:\s]+([\d.]+)',
            r'Sales[_\s]?Order[#:\s]+([\d.]+)',
            r'href=["\'][^"\']*SONO=([\d.]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            so_numbers.update(matches)
        
        return so_numbers
    
    def analyze_data_storage(self):
        """Analyze where data is actually stored"""
        print("\n" + "=" * 80)
        print("Analyzing Data Storage Structure")
        print("=" * 80)
        
        analysis = {
            'endpoints': {},
            'data_sources': [],
            'storage_patterns': []
        }
        
        # Analyze cost summary endpoint
        print("\nAnalyzing SO.CONTRACT.RUN (Cost Summary Report)...")
        try:
            response = self.api.get('/cgi-bin/mvi.exe/SO.CONTRACT.RUN?SONO=12530.1&REPORT_OPT=D&REPORT_WHERE=P', timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Check for database indicators
                text_lower = response.text.lower()
                
                storage_indicators = {
                    'database': ['database', 'db', 'sql', 'query', 'select', 'from', 'where'],
                    'session': ['session', 'sessionid'],
                    'cache': ['cache', 'cached'],
                    'api': ['api', 'rest', 'json', 'ajax'],
                }
                
                print("  Storage indicators found:")
                for category, keywords in storage_indicators.items():
                    found = [kw for kw in keywords if kw in text_lower]
                    if found:
                        print(f"    {category}: {found[:3]}")
                
                # Check for data links
                links = soup.find_all('a', href=True)
                data_links = []
                for link in links:
                    href = link.get('href', '')
                    if any(kw in href.lower() for kw in ['report', 'view', 'data', 'export', 'download']):
                        data_links.append(href)
                
                if data_links:
                    print(f"  Found {len(data_links)} data-related links")
                    for link in data_links[:5]:
                        print(f"    {link[:100]}")
                
                analysis['endpoints']['SO.CONTRACT.RUN'] = {
                    'status': 200,
                    'tables': len(soup.find_all('table')),
                    'data_links': len(data_links),
                    'length': len(response.text)
                }
        except Exception as e:
            print(f"  Error: {e}")
        
        # Analyze WO.STATUS.SUM endpoint
        print("\nAnalyzing WO.STATUS.SUM (Work Order Cost Summary)...")
        try:
            response = self.api.get('/cgi-bin/mvi.exe/WO.STATUS.SUM?WONO=8443', timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                analysis['endpoints']['WO.STATUS.SUM'] = {
                    'status': 200,
                    'tables': len(soup.find_all('table')),
                    'length': len(response.text)
                }
                print(f"  Status: 200, Tables: {len(soup.find_all('table'))}")
        except Exception as e:
            print(f"  Error: {e}")
        
        return analysis

def main():
    """Main mapping function"""
    mapper = KeyedInEndpointMapper()
    
    # Step 1: Map menu structure
    endpoints = mapper.map_menu_structure()
    
    # Step 2: Find listing endpoints
    listings = mapper.find_listing_endpoints()
    
    # Step 3: Extract all IDs
    ids = mapper.extract_all_ids_from_listings()
    
    # Step 4: Analyze data storage
    storage = mapper.analyze_data_storage()
    
    # Save complete map
    complete_map = {
        'mapped_at': datetime.now().isoformat(),
        'endpoints': endpoints,
        'listings': listings,
        'ids': ids,
        'storage_analysis': storage
    }
    
    output_file = get_project_root() / 'complete_endpoint_map.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(complete_map, f, indent=2, default=str)
    
    print("\n" + "=" * 80)
    print("Mapping Complete!")
    print("=" * 80)
    print(f"Total endpoints mapped: {len(endpoints)}")
    print(f"Work Orders found: {len(ids['work_orders'])}")
    print(f"Service Orders found: {len(ids['service_orders'])}")
    print(f"Sales Orders found: {len(ids['sales_orders'])}")
    print(f"\nComplete map saved to: {output_file}")
    print("=" * 80)

if __name__ == '__main__':
    main()


