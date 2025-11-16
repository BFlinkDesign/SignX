from bs4 import BeautifulSoup
import json

print('=' * 80)
print('Analyzing Work Order Inquiry Form')
print('=' * 80)

# Read the WO.INQUIRY page
with open('WO.INQUIRY.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

# Find the form
form = soup.find('form')
if form:
    print(f'\n Form Details:')
    print(f'   Action: {form.get("action", "")}')
    print(f'   Method: {form.get("method", "GET")}')
    
    # Find all input fields
    inputs = form.find_all(['input', 'select', 'textarea'])
    
    print(f'\n Form Fields ({len(inputs)} total):\n')
    
    for inp in inputs:
        tag = inp.name
        field_type = inp.get('type', 'text')
        field_name = inp.get('name', '')
        field_value = inp.get('value', '')
        field_id = inp.get('id', '')
        
        if tag == 'select':
            options = inp.find_all('option')
            print(f'   SELECT {field_name}:')
            for opt in options[:10]:  # Show first 10 options
                val = opt.get('value', '')
                text = opt.get_text(strip=True)
                print(f'      - {val}: {text}')
        else:
            print(f'   {tag.upper():8s} {field_type:12s} {field_name:30s} = {field_value}')

# Show the full HTML (it's small)
print(f'\n' + '=' * 80)
print('Full HTML:')
print('=' * 80)
print(html)
print('=' * 80)

print('\nNow we know what parameters to submit to get work order data!')
