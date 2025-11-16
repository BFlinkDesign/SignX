# Pre-Deployment Validation Script (PowerShell)
# Runs before deployment to verify readiness

$ErrorActionPreference = "Stop"

Write-Host "=== Pre-Deployment Validation ===" -ForegroundColor Cyan
Write-Host ""

# Check Docker Compose services (if running)
Write-Host "1. Checking Docker Compose services..."
$composeStatus = docker compose -f infra/compose.yaml ps 2>$null
if ($composeStatus -match "healthy") {
    Write-Host "   ✅ Services running and healthy" -ForegroundColor Green
    $existingServices = $true
} else {
    Write-Host "   ℹ️  No existing services (fresh deployment)" -ForegroundColor Yellow
    $existingServices = $false
}

# Check database (if accessible)
Write-Host ""
Write-Host "2. Checking database..."
if ($existingServices) {
    $dbContainer = docker compose -f infra/compose.yaml ps db -q 2>$null | Select-Object -First 1
    if ($dbContainer) {
        $tableCount = docker exec $dbContainer psql -U apex -d apex -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>$null
        if ($tableCount -and $tableCount.Trim() -ne "0") {
            Write-Host "   ✅ Database accessible and has tables" -ForegroundColor Green
            
            # Check pole_sections table specifically (if exists)
            $poleCount = docker exec $dbContainer psql -U apex -d apex -t -c "SELECT COUNT(*) FROM pole_sections;" 2>$null | ForEach-Object { $_.Trim() }
            if ($poleCount -and $poleCount -ne "0") {
                Write-Host "   ✅ pole_sections table has data ($poleCount rows)" -ForegroundColor Green
            } else {
                Write-Host "   ⚠️  pole_sections table empty or doesn't exist (may need seed data)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "   ⚠️  Database accessible but no tables (migrations needed)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ℹ️  Database container not running (will start during deployment)" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ℹ️  Database not running (will start during deployment)" -ForegroundColor Yellow
}

# Run unit tests
Write-Host ""
Write-Host "3. Running unit tests..."
if (Test-Path "tests/unit" -PathType Container) {
    $testFiles = Get-ChildItem -Path "tests/unit" -Filter "*.py" -Recurse -ErrorAction SilentlyContinue
    if ($testFiles) {
        if (Get-Command pytest -ErrorAction SilentlyContinue) {
            try {
                pytest tests/unit/ --maxfail=5 -q 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "   ✅ Unit tests passed" -ForegroundColor Green
                } else {
                    Write-Host "   ❌ Unit tests failed" -ForegroundColor Red
                    Write-Host "   Running with verbose output..."
                    pytest tests/unit/ --maxfail=5 -v
                    exit 1
                }
            } catch {
                Write-Host "   ❌ Unit tests failed with error" -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host "   ⚠️  pytest not available, skipping tests" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ⚠️  No unit tests found, skipping" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ⚠️  No unit tests found, skipping" -ForegroundColor Yellow
}

# Check Docker daemon
Write-Host ""
Write-Host "4. Checking Docker daemon..."
try {
    docker ps | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Docker daemon running" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Docker daemon not running" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "   ❌ Docker daemon not accessible" -ForegroundColor Red
    exit 1
}

# Check ports available
Write-Host ""
Write-Host "5. Checking port availability..."
$ports = @(8000, 5173, 8002, 5432, 6379, 9200, 9000, 9001, 5601, 3001, 9187)
$portsInUse = 0

foreach ($port in $ports) {
    $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connection) {
        Write-Host "   ⚠️  Port $port in use" -ForegroundColor Yellow
        $portsInUse++
    }
}

if ($portsInUse -gt 0) {
    Write-Host "   ⚠️  $portsInUse ports in use (may need to stop existing services)" -ForegroundColor Yellow
} else {
    Write-Host "   ✅ All ports available" -ForegroundColor Green
}

# Validate configuration
Write-Host ""
Write-Host "6. Validating compose.yaml..."
Push-Location infra
try {
    docker compose config | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ compose.yaml syntax valid" -ForegroundColor Green
    } else {
        Write-Host "   ❌ compose.yaml syntax invalid" -ForegroundColor Red
        docker compose config
        Pop-Location
        exit 1
    }
} catch {
    Write-Host "   ❌ compose.yaml validation failed" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

# Check critical fixes
Write-Host ""
Write-Host "7. Verifying critical fixes..."
$composeContent = Get-Content infra/compose.yaml -Raw
if ($composeContent -match "uid=1000,gid=1000,mode=1777") {
    Write-Host "   ✅ tmpfs ownership fix applied" -ForegroundColor Green
} else {
    Write-Host "   ❌ tmpfs ownership fix NOT applied" -ForegroundColor Red
    exit 1
}

# Summary
Write-Host ""
Write-Host "=== Pre-Deployment Validation Summary ===" -ForegroundColor Cyan
Write-Host "✅ Pre-deployment checks PASSED" -ForegroundColor Green
Write-Host ""
Write-Host "Ready for deployment!" -ForegroundColor Green
exit 0

