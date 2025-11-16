# Run tests for SignX-Intel
Write-Host "🧪 Running tests..." -ForegroundColor Cyan

# Activate virtual environment
& .\.venv\Scripts\Activate.ps1

# Run pytest
python -m pytest -v --cov=src/signx_intel --cov-report=term-missing

