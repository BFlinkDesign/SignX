#!/usr/bin/env python3
"""
Extract KeyedIn cookies with credentials
Uses stored credentials for automatic login
"""

from keyedin_cdp_extractor import KeyedInCDPExtractor, get_project_root

# Credentials
USERNAME = "BradyF"
PASSWORD = "[REDACTED]"

if __name__ == '__main__':
    print('=' * 80)
    print('KeyedIn Cookie Extraction with Auto-Login')
    print('=' * 80)
    
    extractor = KeyedInCDPExtractor(
        username=USERNAME,
        password=PASSWORD
    )
    
    result = extractor.extract_session(
        output_file='keyedin_chrome_session.json',
        capture_network=True
    )
    
    output_path = get_project_root() / 'keyedin_chrome_session.json'
    
    print('\n' + '=' * 80)
    print('Extraction Complete!')
    print('=' * 80)
    print(f"Cookies extracted: {len(result['cookies'])}")
    if result['network']:
        print(f"Network requests captured: {result['network']['total_requests']}")
    print(f"Output file: {output_path}")
    print('=' * 80)
    
    # Test the API with extracted cookies
    print('\nTesting API with extracted cookies...')
    from keyedin_api_enhanced import KeyedInAPIEnhanced
    
    api = KeyedInAPIEnhanced(
        cookies_file='keyedin_chrome_session.json',
        username=USERNAME,
        password=PASSWORD,
        auto_refresh=True
    )
    
    if api.validate_session():
        print("✅ API session validated successfully!")
        print(f"   Cookies file: {api.cookies_file}")
        print(f"   Session valid: {api.session_valid}")
    else:
        print("⚠️ Session validation failed - may need to refresh")


