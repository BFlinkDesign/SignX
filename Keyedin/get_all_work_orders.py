#!/usr/bin/env python3
"""
Get ALL Work Order Numbers from KeyedIn
Tries multiple methods to find all work orders in the system
"""

from keyedin_api_enhanced import KeyedInAPIEnhanced
from bs4 import BeautifulSoup
import re
import json
from pathlib import Path

def get_all_work_orders():
    """Get all work order numbers using multiple methods"""
    api = KeyedInAPIEnhanced(auto_refresh=False)
    
    print("=" * 80)
    print("Finding ALL Work Order Numbers")
    print("=" * 80)
    
    all_wos = set()
    
    # Method 1: Try WO.INQUIRY with form submission to get all
    print("\nMethod 1: Querying WO.INQUIRY form...")
    try:
        # Get the form first
        response = api.get('/cgi-bin/mvi.exe/WO.INQUIRY', timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find form
        form = soup.find('form')
        if form:
            action = form.get('action', 'WO.INQUIRY')
            method = form.get('method', 'GET').upper()
            
            print(f"  Form found: action={action}, method={method}")
            
            # Try submitting with empty/broad parameters
            form_data = {}
            for inp in form.find_all('input'):
                name = inp.get('name')
                if name:
                    inp_type = inp.get('type', 'text')
                    if inp_type in ['text', 'hidden']:
                        form_data[name] = ''  # Empty to get all
                    elif inp_type == 'checkbox':
                        form_data[name] = 'on'  # Check all
                    else:
                        form_data[name] = inp.get('value', '')
            
            # Try POST with form data
            if method == 'POST':
                response = api.post(f'/cgi-bin/mvi.exe/{action}', data=form_data, timeout=15)
            else:
                response = api.get(f'/cgi-bin/mvi.exe/{action}', params=form_data, timeout=15)
            
            if response.status_code == 200:
                wo_nos = extract_wo_numbers(response.text)
                all_wos.update(wo_nos)
                print(f"  Found {len(wo_nos)} work orders")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Method 2: Try WORKORDER.LIST
    print("\nMethod 2: Checking WORKORDER.LIST...")
    try:
        response = api.get('/cgi-bin/mvi.exe/WORKORDER.LIST', timeout=15)
        if response.status_code == 200:
            wo_nos = extract_wo_numbers(response.text)
            all_wos.update(wo_nos)
            print(f"  Found {len(wo_nos)} work orders")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Method 3: Try WO.HISTORY - might list all WOs
    print("\nMethod 3: Checking WO.HISTORY...")
    try:
        response = api.get('/cgi-bin/mvi.exe/WO.HISTORY', timeout=15)
        if response.status_code == 200:
            wo_nos = extract_wo_numbers(response.text)
            all_wos.update(wo_nos)
            print(f"  Found {len(wo_nos)} work orders")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Method 4: Try WO.GROUP.ANALYSIS - might show grouped WOs
    print("\nMethod 4: Checking WO.GROUP.ANALYSIS...")
    try:
        response = api.get('/cgi-bin/mvi.exe/WO.GROUP.ANALYSIS', timeout=15)
        if response.status_code == 200:
            wo_nos = extract_wo_numbers(response.text)
            all_wos.update(wo_nos)
            print(f"  Found {len(wo_nos)} work orders")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Method 5: Check if there's an export endpoint
    print("\nMethod 5: Checking export endpoints...")
    export_endpoints = [
        '/cgi-bin/mvi.exe/EXPORT.WIP.SUMMARY',
        '/cgi-bin/mvi.exe/EXPORT.WO.LABOR.ANALYSIS',
    ]
    
    for endpoint in export_endpoints:
        try:
            response = api.get(endpoint, timeout=15)
            if response.status_code == 200:
                # Check if it's CSV or data format
                if 'csv' in response.headers.get('Content-Type', '').lower() or ',' in response.text[:100]:
                    # Parse CSV for work order numbers
                    lines = response.text.split('\n')[:100]  # First 100 lines
                    for line in lines:
                        # Look for numbers that might be WO numbers
                        numbers = re.findall(r'\b(\d{4,8})\b', line)
                        all_wos.update(numbers)
                    print(f"  Found work orders in {endpoint}")
        except:
            pass
    
    # Convert to sorted list
    work_orders = sorted([wo for wo in all_wos if wo.isdigit()], key=lambda x: int(x))
    
    print(f"\n" + "=" * 80)
    print(f"Total unique work orders found: {len(work_orders)}")
    if work_orders:
        print(f"Sample: {work_orders[:20]}")
    print("=" * 80)
    
    # Save work order list
    output_file = Path('all_work_orders.json')
    with open(output_file, 'w') as f:
        json.dump({
            'total': len(work_orders),
            'work_orders': work_orders,
            'found_at': str(datetime.now())
        }, f, indent=2)
    
    print(f"\nSaved work order list to: {output_file}")
    
    return work_orders

def extract_wo_numbers(html):
    """Extract work order numbers from HTML"""
    wo_numbers = set()
    
    # Patterns
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
            # Check links in row
            for link in row.find_all('a', href=True):
                href = link.get('href', '')
                if 'WONO=' in href:
                    match = re.search(r'WONO=(\d+)', href)
                    if match:
                        wo_numbers.add(match.group(1))
            
            # Check cell text
            cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
            for cell in cells:
                # Look for 4-8 digit numbers
                numbers = re.findall(r'\b(\d{4,8})\b', cell)
                for num in numbers:
                    if not re.match(r'^(19|20)\d{2}', num):  # Not a year
                        wo_numbers.add(num)
    
    return wo_numbers

if __name__ == '__main__':
    from datetime import datetime
    work_orders = get_all_work_orders()
    print(f"\nReady to extract cost summaries for {len(work_orders)} work orders")
    print("Run: python extract_all_detailed_cost_summaries.py")


