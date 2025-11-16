from bs4 import BeautifulSoup
from pathlib import Path

print('=' * 80)
print('Analyzing KeyedIn Work Order List')
print('=' * 80)

# Check what files we have
files = ['WORKORDER_LIST.html', 'SERVICE_CALL_LIST.html', 'MAIN.html']

for filename in files:
    html_file = Path(filename)
    if html_file.exists():
        print(f'\n {filename}')
        print('=' * 80)
        
        html = html_file.read_text(encoding='utf-8')
        print(f'Length: {len(html)} bytes\n')
        
        # Show full content (files are small)
        print(html)
        print('\n' + '=' * 80)
        
        # Parse structure
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for iframes (KeyedIn often uses iframes)
        iframes = soup.find_all('iframe')
        if iframes:
            print(f'\n  Found {len(iframes)} iframes:')
            for iframe in iframes:
                src = iframe.get('src', '')
                print(f'   Source: {src}')
        
        # Look for links
        links = soup.find_all('a', href=True)
        if links:
            print(f'\n Found {len(links)} links:')
            for link in links[:20]:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                print(f'   {text:50s}  {href}')
        
        print('\n')
    else:
        print(f' {filename} not found')

print('=' * 80)
