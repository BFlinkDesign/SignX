#!/usr/bin/env python3
"""
Comprehensive Data Extraction from KeyedIn
Pulls data from multiple endpoints and pages
"""

import json
import os
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from keyedin_api_enhanced import KeyedInAPIEnhanced, get_project_root

def extract_menu_data(api):
    """Extract menu structure"""
    print("\n" + "=" * 80)
    print("Extracting Menu Data")
    print("=" * 80)
    
    try:
        menu = api.get_menu()
        print(f"[OK] Menu extracted: {type(menu)}")
        
        if isinstance(menu, dict):
            print(f"  Keys: {list(menu.keys())[:10]}")
            return menu
        else:
            print(f"  Menu data: {str(menu)[:200]}")
            return menu
    except Exception as e:
        print(f"[FAIL] Error extracting menu: {e}")
        return None

def extract_work_order_data(api):
    """Extract work order related data"""
    print("\n" + "=" * 80)
    print("Extracting Work Order Data")
    print("=" * 80)
    
    endpoints = {
        'WO Inquiry Form': '/cgi-bin/mvi.exe/WO.INQUIRY',
        'WO History': '/cgi-bin/mvi.exe/WO.HISTORY',
        'WO Cost Summary': '/cgi-bin/mvi.exe/WO.COST.SUMMARY',
        'WO Completion Inquiry': '/cgi-bin/mvi.exe/WO.COMPLETION.INQUIRY',
        'WO Group Analysis': '/cgi-bin/mvi.exe/WO.GROUP.ANALYSIS',
        'Work Order List': '/cgi-bin/mvi.exe/WORKORDER.LIST',
    }
    
    results = {}
    
    for name, endpoint in endpoints.items():
        try:
            print(f"\n  Extracting: {name}")
            response = api.get(endpoint, timeout=15)
            
            if response.status_code == 200:
                # Try to parse as HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract tables
                tables = soup.find_all('table')
                forms = soup.find_all('form')
                inputs = soup.find_all('input')
                
                data = {
                    'status': response.status_code,
                    'length': len(response.text),
                    'tables': len(tables),
                    'forms': len(forms),
                    'input_fields': len(inputs),
                    'url': endpoint,
                    'content_preview': response.text[:500]
                }
                
                # Extract table data if present
                if tables:
                    table_data = []
                    for i, table in enumerate(tables[:3]):  # First 3 tables
                        rows = []
                        for tr in table.find_all('tr')[:10]:  # First 10 rows
                            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                            if cells:
                                rows.append(cells)
                        if rows:
                            table_data.append({
                                'table_index': i,
                                'rows': rows,
                                'row_count': len(rows)
                            })
                    data['table_data'] = table_data
                
                # Extract form fields
                if forms:
                    form_fields = []
                    for form in forms[:2]:  # First 2 forms
                        fields = []
                        for inp in form.find_all('input'):
                            fields.append({
                                'name': inp.get('name'),
                                'type': inp.get('type'),
                                'id': inp.get('id'),
                                'value': inp.get('value', '')
                            })
                        form_fields.append({
                            'action': form.get('action'),
                            'method': form.get('method'),
                            'fields': fields
                        })
                    data['form_fields'] = form_fields
                
                results[name] = data
                print(f"    [OK] Extracted: {len(response.text):,} bytes, {len(tables)} tables, {len(forms)} forms")
            else:
                results[name] = {'status': response.status_code, 'error': 'Non-200 status'}
                print(f"    [WARN] Status {response.status_code}")
                
        except Exception as e:
            results[name] = {'error': str(e)}
            print(f"    [FAIL] Error: {e}")
    
    return results

def extract_service_call_data(api):
    """Extract service call data"""
    print("\n" + "=" * 80)
    print("Extracting Service Call Data")
    print("=" * 80)
    
    endpoints = {
        'Service Call List': '/cgi-bin/mvi.exe/SERVICE.CALL.LIST',
        'Assigned Service Calls': '/cgi-bin/mvi.exe/WIDGET.ASSIGNED.SERVICE.CALLS?ACTION=AJAX',
    }
    
    results = {}
    
    for name, endpoint in endpoints.items():
        try:
            print(f"\n  Extracting: {name}")
            response = api.get(endpoint, timeout=15)
            
            if response.status_code == 200:
                # Try JSON first
                try:
                    json_data = response.json()
                    results[name] = {
                        'type': 'json',
                        'data': json_data,
                        'status': response.status_code
                    }
                    print(f"    [OK] JSON data extracted")
                except:
                    # Parse as HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    tables = soup.find_all('table')
                    results[name] = {
                        'type': 'html',
                        'length': len(response.text),
                        'tables': len(tables),
                        'status': response.status_code,
                        'content_preview': response.text[:500]
                    }
                    print(f"    [OK] HTML data extracted: {len(response.text):,} bytes, {len(tables)} tables")
            else:
                results[name] = {'status': response.status_code, 'error': 'Non-200 status'}
                print(f"    [WARN] Status {response.status_code}")
                
        except Exception as e:
            results[name] = {'error': str(e)}
            print(f"    [FAIL] Error: {e}")
    
    return results

