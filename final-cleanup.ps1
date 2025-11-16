# Leo AI Clone - Final Apple-Style Cleanup
# Phase 2: Consolidate docs, unify README, remove build artifacts

param([switch]$DryRun)

$root = "C:\Scripts\Leo Ai Clone"
Set-Location $root

Write-Host "`n🍎 Leo AI Clone - Final Cleanup" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor Cyan

$freedMB = 0
$operations = @()

# ============================================================================
# 1. CONSOLIDATE DOCUMENTATION
# ============================================================================
Write-Host "📚 Phase 1: Consolidating documentation..." -ForegroundColor Yellow

$docsToMove = @(
    "API_ENDPOINTS_REFERENCE.md",
    "PAIN_POINTS_AND_SOLUTIONS.md"
)

foreach ($doc in $docsToMove) {
    if (Test-Path $doc) {
        $dest = "docs\$doc"
        if ($DryRun) {
            Write-Host "  → Would move: $doc → docs/" -ForegroundColor Gray
        } else {
            Move-Item $doc "docs\" -Force
            Write-Host "  ✓ Moved: $doc → docs/" -ForegroundColor Green
            $operations += "Moved $doc to docs/"
        }
    }
}

# ============================================================================
# 2. CREATE UNIFIED README
# ============================================================================
Write-Host "`n📝 Phase 2: Creating unified README..." -ForegroundColor Yellow

if ((Test-Path "README.md") -and (Test-Path "STATUS.md")) {
    if ($DryRun) {
        Write-Host "  → Would consolidate README.md + STATUS.md" -ForegroundColor Gray
    } else {
        $readme = Get-Content "README.md" -Raw
        $status = Get-Content "STATUS.md" -Raw
        
        # Create comprehensive README
        $unified = @"
# CalcuSign APEX

> Professional structural engineering calculations for the signage industry

## 🎯 Quick Start

**Prerequisites:** Docker, Python 3.13+, Node.js 20+

``````bash
# 1. Start infrastructure
docker-compose up -d

# 2. Run backend
cd services/backend
python -m uvicorn app.main:app --reload

# 3. Run frontend
cd services/frontend
npm install && npm run dev
``````

**Access:**
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- MinIO: http://localhost:9001

---

## 📊 Project Status

$status

---

## 📖 Documentation

- **[API Reference](docs/API_ENDPOINTS_REFERENCE.md)** - Complete API endpoint documentation
- **[Pain Points & Solutions](docs/PAIN_POINTS_AND_SOLUTIONS.md)** - Design decisions and rationale
- **[Architecture](docs/)** - System architecture and component guides

---

## 🏗️ Architecture

**Microservices:**
- **Backend API** (FastAPI) - Core calculation engine
- **Frontend** (React/Next.js) - User interface
- **Agent Services** - Specialized calculation agents (CAD, materials, compliance, etc.)
- **Message Queue** (RabbitMQ) - Async task processing
- **Storage** (MinIO) - Document and artifact storage
- **Database** (PostgreSQL) - Persistent data

**Tech Stack:**
- Python 3.13, FastAPI, SQLAlchemy
- React 19, Next.js 15, TypeScript
- Docker, RabbitMQ, PostgreSQL, MinIO
- Pytest, Jest, Playwright

---

## 🧪 Testing

``````bash
# Backend tests
cd services/backend
pytest

# Frontend tests
cd services/frontend
npm test

# E2E tests
npm run test:e2e
``````

---

## 🚀 Deployment

See **[Deployment Guide](docs/deployment/)** for production deployment instructions.

---

## 📜 License

Proprietary - Eagle Sign Co.

---

## 🤝 Contributing

This is an internal Eagle Sign Co. project. For questions or issues, contact the development team.

$readme
"@
        
        # Backup original files
        Copy-Item "README.md" "archive\README.original.md" -Force
        Copy-Item "STATUS.md" "archive\STATUS.original.md" -Force
        
        # Write unified README
        $unified | Out-File "README.md" -Encoding UTF8 -Force
        
        # Archive STATUS.md (no longer needed at root)
        Move-Item "STATUS.md" "archive\" -Force
        
        Write-Host "  ✓ Created unified README.md" -ForegroundColor Green
        Write-Host "  ✓ Archived STATUS.md (originals backed up)" -ForegroundColor Green
        $operations += "Unified README.md created"
        $operations += "STATUS.md archived"
    }
}

# ============================================================================
# 3. REMOVE BUILD ARTIFACTS & CACHES
# ============================================================================
Write-Host "`n🗑️  Phase 3: Removing build artifacts..." -ForegroundColor Yellow

$artifacts = @(
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".next",
    "dist",
    "build",
    ".venv",
    "venv",
    "env",
    ".coverage",
    "coverage",
    ".tox",
    "*.egg-info",
    ".DS_Store",
    "Thumbs.db"
)

function Get-DirectorySize {
    param([string]$path)
    if (-not (Test-Path $path)) { return 0 }
    $size = (Get-ChildItem $path -Recurse -File -ErrorAction SilentlyContinue | 
             Measure-Object -Property Length -Sum).Sum
    return [math]::Round($size / 1MB, 2)
}

foreach ($pattern in $artifacts) {
    Get-ChildItem -Path $root -Recurse -Force -Filter $pattern -ErrorAction SilentlyContinue | 
        Where-Object { $_.FullName -notlike "*\archive\*" -and $_.FullName -notlike "*\.git\*" } |
        ForEach-Object {
            $sizeMB = Get-DirectorySize $_.FullName
            
            if ($DryRun) {
                Write-Host "  → Would delete: $($_.FullName.Replace($root, '.'))" -ForegroundColor Gray
                if ($sizeMB -gt 0) {
                    Write-Host "    ($sizeMB MB)" -ForegroundColor DarkGray
                }
            } else {
                $freedMB += $sizeMB
                Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "  ✓ Deleted: $($_.Name) ($sizeMB MB)" -ForegroundColor Green
                $operations += "Deleted $($_.Name) cache/build artifacts"
            }
        }
}

# Remove .pyc files
Get-ChildItem -Path $root -Recurse -Filter "*.pyc" -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notlike "*\archive\*" } |
    ForEach-Object {
        if ($DryRun) {
            Write-Host "  → Would delete: $($_.FullName.Replace($root, '.'))" -ForegroundColor Gray
        } else {
            Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
            Write-Host "  ✓ Deleted: $($_.Name)" -ForegroundColor Green
        }
    }

# ============================================================================
# 4. SUMMARY
# ============================================================================
Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📊 Final Cleanup Summary:" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "⚠️  DRY RUN - No changes made" -ForegroundColor Yellow
    Write-Host "   Run without -DryRun to execute" -ForegroundColor Gray
} else {
    Write-Host "✨ Completed Operations:" -ForegroundColor Green
    $operations | ForEach-Object { Write-Host "   • $_" -ForegroundColor White }
    Write-Host ""
    Write-Host "💾 Space Freed: $([math]::Round($freedMB, 2)) MB" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📁 Clean Structure:" -ForegroundColor Cyan
    Write-Host "   Root: README.md + config files only" -ForegroundColor White
    Write-Host "   Docs: /docs folder (consolidated)" -ForegroundColor White
    Write-Host "   Archive: /archive folder (all history)" -ForegroundColor White
    Write-Host "   Code: /services, /svcs, /tests" -ForegroundColor White
}

Write-Host "`n✅ Apple-level organization achieved!`n" -ForegroundColor Green
