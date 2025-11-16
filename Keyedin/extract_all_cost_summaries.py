#!/usr/bin/env python3
"""
Extract ALL Detailed Cost Summaries from KeyedIn System
Pulls every cost summary available in the system
"""

import json
import os
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from keyedin_api_enhanced import KeyedInAPIEnhanced, get_project_root
import time

class CostSummaryExtractor:
    """Extract all cost summaries from KeyedIn"""
    
    def __init__(self):
        self.api = KeyedInAPIEnhanced(auto_refresh=False)
        self.all_summaries = []
        
    def get_all_work_orders(self):
        """Get list of all work orders to extract cost summaries for"""
        print("\n" + "=" * 80)
        print("Step 1: Getting All Work Orders")
        print("=" * 80)
        
        work_orders = []
        
        # Try multiple endpoints to get work order list
        endpoints = [
            '/cgi-bin/mvi.exe/WORKORDER.LIST',
            '/cgi-bin/mvi.exe/WO.HISTORY',
            '/cgi-bin/mvi.exe/WO.INQUIRY',
        ]
        
        for endpoint in endpoints:
            try:
                print(f"\n  Trying: {endpoint}")
                response = self.api.get(endpoint, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    tables = soup.find_all('table')
                    
                    print(f"    Found {len(tables)} tables")
                    
                    # Extract work order numbers from tables
                    for table in tables:
                        for row in table.find_all('tr'):
                            cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                            
                            # Look for work order numbers (typically in first column or links)
                            for cell in cells:
                                # Check if cell contains work order number pattern
                                # Work orders often have format like WO12345 or just numbers
                                if cell and len(cell) > 0:
                                    # Check for links to work orders
                                    links = row.find_all('a', href=True)
                                    for link in links:
                                        href = link.get('href', '')
                                        if 'WONO=' in href or 'WO.' in href.upper():
                                            wo_no = link.get_text(strip=True)
                                            if wo_no and wo_no not in work_orders:
                                                work_orders.append(wo_no)
                                                print(f"      Found WO: {wo_no}")
                    
                    # Also check for input fields that might have work order numbers
                    inputs = soup.find_all('input', {'name': lambda x: x and 'WONO' in x.upper()})
                    for inp in inputs:
                        value = inp.get('value', '')
                        if value and value not in work_orders:
                            work_orders.append(value)
                            print(f"      Found WO from input: {value}")
                            
            except Exception as e:
                print(f"    Error: {e}")
        
        print(f"\n  Total work orders found: {len(work_orders)}")
        return work_orders
    
    def extract_cost_summary(self, work_order_no=None):
        """Extract cost summary for a specific work order or all"""
        print("\n" + "=" * 80)
        print("Step 2: Extracting Cost Summaries")
        print("=" * 80)
        
        # Try different cost summary endpoints (WO.STATUS.SUM is the detailed cost summary)
        cost_endpoints = [
            '/cgi-bin/mvi.exe/WO.STATUS.SUM',  # Costing - Summary (detailed)
            '/cgi-bin/mvi.exe/WO.COST.SUMMARY',
            '/cgi-bin/mvi.exe/WO.COST.DETAIL',
            '/cgi-bin/mvi.exe/WO.STATUS.MATL',  # Costing - Material
            '/cgi-bin/mvi.exe/WO.STATUS.LABR',  # Costing - Labor
            '/cgi-bin/mvi.exe/WO.STATUS.LDTL',  # Costing - Labor Details
        ]
        
        summaries = []
        
        # First, try to get cost summary form to understand parameters
        print("\n  Analyzing cost summary form...")
        try:
            response = self.api.get('/cgi-bin/mvi.exe/WO.COST.SUMMARY', timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find form to understand what parameters are needed
                forms = soup.find_all('form')
                print(f"    Found {len(forms)} forms")
                
                for form in forms:
                    action = form.get('action', '')
                    method = form.get('method', 'GET')
                    
                    # Extract form fields
                    inputs = form.find_all('input')
                    selects = form.find_all('select')
                    
                    print(f"    Form action: {action}, method: {method}")
                    print(f"    Inputs: {len(inputs)}, Selects: {len(selects)}")
                    
                    # Check for work order number field
                    for inp in inputs:
                        name = inp.get('name', '')
                        if 'WONO' in name.upper() or 'WORK' in name.upper():
                            print(f"      Found WO field: {name}")
                    
        except Exception as e:
            print(f"    Error analyzing form: {e}")
        
        # Try to get all cost summaries
        print("\n  Attempting to extract all cost summaries...")
        
        # Method 1: Try WO.STATUS.SUM (Costing - Summary) - the detailed cost summary endpoint
        try:
            print("\n  Trying WO.STATUS.SUM (Costing - Summary)...")
            # Try without parameters first (might return all or show form)
            response = self.api.get('/cgi-bin/mvi.exe/WO.STATUS.SUM', timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                tables = soup.find_all('table')
                forms = soup.find_all('form')
                
                print(f"    Found {len(tables)} tables, {len(forms)} forms")
                
                # If there's a form, it needs work order number
                if forms:
                    print("    Form found - will need work order numbers")
                    # Extract form to understand parameters
                    for form in forms:
                        inputs = form.find_all('input')
                        selects = form.find_all('select')
                        print(f"      Form has {len(inputs)} inputs, {len(selects)} selects")
                        for inp in inputs:
                            name = inp.get('name', '')
                            if name:
                                print(f"        Input: {name} = {inp.get('value', '')}")
                
                # Extract data from tables if present
                for i, table in enumerate(tables):
                    table_data = self._extract_table_data(table)
                    if table_data:
                        summaries.append({
                            'source': 'WO.STATUS.SUM',
                            'table_index': i,
                            'data': table_data
                        })
                        print(f"      Extracted table {i}: {len(table_data['rows'])} rows")
                        
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 1b: Try WO.COST.SUMMARY
        try:
            print("\n  Trying WO.COST.SUMMARY...")
            response = self.api.get('/cgi-bin/mvi.exe/WO.COST.SUMMARY', timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                tables = soup.find_all('table')
                
                print(f"    Found {len(tables)} tables in cost summary")
                
                # Extract data from tables
                for i, table in enumerate(tables):
                    table_data = self._extract_table_data(table)
                    if table_data:
                        summaries.append({
                            'source': 'WO.COST.SUMMARY',
                            'table_index': i,
                            'data': table_data
                        })
                        print(f"      Extracted table {i}: {len(table_data['rows'])} rows")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 2: Try cost detail endpoint
        try:
            print("\n  Trying WO.COST.DETAIL endpoint...")
            response = self.api.get('/cgi-bin/mvi.exe/WO.COST.DETAIL', timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                tables = soup.find_all('table')
                
                print(f"    Found {len(tables)} tables")
                
                for i, table in enumerate(tables):
                    table_data = self._extract_table_data(table)
                    if table_data:
                        summaries.append({
                            'source': 'WO.COST.DETAIL',
                            'table_index': i,
                            'data': table_data
                        })
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 3: Try work order history which contains cost data
        try:
            print("\n  Extracting from WO.HISTORY (contains cost history)...")
            response = self.api.get('/cgi-bin/mvi.exe/WO.HISTORY', timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                tables = soup.find_all('table')
                
                print(f"    Found {len(tables)} tables in history")
                
                for i, table in enumerate(tables):
                    table_data = self._extract_table_data(table)
                    if table_data:
                        # Check if this table contains cost data
                        headers = table_data.get('headers', [])
                        if any('cost' in str(h).lower() or 'amount' in str(h).lower() or 'total' in str(h).lower() for h in headers):
                            summaries.append({
                                'source': 'WO.HISTORY',
                                'table_index': i,
                                'data': table_data,
                                'type': 'cost_history'
                            })
                            print(f"      Found cost data in table {i}")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 4: Try to query by work order if we have a list
        work_orders = self.get_all_work_orders()
        
        # Also try to extract work order numbers from WO.INQUIRY page
        print("\n  Extracting work order numbers from WO.INQUIRY...")
        try:
            import re
            response = self.api.get('/cgi-bin/mvi.exe/WO.INQUIRY', timeout=15)
            if response.status_code == 200:
                # Find work order numbers in the HTML
                wo_patterns = [
                    r'WONO[=\s]+(\d+)',
                    r'WO[:\s]+(\d+)',
                    r'work[_\s]?order[:\s]+(\d+)',
                    r'value=["\'](\d+)["\'].*WONO',
                ]
                
                found_wos = set()
                for pattern in wo_patterns:
                    matches = re.findall(pattern, response.text, re.IGNORECASE)
                    found_wos.update(matches)
                
                if found_wos:
                    print(f"    Found {len(found_wos)} work order numbers in page")
                    work_orders.extend(list(found_wos))
                    work_orders = list(set(work_orders))  # Remove duplicates
        except Exception as e:
            print(f"    Error extracting WOs: {e}")
        
        if work_orders:
            print(f"\n  Attempting to extract cost summaries for {len(work_orders)} work orders...")
            print("  (This may take a while...)")
            
            for i, wo_no in enumerate(work_orders[:100], 1):  # Increased limit
                try:
                    # Try WO.STATUS.SUM first (detailed cost summary)
                    response = self.api.get(f'/cgi-bin/mvi.exe/WO.STATUS.SUM?WONO={wo_no}', timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        tables = soup.find_all('table')
                        
                        if tables:
                            for table in tables:
                                table_data = self._extract_table_data(table)
                                if table_data and table_data.get('rows'):
                                    summaries.append({
                                        'work_order': wo_no,
                                        'source': 'WO.STATUS.SUM',
                                        'data': table_data,
                                        'extracted_at': datetime.now().isoformat()
                                    })
                            
                            if i % 10 == 0:
                                print(f"    Processed {i}/{min(len(work_orders), 100)} work orders... ({len(summaries)} summaries found)")
                        
                        time.sleep(0.3)  # Be nice to the server
                        
                except Exception as e:
                    if 'timeout' not in str(e).lower():
                        print(f"    Error processing WO {wo_no}: {e}")
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        tables = soup.find_all('table')
                        
                        for table in tables:
                            table_data = self._extract_table_data(table)
                            if table_data:
                                summaries.append({
                                    'work_order': wo_no,
                                    'source': 'WO.COST.SUMMARY',
                                    'data': table_data
                                })
                        
                        if i % 10 == 0:
                            print(f"    Processed {i}/{min(len(work_orders), 50)} work orders...")
                        
                        time.sleep(0.5)  # Be nice to the server
                        
                except Exception as e:
                    print(f"    Error processing WO {wo_no}: {e}")
        
        return summaries
    
    def _extract_table_data(self, table):
        """Extract structured data from HTML table"""
        try:
            headers = []
            rows = []
            
            # Get headers from first row
            header_row = table.find('tr')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
            
            # Get data rows
            for row in table.find_all('tr')[1:]:
                cells = [td.get_text(strip=True) for td in row.find_all('td')]
                if cells:
                    rows.append(cells)
            
            if rows or headers:
                return {
                    'headers': headers,
                    'rows': rows,
                    'row_count': len(rows)
                }
        except Exception as e:
            print(f"      Error extracting table: {e}")
        
        return None
    
    def extract_all(self):
        """Extract all cost summaries"""
        print("=" * 80)
        print("Extracting ALL Detailed Cost Summaries")
        print("=" * 80)
        print(f"Started: {datetime.now()}")
        
        if not self.api.validate_session():
            print("[FAIL] Session invalid. Cannot extract data.")
            return None
        
        print("[OK] Session validated")
        
        # Extract all cost summaries
        summaries = self.extract_cost_summary()
        
        # Save results
        output_dir = get_project_root() / 'cost_summaries'
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save complete data
        output_file = output_dir / f'all_cost_summaries_{timestamp}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'extraction_date': datetime.now().isoformat(),
                'total_summaries': len(summaries),
                'summaries': summaries
            }, f, indent=2, default=str)
        
        print(f"\n[OK] Saved {len(summaries)} cost summaries to: {output_file}")
        
        # Also save as CSV for easier viewing
        self._save_as_csv(summaries, output_dir / f'cost_summaries_{timestamp}.csv')
        
        print(f"\n[OK] Also saved as CSV: cost_summaries_{timestamp}.csv")
        
        return summaries
    
    def _save_as_csv(self, summaries, csv_file):
        """Save summaries as CSV"""
        import csv
        
        try:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow(['Work Order', 'Source', 'Table Index', 'Headers', 'Row Count', 'Data Preview'])
                
                # Write data
                for summary in summaries:
                    wo = summary.get('work_order', 'N/A')
                    source = summary.get('source', 'N/A')
                    table_idx = summary.get('table_index', 'N/A')
                    data = summary.get('data', {})
                    headers = ', '.join(data.get('headers', []))
                    row_count = data.get('row_count', 0)
                    preview = str(data.get('rows', [])[:2])[:200] if data.get('rows') else ''
                    
                    writer.writerow([wo, source, table_idx, headers, row_count, preview])
        except Exception as e:
            print(f"[WARN] Could not save CSV: {e}")

def main():
    """Main execution"""
    extractor = CostSummaryExtractor()
    summaries = extractor.extract_all()
    
    if summaries:
        print("\n" + "=" * 80)
        print("Extraction Summary")
        print("=" * 80)
        print(f"Total cost summaries extracted: {len(summaries)}")
        print(f"Completed: {datetime.now()}")
        print("=" * 80)
    else:
        print("\n[WARN] No cost summaries extracted")

if __name__ == '__main__':
    main()

