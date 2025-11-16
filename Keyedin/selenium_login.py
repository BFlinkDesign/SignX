from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service
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
print('KeyedIn Login with Selenium (Browser Automation)')
print('=' * 80)

# Setup Edge browser
options = Options()
# options.add_argument('--headless')  # Uncomment to hide browser
driver = webdriver.Edge(options=options)

try:
    # Navigate to login page
    print('\n1. Opening login page...')
    driver.get('http://eaglesign.keyedinsign.com/')
    time.sleep(2)
    
    print(f'   Current URL: {driver.current_url}')
    print(f'   Page title: {driver.title}')
    
    # Fill in credentials
    print(f'\n2. Entering credentials...')
    username_field = driver.find_element(By.ID, 'USERNAME')
    password_field = driver.find_element(By.ID, 'PASSWORD')
    
    username_field.clear()
    username_field.send_keys(username)
    print(f'   Username: {username}')
    
    password_field.clear()
    password_field.send_keys(password)
    print(f'   Password: {"*" * len(password)}')
    
    # Click login button
    print('\n3. Clicking login button...')
    login_button = driver.find_element(By.ID, 'btnLogin')
    login_button.click()
    
    # Wait for page to load
    time.sleep(3)
    
    print(f'\n4. After login:')
    print(f'   Current URL: {driver.current_url}')
    print(f'   Page title: {driver.title}')
    
    # Check for success
    if 'LOGIN.START' in driver.current_url:
        print('\n    Still on login page - Login failed!')
        
        # Check for error message
        try:
            error_elem = driver.find_element(By.ID, 'ERROR_MSG')
            error_text = error_elem.text
            if error_text:
                print(f'   Error: {error_text}')
        except:
            print('   No error message found')
    else:
        print('\n    LOGIN SUCCESSFUL!')
        
        # Save the page
        with open('selenium_logged_in.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print('   Saved page to: selenium_logged_in.html')
        
        # Find work order links
        links = driver.find_elements(By.TAG_NAME, 'a')
        work_links = [link for link in links 
                     if any(kw in link.text.lower() 
                           for kw in ['work', 'order', 'service', 'job'])]
        
        if work_links:
            print(f'\n   Found {len(work_links)} work-related links:')
            for link in work_links[:10]:
                print(f'      {link.text[:40]}  {link.get_attribute("href")}')
    
    print('\n   Browser will stay open for 10 seconds...')
    time.sleep(10)
    
except Exception as e:
    print(f'\n Error: {e}')
    import traceback
    traceback.print_exc()
    
finally:
    driver.quit()
    print('\n Browser closed')

print('=' * 80)
