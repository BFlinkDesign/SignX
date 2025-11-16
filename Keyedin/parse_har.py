import json
from urllib.parse import urlparse, parse_qs

def parse_har_file(har_file='keyedin_network.har'):
    '''Parse HAR file to extract Informer API calls'''
    
    with open(har_file, 'r', encoding='utf-8') as f:
        har_data = json.load(f)
    
    entries = har_data.get('log', {}).get('entries', [])
    
    print(f'Found {len(entries)} network requests in HAR file\n')
    
    # Filter for Informer API calls
    api_calls = []
    
    for entry in entries:
        request = entry.get('request', {})
        response = entry.get('response', {})
        
        url = request.get('url', '')
        method = request.get('method', '')
        
        # Filter for KeyedIn Informer requests
        if 'eaglesign.keyedinsign.com:8443' in url:
            # Skip static resources
            if any(ext in url.lower() for ext in ['.js', '.css', '.png', '.jpg', '.gif', '.woff', '.ttf']):
                continue
            
            api_call = {
                'method': method,
                'url': url,
                'status': response.get('status', 0),
                'content_type': response.get('content', {}).get('mimeType', ''),
                'post_data': request.get('postData', {}).get('text', None)
            }
            
            # Try to get response data
            response_content = response.get('content', {})
            if response_content.get('text'):
                api_call['response_preview'] = response_content['text'][:200]
            
            api_calls.append(api_call)
    
    return api_calls

def analyze_api_calls(api_calls):
    '''Analyze and categorize API calls'''
    
    print('=' * 80)
    print('Informer API Calls Analysis')
    print('=' * 80)
    
    # Group by URL pattern
    url_patterns = {}
    
    for call in api_calls:
        url = call['url']
        parsed = urlparse(url)
        path = parsed.path
        
        if path not in url_patterns:
            url_patterns[path] = []
        url_patterns[path].append(call)
    
    print(f'\nFound {len(url_patterns)} unique API endpoints:\n')
    
    for path, calls in url_patterns.items():
        print(f' {path}')
        print(f'   Calls: {len(calls)}')
        print(f'   Method: {calls[0]["method"]}')
        print(f'   Status: {calls[0]["status"]}')
        
        if calls[0].get('post_data'):
            print(f'   POST data: {calls[0]["post_data"][:100]}...')
        
        if calls[0].get('response_preview'):
            print(f'   Response preview: {calls[0]["response_preview"][:100]}...')
        
        print()
    
    return url_patterns

# Instructions
print('=' * 80)
print('HAR File Parser for KeyedIn Informer API')
print('=' * 80)
print()
print('INSTRUCTIONS:')
print('1. Open Chrome and login to KeyedIn')
print('2. Press F12 to open DevTools')
print('3. Go to Network tab')
print('4. Navigate to: Production  (BI) - Work Order Listing')
print('5. Wait for report to fully load')
print('6. Right-click in Network tab  "Save all as HAR with content"')
print('7. Save as: keyedin_network.har')
print('8. Place the file in this directory')
print('9. Re-run this script')
print()
print('=' * 80)

# Check if HAR file exists
import os
if os.path.exists('keyedin_network.har'):
    print('\n Found keyedin_network.har!')
    
    api_calls = parse_har_file()
    url_patterns = analyze_api_calls(api_calls)
    
    # Save results
    with open('informer_api_calls_from_har.json', 'w') as f:
        json.dump({
            'api_calls': api_calls,
            'url_patterns': {k: [c['url'] for c in v] for k, v in url_patterns.items()}
        }, f, indent=2)
    
    print(' Saved analysis to: informer_api_calls_from_har.json')
    print()
    print(' Now we can build a scraper using these endpoints!')
    
else:
    print('\n  keyedin_network.har not found')
    print('Follow the instructions above to capture network traffic')
