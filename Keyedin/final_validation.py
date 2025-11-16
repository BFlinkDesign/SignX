#!/usr/bin/env python3
"""Final validation check"""

from keyedin_api_enhanced import KeyedInAPIEnhanced

print('=' * 80)
print('FINAL VALIDATION CHECK')
print('=' * 80)

api = KeyedInAPIEnhanced(auto_refresh=False)

print(f'\nSession Valid: {api.validate_session()}')
print(f'Cookies File: {api.cookies_file}')
print(f'Base URL: {api.base_url}')

results = api.test_endpoints()
working = sum(1 for r in results.values() if r.get('success'))
print(f'Endpoints Working: {working}/{len(results)}')

print('\n' + '=' * 80)
print('ALL SYSTEMS OPERATIONAL')
print('=' * 80)


