#!/usr/bin/env python3
"""
KeyedIn Session Extractor
Extracts cookies, authToken, and clientId needed for API access
"""

import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def extract_session(output_file='keyedin_session.json'):
    """
    Extract session information from KeyedIn
    """
    print("=" * 80)
    print("KEYEDIN SESSION EXTRACTOR")
    print("=" * 80)
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--start-maximized')
    # chrome_options.add_argument('--headless')  # Uncomment to run headless
    
    # Initialize driver
    driver = None
    
    try:
        print("\n🌐 Opening Chrome browser...")
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to KeyedIn login
        keyedin_url = "https://eaglesign.keyedinsign.com:8443/eaglesign/"
        print(f"📍 Navigating to: {keyedin_url}\n")
        driver.get(keyedin_url)
        
        print("=" * 80)
        print("🔐 PLEASE LOG IN TO KEYEDIN IN THE BROWSER WINDOW")
        print("=" * 80)
        print("\nInstructions:")
        print("  1. Complete the login process in the browser")
        print("  2. Wait until you see the KeyedIn dashboard")
        print("  3. Then come back here and press Enter")
        
        input("\nPress Enter after you've successfully logged in...")
        
        # Navigate to Informer to trigger token generation
        print("\n📂 Navigating to Informer...")
        informer_url = "https://eaglesign.keyedinsign.com:8443/eaglesign/?locale=en_US#action=ReportsHome"
        driver.get(informer_url)
        time.sleep(5)  # Wait for Informer to fully initialize
        
        print("\n🍪 Extracting session cookies...")
        cookies = driver.get_cookies()
        session_cookies = {c['name']: c['value'] for c in cookies}
        
        print(f"✓ Found {len(session_cookies)} cookies")
        
        print("\n🔑 Extracting authToken and clientId...")
        
        # Execute JavaScript to capture network requests
        # This script monitors XHR requests and extracts tokens from URLs
        js_extract_tokens = """
        return new Promise((resolve) => {
            // Check if we already have requests in performance API
            const entries = performance.getEntriesByType("resource");
            const rpcRequests = entries.filter(e => 
                e.name.includes('authToken') && e.name.includes('RPC')
            );
            
            if (rpcRequests.length > 0) {
                const url = rpcRequests[0].name;
                const urlObj = new URL(url);
                resolve({
                    authToken: urlObj.searchParams.get('authToken'),
                    clientId: urlObj.searchParams.get('clientId')
                });
            } else {
                // If no requests yet, wait for one
                const observer = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (entry.name.includes('authToken') && entry.name.includes('RPC')) {
                            const urlObj = new URL(entry.name);
                            observer.disconnect();
                            resolve({
                                authToken: urlObj.searchParams.get('authToken'),
                                clientId: urlObj.searchParams.get('clientId')
                            });
                            break;
                        }
                    }
                });
                observer.observe({ entryTypes: ['resource'] });
                
                // Timeout after 10 seconds
                setTimeout(() => {
                    observer.disconnect();
                    resolve({ authToken: null, clientId: null });
                }, 10000);
            }
        });
        """
        
        tokens = driver.execute_async_script(js_extract_tokens)
        
        auth_token = tokens.get('authToken')
        client_id = tokens.get('clientId')
        
        if not auth_token:
            print("⚠️  Could not extract tokens from existing requests")
            print("    Triggering a new request by clicking on Reports...")
            
            # Try to trigger a request by interacting with the page
            try:
                # Wait a bit more and try again
                time.sleep(3)
                tokens = driver.execute_async_script(js_extract_tokens)
                auth_token = tokens.get('authToken')
                client_id = tokens.get('clientId')
            except Exception as e:
                print(f"    Note: {e}")
        
        # Prepare session data
        session_data = {
            'cookies': session_cookies,
            'authToken': auth_token,
            'clientId': client_id,
            'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'base_url': 'https://eaglesign.keyedinsign.com:8443/eaglesign/'
        }
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        print("\n" + "=" * 80)
        print("✓ SESSION EXTRACTED SUCCESSFULLY")
        print("=" * 80)
        print(f"\nSaved to: {output_file}")
        print(f"\nExtracted:")
        print(f"  - Cookies: {len(session_cookies)}")
        print(f"    • JSESSIONID: {'✓' if 'JSESSIONID' in session_cookies else '✗'}")
        print(f"    • SESSIONID: {'✓' if 'SESSIONID' in session_cookies else '✗'}")
        print(f"  - authToken: {'✓' if auth_token else '✗'}")
        print(f"  - clientId: {'✓' if client_id else '✗'}")
        
        if not auth_token or not client_id:
            print("\n⚠️  WARNING: Tokens not found")
            print("    The extraction script will attempt to obtain them during runtime")
            print("    This is normal if Informer hasn't made any API calls yet")
        
        print(f"\nNext step: python keyedin_complete_extraction.py --session-file {output_file}")
        
        return output_file
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        if driver:
            print("\n🔒 Closing browser...")
            time.sleep(2)
            driver.quit()

if __name__ == '__main__':
    extract_session()