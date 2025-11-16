# KeyedIn Extraction Method Advisor
# Checks your access and recommends the best extraction approach

Write-Host "`n" + ("=" * 80) -ForegroundColor Cyan
Write-Host " KEYEDIN EXTRACTION METHOD ADVISOR" -ForegroundColor Yellow
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

$score = @{
    SQL = 0
    Informer = 0
}

# Check 1: Python installation
Write-Host "[1/5] Checking Python..." -ForegroundColor White
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ Python installed: $pythonVersion" -ForegroundColor Green
    $score.SQL++
    $score.Informer++
} catch {
    Write-Host "  ✗ Python not found" -ForegroundColor Red
    Write-Host "    Install from: python.org" -ForegroundColor Yellow
}

# Check 2: SQL Server access
Write-Host "`n[2/5] Checking SQL Server access..." -ForegroundColor White
$server = Read-Host "  Enter SQL Server instance (press Enter to skip)"

if (-not [string]::IsNullOrWhiteSpace($server)) {
    $database = Read-Host "  Enter database name (default: KeyedIn)"
    if ([string]::IsNullOrWhiteSpace($database)) { $database = "KeyedIn" }
    
    try {
        $testQuery = sqlcmd -S $server -d $database -Q "SELECT 1" -h -1 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ SQL Server accessible!" -ForegroundColor Green
            $score.SQL += 10  # Big bonus for SQL access
            $sqlServer = $server
            $sqlDatabase = $database
        } else {
            throw "Access denied"
        }
    } catch {
        Write-Host "  ✗ Cannot access SQL Server" -ForegroundColor Red
        Write-Host "    (This is OK - we'll use web extraction)" -ForegroundColor Gray
    }
} else {
    Write-Host "  ⊘ Skipped SQL Server test" -ForegroundColor Gray
}

# Check 3: Web browser access
Write-Host "`n[3/5] Checking web access to KeyedIn..." -ForegroundColor White
$keyedinUrl = "https://eaglesign.keyedinsign.com:8443/eaglesign/"

try {
    $webTest = Invoke-WebRequest -Uri $keyedinUrl -Method Head -TimeoutSec 5 -UseBasicParsing 2>&1
    Write-Host "  ✓ KeyedIn web interface reachable" -ForegroundColor Green
    $score.Informer += 5
} catch {
    Write-Host "  ✗ Cannot reach KeyedIn web interface" -ForegroundColor Red
    Write-Host "    Check network connection or VPN" -ForegroundColor Yellow
}

# Check 4: Chrome browser (for cookie extraction)
Write-Host "`n[4/5] Checking Chrome browser..." -ForegroundColor White
$chromePaths = @(
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "${env:LocalAppData}\Google\Chrome\Application\chrome.exe"
)

$chromeFound = $false
foreach ($path in $chromePaths) {
    if (Test-Path $path) {
        Write-Host "  ✓ Chrome installed: $path" -ForegroundColor Green
        $chromeFound = $true
        $score.Informer += 2
        break
    }
}

if (-not $chromeFound) {
    Write-Host "  ⊘ Chrome not found (optional)" -ForegroundColor Gray
    Write-Host "    You can still extract via Informer, but manual cookie extraction needed" -ForegroundColor Yellow
}

# Check 5: Available disk space
Write-Host "`n[5/5] Checking available disk space..." -ForegroundColor White
$drive = (Get-Location).Drive.Name
$disk = Get-PSDrive $drive
$freeGB = [math]::Round($disk.Free / 1GB, 2)

if ($freeGB -gt 50) {
    Write-Host "  ✓ Sufficient space: ${freeGB}GB free" -ForegroundColor Green
    $score.SQL++
    $score.Informer++
} elseif ($freeGB -gt 10) {
    Write-Host "  ! Limited space: ${freeGB}GB free" -ForegroundColor Yellow
    Write-Host "    Should be OK, but monitor during extraction" -ForegroundColor Gray
} else {
    Write-Host "  ✗ Low disk space: ${freeGB}GB free" -ForegroundColor Red
    Write-Host "    Free up space before extraction" -ForegroundColor Yellow
}

# Generate recommendation
Write-Host "`n" + ("=" * 80) -ForegroundColor Cyan
Write-Host " RECOMMENDATION" -ForegroundColor Yellow
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

