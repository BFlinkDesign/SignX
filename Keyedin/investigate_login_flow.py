#!/usr/bin/env python3
"""
Investigate LOGIN.START endpoint and data storage
Analyzes the login flow and where data is stored
"""

import os
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    # Try alternative .env file names
    for alt_name in ['.env.keyedin', '.env.keyedin_api']:
        alt_file = Path(__file__).parent / alt_name
        if alt_file.exists():
            load_dotenv(alt_file)
            break

username = os.getenv('KEYEDIN_USERNAME', 'BradyF')
password = os.getenv('KEYEDIN_PASSWORD', '')
base_url = os.getenv('KEYEDIN_BASE_URL', 'https://eaglesign.keyedinsign.com')

print('=' * 80)
print('KeyedIn LOGIN.START Endpoint Investigation')
print('=' * 80)
print(f'Base URL: {base_url}')
print(f'Username: {username}')
print(f'Password: {"*" * len(password)}')

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
})

# Step 1: Get LOGIN.START page
print('\n' + '=' * 80)
print('Step 1: Fetching LOGIN.START page')
print('=' * 80)

login_start_url = f'{base_url}/cgi-bin/mvi.exe/LOGIN.START'
print(f'URL: {login_start_url}')

try:
    response = session.get(login_start_url, timeout=10, allow_redirects=True)
    print(f'Status: {response.status_code}')
    print(f'Final URL: {response.url}')
    print(f'Response length: {len(response.text)} bytes')
    print(f'Cookies received: {len(session.cookies)}')
    
    # Save the login page
    login_page_file = Path(__file__).parent / 'login_start_page.html'
    with open(login_page_file, 'w', encoding='utf-8') as f:
        f.write(response.text)
    print(f'Saved to: {login_page_file}')
    
    # Analyze the HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print('\n' + '=' * 80)
    print('Page Analysis')
    print('=' * 80)
    
    # Find forms
    forms = soup.find_all('form')
    print(f'\nForms found: {len(forms)}')
    
    for i, form in enumerate(forms, 1):
        print(f'\nForm {i}:')
        print(f'  Action: {form.get("action", "N/A")}')
        print(f'  Method: {form.get("method", "GET").upper()}')
        print(f'  Enctype: {form.get("enctype", "N/A")}')
        
        # Find all inputs
        inputs = form.find_all('input')
        print(f'  Inputs ({len(inputs)}):')
        for inp in inputs:
            inp_type = inp.get('type', 'text')
            inp_name = inp.get('name', 'N/A')
            inp_id = inp.get('id', 'N/A')
            inp_value = inp.get('value', '')
            print(f'    - Type: {inp_type}, Name: {inp_name}, ID: {inp_id}, Value: {inp_value[:50]}')
        
        # Find buttons
        buttons = form.find_all(['button', 'input'], {'type': ['submit', 'button']})
        if buttons:
            print(f'  Buttons ({len(buttons)}):')
            for btn in buttons:
                btn_type = btn.get('type', 'button')
                btn_id = btn.get('id', 'N/A')
                btn_value = btn.get('value', btn.text.strip()[:50])
                print(f'    - Type: {btn_type}, ID: {btn_id}, Value: {btn_value}')
    
    # Find hidden fields
    hidden_inputs = soup.find_all('input', {'type': 'hidden'})
    if hidden_inputs:
        print(f'\nHidden fields ({len(hidden_inputs)}):')
        for inp in hidden_inputs:
            print(f'  - {inp.get("name")}: {inp.get("value", "")[:100]}')
    
    # Find JavaScript that might handle login
    scripts = soup.find_all('script')
    print(f'\nScripts found: {len(scripts)}')
    for i, script in enumerate(scripts[:3], 1):  # Show first 3
        script_text = script.string or ''
        if script_text:
            # Look for login-related code
            if any(keyword in script_text.lower() for keyword in ['login', 'username', 'password', 'submit']):
                print(f'\nScript {i} (login-related):')
                print(f'  Length: {len(script_text)} chars')
                # Show relevant lines
                lines = script_text.split('\n')
                relevant_lines = [line.strip() for line in lines if any(kw in line.lower() for kw in ['login', 'username', 'password', 'submit', 'form'])]
                for line in relevant_lines[:5]:
                    print(f'  {line[:100]}')
    
    # Check for data storage indicators
    print('\n' + '=' * 80)
    print('Data Storage Analysis')
    print('=' * 80)
    
    # Look for API endpoints, AJAX calls, or data endpoints
    text_lower = response.text.lower()
    
    storage_indicators = {
        'api': ['api', '/api/', 'ajax', 'xhr', 'fetch'],
        'database': ['database', 'db', 'sql', 'query'],
        'session': ['session', 'sessionid', 'cookie'],
        'storage': ['localstorage', 'sessionstorage', 'indexeddb'],
        'endpoints': ['/cgi-bin/', '/rest/', '/service/', '/data/']
    }
    
    for category, keywords in storage_indicators.items():
        found = [kw for kw in keywords if kw in text_lower]
        if found:
            print(f'\n{category.upper()} indicators found:')
            for kw in found[:5]:
                print(f'  - {kw}')
    
    # Step 2: Try to understand the login POST
    print('\n' + '=' * 80)
    print('Step 2: Analyzing Login POST Requirements')
    print('=' * 80)
    
    # Based on previous code analysis, the login typically posts to base URL
    login_post_url = base_url  # Usually posts to root, not LOGIN.START
    
    # Determine form action
    if forms:
        form_action = forms[0].get('action', '')
        if form_action:
            if form_action.startswith('http'):
                login_post_url = form_action
            elif form_action.startswith('/'):
                login_post_url = f'{base_url}{form_action}'
            else:
                login_post_url = f'{base_url}/{form_action}'
    
    print(f'Login POST URL: {login_post_url}')
    
    # Build login data based on form analysis
    login_data = {}
    if forms:
        for inp in forms[0].find_all('input'):
            inp_name = inp.get('name')
            inp_value = inp.get('value', '')
            if inp_name and inp.get('type') != 'submit':
                login_data[inp_name] = inp_value
    
    # Override with actual credentials
    login_data['USERNAME'] = username
    login_data['PASSWORD'] = password
    
    # Check if SECURE field is needed (from corrected_login.py)
    if 'SECURE' not in login_data:
        login_data['SECURE'] = 'false'  # For HTTP, use 'false'
    
    print(f'\nLogin data structure:')
    for key, value in login_data.items():
        if 'PASSWORD' in key:
            print(f'  {key}: {"*" * len(str(value))}')
        else:
            print(f'  {key}: {value}')
    
    # Step 3: Test login (optional - commented out to avoid actual login)
    print('\n' + '=' * 80)
    print('Step 3: Login Flow Summary')
    print('=' * 80)
    print('''
Login Flow:
1. GET /cgi-bin/mvi.exe/LOGIN.START
   - Returns login form HTML
   - Sets initial session cookies
   
2. POST to base URL (or form action)
   - Fields: USERNAME, PASSWORD, SECURE (and any hidden fields)
   - Creates authenticated session
   - Sets SESSIONID cookie
   
3. Subsequent requests use SESSIONID cookie
   - All API calls include session cookie
   - Session stored server-side
   - Cookies stored client-side
   
Data Storage:
- Server-side: Session data stored in server memory/database
- Client-side: Cookies (SESSIONID, user, secure, etc.)
- Session ID links client cookies to server session
    ''')
    
    print('\n' + '=' * 80)
    print('Investigation Complete')
    print('=' * 80)
    
except Exception as e:
    print(f'\nError during investigation: {e}')
    import traceback
    traceback.print_exc()


