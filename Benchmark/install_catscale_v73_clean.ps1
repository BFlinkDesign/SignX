# CAT Scale Benchmark System v7.3 - Clean Modular Installer
# Bulletproof Edition with External Module Loading
param(
    [string]$InstallPath = "C:\Scripts\Benchmark",
    [switch]$Uninstall = $false,
    [switch]$Repair = $false,
    [string]$ModulesPath = $PSScriptRoot
)

$ErrorActionPreference = "Stop"
$ProgressPreference = 'SilentlyContinue'
$Global:LogFile = "$env:TEMP\catscale_install_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$Global:Version = "7.3.0"

# Enhanced logging
function Write-Log {
    param($Message, $Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Add-Content -Path $Global:LogFile -Value $logMessage -ErrorAction SilentlyContinue
    
    switch ($Level) {
        "ERROR" { Write-Host $Message -ForegroundColor Red }
        "WARNING" { Write-Host $Message -ForegroundColor Yellow }
        "SUCCESS" { Write-Host $Message -ForegroundColor Green }
        default { Write-Host $Message -ForegroundColor Cyan }
    }
}

# Professional header
function Show-Header {
    Clear-Host
    $header = @"
╔════════════════════════════════════════════════════════════════════════════════╗
║                    CAT SCALE BENCHMARK SYSTEM v7.3                               ║
║                Bulletproof Edition - Clean Modular Install                       ║
╠════════════════════════════════════════════════════════════════════════════════╣
║  ► Work Order Capture Working    ► Validation Accurate     ► OCR Auto-Mode      ║
║  ► Triple-Hash Caching          ► Statistical Analysis    ► GPU Ready           ║
║  ► Professional GUI             ► One-Click Install       ► Auto-Recovery       ║
╚════════════════════════════════════════════════════════════════════════════════╝
"@
    Write-Host $header -ForegroundColor Cyan
    Write-Host ""
}

Show-Header

# Ensure elevated (Top Fix 3)
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Log "Administrator privileges are required. Please re-run as Administrator." "ERROR"
    Read-Host "Press Enter to exit"
    exit 1
}

# Uninstall mode
if ($Uninstall) {
    Write-Log "Starting uninstallation..." "WARNING"
    
    if (Test-Path $InstallPath) {
        # Remove shortcuts
        $shortcuts = @(
            "$([Environment]::GetFolderPath('Desktop'))\CAT Scale Benchmarker.lnk",
            "$([Environment]::GetFolderPath('Programs'))\CAT Scale Benchmark\*.lnk",
            "$env:APPDATA\Microsoft\Windows\SendTo\CAT Scale Parser.bat"
        )
        
        foreach ($shortcut in $shortcuts) {
            if (Test-Path $shortcut) {
                Remove-Item $shortcut -Force -ErrorAction SilentlyContinue
                Write-Log "  Removed: $shortcut" "SUCCESS"
            }
        }
        
        # Remove installation
        Remove-Item $InstallPath -Recurse -Force
        Write-Log "Uninstallation complete" "SUCCESS"
    } else {
        Write-Log "Installation not found at $InstallPath" "WARNING"
    }
    exit 0
}

# Repair mode
if ($Repair) {
    Write-Log "Starting repair..." "WARNING"
    if (Test-Path "$InstallPath\venv") {
        Remove-Item "$InstallPath\venv" -Recurse -Force
        Write-Log "  Cleared virtual environment" "SUCCESS"
    }
    # Continue with normal installation
}

# Check Python with version validation (with py.exe fallback)
Write-Log "Checking Python installation..."
$pythonVersion = $null
$pythonCmd = $null

# Try python first
try {
    $pythonOutput = python --version 2>&1
    $pythonCmd = "python"
} catch {
    # Try py.exe as fallback
    try {
        $pythonOutput = py -3 --version 2>&1
        $pythonCmd = "py -3"
    } catch {
        $pythonOutput = $null
    }
}

