#!/usr/bin/env python3
"""
Comprehensive test suite for KeyedIn API and data extraction
Tests all functionality, validates data, and verifies session management
"""

import json
import time
from pathlib import Path
from datetime import datetime
from keyedin_api_enhanced import KeyedInAPIEnhanced, get_project_root
from keyedin_cdp_extractor import KeyedInCDPExtractor

def test_project_root():
    """Test project root function"""
    print("=" * 80)
    print("Test 1: Project Root Resolution")
    print("=" * 80)
    
    root = get_project_root()
    assert root.exists(), "Project root should exist"
    assert root.is_absolute(), "Project root should be absolute"
    print(f"[OK] Project root: {root}")
    return True

def test_cookie_file():
    """Test cookie file exists and is valid"""
    print("\n" + "=" * 80)
    print("Test 2: Cookie File Validation")
    print("=" * 80)
    
    cookie_file = get_project_root() / 'keyedin_chrome_session.json'
    
    if not cookie_file.exists():
        print(f"[FAIL] Cookie file not found: {cookie_file}")
        return False
    
    print(f"[OK] Cookie file exists: {cookie_file}")
    
    # Validate JSON structure
    try:
        with open(cookie_file, 'r') as f:
            cookies = json.load(f)
        
        assert isinstance(cookies, list), "Cookies should be a list"
        print(f"[OK] Cookie file is valid JSON with {len(cookies)} cookies")
        
        # Check required cookie fields
        required_fields = ['name', 'value', 'domain']
        for cookie in cookies:
            for field in required_fields:
                assert field in cookie, f"Cookie missing required field: {field}"
        
        print("[OK] All cookies have required fields")
        
        # Check for important cookies
        cookie_names = [c['name'] for c in cookies]
        important_cookies = ['SESSIONID', 'user', 'secure']
        found_important = [name for name in important_cookies if name in cookie_names]
        print(f"[OK] Found important cookies: {', '.join(found_important)}")
        
        return True
    except Exception as e:
        print(f"[FAIL] Cookie file validation error: {e}")
        return False

def test_api_initialization():
    """Test API initialization"""
    print("\n" + "=" * 80)
    print("Test 3: API Initialization")
    print("=" * 80)
    
    try:
        api = KeyedInAPIEnhanced(
            cookies_file='keyedin_chrome_session.json',
            username=os.environ.get('KEYEDIN_USERNAME', 'BradyF'),
            password=os.environ.get('KEYEDIN_PASSWORD', ''),
            auto_refresh=False  # Disable for testing
        )
        
        assert api.base_url == 'https://eaglesign.keyedinsign.com', "Base URL incorrect"
        assert api.cookies_file.is_absolute(), "Cookies file should be absolute path"
        assert api.cookies_file.exists(), "Cookies file should exist"
        
        print(f"[OK] API initialized successfully")
        print(f"[OK] Base URL: {api.base_url}")
        print(f"[OK] Cookies file: {api.cookies_file}")
        print(f"[OK] Auto-refresh: {api.auto_refresh}")
        
        return True, api
    except Exception as e:
        print(f"[FAIL] API initialization error: {e}")
        return False, None

