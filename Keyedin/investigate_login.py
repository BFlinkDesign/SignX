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
base_url = os.getenv("KEYEDIN_BASE_URL")

print("=" * 80)
print("KeyedIn Login Page Investigation")
print("=" * 80)

session = requests.Session()
url = f"{base_url}/cgi-bin/mvi.exe/LOGIN.START"

print(f"\nFetching: {url}")
r = session.get(url, timeout=10, allow_redirects=True)

print(f"Status: {r.status_code}")
print(f"Final URL: {r.url}")
print(f"Response length: {len(r.text)} bytes")

# Save HTML
html_file = "login_page.html"
with open(html_file, 'w', encoding='utf-8') as f:
    f.write(r.text)
print(f"\nSaved HTML to: {html_file}")

# Show the content
print("\n" + "=" * 80)
print("HTML CONTENT:")
print("=" * 80)
print(r.text)
print("=" * 80)

# Analyze structure
soup = BeautifulSoup(r.text, 'html.parser')
print("\nPage Analysis:")
print(f"  Forms: {len(soup.find_all('form'))}")
print(f"  Input fields: {len(soup.find_all('input'))}")
print(f"  Links: {len(soup.find_all('a'))}")
print(f"  Scripts: {len(soup.find_all('script'))}")

if soup.find_all('form'):
    print("\nForm details:")
    for form in soup.find_all('form'):
        print(f"  Action: {form.get('action')}")
        print(f"  Method: {form.get('method')}")
        for inp in form.find_all('input'):
            print(f"    Input: name={inp.get('name')}, type={inp.get('type')}")

print("\n" + "=" * 80)
