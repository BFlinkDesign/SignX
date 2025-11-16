#!/usr/bin/env python3
"""
Extract ALL Detailed Cost Summaries using SO.CONTRACT.RUN Report Endpoint
Uses the actual cost summary report endpoint discovered
"""

import json
import re
import time
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from keyedin_api_enhanced import KeyedInAPIEnhanced, get_project_root
from urllib.parse import urlencode, quote

class CostSummaryReportExtractor:
    """Extract cost summaries using SO.CONTRACT.RUN report endpoint"""
    
    def __init__(self):
        self.api = KeyedInAPIEnhanced(auto_refresh=False)
        self.all_summaries = []
        
    def get_all_sales_orders(self):
        """Get all sales order numbers to query cost summaries for"""
        print("\n" + "=" * 80)
        print("Step 1: Finding All Sales Order Numbers")
        print("=" * 80)
        
        sales_orders = set()
        
        # Method 1: Try SO.CONTRACT.RUN without parameters (might list all)
        print("\n  Method 1: Checking SO.CONTRACT.RUN endpoint...")
        try:
            response = self.api.get('/cgi-bin/mvi.exe/SO.CONTRACT.RUN', timeout=15)
            if response.status_code == 200:
                # Extract sales order numbers from the page
                sono_nos = self._extract_sono_numbers(response.text)
                sales_orders.update(sono_nos)
                if sono_nos:
                    print(f"    Found {len(sono_nos)} sales order numbers")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 2: Try to find sales orders from work orders
        # Sales orders are often linked to work orders
        print("\n  Method 2: Extracting from work order data...")
        try:
            # Get work order status summaries which contain sales order info
            response = self.api.get('/cgi-bin/mvi.exe/WO.STATUS.SUM', timeout=15)
            if response.status_code == 200:
                # Look for sales order references
                sono_patterns = [
                    r'SONO[=\s:]+([\d.]+)',
                    r'Sales[_\s]?Order[#:\s]+([\d.]+)',
                    r'SO[#:\s]+([\d.]+)',
                ]
                
                for pattern in sono_patterns:
                    matches = re.findall(pattern, response.text, re.IGNORECASE)
                    sales_orders.update(matches)
                
                if sales_orders:
                    print(f"    Found {len(sales_orders)} sales order numbers")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 3: Try known sales order from URL (12530.1)
        # Use it as a seed to find pattern
        known_sono = '12530.1'
        sales_orders.add(known_sono)
        print(f"\n  Method 3: Using known sales order {known_sono} as seed...")
        
        # Try nearby sales orders
        try:
            base_sono = float(known_sono)
            # Try ±100 range
            for offset in range(-100, 101):
                test_sono = f"{base_sono + offset:.1f}"
                # Quick test
                response = self.api.get(
                    f'/cgi-bin/mvi.exe/SO.CONTRACT.RUN?SONO={quote(test_sono)}&REPORT_OPT=D&REPORT_WHERE=P',
                    timeout=3
                )
                if response.status_code == 200 and 'error' not in response.text.lower()[:200]:
                    sales_orders.add(test_sono)
                    if len(sales_orders) % 10 == 0:
                        print(f"      Found {len(sales_orders)} sales orders so far...")
        except Exception as e:
            print(f"    Error in range discovery: {e}")
        
        sales_orders_list = sorted(list(sales_orders), key=lambda x: float(x) if '.' in x else float(x + '.0'))
        
        print(f"\n  Total unique sales orders found: {len(sales_orders_list)}")
        if sales_orders_list:
            print(f"  Range: {sales_orders_list[0]} to {sales_orders_list[-1]}")
            print(f"  Sample: {sales_orders_list[:10]}")
        
        return sales_orders_list
    
    def _extract_sono_numbers(self, html):
        """Extract sales order numbers from HTML"""
        sono_numbers = set()
        
        patterns = [
            r'SONO[=\s:]+([\d.]+)',
            r'Sales[_\s]?Order[#:\s]+([\d.]+)',
            r'SO[#:\s]+([\d.]+)',
            r'value=["\']([\d.]+)["\'].*SONO',
            r'href=["\'][^"\']*SONO=([\d.]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            sono_numbers.update(matches)
        
        return sono_numbers
    
    def extract_cost_summary_for_sono(self, sales_order_no, report_option='D'):
        """Extract detailed cost summary for a sales order"""
        try:
            # Use SO.CONTRACT.RUN endpoint with detailed report option
            params = {
                'SONO': sales_order_no,
                'REPORT_OPT': report_option,  # D = Detailed
                'START_DATE': '',
                'END_DATE': '',
                'REPORT_WHERE': 'P',  # P = ? (need to check what this means)
                'CLOSE_WINDOW': 'N'
            }
            
            # Build URL with proper encoding
            param_str = urlencode(params, quote_via=quote)
            endpoint = f'/cgi-bin/mvi.exe/SO.CONTRACT.RUN?{param_str}'
            
            response = self.api.get(endpoint, timeout=15)
            
            if response.status_code == 200:
                # Check if it's an error or actual report
                if 'error' in response.text.lower()[:500] or 'not found' in response.text.lower()[:500]:
                    return None
                
                soup = BeautifulSoup(response.text, 'html.parser')
                tables = soup.find_all('table')
                
                if tables:
                    summary = {
                        'sales_order': sales_order_no,
                        'source': 'SO.CONTRACT.RUN',
                        'report_option': report_option,
                        'extracted_at': datetime.now().isoformat(),
                        'url': endpoint,
                        'tables': []
                    }
                    
                    # Extract all tables
                    for i, table in enumerate(tables):
                        table_data = self._extract_table_data(table)
                        if table_data and (table_data.get('rows') or table_data.get('headers')):
                            summary['tables'].append({
                                'table_index': i,
                                'headers': table_data.get('headers', []),
                                'rows': table_data.get('rows', []),
                                'row_count': len(table_data.get('rows', []))
                            })
                    
                    # Also check for report view link
                    report_view_links = soup.find_all('a', href=True)
                    for link in report_view_links:
                        href = link.get('href', '')
                        if 'REPORT.VIEW' in href or 'VIEW.LOG' in href:
                            summary['report_view_url'] = href
                    
                    if summary['tables']:
                        return summary
                        
        except Exception as e:
            return {'sales_order': sales_order_no, 'error': str(e)}
        
        return None
    
    def _extract_table_data(self, table):
        """Extract data from HTML table"""
        try:
            headers = []
            rows = []
            
            # Get headers
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
            
            # Extract data rows
            for row in data_rows:
                cells = [td.get_text(strip=True) for td in row.find_all('td')]
                if cells:
                    rows.append(cells)
            
            return {
                'headers': headers,
                'rows': rows,
                'row_count': len(rows)
            }
        except Exception as e:
            return None
    
    def extract_all(self, sales_orders=None, max_sales_orders=None):
        """Extract all cost summaries"""
        print("=" * 80)
        print("Extracting ALL Detailed Cost Summaries via SO.CONTRACT.RUN")
        print("=" * 80)
        print(f"Started: {datetime.now()}")
        
        if not self.api.validate_session():
            print("[FAIL] Session invalid. Cannot extract data.")
            return None
        
        print("[OK] Session validated")
        
        # Get sales order list
        if sales_orders is None:
            sales_orders = self.get_all_sales_orders()
        
        if not sales_orders:
            print("\n[WARN] No sales orders found.")
            print("Trying with known sales order from URL...")
            sales_orders = ['12530.1']  # Known from user's URL
        
        if max_sales_orders:
            sales_orders = sales_orders[:max_sales_orders]
            print(f"\nLimiting to first {max_sales_orders} sales orders")
        
        print(f"\n" + "=" * 80)
        print(f"Extracting Cost Summaries for {len(sales_orders)} Sales Orders")
        print("=" * 80)
        print("(This will take a while - please be patient...)")
        print(f"Estimated time: ~{len(sales_orders) * 0.5 / 60:.1f} minutes")
        
        successful = 0
        failed = 0
        not_found = 0
        
        for i, sono in enumerate(sales_orders, 1):
            try:
                # Try detailed report option first
                summary = self.extract_cost_summary_for_sono(sono, report_option='D')
                
                if summary:
                    if 'error' not in summary:
                        self.all_summaries.append(summary)
                        successful += 1
                        
                        if i % 10 == 0 or successful % 10 == 0:
                            print(f"  Progress: {i}/{len(sales_orders)} - {successful} summaries extracted, {failed} failed, {not_found} not found")
                    else:
                        failed += 1
                else:
                    not_found += 1
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                failed += 1
                if i % 50 == 0:
                    print(f"  Exception on SO {sono}: {e}")
        
        # Save results
        if self.all_summaries:
            output_dir = get_project_root() / 'cost_summaries'
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save complete JSON
            output_file = output_dir / f'all_cost_summaries_so_contract_{timestamp}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'extraction_date': datetime.now().isoformat(),
                    'total_sales_orders_queried': len(sales_orders),
                    'total_summaries_extracted': len(self.all_summaries),
                    'total_tables': sum(len(s.get('tables', [])) for s in self.all_summaries),
                    'successful': successful,
                    'failed': failed,
                    'not_found': not_found,
                    'summaries': self.all_summaries
                }, f, indent=2, default=str)
            
            print(f"\n[OK] Extraction Complete!")
            print(f"     Sales orders queried: {len(sales_orders)}")
            print(f"     Summaries extracted: {len(self.all_summaries)}")
            print(f"     Total tables: {sum(len(s.get('tables', [])) for s in self.all_summaries)}")
            print(f"     Successful: {successful}, Failed: {failed}, Not Found: {not_found}")
            print(f"     Saved to: {output_file}")
            
            # Save individual files
            individual_dir = output_dir / 'individual_summaries_so'
            individual_dir.mkdir(exist_ok=True)
            
            for summary in self.all_summaries:
                sono = summary.get('sales_order')
                if sono:
                    sono_file = individual_dir / f'SO_{sono.replace(".", "_")}_cost_summary_{timestamp}.json'
                    with open(sono_file, 'w', encoding='utf-8') as f:
                        json.dump(summary, f, indent=2, default=str)
            
            print(f"     Individual files: {individual_dir}")
        
        return self.all_summaries

def main():
    """Main execution"""
    import sys
    
    extractor = CostSummaryReportExtractor()
    
    # Check for command line arguments
    sales_orders = None
    max_sos = None
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.isdigit():
            max_sos = int(arg)
        elif Path(arg).exists():
            with open(arg, 'r') as f:
                data = json.load(f)
                sales_orders = data.get('sales_orders', [])
    
    summaries = extractor.extract_all(sales_orders=sales_orders, max_sales_orders=max_sos)
    
    if summaries:
        print("\n" + "=" * 80)
        print("[SUCCESS] Extraction Complete!")
        print("=" * 80)
        print(f"Total detailed cost summaries: {len(summaries)}")
        print(f"Total tables extracted: {sum(len(s.get('tables', [])) for s in summaries)}")
        print(f"Completed: {datetime.now()}")
        print("=" * 80)

if __name__ == '__main__':
    main()


