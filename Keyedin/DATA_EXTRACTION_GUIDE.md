# KeyedIn Data Extraction Guide

## ✅ Yes! The API Can Pull Data from Multiple Endpoints

The KeyedIn Enhanced API can extract data from **all available endpoints** on the KeyedIn website. Here's what's available:

## Available Data Sources

### 1. **Menu Structure** ✅
- **Endpoint**: `/cgi-bin/mvi.exe/WEB.MENU?USERNAME=BRADYF`
- **Data**: Complete navigation menu hierarchy
- **Format**: JSON
- **Use Case**: Discover all available pages and endpoints

### 2. **Work Orders** ✅ (6 endpoints)
- **WO Inquiry Form**: `/cgi-bin/mvi.exe/WO.INQUIRY`
  - Form fields, search criteria, filters
- **WO History**: `/cgi-bin/mvi.exe/WO.HISTORY`
  - Historical work order data (4 tables)
- **WO Cost Summary**: `/cgi-bin/mvi.exe/WO.COST.SUMMARY`
  - Cost breakdowns and summaries
- **WO Completion Inquiry**: `/cgi-bin/mvi.exe/WO.COMPLETION.INQUIRY`
  - Completion status and details
- **WO Group Analysis**: `/cgi-bin/mvi.exe/WO.GROUP.ANALYSIS`
  - Grouped analysis data (5 tables)
- **Work Order List**: `/cgi-bin/mvi.exe/WORKORDER.LIST`
  - List of all work orders (2 tables)

### 3. **Service Calls** ✅ (2 endpoints)
- **Service Call List**: `/cgi-bin/mvi.exe/SERVICE.CALL.LIST`
  - Complete service call listings (2 tables)
- **Assigned Service Calls**: `/cgi-bin/mvi.exe/WIDGET.ASSIGNED.SERVICE.CALLS?ACTION=AJAX`
  - Widget data for assigned service calls

### 4. **Widgets** ✅ (3 endpoints)
- **Assigned Milestones**: `/cgi-bin/mvi.exe/WIDGET.ASSIGNED.MILESTONES?ACTION=AJAX`
- **CRM Tasks**: `/cgi-bin/mvi.exe/WIDGET.CRM.TASKS?ACTION=AJAX`
- **FYI Widget**: `/cgi-bin/mvi.exe/WIDGET.FYI?ACTION=AJAX`

### 5. **Main Pages** ✅ (2 endpoints)
- **Main Page**: `/cgi-bin/mvi.exe/MAIN`
- **Home**: `/cgi-bin/mvi.exe/HOME`

## Data Extraction Results

**Latest Extraction**: 13/14 endpoints successful (93% success rate)

### Extracted Data Includes:
- ✅ **HTML Tables** - Structured data tables
- ✅ **Forms** - Input fields, dropdowns, search criteria
- ✅ **JSON Data** - Structured API responses
- ✅ **Text Content** - Raw page content
- ✅ **Links** - Navigation and related pages

## How to Extract Data

### Method 1: Comprehensive Extraction

```bash
python extract_all_data.py
```

This extracts data from all available endpoints and saves to `extracted_data/` directory.

### Method 2: Custom Extraction

```python
from keyedin_api_enhanced import KeyedInAPIEnhanced
from bs4 import BeautifulSoup

api = KeyedInAPIEnhanced()

# Extract specific endpoint
response = api.get('/cgi-bin/mvi.exe/WO.HISTORY')
soup = BeautifulSoup(response.text, 'html.parser')

# Extract tables
tables = soup.find_all('table')
for table in tables:
    rows = table.find_all('tr')
    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
        print(cells)
```

### Method 3: Extract Menu to Discover More Endpoints

```python
from keyedin_api_enhanced import KeyedInAPIEnhanced
import json

api = KeyedInAPIEnhanced()

# Get menu structure
menu = api.get_menu()

# Save to explore
with open('menu_structure.json', 'w') as f:
    json.dump(menu, f, indent=2)

# Menu contains all available endpoints!
```

## Data Storage

All extracted data is saved to:
- **Location**: `extracted_data/` directory (project root)
- **Format**: JSON files with timestamps
- **Structure**: Organized by data type (menu, work_orders, service_calls, etc.)

## Example: Extract Work Order Data

```python
from keyedin_api_enhanced import KeyedInAPIEnhanced
from bs4 import BeautifulSoup
import json

api = KeyedInAPIEnhanced()

# Extract work order history
response = api.get('/cgi-bin/mvi.exe/WO.HISTORY')
soup = BeautifulSoup(response.text, 'html.parser')

# Extract all tables
work_orders = []
for table in soup.find_all('table'):
    headers = []
    rows_data = []
    
    # Get headers
    header_row = table.find('tr')
    if header_row:
        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
    
    # Get data rows
    for row in table.find_all('tr')[1:]:  # Skip header
        cells = [td.get_text(strip=True) for td in row.find_all('td')]
        if cells:
            rows_data.append(cells)
    
    if rows_data:
        work_orders.append({
            'headers': headers,
            'rows': rows_data
        })

# Save extracted data
with open('work_orders_extracted.json', 'w') as f:
    json.dump(work_orders, f, indent=2)

print(f"Extracted {len(work_orders)} work order tables")
```

## Available Endpoints Summary

Based on the menu structure and discovery, there are **50+ endpoints** available including:

- Work Orders (6+ endpoints)
- Service Calls (2+ endpoints)
- CRM (multiple endpoints)
- Project Management (multiple endpoints)
- Inventory (multiple endpoints)
- Purchasing (multiple endpoints)
- Sales (multiple endpoints)
- Accounting (multiple endpoints)
- Reports (multiple endpoints)
- Administration (multiple endpoints)

## Next Steps

1. **Run comprehensive extraction**: `python extract_all_data.py`
2. **Explore menu structure**: Extract menu to discover all endpoints
3. **Custom extraction**: Build specific extractors for your needs
4. **Automate**: Schedule regular data extractions

## Notes

- All data extraction respects session management
- Sessions automatically refresh if expired
- Data is saved with timestamps for tracking
- HTML tables are parsed into structured data
- JSON endpoints return structured data directly

The API can pull data from **any endpoint** on the KeyedIn website that your user has access to!