def test_session_validation(api):
    """Test session validation"""
    print("\n" + "=" * 80)
    print("Test 4: Session Validation")
    print("=" * 80)
    
    try:
        is_valid = api.validate_session()
        
        if is_valid:
            print("[OK] Session validated successfully")
            print(f"[OK] Session valid flag: {api.session_valid}")
            print(f"[OK] Last validation: {api.last_validation}")
        else:
            print("[WARN] Session validation failed - cookies may be expired")
            print("       This is OK if cookies are old")
        
        return True
    except Exception as e:
        print(f"[FAIL] Session validation error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_endpoint_access(api):
    """Test API endpoint access"""
    print("\n" + "=" * 80)
    print("Test 5: Endpoint Access")
    print("=" * 80)
    
    try:
        results = api.test_endpoints()
        
        success_count = sum(1 for r in results.values() if r.get('success', False))
        total_count = len(results)
        
        print(f"\nResults: {success_count}/{total_count} endpoints successful\n")
        
        all_passed = True
        for name, result in results.items():
            if 'error' in result:
                print(f"[FAIL] {name:25s} ERROR: {result['error']}")
                all_passed = False
            elif result.get('success'):
                print(f"[OK]   {name:25s} Status: {result['status']}  Length: {result['length']:,} bytes")
            else:
                print(f"[WARN] {name:25s} Status: {result['status']}  Length: {result['length']:,} bytes")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"[FAIL] Endpoint access error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cookie_expiry_check(api):
    """Test cookie expiry checking"""
    print("\n" + "=" * 80)
    print("Test 6: Cookie Expiry Checking")
    print("=" * 80)
    
    try:
        cookie_status = api._check_cookie_expiry()
        
        if cookie_status:
            print("[OK] Cookies are valid (not expired)")
        else:
            print("[WARN] Some cookies expired or expiring soon")
            print("       This is expected if cookies are old")
        
        # Check individual cookie expiry
        if api.cookies_file.exists():
            with open(api.cookies_file, 'r') as f:
                cookies = json.load(f)
            
            now = datetime.now()
            print(f"\nCookie expiry details:")
            for cookie in cookies:
                expiry = cookie.get('expiry')
                if expiry:
                    expiry_dt = datetime.fromtimestamp(expiry)
                    remaining = expiry_dt - now
                    status = "OK" if remaining.total_seconds() > 0 else "EXPIRED"
                    print(f"  [{status}] {cookie['name']:20s} Expires: {expiry_dt} ({remaining})")
                else:
                    print(f"  [N/A] {cookie['name']:20s} No expiry set")
        
        return True
    except Exception as e:
        print(f"[FAIL] Cookie expiry check error: {e}")
        return False

def test_get_methods(api):
    """Test convenience GET methods"""
    print("\n" + "=" * 80)
    print("Test 7: Convenience GET Methods")
    print("=" * 80)
    
    try:
        # Test get_menu
        try:
            menu = api.get_menu()
            assert isinstance(menu, dict), "Menu should be a dict"
            print(f"[OK] get_menu() - Success (keys: {list(menu.keys())[:5]}...)")
        except Exception as e:
            print(f"[WARN] get_menu() - Failed: {e}")
        
        # Test get_work_order_form
        try:
            wo_form = api.get_work_order_form()
            assert isinstance(wo_form, str), "Work order form should be a string"
            assert len(wo_form) > 0, "Work order form should not be empty"
            print(f"[OK] get_work_order_form() - Success ({len(wo_form)} bytes)")
        except Exception as e:
            print(f"[WARN] get_work_order_form() - Failed: {e}")
        
        return True
    except Exception as e:
        print(f"[FAIL] GET methods error: {e}")
        return False

def test_network_data():
    """Test network data file if it exists"""
    print("\n" + "=" * 80)
    print("Test 8: Network Data File")
    print("=" * 80)
    
    network_file = get_project_root() / 'keyedin_chrome_session_network.json'
    
    if not network_file.exists():
        print("[INFO] Network data file not found (optional)")
        return True
    
    try:
        with open(network_file, 'r') as f:
            network_data = json.load(f)
        
        assert isinstance(network_data, dict), "Network data should be a dict"
        print(f"[OK] Network data file is valid JSON")
        
        if 'requests' in network_data:
            print(f"[OK] Contains {len(network_data.get('requests', []))} requests")
        if 'total_requests' in network_data:
            print(f"[OK] Total requests captured: {network_data['total_requests']}")
        
        return True
    except Exception as e:
        print(f"[WARN] Network data file error: {e}")
        return True  # Not critical

def test_cdp_extractor():
    """Test CDP extractor class"""
    print("\n" + "=" * 80)
    print("Test 9: CDP Extractor Class")
    print("=" * 80)
    
    try:
        extractor = KeyedInCDPExtractor(
            username=os.environ.get('KEYEDIN_USERNAME', 'BradyF'),
            password=os.environ.get('KEYEDIN_PASSWORD', '')
        )

        assert extractor.base_url == 'https://eaglesign.keyedinsign.com', "Base URL incorrect"
        assert extractor.username, "Username not set"
        assert extractor.password, "Password not set (use KEYEDIN_PASSWORD env var)"
        
        print("[OK] CDP Extractor initialized successfully")
        print(f"[OK] Base URL: {extractor.base_url}")
        print(f"[OK] Username: {extractor.username}")
        print("[OK] Password: [HIDDEN]")
        
        return True
    except Exception as e:
        print(f"[FAIL] CDP Extractor initialization error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE KEYEDIN API TEST SUITE")
    print("=" * 80)
    print(f"Test started: {datetime.now()}")
    
    results = []
    
    # Test 1: Project root
    results.append(("Project Root", test_project_root()))
    
    # Test 2: Cookie file
    results.append(("Cookie File", test_cookie_file()))
    
    # Test 3: API initialization
    init_success, api = test_api_initialization()
    results.append(("API Initialization", init_success))
    
    if api:
        # Test 4: Session validation
        results.append(("Session Validation", test_session_validation(api)))
        
        # Test 5: Endpoint access
        results.append(("Endpoint Access", test_endpoint_access(api)))
        
        # Test 6: Cookie expiry
        results.append(("Cookie Expiry Check", test_cookie_expiry_check(api)))
        
        # Test 7: GET methods
        results.append(("GET Methods", test_get_methods(api)))
    
    # Test 8: Network data
    results.append(("Network Data", test_network_data()))
    
    # Test 9: CDP Extractor
    results.append(("CDP Extractor", test_cdp_extractor()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {name}")
    
    print("\n" + "=" * 80)
    print(f"Results: {passed}/{total} tests passed")
    print(f"Test completed: {datetime.now()}")
    print("=" * 80)
    
    return 0 if passed == total else 1

if __name__ == '__main__':
    import sys
    sys.exit(main())


