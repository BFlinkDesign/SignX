#!/usr/bin/env python3
"""
COMPLETE DATA EXTRACTION - Extract EVERYTHING from KeyedIn
1. Finds ALL work order numbers, service order numbers, sales order numbers
2. Extracts ALL detailed cost summaries for each
3. Maps all endpoints and data sources
"""

import json
import re
import time
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote
from keyedin_api_enhanced import KeyedInAPIEnhanced, get_project_root

class CompleteDataExtractor:
    """Extract everything from KeyedIn system"""
    
    def __init__(self):
        self.api = KeyedInAPIEnhanced(auto_refresh=False)
        self.work_orders = set()
        self.service_orders = set()
        self.sales_orders = set()
        self.cost_summaries = []
        
    def get_all_work_orders(self):
        """Get ALL work order numbers using multiple methods"""
        print("\n" + "=" * 80)
        print("Step 1: Finding ALL Work Order Numbers")
        print("=" * 80)
        
        # Method 1: Try WO.INQUIRY with form submission (empty params = all)
        print("\n  Method 1: Querying WO.INQUIRY with empty parameters...")
        try:
            # Submit form with empty/broad parameters to get all
            response = self.api.get('/cgi-bin/mvi.exe/WO.INQUIRY', timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try to find and submit the form
                form = soup.find('form')
                if form:
                    # Extract form action
                    action = form.get('action', 'WO.INQUIRY')
                    if action == '[ACTION]':
                        action = 'WO.INQUIRY'
                    
                    # Try POST with empty parameters
                    form_data = {}
                    for inp in form.find_all('input'):
                        name = inp.get('name')
                        if name:
                            inp_type = inp.get('type', 'text')
                            if inp_type in ['text', 'hidden']:
                                form_data[name] = ''  # Empty = all
                            elif inp_type == 'checkbox':
                                form_data[name] = 'on'
                    
                    # Submit form
                    submit_response = self.api.post(f'/cgi-bin/mvi.exe/{action}', data=form_data, timeout=15)
                    if submit_response.status_code == 200:
                        wo_nos = self._extract_wo_numbers(submit_response.text)
                        self.work_orders.update(wo_nos)
                        if wo_nos:
                            print(f"    Found {len(wo_nos)} work orders from form submission")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 2: Try WO.HISTORY - might list all work orders
        print("\n  Method 2: Checking WO.HISTORY...")
        try:
            response = self.api.get('/cgi-bin/mvi.exe/WO.HISTORY', timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract from tables
                for table in soup.find_all('table'):
                    for row in table.find_all('tr'):
                        # Check links
                        for link in row.find_all('a', href=True):
                            href = link.get('href', '')
                            match = re.search(r'WONO=(\d+)', href, re.IGNORECASE)
                            if match:
                                self.work_orders.add(match.group(1))
                        
                        # Check cells
                        cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                        for cell in cells:
                            # Look for work order numbers
                            numbers = re.findall(r'\b(\d{4,8})\b', cell)
                            for num in numbers:
                                if not re.match(r'^(19|20)\d{2}', num):  # Not a year
                                    self.work_orders.add(num)
                
                if self.work_orders:
                    print(f"    Found {len(self.work_orders)} work orders in history")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 3: Try WO.GROUP.ANALYSIS
        print("\n  Method 3: Checking WO.GROUP.ANALYSIS...")
        try:
            response = self.api.get('/cgi-bin/mvi.exe/WO.GROUP.ANALYSIS', timeout=15)
            if response.status_code == 200:
                wo_nos = self._extract_wo_numbers(response.text)
                self.work_orders.update(wo_nos)
                if wo_nos:
                    print(f"    Found {len(wo_nos)} work orders")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 4: Try WO.COMPLETION.INQUIRY
        print("\n  Method 4: Checking WO.COMPLETION.INQUIRY...")
        try:
            response = self.api.get('/cgi-bin/mvi.exe/WO.COMPLETION.INQUIRY', timeout=15)
            if response.status_code == 200:
                wo_nos = self._extract_wo_numbers(response.text)
                self.work_orders.update(wo_nos)
                if wo_nos:
                    print(f"    Found {len(wo_nos)} work orders")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 5: Range-based discovery (if we know some work orders)
        print("\n  Method 5: Range-based discovery...")
        known_wos = ['8443', '7831576']  # From previous extractions
        
        for known_wo in known_wos:
            try:
                wo_int = int(known_wo)
                # Try ±500 range around known WO
                print(f"    Checking range around WO {known_wo}...")
                for offset in range(-500, 501):
                    test_wo = str(wo_int + offset)
                    if int(test_wo) > 0:
                        # Quick check if WO exists
                        response = self.api.get(f'/cgi-bin/mvi.exe/WO.STATUS.SUM?WONO={test_wo}', timeout=3)
                        if response.status_code == 200 and 'error' not in response.text.lower()[:300]:
                            self.work_orders.add(test_wo)
                            if len(self.work_orders) % 50 == 0:
                                print(f"      Found {len(self.work_orders)} work orders so far...")
                        time.sleep(0.1)  # Rate limit
            except:
                pass
        
        work_orders_list = sorted([wo for wo in self.work_orders if wo.isdigit()], key=lambda x: int(x))
        
        print(f"\n  Total unique work orders found: {len(work_orders_list)}")
        if work_orders_list:
            print(f"  Range: {work_orders_list[0]} to {work_orders_list[-1]}")
        
        return work_orders_list
    
    def get_all_service_orders(self):
        """Get ALL service order/call numbers"""
        print("\n" + "=" * 80)
        print("Step 2: Finding ALL Service Order/Call Numbers")
        print("=" * 80)
        
        # Method 1: SERVICE.CALL.LIST
        print("\n  Method 1: Checking SERVICE.CALL.LIST...")
        try:
            response = self.api.get('/cgi-bin/mvi.exe/SERVICE.CALL.LIST', timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract service call numbers
                for table in soup.find_all('table'):
                    for row in table.find_all('tr'):
                        for link in row.find_all('a', href=True):
                            href = link.get('href', '')
                            match = re.search(r'SCNO=(\d+)', href, re.IGNORECASE)
                            if match:
                                self.service_orders.add(match.group(1))
                        
                        cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                        for cell in cells:
                            # Look for service call numbers
                            numbers = re.findall(r'\b(\d{4,8})\b', cell)
                            for num in numbers:
                                if not re.match(r'^(19|20)\d{2}', num):
                                    self.service_orders.add(num)
                
                if self.service_orders:
                    print(f"    Found {len(self.service_orders)} service calls")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 2: Widget endpoint
        print("\n  Method 2: Checking WIDGET.ASSIGNED.SERVICE.CALLS...")
        try:
            response = self.api.get('/cgi-bin/mvi.exe/WIDGET.ASSIGNED.SERVICE.CALLS?ACTION=AJAX', timeout=15)
            if response.status_code == 200:
                sc_nos = self._extract_sc_numbers(response.text)
                self.service_orders.update(sc_nos)
                if sc_nos:
                    print(f"    Found {len(sc_nos)} service calls")
        except Exception as e:
            print(f"    Error: {e}")
        
        service_orders_list = sorted(list(self.service_orders))
        
        print(f"\n  Total unique service orders found: {len(service_orders_list)}")
        
        return service_orders_list
    
    def get_all_sales_orders(self):
        """Get ALL sales order numbers"""
        print("\n" + "=" * 80)
        print("Step 3: Finding ALL Sales Order Numbers")
        print("=" * 80)
        
        # Method 1: SO.INQUIRY
        print("\n  Method 1: Checking SO.INQUIRY...")
        try:
            response = self.api.get('/cgi-bin/mvi.exe/SO.INQUIRY', timeout=15)
            if response.status_code == 200:
                so_nos = self._extract_so_numbers(response.text)
                self.sales_orders.update(so_nos)
                if so_nos:
                    print(f"    Found {len(so_nos)} sales orders")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 2: Extract from work orders (WOs often linked to SOs)
        print("\n  Method 2: Extracting sales orders from work order data...")
        try:
            # Get a sample of work orders and extract their sales orders
            sample_wos = list(self.work_orders)[:50]  # Sample first 50
            for wo_no in sample_wos:
                try:
                    response = self.api.get(f'/cgi-bin/mvi.exe/WO.STATUS.SUM?WONO={wo_no}', timeout=5)
                    if response.status_code == 200:
                        so_nos = self._extract_so_numbers(response.text)
                        self.sales_orders.update(so_nos)
                except:
                    pass
                time.sleep(0.2)
            
            if self.sales_orders:
                print(f"    Found {len(self.sales_orders)} sales orders from work orders")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 3: Range-based discovery using known SO
        print("\n  Method 3: Range-based discovery...")
        known_so = '12530.1'
        self.sales_orders.add(known_so)
        
        try:
            base_so = float(known_so)
            # Try ±200 range
            print(f"    Checking range around SO {known_so}...")
            for offset in range(-200, 201):
                test_so = f"{base_so + offset:.1f}"
                response = self.api.get(
                    f'/cgi-bin/mvi.exe/SO.CONTRACT.RUN?SONO={quote(test_so)}&REPORT_OPT=D&REPORT_WHERE=P',
                    timeout=3
                )
                if response.status_code == 200 and 'error' not in response.text.lower()[:300]:
                    self.sales_orders.add(test_so)
                    if len(self.sales_orders) % 20 == 0:
                        print(f"      Found {len(self.sales_orders)} sales orders so far...")
                time.sleep(0.1)
        except Exception as e:
            print(f"    Error: {e}")
        
        sales_orders_list = sorted(list(self.sales_orders), key=lambda x: float(x) if '.' in x else float(x + '.0'))
        
        print(f"\n  Total unique sales orders found: {len(sales_orders_list)}")
        if sales_orders_list:
            print(f"  Range: {sales_orders_list[0]} to {sales_orders_list[-1]}")
        
        return sales_orders_list
    
    def extract_all_cost_summaries(self, work_orders=None, sales_orders=None):
        """Extract ALL cost summaries"""
        print("\n" + "=" * 80)
        print("Step 4: Extracting ALL Cost Summaries")
        print("=" * 80)
        
        if work_orders is None:
            work_orders = list(self.work_orders)
        if sales_orders is None:
            sales_orders = list(self.sales_orders)
        
        print(f"\n  Extracting cost summaries for:")
        print(f"    - {len(work_orders)} work orders (via WO.STATUS.SUM)")
        print(f"    - {len(sales_orders)} sales orders (via SO.CONTRACT.RUN)")
        print(f"\n  This will take approximately {((len(work_orders) + len(sales_orders)) * 0.5) / 60:.1f} minutes")
        
        # Extract WO cost summaries
        wo_summaries = []
        for i, wo_no in enumerate(work_orders, 1):
            try:
                response = self.api.get(f'/cgi-bin/mvi.exe/WO.STATUS.SUM?WONO={wo_no}', timeout=10)
                if response.status_code == 200 and 'error' not in response.text.lower()[:300]:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    tables = soup.find_all('table')
                    
                    if tables:
                        summary = {
                            'work_order': wo_no,
                            'source': 'WO.STATUS.SUM',
                            'extracted_at': datetime.now().isoformat(),
                            'tables': []
                        }
                        
                        for table in tables:
                            table_data = self._extract_table_data(table)
                            if table_data:
                                summary['tables'].append(table_data)
                        
                        if summary['tables']:
                            wo_summaries.append(summary)
                
                if i % 10 == 0:
                    print(f"    WO Progress: {i}/{len(work_orders)} - {len(wo_summaries)} summaries extracted")
                
                time.sleep(0.5)
            except Exception as e:
                if i % 50 == 0:
                    print(f"    Error on WO {wo_no}: {e}")
        
        # Extract SO cost summaries
        so_summaries = []
        for i, so_no in enumerate(sales_orders, 1):
            try:
                params = {
                    'SONO': so_no,
                    'REPORT_OPT': 'D',
                    'REPORT_WHERE': 'P',
                    'CLOSE_WINDOW': 'N'
                }
                param_str = urlencode(params, quote_via=quote)
                response = self.api.get(f'/cgi-bin/mvi.exe/SO.CONTRACT.RUN?{param_str}', timeout=10)
                
                if response.status_code == 200 and 'error' not in response.text.lower()[:300]:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    tables = soup.find_all('table')
                    
                    if tables:
                        summary = {
                            'sales_order': so_no,
                            'source': 'SO.CONTRACT.RUN',
                            'extracted_at': datetime.now().isoformat(),
                            'tables': []
                        }
                        
                        for table in tables:
                            table_data = self._extract_table_data(table)
                            if table_data:
                                summary['tables'].append(table_data)
                        
                        if summary['tables']:
                            so_summaries.append(summary)
                
                if i % 10 == 0:
                    print(f"    SO Progress: {i}/{len(sales_orders)} - {len(so_summaries)} summaries extracted")
                
                time.sleep(0.5)
            except Exception as e:
                if i % 50 == 0:
                    print(f"    Error on SO {so_no}: {e}")
        
        self.cost_summaries = wo_summaries + so_summaries
        
        print(f"\n  Extraction complete:")
        print(f"    - {len(wo_summaries)} work order cost summaries")
        print(f"    - {len(so_summaries)} sales order cost summaries")
        print(f"    - Total: {len(self.cost_summaries)} cost summaries")
        
        return self.cost_summaries
    
    def _extract_wo_numbers(self, html):
        """Extract work order numbers from HTML"""
        wo_numbers = set()
        
        patterns = [
            r'WONO[=\s:]+(\d+)',
            r'WO[#:\s]+(\d+)',
            r'href=["\'][^"\']*WONO=(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            wo_numbers.update(matches)
        
        return wo_numbers
    
    def _extract_sc_numbers(self, html):
        """Extract service call numbers"""
        sc_numbers = set()
        patterns = [
            r'SCNO[=\s:]+(\d+)',
            r'SC[#:\s]+(\d+)',
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
            r'href=["\'][^"\']*SONO=([\d.]+)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            so_numbers.update(matches)
        return so_numbers
    
    def _extract_table_data(self, table):
        """Extract data from HTML table"""
        try:
            headers = []
            rows = []
            
            header_row = table.find('tr')
            if header_row:
                th_tags = header_row.find_all('th')
                if th_tags:
                    headers = [th.get_text(strip=True) for th in th_tags]
                    data_rows = table.find_all('tr')[1:]
                else:
                    first_cells = header_row.find_all(['td', 'th'])
                    if first_cells:
                        headers = [cell.get_text(strip=True) for cell in first_cells]
                    data_rows = table.find_all('tr')[1:]
            else:
                data_rows = table.find_all('tr')
            
            for row in data_rows:
                cells = [td.get_text(strip=True) for td in row.find_all('td')]
                if cells:
                    rows.append(cells)
            
            if rows or headers:
                return {
                    'headers': headers,
                    'rows': rows,
                    'row_count': len(rows)
                }
        except:
            pass
        return None
    
    def save_all_data(self):
        """Save all extracted data"""
        output_dir = get_project_root() / 'complete_extraction'
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save IDs
        ids_file = output_dir / f'all_ids_{timestamp}.json'
        with open(ids_file, 'w', encoding='utf-8') as f:
            json.dump({
                'extracted_at': datetime.now().isoformat(),
                'work_orders': sorted(list(self.work_orders), key=lambda x: int(x) if x.isdigit() else 0),
                'service_orders': sorted(list(self.service_orders)),
                'sales_orders': sorted(list(self.sales_orders), key=lambda x: float(x) if '.' in x else float(x + '.0'))
            }, f, indent=2, default=str)
        
        # Save cost summaries
        summaries_file = output_dir / f'all_cost_summaries_{timestamp}.json'
        with open(summaries_file, 'w', encoding='utf-8') as f:
            json.dump({
                'extracted_at': datetime.now().isoformat(),
                'total_summaries': len(self.cost_summaries),
                'work_order_summaries': len([s for s in self.cost_summaries if 'work_order' in s]),
                'sales_order_summaries': len([s for s in self.cost_summaries if 'sales_order' in s]),
                'summaries': self.cost_summaries
            }, f, indent=2, default=str)
        
        print(f"\n[OK] All data saved to: {output_dir}")
        print(f"     IDs: {ids_file.name}")
        print(f"     Cost Summaries: {summaries_file.name}")

def main():
    """Main execution"""
    extractor = CompleteDataExtractor()
    
    print("=" * 80)
    print("COMPLETE DATA EXTRACTION FROM KEYEDIN")
    print("=" * 80)
    print(f"Started: {datetime.now()}")
    
    if not extractor.api.validate_session():
        print("[FAIL] Session invalid")
        return
    
    # Step 1: Get all work orders
    work_orders = extractor.get_all_work_orders()
    
    # Step 2: Get all service orders
    service_orders = extractor.get_all_service_orders()
    
    # Step 3: Get all sales orders
    sales_orders = extractor.get_all_sales_orders()
    
    # Step 4: Extract all cost summaries
    summaries = extractor.extract_all_cost_summaries(work_orders, sales_orders)
    
    # Step 5: Save everything
    extractor.save_all_data()
    
    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE!")
    print("=" * 80)
    print(f"Work Orders: {len(work_orders)}")
    print(f"Service Orders: {len(service_orders)}")
    print(f"Sales Orders: {len(sales_orders)}")
    print(f"Cost Summaries: {len(summaries)}")
    print(f"Completed: {datetime.now()}")
    print("=" * 80)

if __name__ == '__main__':
    main()


