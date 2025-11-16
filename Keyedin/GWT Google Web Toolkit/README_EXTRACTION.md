# KeyedIn Complete Data Extraction Project
## Emergency Backup Before Migration

**⚠️ CRITICAL: You're about to lose decades of historical data during the KeyedIn upgrade.**

This project extracts **ALL** your Eagle Sign Co. data from KeyedIn before the migration limits you to only 3 years.

---

## Quick Start Decision Tree

```
Do you have SQL Server access to KeyedIn database?
│
├─ YES → Use Method 1 (FASTEST - 2-4 hours)
│         Contact IT for server name and credentials
│
└─ NO  → Use Method 2 (COMPREHENSIVE - 1-3 days)
          Extracts via Informer web interface
```

---

## Method 1: SQL Server Direct Extraction (RECOMMENDED)

### ⚡ Fastest Method - Complete Database Dump

**Time: 2-4 hours**  
**Coverage: 100% of all data**  
**Complexity: Low (if you have access)**

### Step 1: Get Database Access Info

Contact your IT department and ask:

1. **SQL Server Instance Name**
   - Examples: `KEYEDIN-SERVER\SQLEXPRESS` or `192.168.x.x\MSSQLSERVER`
   - Ask: "What's the SQL Server instance for our KeyedIn database?"

2. **Database Name**
   - Usually: `KeyedIn`, `KeyedInSign`, or `EAGLE_KEYIN`
   - Ask: "What's the exact database name for KeyedIn?"

3. **Your Access Level**
   - Ask: "Do I have READ permissions on the KeyedIn database?"

### Step 2: Test Connection

```powershell
# Test if you can reach the SQL Server
$Server = "YOUR-SERVER\INSTANCE"  # From IT
$Database = "KeyedIn"              # From IT

# Test connection
sqlcmd -S $Server -d $Database -Q "SELECT @@VERSION"
```

**Success?** → Proceed to Step 3  
**Failed?** → Use Method 2 instead

### Step 3: Install Dependencies

```powershell
cd C:\Scripts\SignX\keyedin
pip install pyodbc pandas
```

### Step 4: Run Extraction

```powershell
python keyedin_sql_extraction.py --server "YOUR-SERVER\INSTANCE" --database "KeyedIn"
```

**This will extract:**
- All tables
- All records
- Complete schema
- Saved as CSV, JSON, and SQLite

**Output location:** `C:\Scripts\SignX\keyedin\keyedin_backup_sql\`

---

## Method 2: Informer API Extraction (IF NO DB ACCESS)

### 🌐 Web-Based Extraction via Informer Portal

**Time: 1-3 days (depends on data volume)**  
**Coverage: All accessible reports/views**  
**Complexity: Medium**

### Prerequisites

```powershell
pip install selenium webdriver-manager requests
```

### Step 1: Extract Session Cookies

```powershell
cd C:\Scripts\SignX\keyedin
python extract_cookies.py
```

**What this does:**
1. Opens Chrome browser
2. Navigates to KeyedIn login
3. **YOU log in manually**
4. Script captures your session cookies
5. Saves to `session_cookies.json`

### Step 2: Run Complete Extraction

```powershell
python keyedin_complete_extraction.py --session-file session_cookies.json
```

**This will:**
1. Discover all available reports in Informer
2. Extract data from each report (paginated)
3. Save as CSV, JSON, and SQLite
4. Handle rate limiting and errors
5. Generate progress logs and summary

**Output location:** `C:\Scripts\SignX\keyedin\keyedin_backup\`

### Monitoring Progress

The extraction runs in the foreground with live logging:

```
================================================================================
KEYEDIN COMPLETE DATA EXTRACTION
================================================================================
Started: 2025-11-12 10:30:00

================================================================================
PHASE 1: DISCOVERING ALL REPORTS
================================================================================
✓ Discovered 47 reports
✓ Saved report catalog to keyedin_backup/metadata/report_catalog.json

================================================================================
PHASE 2: EXTRACTING ALL DATA
================================================================================

[1/47] Processing: Work Orders
--- Extracting: Work Orders ---
  Page 1: 1000 records (Total: 1000)
  Page 2: 1000 records (Total: 2000)
  Page 3: 847 records (Total: 2847)
