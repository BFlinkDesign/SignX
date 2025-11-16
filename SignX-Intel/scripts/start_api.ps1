# Start SignX-Intel API Server
Write-Host "🚀 Starting SignX-Intel API..." -ForegroundColor Cyan

# Activate virtual environment
& .\.venv\Scripts\Activate.ps1

# Start API server
uvicorn src.signx_intel.api.main:app --host 127.0.0.1 --port 8000 --reload

