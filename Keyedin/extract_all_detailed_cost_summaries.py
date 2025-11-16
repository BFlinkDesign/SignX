#!/usr/bin/env python3
"""
Extract EVERY Detailed Cost Summary from KeyedIn System
Uses WO.STATUS.SUM endpoint to get detailed cost summaries for all work orders
"""

import json
import re
import time
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from keyedin_api_enhanced import KeyedInAPIEnhanced, get_project_root

class DetailedCostSummaryExtractor:
    """Extract all detailed cost summaries using WO.STATUS.SUM"""
    
    def __init__(self):
        self.api = KeyedInAPIEnhanced(auto_refresh=False)
        self.all_summaries = []
        self.work_orders = []
        
    def get_all_work_order_numbers(self):
        """Extract all work order numbers from the system"""
        print("\n" + "=" * 80)
        print("Step 1: Finding All Work Order Numbers")
        print("=" * 80)
        
        work_orders = set()
        
        # Method 1: Try WO.INQUIRY with different query parameters to get all WOs
        print("\n  Method 1: Querying WO.INQUIRY for work orders...")
        try:
            # Try with empty/wide parameters to get all work orders
            params_variations = [
                {},  # No params - might return all
                {'STATUS': 'ALL'},
                {'STATUS': ''},
                {'WONO': ''},
            ]
            
            for params in params_variations:
                try:
                    response = self.api.get('/cgi-bin/mvi.exe/WO.INQUIRY', params=params, timeout=15)
                    if response.status_code == 200:
                        # Extract work order numbers from response
                        wo_nos = self._extract_wo_numbers_from_html(response.text)
                        work_orders.update(wo_nos)
                        if wo_nos:
                            print(f"    Found {len(wo_nos)} work orders with params {params}")
                except:
                    pass
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 2: Try WORKORDER.LIST
        print("\n  Method 2: Checking WORKORDER.LIST...")
        try:
            response = self.api.get('/cgi-bin/mvi.exe/WORKORDER.LIST', timeout=15)
            if response.status_code == 200:
                wo_nos = self._extract_wo_numbers_from_html(response.text)
                work_orders.update(wo_nos)
                if wo_nos:
                    print(f"    Found {len(wo_nos)} work orders")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 3: Try WO.HISTORY (contains work order references)
        print("\n  Method 3: Checking WO.HISTORY...")
        try:
            response = self.api.get('/cgi-bin/mvi.exe/WO.HISTORY', timeout=15)
            if response.status_code == 200:
                wo_nos = self._extract_wo_numbers_from_html(response.text)
                work_orders.update(wo_nos)
                if wo_nos:
                    print(f"    Found {len(wo_nos)} work orders")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 4: Try to get work orders from menu or other endpoints
        print("\n  Method 4: Checking menu structure for work order references...")
        try:
            menu = self.api.get_menu()
            menu_str = json.dumps(menu)
            # Look for work order numbers in menu
            wo_nos = re.findall(r'\b\d{4,}\b', menu_str)  # 4+ digit numbers might be WO numbers
            work_orders.update(wo_nos)
            if wo_nos:
                print(f"    Found {len(wo_nos)} potential work order numbers")
        except Exception as e:
            print(f"    Error: {e}")
        
        work_orders_list = sorted(list(work_orders), key=lambda x: int(x) if x.isdigit() else 0)
        print(f"\n  Total unique work orders found: {len(work_orders_list)}")
        
        if work_orders_list:
            print(f"  Sample: {work_orders_list[:10]}")
        
        return work_orders_list
    
    def _extract_wo_numbers_from_html(self, html):
        """Extract work order numbers from HTML content"""
        wo_numbers = set()
        
        # Patterns to find work order numbers
        patterns = [
            r'WONO[=\s:]+(\d+)',  # WONO=12345 or WONO: 12345
            r'WO[#:\s]+(\d+)',    # WO#12345 or WO: 12345
            r'work[_\s]?order[#:\s]+(\d+)',  # Work Order #12345
            r'value=["\'](\d{4,})["\']',  # Value="12345" (4+ digits)
            r'href=["\'][^"\']*WONO=(\d+)',  # Links with WONO parameter
            r'href=["\'][^"\']*WO\.STATUS[^"\']*WONO=(\d+)',  # Links to WO.STATUS with WONO
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            wo_numbers.update(matches)
        
        # Also check table cells for numeric values that might be WO numbers
        soup = BeautifulSoup(html, 'html.parser')
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                for cell in cells:
                    # Look for 4-8 digit numbers that might be work orders
                    numbers = re.findall(r'\b(\d{4,8})\b', cell)
                    for num in numbers:
                        # Filter out dates and other common number patterns
                        if not re.match(r'^(19|20)\d{2}', num):  # Not a year
                            wo_numbers.add(num)
        
        return wo_numbers
    
    def extract_detailed_cost_summary(self, work_order_no):
        """Extract detailed cost summary for a specific work order"""
        try:
            # Use WO.STATUS.SUM - the detailed cost summary endpoint
            response = self.api.get(f'/cgi-bin/mvi.exe/WO.STATUS.SUM?WONO={work_order_no}', timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                tables = soup.find_all('table')
                
                if tables:
                    summary_data = {
                        'work_order': work_order_no,
                        'source': 'WO.STATUS.SUM',
                        'extracted_at': datetime.now().isoformat(),
                        'tables': []
                    }
                    
                    # Extract all tables
                    for i, table in enumerate(tables):
                        table_data = self._extract_detailed_table_data(table)
                        if table_data:
                            summary_data['tables'].append({
                                'table_index': i,
                                'headers': table_data.get('headers', []),
                                'rows': table_data.get('rows', []),
                                'row_count': table_data.get('row_count', 0)
                            })
                    
                    # Also save raw HTML for reference
                    summary_data['raw_html_length'] = len(response.text)
                    
                    return summary_data
                    
        except Exception as e:
            return {'work_order': work_order_no, 'error': str(e)}
        
        return None
    
    def _extract_detailed_table_data(self, table):
        """Extract detailed data from HTML table"""
        try:
            headers = []
            rows = []
            
            # Get headers - check for th or first row
            header_row = table.find('tr')
            if header_row:
                # Check if first row has th tags (header row)
                th_tags = header_row.find_all('th')
                if th_tags:
                    headers = [th.get_text(strip=True) for th in th_tags]
                    # Data rows start from second row
                    data_rows = table.find_all('tr')[1:]
                else:
                    # First row might be header without th tags
                    headers = [td.get_text(strip=True) for td in header_row.find_all('td')]
                    data_rows = table.find_all('tr')[1:]
            else:
                data_rows = table.find_all('tr')
            
            # Extract data rows
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
        except Exception as e:
            print(f"      Error extracting table: {e}")
        
        return None
    
    def extract_all(self, max_work_orders=None):
        """Extract all detailed cost summaries"""
        print("=" * 80)
        print("Extracting ALL Detailed Cost Summaries")
        print("=" * 80)
        print(f"Started: {datetime.now()}")
        
        if not self.api.validate_session():
            print("[FAIL] Session invalid. Cannot extract data.")
            return None
        
        print("[OK] Session validated")
        
        # Step 1: Get all work order numbers
        work_orders = self.get_all_work_order_numbers()
        
        if not work_orders:
            print("\n[WARN] No work orders found. Trying alternative method...")
            # Try to extract from WO.STATUS.SUM form to see what parameters it needs
            try:
                response = self.api.get('/cgi-bin/mvi.exe/WO.STATUS.SUM', timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Save the form HTML for analysis
                    form_file = get_project_root() / 'wo_status_sum_form.html'
                    with open(form_file, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    print(f"  Saved form HTML to: {form_file}")
                    print("  Please check the form to see what parameters are needed")
            except:
                pass
        
        # Step 2: Extract cost summary for each work order
        if work_orders:
            if max_work_orders:
                work_orders = work_orders[:max_work_orders]
            
            print(f"\n" + "=" * 80)
            print(f"Step 2: Extracting Cost Summaries for {len(work_orders)} Work Orders")
            print("=" * 80)
            print("(This will take a while - please be patient...)")
            
            successful = 0
            failed = 0
            
            for i, wo_no in enumerate(work_orders, 1):
                try:
                    summary = self.extract_detailed_cost_summary(wo_no)
                    
                    if summary and 'error' not in summary:
                        if summary.get('tables'):
                            self.all_summaries.append(summary)
                            successful += 1
                            
                            if i % 10 == 0:
                                print(f"  Progress: {i}/{len(work_orders)} - {successful} summaries extracted")
                    else:
                        failed += 1
                        if summary and 'error' in summary:
                            if i % 50 == 0:  # Only print errors every 50th to avoid spam
                                print(f"  Error on WO {wo_no}: {summary.get('error', 'Unknown')}")
                    
                    # Rate limiting
                    time.sleep(0.5)  # Half second between requests
                    
                except Exception as e:
                    failed += 1
                    if i % 50 == 0:
                        print(f"  Exception on WO {wo_no}: {e}")
            
            print(f"\n  Extraction complete: {successful} successful, {failed} failed")
        else:
            # Try to extract whatever is available without work order numbers
            print("\n  No work orders found. Attempting to extract available cost data...")
            try:
                response = self.api.get('/cgi-bin/mvi.exe/WO.STATUS.SUM', timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    tables = soup.find_all('table')
                    
                    if tables:
                        summary_data = {
                            'source': 'WO.STATUS.SUM (no WONO)',
                            'extracted_at': datetime.now().isoformat(),
                            'tables': []
                        }
                        
                        for i, table in enumerate(tables):
                            table_data = self._extract_detailed_table_data(table)
                            if table_data:
                                summary_data['tables'].append({
                                    'table_index': i,
                                    'headers': table_data.get('headers', []),
                                    'rows': table_data.get('rows', []),
                                    'row_count': table_data.get('row_count', 0)
                                })
                        
                        if summary_data['tables']:
                            self.all_summaries.append(summary_data)
                            print(f"  Extracted {len(summary_data['tables'])} tables")
            except Exception as e:
                print(f"  Error: {e}")
        
        # Step 3: Save results
        if self.all_summaries:
            output_dir = get_project_root() / 'cost_summaries'
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save complete JSON
            output_file = output_dir / f'all_detailed_cost_summaries_{timestamp}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'extraction_date': datetime.now().isoformat(),
                    'total_summaries': len(self.all_summaries),
                    'total_tables': sum(len(s.get('tables', [])) for s in self.all_summaries),
                    'summaries': self.all_summaries
                }, f, indent=2, default=str)
            
            print(f"\n[OK] Saved {len(self.all_summaries)} detailed cost summaries")
            print(f"     Total tables extracted: {sum(len(s.get('tables', [])) for s in self.all_summaries)}")
            print(f"     File: {output_file}")
            
            # Also save individual files per work order for easier access
            individual_dir = output_dir / 'individual_summaries'
            individual_dir.mkdir(exist_ok=True)
            
            for summary in self.all_summaries:
                wo_no = summary.get('work_order', 'unknown')
                if wo_no != 'unknown':
                    wo_file = individual_dir / f'cost_summary_WO_{wo_no}_{timestamp}.json'
                    with open(wo_file, 'w', encoding='utf-8') as f:
                        json.dump(summary, f, indent=2, default=str)
            
            print(f"     Individual files saved to: {individual_dir}")
        
        return self.all_summaries

def main():
    """Main execution"""
    extractor = DetailedCostSummaryExtractor()
    
    # Ask user if they want to limit the number (for testing)
    import sys
    max_wos = None
    if len(sys.argv) > 1:
        try:
            max_wos = int(sys.argv[1])
            print(f"Limiting to first {max_wos} work orders (for testing)")
        except:
            pass
    
    summaries = extractor.extract_all(max_work_orders=max_wos)
    
    if summaries:
        print("\n" + "=" * 80)
        print("Extraction Complete!")
        print("=" * 80)
        print(f"Total detailed cost summaries extracted: {len(summaries)}")
        print(f"Total tables: {sum(len(s.get('tables', [])) for s in summaries)}")
        print(f"Completed: {datetime.now()}")
        print("=" * 80)
    else:
        print("\n[WARN] No cost summaries extracted")
        print("This might mean:")
        print("  1. No work orders found in the system")
        print("  2. Work order numbers need to be provided differently")
        print("  3. Check wo_status_sum_form.html to see form requirements")

if __name__ == '__main__':
    main()


