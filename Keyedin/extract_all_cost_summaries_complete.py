#!/usr/bin/env python3
"""
Complete Solution: Extract ALL Detailed Cost Summaries
- Uses WO.STATUS.SUM endpoint (the detailed cost summary)
- Supports manual work order list input
- Tries to discover work orders automatically
- Extracts comprehensive cost data
"""

import json
import re
import time
import sys
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from keyedin_api_enhanced import KeyedInAPIEnhanced, get_project_root

class CompleteCostSummaryExtractor:
    """Complete cost summary extraction solution"""
    
    def __init__(self):
        self.api = KeyedInAPIEnhanced(auto_refresh=False)
        self.all_summaries = []
        
    def discover_work_orders(self):
        """Try multiple methods to discover work order numbers"""
        print("\n" + "=" * 80)
        print("Discovering Work Order Numbers")
        print("=" * 80)
        
        work_orders = set()
        
        # Method 1: Check if there's a saved list
        saved_list = get_project_root() / 'all_work_orders.json'
        if saved_list.exists():
            try:
                with open(saved_list, 'r') as f:
                    data = json.load(f)
                    if 'work_orders' in data:
                        work_orders.update(data['work_orders'])
                        print(f"  Loaded {len(data['work_orders'])} work orders from saved list")
            except:
                pass
        
        # Method 2: Try WO.STATUS.SUM form - might have default data
        print("\n  Checking WO.STATUS.SUM for work order references...")
        try:
            response = self.api.get('/cgi-bin/mvi.exe/WO.STATUS.SUM', timeout=15)
            if response.status_code == 200:
                wo_nos = self._extract_numbers(response.text)
                work_orders.update(wo_nos)
                if wo_nos:
                    print(f"    Found {len(wo_nos)} work order numbers")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 3: Try WO.HISTORY - extract from cost history tables
        print("\n  Extracting from WO.HISTORY cost data...")
        try:
            response = self.api.get('/cgi-bin/mvi.exe/WO.HISTORY', timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                tables = soup.find_all('table')
                
                for table in tables:
                    for row in table.find_all('tr'):
                        # Check links
                        for link in row.find_all('a', href=True):
                            href = link.get('href', '')
                            match = re.search(r'WONO=(\d+)', href, re.IGNORECASE)
                            if match:
                                work_orders.add(match.group(1))
                        
                        # Check cells for work order numbers
                        cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                        for cell in cells:
                            # Look for work order patterns
                            matches = re.findall(r'\b(\d{4,8})\b', cell)
                            for match in matches:
                                if not re.match(r'^(19|20)\d{2}', match):  # Not a year
                                    work_orders.add(match)
                
                if work_orders:
                    print(f"    Found {len(work_orders)} work order numbers in history")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 4: Try WO.GROUP.ANALYSIS
        print("\n  Checking WO.GROUP.ANALYSIS...")
        try:
            response = self.api.get('/cgi-bin/mvi.exe/WO.GROUP.ANALYSIS', timeout=15)
            if response.status_code == 200:
                wo_nos = self._extract_numbers(response.text)
                work_orders.update(wo_nos)
                if wo_nos:
                    print(f"    Found {len(wo_nos)} work order numbers")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Method 5: Try range-based discovery (if we know approximate range)
        # This is a fallback - try common work order number ranges
        print("\n  Attempting range-based discovery...")
        print("    (Trying common work order number patterns)")
        
        # Try a few known work orders first to establish pattern
        known_wos = ['8443', '7831576']  # From previous extraction
        
        # If we have known WOs, try nearby numbers
        for known_wo in known_wos:
            try:
                wo_int = int(known_wo)
                # Try ±100 range
                for test_wo in range(max(1, wo_int - 100), wo_int + 101):
                    test_wo_str = str(test_wo)
                    # Quick test - just check if endpoint responds (don't extract yet)
                    response = self.api.get(f'/cgi-bin/mvi.exe/WO.STATUS.SUM?WONO={test_wo_str}', timeout=5)
                    if response.status_code == 200 and 'error' not in response.text.lower()[:200]:
                        work_orders.add(test_wo_str)
                        if len(work_orders) % 10 == 0:
                            print(f"      Found {len(work_orders)} work orders so far...")
            except:
                pass
        
        work_orders_list = sorted([wo for wo in work_orders if wo.isdigit()], key=lambda x: int(x))
        
        print(f"\n  Total unique work orders discovered: {len(work_orders_list)}")
        if work_orders_list:
            print(f"  Range: {work_orders_list[0]} to {work_orders_list[-1]}")
            print(f"  Sample: {work_orders_list[:10]}")
        
        return work_orders_list
    
    def _extract_numbers(self, text):
        """Extract potential work order numbers from text"""
        numbers = set()
        
        # Patterns for work order numbers
        patterns = [
            r'WONO[=\s:]+(\d+)',
            r'WO[#:\s]+(\d+)',
            r'href=["\'][^"\']*WONO=(\d+)',
            r'href=["\'][^"\']*WO\.STATUS[^"\']*WONO=(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            numbers.update(matches)
        
        return numbers
    
    def extract_cost_summary_for_wo(self, work_order_no):
        """Extract detailed cost summary for a work order"""
        try:
            # Use WO.STATUS.SUM - the detailed cost summary endpoint
            response = self.api.get(f'/cgi-bin/mvi.exe/WO.STATUS.SUM?WONO={work_order_no}', timeout=15)
            
            if response.status_code == 200:
                # Check if it's an error page or actual data
                if 'error' in response.text.lower()[:500] or 'not found' in response.text.lower()[:500]:
                    return None
                
                soup = BeautifulSoup(response.text, 'html.parser')
                tables = soup.find_all('table')
                
                if tables:
                    summary = {
                        'work_order': work_order_no,
                        'source': 'WO.STATUS.SUM',
                        'extracted_at': datetime.now().isoformat(),
                        'url': f'/cgi-bin/mvi.exe/WO.STATUS.SUM?WONO={work_order_no}',
                        'tables': []
                    }
                    
                    # Extract all tables with detailed data
                    for i, table in enumerate(tables):
                        table_data = self._extract_table_data(table)
                        if table_data and (table_data.get('rows') or table_data.get('headers')):
                            summary['tables'].append({
                                'table_index': i,
                                'headers': table_data.get('headers', []),
                                'rows': table_data.get('rows', []),
                                'row_count': len(table_data.get('rows', []))
                            })
                    
                    # Only return if we have actual data
                    if summary['tables']:
                        return summary
                        
        except Exception as e:
            return {'work_order': work_order_no, 'error': str(e)}
        
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
                    # First row might be header
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
    
    def extract_all(self, work_orders=None, max_work_orders=None):
        """Extract all cost summaries"""
        print("=" * 80)
        print("Extracting ALL Detailed Cost Summaries")
        print("=" * 80)
        print(f"Started: {datetime.now()}")
        
        if not self.api.validate_session():
            print("[FAIL] Session invalid. Cannot extract data.")
            return None
        
        print("[OK] Session validated")
        
        # Get work order list
        if work_orders is None:
            work_orders = self.discover_work_orders()
        
        if not work_orders:
            print("\n[WARN] No work orders found automatically.")
            print("Options:")
            print("  1. Provide work order list manually")
            print("  2. Check if work orders need to be queried differently")
            print("  3. Use Informer BI portal for data export")
            return None
        
        if max_work_orders:
            work_orders = work_orders[:max_work_orders]
            print(f"\nLimiting to first {max_work_orders} work orders")
        
        print(f"\n" + "=" * 80)
        print(f"Extracting Cost Summaries for {len(work_orders)} Work Orders")
        print("=" * 80)
        print("(This will take a while - please be patient...)")
        print(f"Estimated time: ~{len(work_orders) * 0.5 / 60:.1f} minutes")
        
        successful = 0
        failed = 0
        not_found = 0
        
        for i, wo_no in enumerate(work_orders, 1):
            try:
                summary = self.extract_cost_summary_for_wo(wo_no)
                
                if summary:
                    if 'error' not in summary:
                        self.all_summaries.append(summary)
                        successful += 1
                        
                        if i % 10 == 0 or successful % 10 == 0:
                            print(f"  Progress: {i}/{len(work_orders)} - {successful} summaries extracted, {failed} failed, {not_found} not found")
                    else:
                        failed += 1
                else:
                    not_found += 1
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                failed += 1
                if i % 50 == 0:
                    print(f"  Exception on WO {wo_no}: {e}")
        
        # Save results
        if self.all_summaries:
            output_dir = get_project_root() / 'cost_summaries'
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save complete JSON
            output_file = output_dir / f'all_detailed_cost_summaries_{timestamp}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'extraction_date': datetime.now().isoformat(),
                    'total_work_orders_queried': len(work_orders),
                    'total_summaries_extracted': len(self.all_summaries),
                    'total_tables': sum(len(s.get('tables', [])) for s in self.all_summaries),
                    'successful': successful,
                    'failed': failed,
                    'not_found': not_found,
                    'summaries': self.all_summaries
                }, f, indent=2, default=str)
            
            print(f"\n[OK] Extraction Complete!")
            print(f"     Work orders queried: {len(work_orders)}")
            print(f"     Summaries extracted: {len(self.all_summaries)}")
            print(f"     Total tables: {sum(len(s.get('tables', [])) for s in self.all_summaries)}")
            print(f"     Successful: {successful}, Failed: {failed}, Not Found: {not_found}")
            print(f"     Saved to: {output_file}")
            
            # Save individual files
            individual_dir = output_dir / 'individual_summaries'
            individual_dir.mkdir(exist_ok=True)
            
            for summary in self.all_summaries:
                wo_no = summary.get('work_order')
                if wo_no:
                    wo_file = individual_dir / f'WO_{wo_no}_cost_summary_{timestamp}.json'
                    with open(wo_file, 'w', encoding='utf-8') as f:
                        json.dump(summary, f, indent=2, default=str)
            
            print(f"     Individual files: {individual_dir}")
        
        return self.all_summaries

