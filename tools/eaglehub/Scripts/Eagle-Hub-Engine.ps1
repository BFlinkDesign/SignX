# Eagle Workflow Hub 2.0 - Main Engine
$global:EagleHubVersion = "2.0.0"
$global:HubPath = "\\ES-FS02\users\brady\EagleHub"
$global:LocalPath = "C:\Users\Brady.EAGLE\Documents\EagleHub2"

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "   EAGLE WORKFLOW HUB 2.0 STARTING  " -ForegroundColor White
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Settings
$settings = @{
    AutoMode = $true
    ScanInterval = 30
    EmailInterval = 15
    PriorityCustomers = @("DSM Airport", "Wells Fargo", "Berkshire", "Valley Church")
}

Write-Host "Settings:" -ForegroundColor Yellow
Write-Host "  Auto Mode: $($settings.AutoMode)" -ForegroundColor White
Write-Host "  Scan Interval: $($settings.ScanInterval) minutes" -ForegroundColor White
Write-Host "  Email Check: $($settings.EmailInterval) minutes" -ForegroundColor White
Write-Host ""

Write-Host "Priority Customers:" -ForegroundColor Yellow
$settings.PriorityCustomers | ForEach-Object { Write-Host "  - $_" -ForegroundColor White }
Write-Host ""

Write-Host "[1] Check Outlook Emails" -ForegroundColor Cyan
Write-Host "[2] Process KeyedIn Data" -ForegroundColor Cyan
Write-Host "[3] Settings" -ForegroundColor Cyan
Write-Host "[X] Exit" -ForegroundColor Red
Write-Host ""

$choice = Read-Host "Select option"

switch ($choice) {
    "1" { 
        Write-Host "Checking Outlook for BID REQUEST emails..." -ForegroundColor Yellow
        Write-Host "Feature coming soon!" -ForegroundColor Gray
    }
    "2" { 
        Write-Host "Processing KeyedIn data..." -ForegroundColor Yellow
        Write-Host "Feature coming soon!" -ForegroundColor Gray
    }
    "3" { 
        Write-Host "Opening settings in Chrome dashboard..." -ForegroundColor Yellow
        Start-Process chrome.exe -ArgumentList "$global:HubPath\Dashboard.html"
    }
    "X" { exit }
}

Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
