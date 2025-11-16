import json

print('=' * 80)
print('Analyzing KeyedIn Menu Structure')
print('=' * 80)

with open('WEB.MENU.json', 'r') as f:
    data = json.load(f)

menu = data.get('menu', [])

print(f'\n Found {len(menu)} menu items\n')

# Recursively explore menu structure
def explore_menu(items, indent=0):
    for item in items:
        prefix = '  ' * indent
        
        # Get item details
        label = item.get('label', item.get('text', 'No label'))
        url = item.get('url', item.get('href', ''))
        item_type = item.get('type', '')
        
        # Highlight work order related items
        keywords = ['work', 'order', 'service', 'job', 'report', 'invoice', 'estimate']
        is_important = any(kw in label.lower() or kw in url.lower() for kw in keywords)
        
        marker = '' if is_important else '  '
        
        if url:
            print(f'{marker} {prefix}{label:50s}  {url}')
        else:
            print(f'{marker} {prefix}{label}')
        
        # Check for submenu
        submenu = item.get('submenu', item.get('children', item.get('items', [])))
        if submenu:
            explore_menu(submenu, indent + 1)

explore_menu(menu)

print('\n' + '=' * 80)
print('Look for URLs containing work orders, reports, or data!')
print('=' * 80)