def extract_widget_data(api):
    """Extract widget data"""
    print("\n" + "=" * 80)
    print("Extracting Widget Data")
    print("=" * 80)
    
    endpoints = {
        'Assigned Milestones': '/cgi-bin/mvi.exe/WIDGET.ASSIGNED.MILESTONES?ACTION=AJAX',
        'CRM Tasks': '/cgi-bin/mvi.exe/WIDGET.CRM.TASKS?ACTION=AJAX',
        'FYI Widget': '/cgi-bin/mvi.exe/WIDGET.FYI?ACTION=AJAX',
    }
    
    results = {}
    
    for name, endpoint in endpoints.items():
        try:
            print(f"\n  Extracting: {name}")
            response = api.get(endpoint, timeout=15)
            
            if response.status_code == 200:
                # Try JSON first
                try:
                    json_data = response.json()
                    results[name] = {
                        'type': 'json',
                        'data': json_data,
                        'status': response.status_code
                    }
                    print(f"    [OK] JSON data extracted")
                except:
                    results[name] = {
                        'type': 'text',
                        'length': len(response.text),
                        'status': response.status_code,
                        'content': response.text[:1000]
                    }
                    print(f"    [OK] Text data extracted: {len(response.text):,} bytes")
            else:
                results[name] = {'status': response.status_code, 'error': 'Non-200 status'}
                print(f"    [WARN] Status {response.status_code}")
                
        except Exception as e:
            results[name] = {'error': str(e)}
            print(f"    [FAIL] Error: {e}")
    
    return results

def extract_main_pages(api):
    """Extract main application pages"""
    print("\n" + "=" * 80)
    print("Extracting Main Pages")
    print("=" * 80)
    
    endpoints = {
        'Main Page': '/cgi-bin/mvi.exe/MAIN',
        'Home': '/cgi-bin/mvi.exe/HOME',
    }
    
    results = {}
    
    for name, endpoint in endpoints.items():
        try:
            print(f"\n  Extracting: {name}")
            response = api.get(endpoint, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                results[name] = {
                    'length': len(response.text),
                    'tables': len(soup.find_all('table')),
                    'forms': len(soup.find_all('form')),
                    'links': len(soup.find_all('a')),
                    'status': response.status_code,
                    'title': soup.title.string if soup.title else None
                }
                print(f"    [OK] Extracted: {len(response.text):,} bytes")
            else:
                results[name] = {'status': response.status_code, 'error': 'Non-200 status'}
                print(f"    [WARN] Status {response.status_code}")
                
        except Exception as e:
            results[name] = {'error': str(e)}
            print(f"    [FAIL] Error: {e}")
    
    return results

def save_extracted_data(all_data, output_dir):
    """Save all extracted data to files"""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save complete data
    complete_file = output_dir / f'extracted_data_{timestamp}.json'
    with open(complete_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, default=str)
    print(f"\n[OK] Complete data saved to: {complete_file}")
    
    # Save individual sections
    for section_name, section_data in all_data.items():
        if section_data:
            section_file = output_dir / f'{section_name.lower().replace(" ", "_")}_{timestamp}.json'
            with open(section_file, 'w', encoding='utf-8') as f:
                json.dump(section_data, f, indent=2, default=str)
            print(f"[OK] {section_name} saved to: {section_file}")

def main():
    """Main extraction function"""
    print("=" * 80)
    print("KeyedIn Comprehensive Data Extraction")
    print("=" * 80)
    print(f"Started: {datetime.now()}")
    
    # Initialize API
    api = KeyedInAPIEnhanced(auto_refresh=False)
    
    if not api.validate_session():
        print("[FAIL] Session validation failed. Cannot extract data.")
        return
    
    print("[OK] Session validated")
    
    # Extract data from all sources
    all_data = {
        'menu': extract_menu_data(api),
        'work_orders': extract_work_order_data(api),
        'service_calls': extract_service_call_data(api),
        'widgets': extract_widget_data(api),
        'main_pages': extract_main_pages(api),
    }
    
    # Save extracted data
    output_dir = get_project_root() / 'extracted_data'
    save_extracted_data(all_data, output_dir)
    
    # Summary
    print("\n" + "=" * 80)
    print("Extraction Summary")
    print("=" * 80)
    
    total_endpoints = 0
    successful = 0
    
    for section_name, section_data in all_data.items():
        if isinstance(section_data, dict):
            section_total = len(section_data)
            section_success = sum(1 for v in section_data.values() if isinstance(v, dict) and v.get('status') == 200)
            total_endpoints += section_total
            successful += section_success
            print(f"{section_name:20s} {section_success}/{section_total} successful")
    
    print(f"\nTotal: {successful}/{total_endpoints} endpoints extracted successfully")
    print(f"Completed: {datetime.now()}")
    print("=" * 80)

if __name__ == '__main__':
    main()


