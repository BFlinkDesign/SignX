import json

with open('WEB.MENU.json', 'r') as f:
    data = json.load(f)

menu = data.get('menu', [])

print('=' * 80)
print('Finding ALL Informer Portal URLs (extURL entries)')
print('=' * 80)

def find_ext_urls(items, path=''):
    results = []
    for item in items:
        label = item.get('text', '')
        ext_url = item.get('extURL', '')
        
        # Only items with actual extURL
        if ext_url:
            results.append({
                'path': path,
                'label': label,
                'url': ext_url
            })
        
        # Check submenu
        submenu = item.get('submenu', [])
        if submenu:
            new_path = f'{path} > {label}' if path else label
            results.extend(find_ext_urls(submenu, new_path))
    
    return results

informer_urls = find_ext_urls(menu)

print(f'\nFound {len(informer_urls)} Informer portal reports:\n')

for report in informer_urls:
    print(f' {report["label"]}')
    print(f'   Path: {report["path"]}')
    print(f'    {report["url"]}')
    print()

# Save to file
with open('informer_portal_urls.json', 'w') as f:
    json.dump(informer_urls, f, indent=2)

print('=' * 80)
print(f' Saved {len(informer_urls)} URLs to: informer_portal_urls.json')
print('=' * 80)
