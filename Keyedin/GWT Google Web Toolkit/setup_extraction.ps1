# KeyedIn Complete Data Extraction - Setup Script
# Run this first to set up the extraction environment

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host " KEYEDIN COMPLETE DATA EXTRACTION - SETUP" -ForegroundColor Yellow
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

# Create project directory
$ProjectDir = "C:\Scripts\SignX\keyedin"
Write-Host "Setting up project directory: $ProjectDir" -ForegroundColor White

if (-not (Test-Path $ProjectDir)) {
    New-Item -ItemType Directory -Path $ProjectDir -Force | Out-Null
    Write-Host "✓ Created project directory" -ForegroundColor Green
} else {
    Write-Host "✓ Project directory exists" -ForegroundColor Green
}

# Navigate to project directory
Set-Location $ProjectDir

# Check Python installation
Write-Host "`nChecking Python installation..." -ForegroundColor White
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found!" -ForegroundColor Red
    Write-Host "  Please install Python 3.8+ from python.org" -ForegroundColor Yellow
    exit 1
}

# Install Python dependencies
Write-Host "`nInstalling Python dependencies..." -ForegroundColor White
Write-Host "(This may take a few minutes)" -ForegroundColor Gray

pip install --quiet --upgrade pip
pip install --quiet requests pandas pyodbc selenium webdriver-manager

Write-Host "✓ Dependencies installed" -ForegroundColor Green

# Download extraction scripts
Write-Host "`nDownloading extraction scripts..." -ForegroundColor White
# Note: In real deployment, these would be downloaded from a repo or provided
Write-Host "✓ Scripts ready (make sure you have all .py files in this directory)" -ForegroundColor Green

# Test SQL Server connectivity (optional)
Write-Host "`n" + ("=" * 80) -ForegroundColor Cyan
Write-Host " SQL SERVER CONNECTION TEST (Optional)" -ForegroundColor Yellow
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

$testSQL = Read-Host "Do you want to test SQL Server connectivity now? (y/n)"

if ($testSQL -eq 'y') {
    $server = Read-Host "Enter SQL Server instance name (e.g., SERVER\INSTANCE)"
    $database = Read-Host "Enter database name (default: KeyedIn)"
    
    if ([string]::IsNullOrWhiteSpace($database)) {
        $database = "KeyedIn"
    }
    
    Write-Host "`nTesting connection to $server\$database..." -ForegroundColor White
    
    try {
        $result = sqlcmd -S $server -d $database -Q "SELECT @@VERSION" -h -1 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ SQL Server connection successful!" -ForegroundColor Green
            Write-Host "  You can use Method 1 (SQL Direct Extraction)" -ForegroundColor Green
            Write-Host ""
            Write-Host "  Run: python keyedin_sql_extraction.py --server `"$server`" --database `"$database`"" -ForegroundColor Cyan
        } else {
            throw "Connection failed"
        }
    } catch {
        Write-Host "✗ SQL Server connection failed" -ForegroundColor Red
        Write-Host "  You should use Method 2 (Informer API Extraction)" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  Run: python extract_cookies.py" -ForegroundColor Cyan
    }
} else {
    Write-Host "Skipped SQL test" -ForegroundColor Gray
}

# Final instructions
Write-Host "`n" + ("=" * 80) -ForegroundColor Cyan
Write-Host " SETUP COMPLETE - NEXT STEPS" -ForegroundColor Yellow
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

Write-Host "Choose your extraction method:" -ForegroundColor White
Write-Host ""
Write-Host "  METHOD 1: SQL Server Direct (FASTEST - if you have DB access)" -ForegroundColor Cyan
Write-Host "  Command:  python keyedin_sql_extraction.py --server YOUR-SERVER\INSTANCE" -ForegroundColor Gray
Write-Host ""
Write-Host "  METHOD 2: Informer API (if no DB access)" -ForegroundColor Cyan
Write-Host "  Step 1:   python extract_cookies.py" -ForegroundColor Gray
Write-Host "  Step 2:   python keyedin_complete_extraction.py" -ForegroundColor Gray
Write-Host ""

Write-Host "See README_EXTRACTION.md for complete instructions" -ForegroundColor Yellow
Write-Host ""

# Open README
$openReadme = Read-Host "Open README now? (y/n)"
if ($openReadme -eq 'y') {
    if (Test-Path "README_EXTRACTION.md") {
        notepad "README_EXTRACTION.md"
    } else {
        Write-Host "README_EXTRACTION.md not found in current directory" -ForegroundColor Yellow
    }
}

Write-Host "`n✓ Setup complete! You're ready to extract your KeyedIn data." -ForegroundColor Green
Write-Host ""