if ($pythonOutput -match "Python (\d+)\.(\d+)") {
    $major = [int]$matches[1]
    $minor = [int]$matches[2]
    if ($major -eq 3 -and $minor -ge 9) {
        $pythonVersion = "$major.$minor"
        Write-Log "  ✓ Python $pythonVersion found (using $pythonCmd)" "SUCCESS"
    } else {
        Write-Log "Python 3.9+ required (found $major.$minor)" "ERROR"
        exit 1
    }
} else {
    Write-Log "Python 3.9+ not found. Please install from python.org" "ERROR"
    Write-Log "Download: https://www.python.org/downloads/" "INFO"
    Read-Host "Press Enter to exit"
    exit 1
}

# Create directory structure
Write-Log "Creating directory structure..."
$directories = @(
    $InstallPath,
    "$InstallPath\config",
    "$InstallPath\reports", 
    "$InstallPath\storage",
    "$InstallPath\cache",
    "$InstallPath\logs",
    "$InstallPath\docpack",
    "$InstallPath\docpack\tables",
    "$InstallPath\docpack\pages",
    "$InstallPath\backup",
    "$InstallPath\forensics",
    "$InstallPath\modules"
)

foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Log "  Created: $dir" "SUCCESS"
    }
}

# Setup virtual environment
Write-Log "Setting up Python virtual environment..."
$venvPath = "$InstallPath\venv"
$venvPython = "$venvPath\Scripts\python.exe"
$venvPythonW = "$venvPath\Scripts\pythonw.exe"

if (!(Test-Path $venvPython)) {
    & $pythonCmd -m venv $venvPath 2>&1 | Out-Null
    if (!(Test-Path $venvPython)) {
        Write-Log "Failed to create virtual environment" "ERROR"
        exit 1
    }
}

# Install packages with progress and better error handling
Write-Log "Installing required packages..."
& $venvPython -m pip install --upgrade pip --quiet 2>&1 | Out-Null

$packages = @{
    "Core" = @("pandas>=2.0.0", "numpy>=1.24.0", "duckdb>=0.10.0", "Pillow>=10.0.0")
    "PDF Processing" = @("pdfplumber>=0.11.0", "pypdfium2>=4.20.0", "PyPDF2>=3.0.0")  
    "Data Export" = @("pyarrow>=15.0.0", "openpyxl>=3.1.0", "xlsxwriter>=3.1.0")
    "OCR (Optional)" = @("pytesseract")
}

foreach ($category in $packages.Keys) {
    Write-Log "  Installing $category packages..."
    foreach ($package in $packages[$category]) {
        try {
            $output = & $venvPython -m pip install $package 2>&1
            if ($LASTEXITCODE -ne 0) {
                throw "pip returned exit code $LASTEXITCODE"
            }
            Write-Log "    ✓ $package" "SUCCESS"
        } catch {
            if ($category -eq "OCR (Optional)") {
                Write-Log "    ⚠ $package skipped (optional)" "WARNING"
            } else {
                Write-Log "    ✗ Failed: $package" "ERROR"
                Write-Log "    Error: $_" "ERROR"
                exit 1
            }
        }
    }
}

# Copy Python modules from external files
Write-Log "Installing Python modules..."

# Define module files to copy
$moduleFiles = @{
    "catscale_delta_parser.py" = "$ModulesPath\catscale_delta_parser.py"
    "catscale_gui.pyw" = "$ModulesPath\catscale_gui.pyw"
}

# Check if modules exist in script directory, otherwise download
foreach ($moduleName in $moduleFiles.Keys) {
    $sourcePath = $moduleFiles[$moduleName]
    $destPath = "$InstallPath\$moduleName"
    
    if (Test-Path $sourcePath) {
        Copy-Item -Path $sourcePath -Destination $destPath -Force
        Write-Log "  ✓ Copied module: $moduleName" "SUCCESS"
    } else {
        # Download from GitHub or create minimal version
        Write-Log "  ⚠ Module not found: $moduleName - Creating minimal version" "WARNING"
        
        if ($moduleName -eq "catscale_delta_parser.py") {
            # Create minimal parser if not found
            $minimalParser = @'
#!/usr/bin/env python3
"""CAT Scale Delta Parser v7.3 - Minimal Installation"""
print("ERROR: Full parser module not found.")
print("Please download catscale_delta_parser.py from the repository")
print("and place it in the installation directory.")
exit(1)
'@
            Set-Content -Path $destPath -Value $minimalParser -Encoding UTF8
        }
    }
}

