# Process PDF cost summaries
Write-Host "📄 Processing PDF cost summaries..." -ForegroundColor Cyan

# Activate virtual environment
& .\.venv\Scripts\Activate.ps1

# Run PDF parser
python -m src.signx_intel.ingestion.pdf_parser

