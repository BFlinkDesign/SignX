from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

print('Testing what happens with manual interaction...')

options = Options()
driver = webdriver.Edge(options=options)

try:
    driver.get('http://eaglesign.keyedinsign.com/')
    time.sleep(2)
    
    # Get the SECURE value that JavaScript sets
    secure_value = driver.execute_script('return getProtocol()')
    print(f'JavaScript getProtocol() returns: {secure_value}')
    
    # Get the actual form action
    form = driver.find_element(By.TAG_NAME, 'form')
    action = form.get_attribute('action')
    print(f'Form action: {action}')
    
    # Check what protocol we're on
    print(f'Current URL: {driver.current_url}')
    print(f'Protocol: {driver.execute_script("return window.location.protocol")}')
    
    # Fill in the form
    driver.find_element(By.ID, 'USERNAME').send_keys(username)
    driver.find_element(By.ID, 'PASSWORD').send_keys(password)
    
    # Get SECURE value before submit
    secure_before = driver.find_element(By.ID, 'SECURE').get_attribute('value')
    print(f'SECURE field before submit: [{secure_before}]')
    
    # Click login
    driver.find_element(By.ID, 'btnLogin').click()
    
    # Wait a bit
    time.sleep(5)
    
    print(f'After login URL: {driver.current_url}')
    
    if 'LOGIN.START' not in driver.current_url:
        print(' LOGIN SUCCESSFUL!')
    else:
        print(' Still on login page')
    
    input('Press Enter to close browser...')
    
finally:
    driver.quit()
