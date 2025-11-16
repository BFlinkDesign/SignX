import json

with open('WEB.MENU.json', 'r') as f:
    data = json.load(f)

menu = data.get('menu', [])

print('=' * 80)
print('Finding BI Report URLs (Informer Portal)')
print('=' * 80)

def find_bi_reports(items, path=''):
    results = []
    for item in items:
        label = item.get('text', '')
        ext_url = item.get('extURL', '')
        process = item.get('process', '')
        
        # Look for BI reports (have extURL or start with (BI))
        if ext_url or '(BI)' in label or 'BI' in label:
            if 'work' in label.lower() or 'order' in label.lower() or 'cost' in label.lower():
                results.append({
                    'path': path,
                    'label': label,
                    'extURL': ext_url,
                    'process': process
                })
        
        # Check submenu
        submenu = item.get('submenu', [])
        if submenu:
            new_path = f'{path} > {label}' if path else label
            results.extend(find_bi_reports(submenu, new_path))
    
    return results

bi_reports = find_bi_reports(menu)

print(f'\nFound {len(bi_reports)} BI work order reports:\n')

for report in bi_reports:
    print(f' {report["label"]}')
    print(f'   Path: {report["path"]}')
    if report['extURL']:
        print(f'    URL: {report["extURL"][:100]}...')
    else:
        print(f'   Process: {report["process"]}')
    print()

# Save URLs to file
with open('bi_report_urls.json', 'w') as f:
    json.dump(bi_reports, f, indent=2)

print('=' * 80)
print(' Saved to: bi_report_urls.json')
print('=' * 80)
print('\nThese Informer URLs contain the actual work order data!')
