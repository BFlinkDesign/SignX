from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
print('KeyedIn Login - Pressing Enter (simulating manual login)')
print('=' * 80)

options = Options()
driver = webdriver.Edge(options=options)

try:
    print('\n1. Opening login page...')
    driver.get('https://eaglesign.keyedinsign.com/')
    time.sleep(2)
    
    print(f'\n2. Entering credentials...')
    username_field = driver.find_element(By.ID, 'USERNAME')
    password_field = driver.find_element(By.ID, 'PASSWORD')
    
    username_field.send_keys(username)
    password_field.send_keys(password)
    
    print(f'   Username: {username}')
    print(f'   Password: {"*" * len(password)}')
    
    # Press Enter on password field (triggers: onKeyPress=\"if(event.keyCode==13){validateEntry()}\")
    print(f'\n3. Pressing Enter on password field...')
    password_field.send_keys(Keys.RETURN)
    
    # Wait for response
    time.sleep(5)
    
    print(f'\n4. After login:')
    print(f'   URL: {driver.current_url}')
    print(f'   Title: {driver.title}')
    
    if 'LOGIN.START' not in driver.current_url:
        print('\n    LOGIN SUCCESSFUL!')
        
        with open('selenium_success.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        
        # Get all links
        links = driver.find_elements(By.TAG_NAME, 'a')
        print(f'\n   Found {len(links)} links')
        
        for link in links[:20]:
            try:
                text = link.text.strip()[:50]
                href = link.get_attribute('href') or ''
                if text:
                    print(f'      {text:50s}  {href}')
            except:
                pass
    else:
        print('\n    Still on login page')
        
        # Check for error
        try:
            error_msg_elem = driver.find_element(By.ID, 'ERROR_MSG')
            error_display_elem = driver.find_element(By.ID, 'ERROR_MSG_DISPLAY')
            
            # Check if error is visible
            if error_display_elem.is_displayed():
                print(f'   Error message: {error_msg_elem.text}')
            else:
                print(f'   Error div hidden, no error message')
        except Exception as e:
            print(f'   Could not check error: {e}')
        
        # Check browser console for JavaScript errors
        print(f'\n   Checking browser console...')
        logs = driver.get_log('browser')
        if logs:
            print(f'   Browser console logs:')
            for log in logs:
                print(f'     {log}')
    
    print(f'\n   Keeping browser open for 20 seconds for inspection...')
    time.sleep(20)
    
except Exception as e:
    print(f'\n Error: {e}')
    import traceback
    traceback.print_exc()
    time.sleep(10)

finally:
    driver.quit()

print('=' * 80)
