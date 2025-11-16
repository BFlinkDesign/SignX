import os
import sys
import requests
from bs4 import BeautifulSoup
from pathlib import Path

print("=" * 80)
print("KeyedIn Connection Test")
print("=" * 80)

# Load credentials
env_file = Path(__file__).parent / ".env.keyedin"
if not env_file.exists():
    print("ERROR: .env.keyedin not found")
    sys.exit(1)

with open(env_file) as f:
    for line in f:
        if line.strip() and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k] = v.strip()

username = os.getenv("KEYEDIN_USERNAME")
password = os.getenv("KEYEDIN_PASSWORD")
base_url = os.getenv("KEYEDIN_BASE_URL")

print(f"\nUsername: {username}")
print(f"Password: {'*' * len(password)}")
print(f"Base URL: {base_url}")

# Test connection
session = requests.Session()
url = f"{base_url}/cgi-bin/mvi.exe/LOGIN.START"

print(f"\nTesting connection to: {url}")
try:
    r = session.get(url, timeout=10)
    print(f"Status Code: {r.status_code}")
    
    if r.status_code == 200:
        print(" Server is accessible!")
        print(f"Response length: {len(r.text)} bytes")
        
        # Check for login form
        soup = BeautifulSoup(r.text, 'html.parser')
        form = soup.find('form')
        if form:
            print(" Found login form!")
        else:
            print(" No login form found")
            
    elif r.status_code == 403:
        print(" 403 Forbidden - IP might be blocked")
    else:
        print(f" Unexpected status: {r.status_code}")
        
except Exception as e:
    print(f" Connection failed: {e}")

print("\n" + "=" * 80)
