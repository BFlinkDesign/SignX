import os
import sys
import requests
from bs4 import BeautifulSoup
from pathlib import Path

# Load credentials
env_file = Path(__file__).parent / ".env.keyedin"
with open(env_file) as f:
    for line in f:
        if line.strip() and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k] = v.strip()

username = os.getenv("KEYEDIN_USERNAME")
password = os.getenv("KEYEDIN_PASSWORD")

print("=" * 80)
print("KeyedIn Actual Login Page")
print("=" * 80)

session = requests.Session()

# The JavaScript redirects to this URL
actual_login_url = "http://eaglesign.keyedinsign.com/"

print(f"\nFetching actual login page: {actual_login_url}")
r = session.get(actual_login_url, timeout=10)

print(f"Status: {r.status_code}")
print(f"Response length: {len(r.text)} bytes")

# Save HTML
with open("actual_login_page.html", 'w', encoding='utf-8') as f:
    f.write(r.text)
print("Saved to: actual_login_page.html")

# Analyze
soup = BeautifulSoup(r.text, 'html.parser')
print("\nPage Analysis:")
print(f"  Forms: {len(soup.find_all('form'))}")
print(f"  Input fields: {len(soup.find_all('input'))}")

if soup.find_all('form'):
    print("\n FOUND LOGIN FORM!")
    for form in soup.find_all('form'):
        action = form.get('action', 'no action')
        method = form.get('method', 'GET').upper()
        print(f"\nForm:")
        print(f"  Action: {action}")
        print(f"  Method: {method}")
        print(f"\n  Input fields:")
        for inp in form.find_all('input'):
            name = inp.get('name', 'no name')
            inp_type = inp.get('type', 'text')
            value = inp.get('value', '')
            print(f"    - {name:20s} (type={inp_type:10s}) value={value}")
else:
    print("\n No form found. Here's the page content:")
    print("\n" + "=" * 80)
    print(r.text[:2000])  # First 2000 chars
    print("=" * 80)

print("\n" + "=" * 80)
