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
print('KeyedIn Login - Manual Form Submission')
print('=' * 80)

options = Options()
driver = webdriver.Edge(options=options)

try:
    print('\n1. Opening login page (HTTPS)...')
    driver.get('https://eaglesign.keyedinsign.com/')
    time.sleep(2)
    
    # Fill credentials
    print(f'\n2. Filling form fields...')
    driver.find_element(By.ID, 'USERNAME').send_keys(username)
    driver.find_element(By.ID, 'PASSWORD').send_keys(password)
    
    # Set SECURE field to 'true' (string) for HTTPS
    print(f'   Setting SECURE to "true" (HTTPS)')
    driver.execute_script("document.getElementById('SECURE').value = 'true'")
    
    # Verify values before submit
    print(f'\n3. Verifying form data before submit:')
    un = driver.execute_script("return document.getElementById('USERNAME').value")
    pw_len = driver.execute_script("return document.getElementById('PASSWORD').value.length")
    secure = driver.execute_script("return document.getElementById('SECURE').value")
    
    print(f'   USERNAME: {un}')
    print(f'   PASSWORD: (length={pw_len})')
    print(f'   SECURE: {secure}')
    
    # Submit form directly
    print(f'\n4. Submitting form...')
    driver.execute_script("document.forms[0].submit()")
    
    # Wait for response
    time.sleep(5)
    
    print(f'\n5. After submit:')
    print(f'   URL: {driver.current_url}')
    print(f'   Title: {driver.title}')
    
    if 'LOGIN.START' not in driver.current_url:
        print('\n    LOGIN SUCCESSFUL!')
        
        # Save page
        with open('final_success.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        
        # Find work order links
        links = driver.find_elements(By.TAG_NAME, 'a')
        for link in links[:30]:
            try:
                text = link.text.strip()
                href = link.get_attribute('href') or ''
                if text and ('work' in text.lower() or 'order' in text.lower()):
                    print(f'    {text[:60]}  {href}')
            except:
                pass
        
    else:
        print('\n    Still on login page')
        
        # Check error
        try:
            error_elem = driver.find_element(By.ID, 'ERROR_MSG')
            error = error_elem.text
            if error:
                print(f'   ERROR: {error}')
            
            # Check if error is displayed
            error_display = driver.find_element(By.ID, 'ERROR_MSG_DISPLAY')
            display_style = error_display.get_attribute('style')
            print(f'   Error display style: {display_style}')
            
            # Get error via JavaScript
            js_error = driver.execute_script("return document.getElementById('ERROR_MSG').innerHTML")
            print(f'   Error innerHTML: [{js_error}]')
        except Exception as e:
            print(f'   Could not get error: {e}')
    
    print('\n   Keeping browser open for 15 seconds...')
    time.sleep(15)
    
except Exception as e:
    print(f'\n Exception: {e}')
    import traceback
    traceback.print_exc()
    time.sleep(10)
    
finally:
    driver.quit()

print('\n Done')
print('=' * 80)
