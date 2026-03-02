# SignX Unified Launcher - Big Red Button
# Author: Gemini CLI (v2.1.0 Hardened)

Clear-Host
Write-Host "--- SIGNX PRODUCTION LAUNCHER ---" -ForegroundColor Cyan

$root = "C:\Users\Brady.EAGLE\Desktop\SignX"
$db = "C:\Scripts\signx-warehouse\warehouse\signx.duckdb"
$env = "$root\signx-takeoff\.env"

# 1. Health Check
Write-Host "[1/3] Checking dependencies..."
if (!(Test-Path $db)) { Write-Error "CRITICAL: Warehouse DB not found at $db"; exit }
if (!(Test-Path $env)) { Write-Warning "NOTICE: .env missing. Some API features (Notion/Informer) may be disabled."; }

# 2. Start Backend
Write-Host "[2/3] Starting Backend API Engine..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd $root\signx-takeoff; python app.py"

# 3. Open UI
Write-Host "[3/3] Opening Dashboard..." -ForegroundColor Green
Start-Sleep -s 3
Start-Process "$root\SignX-Dashboard\index.html"

Write-Host "
SYSTEM LIVE. Do not close the black terminal window while working." -ForegroundColor Cyan
