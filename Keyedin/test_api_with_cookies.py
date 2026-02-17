#!/usr/bin/env python3
"""Test the API with extracted cookies"""

from keyedin_api_enhanced import KeyedInAPIEnhanced

print('=' * 80)
print('Testing KeyedIn API with Extracted Cookies')
print('=' * 80)

# Initialize API with credentials for auto-refresh
api = KeyedInAPIEnhanced(
    cookies_file='keyedin_chrome_session.json',
    username='BradyF',
    password=os.environ.get('KEYEDIN_PASSWORD', ''),
    auto_refresh=False  # Disable for testing
)

print(f'\nCookies file: {api.cookies_file}')
print(f'Session valid: {api.session_valid}')

# Validate session
print('\nValidating session...')
if api.validate_session():
    print('[OK] Session validated successfully!')
    
    # Test endpoints
    print('\nTesting endpoints...')
    results = api.test_endpoints()
    
    print('\n' + '=' * 80)
    print('Endpoint Test Results')
    print('=' * 80)
    
    for name, result in results.items():
        if 'error' in result:
            print(f'[FAIL] {name:25s} ERROR: {result["error"]}')
        elif result.get('success'):
            print(f'[OK]   {name:25s} Status: {result["status"]}  Length: {result["length"]:,} bytes')
        else:
            print(f'[WARN] {name:25s} Status: {result["status"]}  Length: {result["length"]:,} bytes')
    
    print('=' * 80)
else:
    print('[FAIL] Session validation failed')
    print('   Cookies may have expired. Run extract_with_credentials.py to refresh.')

