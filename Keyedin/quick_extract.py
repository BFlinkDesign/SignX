#!/usr/bin/env python3
"""
Quick Data Extraction Tool
Simple interface to extract data from KeyedIn endpoints
"""

from keyedin_api_enhanced import KeyedInAPIEnhanced
from bs4 import BeautifulSoup
import json
from pathlib import Path

def extract_endpoint(api, endpoint, name=None):
    """Extract data from a single endpoint"""
    name = name or endpoint.split('/')[-1]
    print(f"\nExtracting: {name}")
    print(f"  Endpoint: {endpoint}")
    
    try:
        response = api.get(endpoint, timeout=15)
        
        if response.status_code == 200:
            # Try JSON first
            try:
                data = response.json()
                print(f"  [OK] JSON data: {len(str(data))} chars")
                return {'type': 'json', 'data': data, 'status': 200}
            except:
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                tables = soup.find_all('table')
                forms = soup.find_all('form')
                
                # Extract table data
                table_data = []
                for table in tables:
                    rows = []
                    for tr in table.find_all('tr'):
                        cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                        if cells:
                            rows.append(cells)
                    if rows:
                        table_data.append(rows)
                
                print(f"  [OK] HTML data: {len(response.text):,} bytes, {len(tables)} tables, {len(forms)} forms")
                return {
                    'type': 'html',
                    'length': len(response.text),
                    'tables': len(tables),
                    'forms': len(forms),
                    'table_data': table_data,
                    'content': response.text,
                    'status': 200
                }
        else:
            print(f"  [WARN] Status {response.status_code}")
            return {'status': response.status_code, 'error': 'Non-200 status'}
            
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return {'error': str(e)}

def main():
    """Interactive data extraction"""
    print("=" * 80)
    print("KeyedIn Quick Data Extraction")
    print("=" * 80)
    
    api = KeyedInAPIEnhanced(auto_refresh=False)
    
    if not api.validate_session():
        print("[FAIL] Session invalid. Please refresh cookies.")
        return
    
    print("[OK] Session validated\n")
    
    # Common endpoints
    endpoints = {
        '1': ('Menu', '/cgi-bin/mvi.exe/WEB.MENU?USERNAME=BRADYF'),
        '2': ('Work Order Inquiry', '/cgi-bin/mvi.exe/WO.INQUIRY'),
        '3': ('Work Order History', '/cgi-bin/mvi.exe/WO.HISTORY'),
        '4': ('Work Order List', '/cgi-bin/mvi.exe/WORKORDER.LIST'),
        '5': ('Service Call List', '/cgi-bin/mvi.exe/SERVICE.CALL.LIST'),
        '6': ('Assigned Service Calls', '/cgi-bin/mvi.exe/WIDGET.ASSIGNED.SERVICE.CALLS?ACTION=AJAX'),
        '7': ('CRM Tasks', '/cgi-bin/mvi.exe/WIDGET.CRM.TASKS?ACTION=AJAX'),
        '8': ('All Work Order Endpoints', 'ALL_WO'),
        '9': ('All Widgets', 'ALL_WIDGETS'),
        '10': ('Custom Endpoint', 'CUSTOM'),
    }
    
    print("Available endpoints:")
    for key, (name, _) in endpoints.items():
        print(f"  {key}. {name}")
    
    choice = input("\nSelect endpoint (1-10) or 'q' to quit: ").strip()
    
    if choice.lower() == 'q':
        return
    
    if choice == '8':  # All Work Order endpoints
        wo_endpoints = [
            ('WO Inquiry', '/cgi-bin/mvi.exe/WO.INQUIRY'),
            ('WO History', '/cgi-bin/mvi.exe/WO.HISTORY'),
            ('WO Cost Summary', '/cgi-bin/mvi.exe/WO.COST.SUMMARY'),
            ('WO Completion', '/cgi-bin/mvi.exe/WO.COMPLETION.INQUIRY'),
            ('WO Group Analysis', '/cgi-bin/mvi.exe/WO.GROUP.ANALYSIS'),
            ('Work Order List', '/cgi-bin/mvi.exe/WORKORDER.LIST'),
        ]
        results = {}
        for name, endpoint in wo_endpoints:
            results[name] = extract_endpoint(api, endpoint, name)
        
    elif choice == '9':  # All Widgets
        widget_endpoints = [
            ('Assigned Service Calls', '/cgi-bin/mvi.exe/WIDGET.ASSIGNED.SERVICE.CALLS?ACTION=AJAX'),
            ('Assigned Milestones', '/cgi-bin/mvi.exe/WIDGET.ASSIGNED.MILESTONES?ACTION=AJAX'),
            ('CRM Tasks', '/cgi-bin/mvi.exe/WIDGET.CRM.TASKS?ACTION=AJAX'),
            ('FYI', '/cgi-bin/mvi.exe/WIDGET.FYI?ACTION=AJAX'),
        ]
        results = {}
        for name, endpoint in widget_endpoints:
            results[name] = extract_endpoint(api, endpoint, name)
            
    elif choice == '10':  # Custom endpoint
        endpoint = input("Enter endpoint (e.g., /cgi-bin/mvi.exe/ENDPOINT): ").strip()
        if endpoint:
            results = {'Custom': extract_endpoint(api, endpoint, 'Custom')}
        else:
            print("No endpoint provided")
            return
            
    elif choice in endpoints:
        name, endpoint = endpoints[choice]
        results = {name: extract_endpoint(api, endpoint, name)}
    else:
        print("Invalid choice")
        return
    
    # Save results
    output_file = Path('quick_extract_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[OK] Results saved to: {output_file}")
    print(f"Extracted {len(results)} endpoint(s)")

if __name__ == '__main__':
    main()