def main():
    """Main execution"""
    import sys
    
    extractor = CompleteCostSummaryExtractor()
    
    # Check for command line arguments
    work_orders = None
    max_wos = None
    
    if len(sys.argv) > 1:
        # Check if it's a number (max work orders) or file (work order list)
        arg = sys.argv[1]
        if arg.isdigit():
            max_wos = int(arg)
        elif Path(arg).exists():
            # Load work orders from file
            with open(arg, 'r') as f:
                data = json.load(f)
                work_orders = data.get('work_orders', [])
                print(f"Loaded {len(work_orders)} work orders from {arg}")
    
    summaries = extractor.extract_all(work_orders=work_orders, max_work_orders=max_wos)
    
    if summaries:
        print("\n" + "=" * 80)
        print("[SUCCESS] Extraction Complete!")
        print("=" * 80)
        print(f"Total detailed cost summaries: {len(summaries)}")
        print(f"Total tables extracted: {sum(len(s.get('tables', [])) for s in summaries)}")
        print(f"Completed: {datetime.now()}")
        print("=" * 80)
    else:
        print("\n[INFO] No summaries extracted")
        print("\nTo extract with a work order list:")
        print("  python extract_all_cost_summaries_complete.py work_orders.json")

if __name__ == '__main__':
    main()

