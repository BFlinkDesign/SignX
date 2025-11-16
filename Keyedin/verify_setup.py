#!/usr/bin/env python3
"""
Quick verification script to check if all components are properly set up
"""

import sys
from pathlib import Path

def check_imports():
    """Check if all required modules can be imported"""
    print("Checking imports...")
    
    try:
        import requests
        print("  [OK] requests")
    except ImportError:
        print("  [FAIL] requests - Install with: pip install requests")
        return False
    
    try:
        import selenium
        print("  [OK] selenium")
    except ImportError:
        print("  [FAIL] selenium - Install with: pip install selenium")
        return False
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        print("  [OK] webdriver-manager")
    except ImportError:
        print("  [FAIL] webdriver-manager - Install with: pip install webdriver-manager")
        return False
    
    return True

def check_files():
    """Check if all required files exist"""
    print("\nChecking files...")
    
    files = [
        'keyedin_api_enhanced.py',
        'keyedin_cdp_extractor.py',
        'test_enhanced_api.py',
        'keyedin_api.py'
    ]
    
    all_exist = True
    for file in files:
        if Path(file).exists():
            print(f"  [OK] {file}")
        else:
            print(f"  [FAIL] {file} - Missing!")
            all_exist = False
    
    return all_exist

def check_cookie_file():
    """Check if cookie file exists"""
    print("\nChecking cookie file...")
    
    cookie_file = Path('keyedin_chrome_session.json')
    if cookie_file.exists():
        print(f"  [OK] {cookie_file} exists")
        
        # Check if it's valid JSON
        try:
            import json
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
            print(f"  [OK] Cookie file is valid JSON ({len(cookies)} cookies)")
            return True
        except Exception as e:
            print(f"  [WARN] Cookie file exists but invalid: {e}")
            print("  Run keyedin_cdp_extractor.py to extract fresh cookies")
            return False
    else:
        print(f"  [WARN] {cookie_file} not found")
        print("  Run keyedin_cdp_extractor.py to extract cookies")
        return False

def check_api_classes():
    """Check if API classes can be imported"""
    print("\nChecking API classes...")
    
    try:
        from keyedin_api_enhanced import KeyedInAPIEnhanced
        print("  [OK] KeyedInAPIEnhanced")
    except Exception as e:
        print(f"  [FAIL] KeyedInAPIEnhanced - Error: {e}")
        return False
    
    try:
        from keyedin_cdp_extractor import KeyedInCDPExtractor
        print("  [OK] KeyedInCDPExtractor")
    except Exception as e:
        print(f"  [FAIL] KeyedInCDPExtractor - Error: {e}")
        return False
    
    return True

def main():
    """Run all checks"""
    print("=" * 80)
    print("KeyedIn Enhanced API Setup Verification")
    print("=" * 80)
    
    checks = [
        ("Imports", check_imports),
        ("Files", check_files),
        ("API Classes", check_api_classes),
        ("Cookie File", check_cookie_file)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n  [ERROR] Error in {name}: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 80)
    print("Summary:")
    print("=" * 80)
    
    all_passed = True
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {name}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("[SUCCESS] All checks passed! Ready to use.")
        print("\nNext steps:")
        print("  1. Run: python test_enhanced_api.py")
        print("  2. Or use in your code: from keyedin_api_enhanced import KeyedInAPIEnhanced")
    else:
        print("[WARNING] Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Install missing packages: pip install selenium webdriver-manager requests")
        print("  - Extract cookies: python keyedin_cdp_extractor.py")
    print("=" * 80)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())