✓ Extracted 2847 total records from Work Orders
  ✓ Saved JSON: keyedin_backup/json/work_orders.json
  ✓ Saved CSV: keyedin_backup/csv/work_orders.csv
  ✓ Saved to SQLite: work_orders table

[2/47] Processing: Quotes
...
```

---

## Understanding Your Extracted Data

### Directory Structure

```
keyedin_backup/
├── csv/                          # All data as CSV files
│   ├── work_orders.csv
│   ├── quotes.csv
│   ├── customers.csv
│   └── ...
├── json/                         # All data as JSON files
│   ├── work_orders.json
│   └── ...
├── metadata/                     # System information
│   └── report_catalog.json      # List of all discovered reports
├── keyedin_complete.db          # SQLite database (ALL DATA)
└── EXTRACTION_SUMMARY.json      # Extraction statistics
```

### Querying Your Backup

**SQLite (Recommended):**

```powershell
# Open SQLite database
sqlite3 keyedin_backup/keyedin_complete.db

# Example queries:
.tables                           # List all tables
SELECT COUNT(*) FROM work_orders; # Count work orders
SELECT * FROM quotes WHERE customer_name LIKE '%ABC%';
```

**Excel/Power Query:**
- Open any CSV file in Excel
- Use Power Query to analyze multiple CSV files

**Python/Pandas:**

```python
import pandas as pd
import sqlite3

# Connect to backup database
conn = sqlite3.connect('keyedin_backup/keyedin_complete.db')

# Query work orders from 2010-2015
df = pd.read_sql("""
    SELECT * FROM work_orders 
    WHERE created_date BETWEEN '2010-01-01' AND '2015-12-31'
""", conn)

print(f"Found {len(df)} work orders from 2010-2015")
```

---

## Validation Checklist

Before declaring success, verify your extraction:

### ✅ Data Volume Check

```powershell
# Count records in backup
sqlite3 keyedin_backup/keyedin_complete.db "
    SELECT 
        name as table_name,
        (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=t.name) as record_count
    FROM sqlite_master t
    WHERE type='table'
"
```

**Compare to KeyedIn:**
- Log into KeyedIn
- Navigate to each major module (Work Orders, Quotes, etc.)
- Check record counts match your backup

### ✅ Date Range Check

```sql
-- Check oldest records
SELECT MIN(created_date), MAX(created_date) FROM work_orders;
```

**Verify:** Should see dates going back to Eagle Sign's early KeyedIn implementation

### ✅ Critical Data Spot Check

Manually verify 5-10 random records:
1. Open KeyedIn and note a work order number
2. Query your backup for that same work order
3. Compare all fields match

---

## What Data Does This Capture?

### Standard KeyedIn Modules (Typical)

- ✅ **Work Orders** - Complete production history
- ✅ **Quotes** - All quote history and conversions
- ✅ **Customers** - Customer database
- ✅ **Projects** - Project management data
- ✅ **Invoices** - Billing history
- ✅ **Purchase Orders** - Procurement records
- ✅ **Inventory** - Parts and materials
- ✅ **Timesheets** - Labor tracking
- ✅ **Employees** - HR data
- ✅ **Vendors** - Supplier information
- ✅ **Service Calls** - Service/maintenance records
- ✅ **Equipment** - Asset tracking

### Your Custom Fields

KeyedIn allows custom fields. This extraction captures:
- Custom text fields
- Custom dropdowns
- Custom date fields
- Custom calculations
- Related records and attachments metadata

**Note:** File attachments (PDFs, images) require separate extraction - see "Advanced: File Attachments" below.

---

## Troubleshooting

### Issue: "Connection failed" (SQL Method)

**Solutions:**
1. Verify server name with IT: `ping SERVER-NAME`
2. Check database name is correct
3. Ensure SQL Server allows Windows Authentication
4. Try alternative connection string (see script comments)

### Issue: "No reports discovered" (Informer Method)

**Solutions:**
1. Check session cookies are fresh (re-run `extract_cookies.py`)
2. Verify you can access Informer portal manually
3. Check firewall isn't blocking port 8443
4. Review `extraction_*.log` file for detailed errors

### Issue: "License quota exceeded"

**This means:** KeyedIn limits concurrent sessions

**Solution:**
1. Close all other KeyedIn browser tabs/windows
2. Wait 5 minutes for sessions to expire
3. Re-run extraction

### Issue: Extraction is very slow

**Expected speeds:**
- SQL Method: 10,000+ records/minute
- Informer Method: 500-1000 records/minute (API rate limits)

**If much slower:**
1. Check network connection quality
2. Run during off-hours (less server load)
3. Consider running on-site at Eagle Sign office

---

## Advanced: File Attachments

KeyedIn stores file attachments (photos, PDFs, drawings) separately. The main extraction gets metadata, but not the actual files.

### Extracting Attachments

1. **Check if files are in database:**

```sql
-- See if files are stored as BLOBs in SQL Server
SELECT TABLE_NAME, COLUMN_NAME 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE DATA_TYPE IN ('varbinary', 'image')
```

2. **If files are in file system:**
   - Ask IT: "Where does KeyedIn store uploaded files?"
   - Usually: `\\SERVER\KeyedInFiles\` or similar
   - Copy entire folder structure

3. **Map files to records:**
   - Backup database has attachment metadata (filename, date, linked record)
   - Use this to organize copied files

---

## After Extraction: Next Steps

### 1. Verify Backup Integrity

Run validation checklist above ✅

### 2. Create Redundant Copies

```powershell
# Copy to multiple locations
robocopy keyedin_backup E:\Backups\KeyedIn\2025-11-12 /E
robocopy keyedin_backup \\NAS\Archives\KeyedIn\2025-11-12 /E