# Copy mapping files if they exist alongside installer
Write-Log "Checking for mapping files..."
$scriptDir = Split-Path -Parent $PSCommandPath
$mappingFiles = @(
    "WORK CODE.xlsx",
    "WORK_CODE.xlsx", 
    "workcode_map.xlsx",
    "SIGN_TYPE_CODES.csv",
    "MFG PARTS 2024.xlsx",
    "MFG Parts USAGE*.xlsx",
    "PURCHASED PARTS*.xlsx"
)

foreach ($pattern in $mappingFiles) {
    $files = Get-ChildItem -Path $scriptDir -Filter $pattern -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        $destPath = "$InstallPath\config\$($file.Name)"
        Copy-Item -Path $file.FullName -Destination $destPath -Force
        Write-Log "  ✓ Copied mapping: $($file.Name)" "SUCCESS"
    }
}

# Create batch launcher
$batchLauncher = @'
@echo off
setlocal
title CAT Scale Benchmark System v7.3

set VENV_PYTHON=%~dp0venv\Scripts\python.exe
set VENV_PYTHONW=%~dp0venv\Scripts\pythonw.exe
set PARSER_SCRIPT=%~dp0catscale_delta_parser.py
set GUI_SCRIPT=%~dp0catscale_gui.pyw

if not exist "%VENV_PYTHON%" (
    echo ERROR: Virtual environment not found
    echo Please run installer first
    pause
    exit /b 1
)

cls
echo ════════════════════════════════════════════════════════════════════════════════
echo                     CAT SCALE BENCHMARK SYSTEM v7.3
echo                           Bulletproof Edition
echo ════════════════════════════════════════════════════════════════════════════════
echo.

if "%~1"=="" (
    echo Starting GUI interface...
    if exist "%VENV_PYTHONW%" (
        start "" "%VENV_PYTHONW%" "%GUI_SCRIPT%"
    ) else (
        start "" "%VENV_PYTHON%" "%GUI_SCRIPT%"
    )
) else (
    echo Processing files...
    "%VENV_PYTHON%" "%PARSER_SCRIPT%" %*
    echo.
    echo ════════════════════════════════════════════════════════════════════════════════
    echo Process complete. Check reports folder for results.
    pause
)
'@

$runPath = "$InstallPath\RUN_CATSCALE.bat"
Set-Content -Path $runPath -Value $batchLauncher -Encoding ASCII
Write-Log "  ✓ Created batch launcher" "SUCCESS"

# Create configuration files
Write-Log "Creating configuration files..."

# Enhanced settings.json with all options
$settings = @{
    tolerance = 0.01
    enable_ocr = "auto"
    ocr_threshold_rows = 5
    docpack = $true
    strict_validation = $true
    cache_enabled = $true
    export_formats = @("csv", "jsonl", "txt")
    decimal_places = 3
    max_workers = 4
    backup_enabled = $true
    log_level = "INFO"
    use_trimmed_mean = $true
    trimmed_percent = 0.1
}

$settingsPath = "$InstallPath\config\settings.json"
$settings | ConvertTo-Json -Depth 10 | Set-Content -Path $settingsPath -Encoding UTF8
Write-Log "  ✓ Created settings.json" "SUCCESS"

# Create version.json
$versionInfo = @{
    app = "7.3.0"
    parser = "7.3.0"
    schema = "1.2.1"
    installed = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    python_cmd = $pythonCmd
    installer = "Clean Modular v7.3"
}

$versionPath = "$InstallPath\version.json"
$versionInfo | ConvertTo-Json | Set-Content -Path $versionPath -Encoding UTF8
Write-Log "  ✓ Created version.json" "SUCCESS"

# Create shortcuts
Write-Log "Creating shortcuts..."
$WshShell = New-Object -ComObject WScript.Shell

