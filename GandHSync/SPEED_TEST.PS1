# Network Speed Test Script
Write-Host "==========================================="
Write-Host "NETWORK TRANSFER SPEED TEST"
Write-Host "==========================================="
Write-Host ""

# Check if drives exist
if (-not (Test-Path G:\)) {
    Write-Host "ERROR: G: drive not found!" -ForegroundColor Red
    pause
    exit
}

# Get size of G: and H: drives
Write-Host "Calculating drive sizes..."
$GSize = (Get-ChildItem G:\ -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
$HSize = (Get-ChildItem H:\ -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum

$GSizeGB = [math]::Round($GSize / 1GB, 2)
$HSizeGB = [math]::Round($HSize / 1GB, 2)
$TotalGB = $GSizeGB + $HSizeGB

Write-Host ""
Write-Host "Drive Sizes:" -ForegroundColor Cyan
Write-Host "G: Drive = $GSizeGB GB"
Write-Host "H: Drive = $HSizeGB GB"
Write-Host "Total    = $TotalGB GB"
Write-Host ""

# Find a test file (at least 10MB)
Write-Host "Finding test file..." -ForegroundColor Yellow
$testFile = Get-ChildItem G:\ -Recurse -ErrorAction SilentlyContinue | 
    Where-Object {$_.Length -gt 10MB -and $_.Length -lt 100MB} | 
    Select-Object -First 1

if (-not $testFile) {
    Write-Host "No suitable test file found. Creating 50MB test..." -ForegroundColor Yellow
    $testFile = "G:\speed_test_temp.dat"
    fsutil file createnew $testFile 52428800
    $created = $true
}

# Test copy speed
Write-Host "Testing transfer speed with: $($testFile.Name) ($([math]::Round($testFile.Length / 1MB, 2)) MB)" -ForegroundColor Yellow
Write-Host "Copying..." -ForegroundColor Gray

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
Copy-Item -Path $testFile.FullName -Destination "C:\WorkSync\speed_test.tmp" -Force
$stopwatch.Stop()

$seconds = $stopwatch.Elapsed.TotalSeconds
$MB = $testFile.Length / 1MB
$MBps = $MB / $seconds
$Mbps = $MBps * 8

# Clean up
Remove-Item "C:\WorkSync\speed_test.tmp" -Force -ErrorAction SilentlyContinue
if ($created) { Remove-Item $testFile -Force -ErrorAction SilentlyContinue }

# Calculate estimates
Write-Host ""
Write-Host "==========================================="
Write-Host "RESULTS:" -ForegroundColor Green
Write-Host "==========================================="
Write-Host "Transfer Speed: $([math]::Round($MBps, 2)) MB/s ($([math]::Round($Mbps, 2)) Mbps)"
Write-Host ""

$GHours = [math]::Round(($GSizeGB * 1024) / ($MBps * 3600), 1)
$HHours = [math]::Round(($HSizeGB * 1024) / ($MBps * 3600), 1)
$TotalHours = [math]::Round(($TotalGB * 1024) / ($MBps * 3600), 1)

Write-Host "ESTIMATED SYNC TIMES:" -ForegroundColor Cyan
Write-Host "G: Drive = $GHours hours"
Write-Host "H: Drive = $HHours hours"
Write-Host "Total    = $TotalHours hours"
Write-Host ""

# Recommendations
if ($TotalHours -gt 8) {
    Write-Host "RECOMMENDATION:" -ForegroundColor Yellow
    Write-Host "Start sync before leaving for the day or run overnight."
} elseif ($TotalHours -gt 4) {
    Write-Host "RECOMMENDATION:" -ForegroundColor Yellow
    Write-Host "Start sync during lunch or a long meeting."
} else {
    Write-Host "RECOMMENDATION:" -ForegroundColor Green
    Write-Host "Sync should complete in a reasonable time. Start anytime!"
}

Write-Host ""
Write-Host "==========================================="
pause