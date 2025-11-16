import json

with open('WEB.MENU.json', 'r') as f:
    data = json.load(f)

menu = data.get('menu', [])

print('=' * 80)
print('Raw Menu JSON Structure')
print('=' * 80)

# Show first 3 menu items with full structure
print('\nFirst 3 menu items (full structure):\n')
for i, item in enumerate(menu[:3]):
    print(f'\nMenu Item {i+1}:')
    print(json.dumps(item, indent=2)[:1000])  # First 1000 chars
    print('...\n')

# Find work order related items
print('\n' + '=' * 80)
print('Searching for Work Order items...')
print('=' * 80)

def find_work_orders(items, path=''):
    results = []
    for item in items:
        label = item.get('label', item.get('text', ''))
        
        if 'work order' in label.lower() or 'job cost' in label.lower():
            results.append({
                'path': path,
                'item': item
            })
        
        # Check submenu with all possible keys
        submenu = (item.get('submenu') or 
                  item.get('children') or 
                  item.get('items') or 
                  item.get('menu') or [])
        
        if submenu:
            new_path = f'{path} > {label}' if path else label
            results.extend(find_work_orders(submenu, new_path))
    
    return results

work_order_items = find_work_orders(menu)

print(f'\nFound {len(work_order_items)} work order related items:\n')

for result in work_order_items[:15]:  # Show first 15
    print(f'\n Path: {result["path"]}')
    print(f'   Item structure:')
    print(json.dumps(result['item'], indent=4)[:500])
    print()

print('=' * 80)
