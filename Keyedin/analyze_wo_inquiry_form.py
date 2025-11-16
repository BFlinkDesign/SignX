#!/usr/bin/env python3
"""Analyze WO.INQUIRY form to understand how to query for all work orders"""

from keyedin_api_enhanced import KeyedInAPIEnhanced
from bs4 import BeautifulSoup
import json

api = KeyedInAPIEnhanced(auto_refresh=False)

print("=" * 80)
print("Analyzing WO.INQUIRY Form")
print("=" * 80)

response = api.get('/cgi-bin/mvi.exe/WO.INQUIRY')
soup = BeautifulSoup(response.text, 'html.parser')

# Find all forms
forms = soup.find_all('form')
print(f"\nFound {len(forms)} forms\n")

for i, form in enumerate(forms):
    print(f"Form {i+1}:")
    print(f"  Action: {form.get('action', 'N/A')}")
    print(f"  Method: {form.get('method', 'GET')}")
    print(f"  Enctype: {form.get('enctype', 'N/A')}")
    
    # Get all inputs
    inputs = form.find_all('input')
    selects = form.find_all('select')
    
    print(f"\n  Inputs ({len(inputs)}):")
    for inp in inputs:
        name = inp.get('name', 'N/A')
        inp_type = inp.get('type', 'text')
        value = inp.get('value', '')
        inp_id = inp.get('id', '')
        print(f"    - Name: {name:20s} Type: {inp_type:10s} ID: {inp_id:20s} Value: {value[:50]}")
    
    print(f"\n  Selects ({len(selects)}):")
    for sel in selects:
        name = sel.get('name', 'N/A')
        print(f"    - Name: {name}")
        options = sel.find_all('option')
        print(f"      Options: {len(options)}")
        for opt in options[:5]:  # First 5 options
            print(f"        {opt.get('value', '')} - {opt.get_text(strip=True)[:50]}")

# Save form HTML for inspection
with open('wo_inquiry_form.html', 'w', encoding='utf-8') as f:
    f.write(response.text)
print(f"\nSaved form HTML to: wo_inquiry_form.html")


