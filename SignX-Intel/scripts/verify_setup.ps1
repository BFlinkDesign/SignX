# Verify SignX-Intel Installation
Write-Host "SignX-Intel Setup Verification" -ForegroundColor Cyan
Write-Host "=" * 60

# Check Python
Write-Host "`nChecking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = py -3.12 --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK: $pythonVersion" -ForegroundColor Green
    }
} catch {
    Write-Host "ERROR: Python 3.12 not installed" -ForegroundColor Red
}

# Check virtual environment
Write-Host "`nChecking virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "OK: Virtual environment exists" -ForegroundColor Green
} else {
    Write-Host "ERROR: Virtual environment not found" -ForegroundColor Red
}

# Check .env file
Write-Host "`nChecking .env file..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "OK: .env file exists" -ForegroundColor Green
} else {
    Write-Host "ERROR: .env file not found" -ForegroundColor Red
}

# Check data directories
Write-Host "`nChecking data directories..." -ForegroundColor Yellow
$directories = @("data/raw", "data/processed", "data/models")
foreach ($dir in $directories) {
    if (Test-Path $dir) {
        Write-Host "OK: $dir" -ForegroundColor Green
    }
}

Write-Host "`nSetup verification complete!" -ForegroundColor Cyan
