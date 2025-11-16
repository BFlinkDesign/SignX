from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
import time
import os
from pathlib import Path

# Load credentials
env_file = Path(__file__).parent / '.env.keyedin'
with open(env_file) as f:
    for line in f:
        if line.strip() and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k] = v.strip()

username = os.getenv('KEYEDIN_USERNAME')
password = os.getenv('KEYEDIN_PASSWORD')

print('=' * 80)
print('KeyedIn Login - FIXED (calling JavaScript directly)')
print('=' * 80)

options = Options()
driver = webdriver.Edge(options=options)

try:
    # Start with HTTPS (it redirects anyway)
    print('\n1. Opening login page (HTTPS)...')
    driver.get('https://eaglesign.keyedinsign.com/')
    time.sleep(2)
    
    print(f'   URL: {driver.current_url}')
    print(f'   Protocol: {driver.execute_script("return window.location.protocol")}')
    
    # Fill credentials
    print(f'\n2. Entering credentials...')
    driver.find_element(By.ID, 'USERNAME').send_keys(username)
    driver.find_element(By.ID, 'PASSWORD').send_keys(password)
    print(f'   Username: {username}')
    print(f'   Password: {"*" * len(password)}')
    
    # Call validateEntry() directly via JavaScript (this is what clicking should do)
    print('\n3. Calling validateEntry() JavaScript function...')
    driver.execute_script('validateEntry()')
    
    # Wait for redirect
    time.sleep(4)
    
    print(f'\n4. After login:')
    print(f'   URL: {driver.current_url}')
    print(f'   Title: {driver.title}')
    
    if 'LOGIN.START' not in driver.current_url:
        print('\n    LOGIN SUCCESSFUL!')
        
        # Save page
        with open('selenium_success.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print('   Saved to: selenium_success.html')
        
        # Find navigation links
        links = driver.find_elements(By.TAG_NAME, 'a')
        work_links = []
        for link in links:
            try:
                text = link.text.strip()
                href = link.get_attribute('href') or ''
                if any(kw in text.lower() or kw in href.lower() 
                       for kw in ['work', 'order', 'service', 'job', 'invoice']):
                    work_links.append((text[:50], href))
            except:
                pass
        
        if work_links:
            print(f'\n   Found {len(work_links)} work-related links:')
            for text, href in work_links[:15]:
                print(f'      {text:50s}  {href}')
        
    else:
        print('\n    Still on login page')
        try:
            error = driver.find_element(By.ID, 'ERROR_MSG').text
            if error:
                print(f'   Error: {error}')
        except:
            pass
    
    print('\n   Browser stays open for 15 seconds...')
    time.sleep(15)
    
except Exception as e:
    print(f'\n Error: {e}')
    import traceback
    traceback.print_exc()
    time.sleep(10)
    
finally:
    driver.quit()
    print('\n Browser closed')

print('=' * 80)
