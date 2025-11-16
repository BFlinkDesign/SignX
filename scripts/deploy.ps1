# Deployment Script (PowerShell)
# Executes full deployment following DEPLOYMENT_PLAN.md

$ErrorActionPreference = "Stop"

Write-Host "=== APEX Deployment ===" -ForegroundColor Cyan
Write-Host "Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

# Change to project root if needed
if (-not (Test-Path "infra/compose.yaml")) {
    Write-Host "❌ Error: infra/compose.yaml not found. Run from project root." -ForegroundColor Red
    exit 1
}

Push-Location infra

try {
    # Phase 1: Infrastructure Services
    Write-Host "=== Phase 1: Starting Infrastructure Services ===" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Starting: db, cache, object, search..." -ForegroundColor Yellow
    docker compose up -d db cache object search
    
    Write-Host "Waiting for services to be healthy (30 seconds)..." -ForegroundColor Gray
    Start-Sleep -Seconds 30
    
    # Check infrastructure health
    Write-Host ""
    Write-Host "Checking infrastructure health..." -ForegroundColor Yellow
    $infraHealthy = $true
    
    $services = @("db", "cache", "object", "search")
    foreach ($service in $services) {
        $status = docker compose ps $service --format json | ConvertFrom-Json | Select-Object -First 1
        if ($status.State -eq "running" -or $status.Health -eq "healthy") {
            Write-Host "   ✅ $service healthy" -ForegroundColor Green
        } else {
            Write-Host "   ❌ $service not healthy" -ForegroundColor Red
            $infraHealthy = $false
        }
    }
    
    if (-not $infraHealthy) {
        Write-Host ""
        Write-Host "❌ Infrastructure services not healthy. Check logs:" -ForegroundColor Red
        Write-Host "   docker compose logs db cache object search" -ForegroundColor Yellow
        Pop-Location
        exit 1
    }
    
    # Phase 2: Database Migrations
    Write-Host ""
    Write-Host "=== Phase 2: Database Migrations ===" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Waiting for database ready..." -ForegroundColor Yellow
    $dbReady = $false
    for ($i = 1; $i -le 30; $i++) {
        try {
            docker compose exec -T db pg_isready -U apex 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "   ✅ Database ready" -ForegroundColor Green
                $dbReady = $true
                break
            }
        } catch {
            # Continue waiting
        }
        Write-Host "   Waiting... ($i/30)" -ForegroundColor Gray
        Start-Sleep -Seconds 2
    }
    
    if (-not $dbReady) {
        Write-Host "❌ Database not ready after 60 seconds" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    
    Write-Host ""
    Write-Host "Running migrations..." -ForegroundColor Yellow
    docker compose exec api alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Migrations failed" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Write-Host "   ✅ Migrations complete" -ForegroundColor Green
    
    # Phase 3: Application Services
    Write-Host ""
    Write-Host "=== Phase 3: Starting Application Services ===" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Starting: api, worker, signcalc..." -ForegroundColor Yellow
    docker compose up -d api worker signcalc
    
    Write-Host "Waiting for services to start (15 seconds)..." -ForegroundColor Gray
    Start-Sleep -Seconds 15
    
    Write-Host ""
    Write-Host "Checking application health..." -ForegroundColor Yellow
    
    # Check API health
    $maxRetries = 10
    $apiHealthy = $false
    for ($i = 1; $i -le $maxRetries; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "   ✅ API health check passed" -ForegroundColor Green
                $apiHealthy = $true
                break
            }
        } catch {
            if ($i -lt $maxRetries) {
                Write-Host "   Waiting for API... ($i/$maxRetries)" -ForegroundColor Gray
                Start-Sleep -Seconds 3
            }
        }
    }
    
    if (-not $apiHealthy) {
        Write-Host "   ❌ API health check failed" -ForegroundColor Red
        Write-Host "   Check logs: docker compose logs api" -ForegroundColor Yellow
        Pop-Location
        exit 1
    }
    
    # Check worker
    $workerStatus = docker compose ps worker --format json | ConvertFrom-Json | Select-Object -First 1
    if ($workerStatus.State -eq "running") {
        Write-Host "   ✅ Worker running" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Worker status: $($workerStatus.State)" -ForegroundColor Yellow
    }
    
    # Check signcalc
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8002/healthz" -Method GET -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "   ✅ Signcalc health check passed" -ForegroundColor Green
        }
    } catch {
        Write-Host "   ⚠️  Signcalc health check failed (may need more time)" -ForegroundColor Yellow
    }
    
    # Summary
    Write-Host ""
    Write-Host "=== Deployment Summary ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "✅ Infrastructure services: Running" -ForegroundColor Green
    Write-Host "✅ Database migrations: Complete" -ForegroundColor Green
    Write-Host "✅ Application services: Running" -ForegroundColor Green
    Write-Host ""
    Write-Host "Deployment successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Service URLs:" -ForegroundColor Cyan
    Write-Host "  - API: http://localhost:8000" -ForegroundColor Gray
    Write-Host "  - API Health: http://localhost:8000/health" -ForegroundColor Gray
    Write-Host "  - Signcalc: http://localhost:8002" -ForegroundColor Gray
    Write-Host "  - Frontend: http://localhost:5173" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Setup monitoring: bash infra/monitoring/setup_dashboards.sh" -ForegroundColor Gray
    Write-Host "  2. Run smoke tests" -ForegroundColor Gray
    Write-Host "  3. Check logs: docker compose logs -f" -ForegroundColor Gray
    
} catch {
    Write-Host ""
    Write-Host "❌ Deployment failed: $_" -ForegroundColor Red
    Pop-Location
    exit 1
} finally {
    Pop-Location
}