# Desktop shortcut
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\CAT Scale Benchmarker.lnk")
$Shortcut.TargetPath = "$InstallPath\RUN_CATSCALE.bat"
$Shortcut.WorkingDirectory = $InstallPath
$Shortcut.IconLocation = "shell32.dll,13"
$Shortcut.Description = "CAT Scale Benchmark System v7.3 - Professional Cost Analysis"
$Shortcut.Save()
Write-Log "  ✓ Desktop shortcut created" "SUCCESS"

# Start menu folder
$StartMenuPath = [Environment]::GetFolderPath("Programs")
$StartFolder = "$StartMenuPath\CAT Scale Benchmark"
if (!(Test-Path $StartFolder)) {
    New-Item -ItemType Directory -Path $StartFolder -Force | Out-Null
}

# Start menu shortcuts
$StartShortcut = $WshShell.CreateShortcut("$StartFolder\CAT Scale Benchmarker.lnk")
$StartShortcut.TargetPath = "$InstallPath\RUN_CATSCALE.bat"
$StartShortcut.WorkingDirectory = $InstallPath
$StartShortcut.Description = "Launch CAT Scale Benchmark System"
$StartShortcut.IconLocation = "shell32.dll,13"
$StartShortcut.Save()

# GUI shortcut with hidden window
$guiTarget = if (Test-Path $venvPythonW) { $venvPythonW } else { $venvPython }
$GuiShortcut = $WshShell.CreateShortcut("$StartFolder\CAT Scale GUI.lnk")
$GuiShortcut.TargetPath = "powershell.exe"
$GuiShortcut.Arguments = "-WindowStyle Hidden -Command `"& '$guiTarget' '$InstallPath\catscale_gui.pyw'`""
$GuiShortcut.WorkingDirectory = $InstallPath
$GuiShortcut.Description = "Launch CAT Scale GUI Interface"
$GuiShortcut.IconLocation = "shell32.dll,76"
$GuiShortcut.Save()

# Uninstall shortcut
$UninstallScriptPath = "$InstallPath\uninstall.ps1"
$uninstallContent = @"
param()
`$ErrorActionPreference = 'Stop'
if (Test-Path '$InstallPath') {
    Remove-Item '$InstallPath\*' -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item '$InstallPath' -Recurse -Force -ErrorAction SilentlyContinue
}
# Clean shortcuts
`$desktop = [Environment]::GetFolderPath('Desktop')
Remove-Item "`$desktop\CAT Scale Benchmarker.lnk" -Force -ErrorAction SilentlyContinue
`$start = [Environment]::GetFolderPath('Programs')
Remove-Item "`$start\CAT Scale Benchmark" -Recurse -Force -ErrorAction SilentlyContinue
`$sendto = "`$env:APPDATA\Microsoft\Windows\SendTo\CAT Scale Parser.bat"
Remove-Item `$sendto -Force -ErrorAction SilentlyContinue
Write-Host 'Uninstallation complete.'
Read-Host 'Press Enter to exit'
"@
Set-Content -Path $UninstallScriptPath -Value $uninstallContent -Encoding UTF8

$UninstallShortcut = $WshShell.CreateShortcut("$StartFolder\Uninstall.lnk")
$UninstallShortcut.TargetPath = "powershell.exe"
$UninstallShortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$UninstallScriptPath`""
$UninstallShortcut.WorkingDirectory = $InstallPath
$UninstallShortcut.Description = "Uninstall CAT Scale Benchmark System"
$UninstallShortcut.IconLocation = "shell32.dll,31"
$UninstallShortcut.Save()
Write-Log "  ✓ Start menu shortcuts created" "SUCCESS"

# SendTo context menu
$SendToPath = "$env:APPDATA\Microsoft\Windows\SendTo"
$SendToFile = "$SendToPath\CAT Scale Parser.bat"
$sendToContent = @"
@echo off
"$InstallPath\RUN_CATSCALE.bat" %*
"@
Set-Content -Path $SendToFile -Value $sendToContent -Encoding ASCII
Write-Log "  ✓ Send To menu entry created" "SUCCESS"

# Create README
$readme = @'
CAT SCALE BENCHMARK SYSTEM v7.3
Bulletproof Edition - Clean Modular Installation
════════════════════════════════════════════════════════════════════════════════