if ($score.SQL -gt $score.Informer) {
    Write-Host "✓ RECOMMENDED: Method 1 - SQL Server Direct Extraction" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Why: You have SQL Server access (fastest method)" -ForegroundColor White
    Write-Host "  Time: 2-4 hours for complete extraction" -ForegroundColor Gray
    Write-Host "  Coverage: 100% of all tables and data" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Command to run:" -ForegroundColor Cyan
    if ($sqlServer) {
        Write-Host "    python keyedin_sql_extraction.py --server `"$sqlServer`" --database `"$sqlDatabase`"" -ForegroundColor White
    } else {
        Write-Host "    python keyedin_sql_extraction.py --server YOUR-SERVER\INSTANCE --database KeyedIn" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "  See README_EXTRACTION.md section: 'Method 1: SQL Server Direct Extraction'" -ForegroundColor Yellow
    
} else {
    Write-Host "✓ RECOMMENDED: Method 2 - Informer API Extraction" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Why: No SQL Server access available" -ForegroundColor White
    Write-Host "  Time: 1-3 days for complete extraction" -ForegroundColor Gray
    Write-Host "  Coverage: All accessible reports and views" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Commands to run:" -ForegroundColor Cyan
    Write-Host "    1. python extract_cookies.py" -ForegroundColor White
    Write-Host "       (Opens browser, you log in, saves cookies)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "    2. python keyedin_complete_extraction.py" -ForegroundColor White
    Write-Host "       (Runs automated extraction)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  See README_EXTRACTION.md section: 'Method 2: Informer API Extraction'" -ForegroundColor Yellow
}

# Additional notes
Write-Host "`n" + ("=" * 80) -ForegroundColor Cyan
Write-Host " IMPORTANT NOTES" -ForegroundColor Yellow
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

Write-Host "⚠️  This extraction is CRITICAL for preserving your data" -ForegroundColor Yellow
Write-Host "    KeyedIn upgrade will only migrate 3 years of history" -ForegroundColor Gray
Write-Host "    This backup preserves ALL of Eagle Sign's historical data" -ForegroundColor Gray
Write-Host ""

Write-Host "📅 Timeline:" -ForegroundColor White
Write-Host "    - Run extraction BEFORE migration date" -ForegroundColor Gray
Write-Host "    - Allow sufficient time (1-3 days for Informer method)" -ForegroundColor Gray
Write-Host "    - Validate extraction before decommissioning old system" -ForegroundColor Gray
Write-Host ""

Write-Host "💾 Backup Strategy:" -ForegroundColor White
Write-Host "    - Keep multiple copies (local + network + cloud)" -ForegroundColor Gray
Write-Host "    - Store in compressed archive for long-term retention" -ForegroundColor Gray
Write-Host "    - Document extraction date and coverage" -ForegroundColor Gray
Write-Host ""

# Save recommendation to file
$recommendation = @"
KeyedIn Extraction Recommendation
Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

Recommended Method: $(if ($score.SQL -gt $score.Informer) { 'SQL Server Direct' } else { 'Informer API' })

SQL Score: $($score.SQL)
Informer Score: $($score.Informer)

System Check Results:
- Python: $(if ($pythonVersion) { 'Installed' } else { 'Not Found' })
- SQL Access: $(if ($sqlServer) { "Yes ($sqlServer\$sqlDatabase)" } else { 'No' })
- Web Access: $(if ($score.Informer -ge 5) { 'Yes' } else { 'Limited' })
- Chrome: $(if ($chromeFound) { 'Installed' } else { 'Not Found' })
- Disk Space: ${freeGB}GB free

Next Steps:
$(if ($score.SQL -gt $score.Informer) {
"1. Run: python keyedin_sql_extraction.py --server `"$sqlServer`" --database `"$sqlDatabase`"
2. Validate extraction
3. Create backup copies"
} else {
"1. Run: python extract_cookies.py
2. Run: python keyedin_complete_extraction.py
3. Monitor progress (1-3 days)
4. Validate extraction
5. Create backup copies"
})

See README_EXTRACTION.md for complete instructions.
"@

$recommendation | Out-File "extraction_recommendation.txt"
Write-Host "📝 Recommendation saved to: extraction_recommendation.txt" -ForegroundColor Cyan
Write-Host ""

# Offer to start extraction
$startNow = Read-Host "Ready to start extraction now? (y/n)"

if ($startNow -eq 'y') {
    if ($score.SQL -gt $score.Informer -and $sqlServer) {
        Write-Host "`nStarting SQL extraction..." -ForegroundColor Green
        python keyedin_sql_extraction.py --server $sqlServer --database $sqlDatabase
    } else {
        Write-Host "`nStarting cookie extraction..." -ForegroundColor Green
        python extract_cookies.py
    }
} else {
    Write-Host "`nNo problem! Run the recommended command when ready." -ForegroundColor White
    Write-Host "See extraction_recommendation.txt for your personalized guide." -ForegroundColor Gray
}

Write-Host ""
