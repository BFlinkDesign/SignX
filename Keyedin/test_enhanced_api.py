#!/usr/bin/env python3
"""
Test script for Enhanced KeyedIn API
Tests session validation, auto-refresh, and cookie management
"""

import time
import json
from keyedin_api_enhanced import KeyedInAPIEnhanced

def test_api():
    """Test the enhanced API"""
    print('=' * 80)
    print('Enhanced KeyedIn API Test Suite')
    print('=' * 80)
    
    # Initialize API
    print('\n[1/5] Initializing API...')
    api = KeyedInAPIEnhanced(
        cookies_file='keyedin_chrome_session.json',  # Saved to project root
        auto_refresh=True,
        refresh_threshold_minutes=30
    )
    
    print(f'   Cookies file: {api.cookies_file}')
    print(f'   Session valid: {api.session_valid}')
    print(f'   Last validation: {api.last_validation}')
    
    # Test session validation
    print('\n[2/5] Testing session validation...')
    is_valid = api.validate_session()
    print(f'   Session validation result: {is_valid}')
    
    # Test endpoint access
    print('\n[3/5] Testing endpoint access...')
    try:
        menu = api.get_menu()
        print(f'   ✅ Menu endpoint: Success (keys: {list(menu.keys())[:5]}...)')
    except Exception as e:
        print(f'   ❌ Menu endpoint: Failed - {e}')
    
    try:
        wo_form = api.get_work_order_form()
        print(f'   ✅ Work Order form: Success ({len(wo_form)} bytes)')
    except Exception as e:
        print(f'   ❌ Work Order form: Failed - {e}')
    
    # Test all endpoints
    print('\n[4/5] Testing all discovered endpoints...')
    results = api.test_endpoints()
    
    success_count = sum(1 for r in results.values() if r.get('success', False))
    total_count = len(results)
    
    print(f'\n   Results: {success_count}/{total_count} endpoints successful\n')
    
    for name, result in results.items():
        if 'error' in result:
            print(f'   ❌ {name:25s} ERROR: {result["error"]}')
        elif result.get('success'):
            print(f'   ✅ {name:25s} Status: {result["status"]}  Length: {result["length"]:,} bytes')
        else:
            print(f'   ⚠️  {name:25s} Status: {result["status"]}  Length: {result["length"]:,} bytes')
    
    # Test cookie expiry checking
    print('\n[5/5] Testing cookie expiry checking...')
    cookie_status = api._check_cookie_expiry()
    print(f'   Cookie expiry check: {"✅ Valid" if cookie_status else "⚠️ Expiring soon or expired"}')
    
    # Show cookie info
    if api.cookies_file.exists():
        with open(api.cookies_file, 'r') as f:
            cookies = json.load(f)
        
        print(f'\n   Cookie details:')
        for cookie in cookies:
            expiry = cookie.get('expiry')
            if expiry:
                from datetime import datetime
                expiry_dt = datetime.fromtimestamp(expiry)
                now = datetime.now()
                remaining = expiry_dt - now
                status = "✅" if remaining.total_seconds() > 0 else "❌"
                print(f'   {status} {cookie["name"]:20s} Expires: {expiry_dt} ({remaining})')
            else:
                print(f'   ⚠️  {cookie["name"]:20s} No expiry set')
    
    print('\n' + '=' * 80)
    print('Test Complete!')
    print('=' * 80)
    print(f'\nSession Status: {"✅ Valid" if api.session_valid else "❌ Invalid"}')
    print(f'Auto-refresh: {"✅ Enabled" if api.auto_refresh else "❌ Disabled"}')
    print(f'Background monitor: {"✅ Running" if api._monitor_thread and api._monitor_thread.is_alive() else "❌ Stopped"}')
    print('\nThe API will automatically refresh the session before cookies expire.')
    print('Press Ctrl+C to stop...')
    
    # Keep running to demonstrate background monitoring
    try:
        while True:
            time.sleep(60)
            print(f"\n[{time.strftime('%H:%M:%S')}] Session check: Valid={api.session_valid}, Last validation={api.last_validation}")
    except KeyboardInterrupt:
        print('\n\nStopping...')
    finally:
        api.stop_monitor()
        print('Done!')

if __name__ == '__main__':
    test_api()