WHAT'S NEW IN v7.3 CLEAN
─────────────────────────
✓ Modular Design: Python modules separate from installer
✓ Smaller Installer: ~20KB vs 3MB+ monolithic file
✓ Easy Updates: Replace Python modules without reinstalling
✓ Better Debugging: Each component isolated
✓ GitHub Ready: Easy to version control

QUICK START
───────────
• Desktop: Click "CAT Scale Benchmarker" shortcut
• Explorer: Right-click PDFs → Send to → CAT Scale Parser
• Command: Drag PDFs onto RUN_CATSCALE.bat

KEY FEATURES
────────────
✓ Work Order Extraction - Captures from page headers
✓ Triple-Hash Caching - File + Content + Image validation
✓ Strict Pass/Fail - Reconciles to printed totals (±$0.01)
✓ Robust Statistics - Trimmed mean with edge case handling
✓ Professional GUI - Progress tracking and error recovery

OUTPUT FILES
────────────
reports/
  ├── benchmarks_*.txt - Executive summary
  ├── labor_benchmark_*.csv - Detailed labor analysis
  ├── work_orders_*.csv - Work order summaries
  ├── materials_*.csv - Material cost analysis
  └── receipts_*.csv - Processing receipts

TROUBLESHOOTING
───────────────
• Check forensics/ folder for error details
• Verify Python modules exist in installation directory
• Review logs/ folder for detailed diagnostics
• Run installer with -Repair flag if issues persist

VERSION INFO
────────────
Version: 7.3.0 (Clean Modular)
Parser: 7.3.0
Schema: 1.2.1
Company: Eagle Sign Company
'@

$readmePath = "$InstallPath\README.txt"
Set-Content -Path $readmePath -Value $readme -Encoding UTF8
Write-Log "  ✓ Created README" "SUCCESS"

# Installation summary
Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "           CAT SCALE v7.3 CLEAN INSTALLATION COMPLETE!" -ForegroundColor Green
Write-Host "                   Modular Bulletproof Edition" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "Installed to: $InstallPath" -ForegroundColor Cyan
Write-Host "Version: 7.3.0 (Clean Modular)" -ForegroundColor Cyan
Write-Host "Log file: $Global:LogFile" -ForegroundColor Gray
Write-Host ""
Write-Host "IMPROVEMENTS:" -ForegroundColor Yellow
Write-Host "  ✓ Modular architecture" -ForegroundColor White
Write-Host "  ✓ External Python modules" -ForegroundColor White
Write-Host "  ✓ Smaller installer size" -ForegroundColor White
Write-Host "  ✓ Easy maintenance" -ForegroundColor White
Write-Host ""
Write-Host "QUICK START:" -ForegroundColor Yellow
Write-Host "  1. Click 'CAT Scale Benchmarker' on desktop" -ForegroundColor White
Write-Host "  2. Select PDF files or folder" -ForegroundColor White
Write-Host "  3. Click 'Process Files'" -ForegroundColor White
Write-Host "  4. View results in reports folder" -ForegroundColor White
Write-Host ""

# Check for Python modules
$moduleCheck = @(
    "$InstallPath\catscale_delta_parser.py",
    "$InstallPath\catscale_gui.pyw"
)

$missingModules = @()
foreach ($module in $moduleCheck) {
    if (!(Test-Path $module)) {
        $missingModules += (Split-Path -Leaf $module)
    }
}

if ($missingModules.Count -gt 0) {
    Write-Host "WARNING: Missing Python modules:" -ForegroundColor Yellow
    foreach ($missing in $missingModules) {
        Write-Host "  - $missing" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Please download the missing modules and place them in:" -ForegroundColor Yellow
    Write-Host "  $InstallPath" -ForegroundColor White
    Write-Host ""
}

$mappingCount = @(Get-ChildItem -Path "$InstallPath\config\*" -Include "*.xlsx","*.csv" -ErrorAction SilentlyContinue).Count
if ($mappingCount -gt 0) {
    Write-Host "Mapping Files Found: $mappingCount files in config/" -ForegroundColor Green
}

$openFolder = Read-Host "Open installation folder? (Y/N)"
if ($openFolder -eq 'Y') {
    Start-Process explorer.exe $InstallPath
}