# Or compress for cloud backup
Compress-Archive -Path keyedin_backup -DestinationPath keyedin_backup_2025-11-12.zip
```

### 3. Document the Extraction

Create a file: `EXTRACTION_NOTES.txt`

```
KeyedIn Data Extraction
Date: 2025-11-12
Extracted by: Brady F.
Method: [SQL / Informer]
Source Server: [server name]
Source Database: [database name]
Date Range: [earliest] to [latest]
Total Records: [count]
Notes: [any issues or special considerations]
```

### 4. Consider Long-Term Storage

**Options:**
1. **Network Archive** - Store on company NAS/file server
2. **Cloud Backup** - Upload to OneDrive/Azure/AWS
3. **External Drive** - Physical backup kept off-site
4. **All of the above** - 3-2-1 backup rule

### 5. Migrate to New System

When migrating to new KeyedIn version:
1. Use their 3-year import for recent data
2. Keep this backup for historical reference
3. Build queries/reports to access old data when needed

---

## Timeline Estimates

### SQL Method
- Setup: 30 minutes
- Extraction: 2-4 hours
- Validation: 1 hour
- **Total: ~4-5 hours**

### Informer Method
- Setup: 30 minutes
- Extraction: 8-48 hours (depends on data volume)
- Validation: 1 hour
- **Total: ~1-3 days**

**Recommendation:** Run overnight or over weekend

---

## Support

If you encounter issues:

1. **Check log files**
   - `extraction_*.log` (Informer method)
   - `sql_extraction_*.log` (SQL method)

2. **Review error messages**
   - Most errors include specific troubleshooting steps

3. **IT Department**
   - Database access issues
   - Network connectivity
   - Server information

4. **KeyedIn Support** (last resort)
   - They may provide database access
   - They may have alternative export tools
   - Note: They'll push you to "just use the 3-year migration" - stand firm on needing ALL data

---

## Legal Considerations

✅ **This is YOUR data** - Eagle Sign owns this business data  
✅ **You have the right to extract it** - Data portability  
✅ **KeyedIn cannot prevent you** - Contract likely includes data ownership clause  
✅ **Keep it secure** - Contains customer, employee, financial data  

**Best practice:** Notify KeyedIn support that you're performing a complete backup before migration. They may even provide assistance.

---

## Success Criteria

You're done when:

- ✅ All tables/reports extracted
- ✅ Record counts verified against source
- ✅ Date ranges span full history
- ✅ Spot checks confirm data accuracy
- ✅ Multiple backup copies created
- ✅ Extraction documented
- ✅ Data accessible via SQL queries
- ✅ Team members can access if needed

---

**Good luck! This extraction protects 95 years of Eagle Sign Co. history. 🦅**
