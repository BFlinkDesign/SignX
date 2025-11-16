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
print("KeyedIn Login - CORRECTED")
print("=" * 80)

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'http://eaglesign.keyedinsign.com/'
})

base_url = "http://eaglesign.keyedinsign.com/"

# Step 1: Get the login page first
print(f"\n1. Getting login page...")
r1 = session.get(base_url, timeout=10)
print(f"   Status: {r1.status_code}")

# Step 2: Prepare CORRECT login data
# SECURE must be 'false' for HTTP (not empty!)
login_data = {
    'SECURE': 'false',  # <-- THIS IS THE FIX!
    'USERNAME': username,
    'PASSWORD': password
}

print(f"\n2. Posting login with corrected SECURE field...")
print(f"   Username: {username}")
print(f"   Password: {'*' * len(password)}")
print(f"   SECURE: false (HTTP)")

# Step 3: POST login
r2 = session.post(base_url, data=login_data, timeout=10, allow_redirects=True)
print(f"\n3. Login response:")
print(f"   Status: {r2.status_code}")
print(f"   Final URL: {r2.url}")
print(f"   Response length: {len(r2.text)} bytes")

# Save response
with open("login_success.html", 'w', encoding='utf-8') as f:
    f.write(r2.text)
print(f"   Saved to: login_success.html")

# Step 4: Check for success
success_indicators = ['logout', 'sign out', 'dashboard', 'welcome', 'menu']
failure_indicators = ['error_msg', 'invalid', 'incorrect']

text_lower = r2.text.lower()
found_success = [ind for ind in success_indicators if ind in text_lower]
found_failure = [ind for ind in failure_indicators if ind in text_lower]

print(f"\n4. Authentication check:")
if found_success:
    print(f"    LOGIN SUCCESSFUL!")
    print(f"   Indicators: {', '.join(found_success)}")
elif found_failure:
    print(f"    LOGIN FAILED")
    print(f"   Indicators: {', '.join(found_failure)}")
else:
    print(f"    Result unclear")

# Check if back at login page
soup = BeautifulSoup(r2.text, 'html.parser')
if soup.find('input', {'id': 'USERNAME'}):
    print(f"    Still on login page (failed)")
else:
    print(f"    Navigated away from login page (likely success!)")

# Step 5: Find navigation links
links = soup.find_all('a', href=True)
print(f"\n5. Navigation links found: {len(links)}")

work_links = []
for link in links:
    href = link.get('href', '')
    text = link.get_text(strip=True)
    if any(kw in text.lower() or kw in href.lower() 
           for kw in ['work', 'order', 'service', 'job', 'report', 'invoice']):
        work_links.append(f"{text[:40]:40s}  {href}")

if work_links:
    print(f"\n   Work-related links ({len(work_links)}):")
    for wl in work_links[:15]:
        print(f"     {wl}")
else:
    print(f"\n   Showing first 20 links:")
    for link in links[:20]:
        href = link.get('href', '')
        text = link.get_text(strip=True)[:40]
        if text:
            print(f"     {text:40s}  {href}")

# Step 6: Check cookies
print(f"\n6. Session cookies: {len(session.cookies)}")
for cookie in session.cookies:
    print(f"     {cookie.name} = {cookie.value[:50]}...")

# Step 7: Preview response
print(f"\n7. Response preview (first 1000 chars):")
print("=" * 80)
print(r2.text[:1000])
print("=" * 80)

print("\n Check 'login_success.html' to see the full dashboard!")
