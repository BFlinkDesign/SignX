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
print("KeyedIn Login Attempt")
print("=" * 80)

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

# Step 1: Get the login page
login_url = "http://eaglesign.keyedinsign.com/"
print(f"\n1. Getting login page: {login_url}")
r = session.get(login_url, timeout=10)
print(f"   Status: {r.status_code}")

# Step 2: Prepare login data
login_data = {
    'SECURE': '',
    'USERNAME': username,
    'PASSWORD': password,
    'btnLogin': 'Sign In'
}

print(f"\n2. Posting login with USERNAME={username}")
print(f"   URL: {login_url}")

# Step 3: Submit login
r2 = session.post(login_url, data=login_data, timeout=10, allow_redirects=True)
print(f"   Status: {r2.status_code}")
print(f"   Final URL: {r2.url}")
print(f"   Response length: {len(r2.text)} bytes")

# Save response
with open("after_login.html", 'w', encoding='utf-8') as f:
    f.write(r2.text)
print(f"   Saved to: after_login.html")

# Step 4: Check for success indicators
print(f"\n3. Checking login result...")

success_indicators = ['logout', 'sign out', 'dashboard', 'work order', 'welcome']
failure_indicators = ['invalid', 'incorrect', 'failed', 'error', 'denied']

text_lower = r2.text.lower()

found_success = [word for word in success_indicators if word in text_lower]
found_failure = [word for word in failure_indicators if word in text_lower]

if found_success:
    print(f"    LOGIN SUCCESSFUL!")
    print(f"   Found indicators: {', '.join(found_success)}")
elif found_failure:
    print(f"    LOGIN FAILED!")
    print(f"   Found indicators: {', '.join(found_failure)}")
else:
    print(f"    Login result unclear")

# Step 5: Look for work order links
print(f"\n4. Searching for work order links...")
soup = BeautifulSoup(r2.text, 'html.parser')
links = soup.find_all('a', href=True)

wo_links = [link['href'] for link in links if 'work' in link['href'].lower() or 'order' in link['href'].lower()]

if wo_links:
    print(f"    Found {len(wo_links)} work order related links:")
    for link in wo_links[:10]:
        print(f"       {link}")
else:
    print(f"    No work order links found")
    print(f"\n   All links found ({len(links)} total):")
    for link in links[:20]:
        href = link['href']
        text = link.get_text(strip=True)[:50]
        print(f"       {href} - {text}")

# Step 6: Show first part of response
print(f"\n5. First 1000 characters of response:")
print("=" * 80)
print(r2.text[:1000])
print("=" * 80)

print("\n Complete! Check 'after_login.html' to see the full page.")
