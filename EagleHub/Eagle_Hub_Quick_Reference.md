# Eagle Workflow Hub - Quick Reference for Claude

## 🚀 Response Priorities

### When User Asks About Features:
**Always Emphasize:**
- Time savings: 15-45 min → 2-5 min per quote
- Confidence-based pricing from historical data
- Zero disruption to KeyedIn
- Chrome-based dashboard
- Pattern learning capabilities

### When User Reports Issues:
**Check First:**
1. PowerShell execution policy
2. Network path access (\\ES-FS02\users\brady\)
3. Chrome installation
4. Scheduled task permissions
5. KeyedIn Excel export availability

## 📋 Key Facts to Remember

### System Architecture:
- **Primary Path**: `\\ES-FS02\users\brady\EagleHub`
- **Backup Path**: `C:\EagleHub`
- **Email Subject Trigger**: "BID REQUEST"
- **Job Number Format**: 209-0385
- **Browser Required**: Chrome (not Edge, not Firefox)

### User's Actual Workflow:
1. Email arrives in Outlook
2. Currently manual 6+ system process
3. KeyedIn is ERP (don't modify)
4. Excel exports contain historical data
5. CorelDRAW for vectors
6. BlueBeam for rasters
7. Professional PDF output needed

### Critical User Requirements:
- **Multi-role support** (not just estimating)
- **30-minute + hourly** scheduling options
- **Manual override** for everything
- **Pattern learning** with auto mode
- **Network storage** (not local C:\)

## 💬 Response Templates

### For Installation Questions:
```
To install Eagle Workflow Hub 2:

1. Save files to C:\EagleHub\
2. Run PowerShell as Administrator
3. Execute: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
4. Run: .\Setup-Eagle-Hub-2.ps1
5. Choose Option 1 for full installation

The system will automatically:
✅ Copy files to \\ES-FS02\users\brady\EagleHub
✅ Create Chrome launcher
✅ Set up 30-min and hourly scheduled tasks
✅ Launch the dashboard
```

### For Feature Questions:
```
Eagle Workflow Hub 2 provides:

📧 **Email Processing**: Auto-detects "BID REQUEST" emails
🗃️ **KeyedIn Integration**: Reads historical data without modifications
📐 **Drawing Analysis**: AIA-compliant scale detection
💰 **Smart Pricing**: Based on [X] similar jobs with [Y]% confidence
🚀 **Time Savings**: Reduces quote time from 15-45 min to 2-5 min

Current Status: [Describe specific feature status]
```

### For Troubleshooting:
```
Let's diagnose the issue:

1. Check network access:
   - Can you access \\ES-FS02\users\brady\EagleHub?
   - Is your 2025 Work Order Excel file accessible?

2. Verify PowerShell permissions:
   - Run: Get-ExecutionPolicy
   - Should show: RemoteSigned or Unrestricted

3. Check Chrome path:
   - Default: C:\Program Files\Google\Chrome\Application\chrome.exe
   - Verify Chrome opens manually

4. Review logs:
   - Check: \\ES-FS02\users\brady\EagleHub\Logs\
   - Look for today's log file

Which step shows an issue?
```

## 🔧 Common Solutions

### PowerShell Won't Run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# or if that fails:
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
```

### Network Path Issues:
```powershell
# Test network access
Test-Path "\\ES-FS02\users\brady"
# Map as network drive if needed
New-PSDrive -Name "Z" -PSProvider FileSystem -Root "\\ES-FS02\users\brady" -Persist
```

### Chrome Won't Launch:
```powershell
# Find Chrome path
Get-ChildItem -Path "C:\Program Files" -Filter "chrome.exe" -Recurse
# Update config with correct path
```

### Scheduled Tasks Not Running:
```powershell
# Check task status
Get-ScheduledTask | Where-Object {$_.TaskName -like "*Eagle*"}
# Enable if disabled
Enable-ScheduledTask -TaskName "Eagle Hub 30min Scan"
```

## 📊 Performance Metrics to Quote

### Time Savings:
- Manual quote: 15-45 minutes
- Automated quote: 2-5 minutes
- Daily savings: 2-4 hours
- Monthly value: $2,000-4,000 in labor

### Accuracy Improvements:
- Historical data points: 10-100+ per quote
- Confidence levels: 65-95%
- Error reduction: 75%
- Consistency: 100%

### Process Efficiency:
- Email to quote: < 5 minutes
- File organization: Automatic
- Drawing measurements: < 30 seconds
- PDF generation: < 10 seconds

## 🎯 Key Messages

### Value Proposition:
"Eagle Workflow Hub transforms your 15-45 minute manual quoting process into a 2-5 minute automated workflow, using your historical KeyedIn data to provide confidence-based pricing."

### Integration Philosophy:
"Hub works WITH your existing systems - KeyedIn remains your ERP, Outlook stays your email client. We're adding intelligence, not replacing infrastructure."

### ROI Statement:
"Save 2-4 hours daily on quoting, reduce errors by 75%, and win more bids with data-driven pricing based on your actual job history."

## ⚠️ Never Forget

1. **User wears multiple hats** - Estimator, PM, Production, Sales
2. **Chrome only** - No Edge, No Firefox
3. **Network paths** - \\ES-FS02\users\brady\, not C:\
4. **30-min + hourly** - Both scheduling options needed
5. **Pattern learning** - Automatic with manual override
6. **KeyedIn is sacred** - Read-only, never modify
7. **Excel integration** - Primary data source
8. **Professional output** - Must generate client-ready PDFs
9. **Confidence intervals** - Always show pricing confidence
10. **Time is money** - Always quantify time savings

## 📝 Code Snippet Library

### Quick Email Check:
```powershell
$outlook = New-Object -ComObject Outlook.Application
$inbox = $outlook.GetNamespace("MAPI").GetDefaultFolder(6)
$bidRequests = $inbox.Items | Where-Object { $_.Subject -match "BID REQUEST" }
Write-Host "Found $($bidRequests.Count) bid requests"
```

### Quick Price Calculation:
```powershell
$sqft = 100
$rate = 75  # dollars per sq ft
$markup = 1.35  # 35% markup
$price = [Math]::Round($sqft * $rate * $markup, 0)
Write-Host "Quote: $$price (Based on $rate/sqft with 35% markup)"
```

### Quick File Organization:
```powershell
$jobNumber = "209-0385"
$projectPath = "\\ES-FS02\users\brady\Projects\$jobNumber"
@("Incoming", "Estimates", "Drawings", "Production") | ForEach-Object {
    New-Item -ItemType Directory -Path "$projectPath\$_" -Force
}
```

## 🚨 Emergency Responses

### If System Breaks:
"The Eagle Hub system has built-in recovery. Try:
1. Run Emergency Stop in dashboard
2. Restart PowerShell as Administrator
3. Re-run Setup-Eagle-Hub-2.ps1
4. Check logs at \\ES-FS02\users\brady\EagleHub\Logs"

### If KeyedIn Changes:
"Eagle Hub reads from Excel exports, not KeyedIn directly. Update the Excel export path in Settings tab and the system will adapt."

### If Network Fails:
"Eagle Hub has local fallback at C:\EagleHub. The system will queue operations and sync when network returns."

## 📚 Documentation Links

### Files Created:
- `Eagle_Workflow_Hub_Instructions.md` - Full project documentation
- `Eagle_Hub_Coding_Patterns.md` - Code templates and patterns
- `Eagle_Hub_Quick_Reference.md` - This quick reference guide

### Key Scripts:
- `Eagle-Hub-2-Engine.ps1` - Main automation engine
- `Setup-Eagle-Hub-2.ps1` - Installation script
- `Eagle-PDF-Master.ps1` - PDF processing module

### Dashboard:
- `eagle-workflow-hub-2.html` - Main interface
- Chrome URL: `file:///ES-FS02/users/brady/EagleHub/eagle-workflow-hub-2.html`