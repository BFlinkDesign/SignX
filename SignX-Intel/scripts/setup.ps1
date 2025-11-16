# SignX-Intel Setup Script (Windows PowerShell)
# This script sets up the development environment

Write-Host "🚀 SignX-Intel Setup" -ForegroundColor Cyan
Write-Host "=" * 60

# Check Python version
Write-Host "`n📋 Checking Python version..." -ForegroundColor Yellow
$pythonVersion = py -3.12 --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "❌ Python 3.12 not found!" -ForegroundColor Red
    Write-Host "   Please install Python 3.12 from python.org" -ForegroundColor Yellow
    exit 1
}

# Create virtual environment
Write-Host "`n📦 Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "⚠️  Virtual environment already exists. Skipping..." -ForegroundColor Yellow
} else {
    py -3.12 -m venv .venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "`n🔧 Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "`n⬆️  Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install dependencies
Write-Host "`n📥 Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host "`n✅ Installation complete!" -ForegroundColor Green

# Check for .env file
Write-Host "`n🔐 Checking environment configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "✅ .env file exists" -ForegroundColor Green
} else {
    Write-Host "⚠️  .env file not found. Creating from template..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "✅ .env file created. Please edit it with your settings." -ForegroundColor Green
}

# Check Docker
Write-Host "`n🐳 Checking Docker..." -ForegroundColor Yellow
$dockerVersion = docker --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ $dockerVersion" -ForegroundColor Green
    
    Write-Host "`n🚀 Starting Docker services..." -ForegroundColor Yellow
    docker-compose up -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Docker services started" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Failed to start Docker services" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Docker not found. Please install Docker Desktop." -ForegroundColor Yellow
    Write-Host "   Download: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
}

# Create data directories
Write-Host "`n📁 Creating data directories..." -ForegroundColor Yellow
$directories = @("data/raw", "data/processed", "data/models", "migrations/versions")
foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "✅ Created $dir" -ForegroundColor Green
    }
}

Write-Host "`n" + ("=" * 60) -ForegroundColor Cyan
Write-Host "🎉 Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit .env file with your settings"
Write-Host "  2. Initialize database: alembic upgrade head"
Write-Host "  3. Start the API: uvicorn src.signx_intel.api.main:app --reload"
Write-Host "  4. Visit http://localhost:8000/api/v1/docs"
Write-Host ""
Write-Host "For more info, see README.md" -ForegroundColor Yellow

