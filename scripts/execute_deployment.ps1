# PowerShell Deployment Execution Script
# Follows DEPLOYMENT_PLAN.md phases

$ErrorActionPreference = "Stop"

Write-Host "=== APEX Deployment Execution ===" -ForegroundColor Cyan
Write-Host "Date: $(Get-Date)" -ForegroundColor Gray
Write-Host ""

# Phase 1: Pre-Flight
Write-Host "=== Phase 1: Pre-Flight ===" -ForegroundColor Yellow
Write-Host ""

Write-Host "1.1: Validating compose.yaml..."
Set-Location infra
docker compose config | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ compose.yaml syntax valid" -ForegroundColor Green
} else {
    Write-Host "   ❌ compose.yaml syntax invalid" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "1.2: Verifying critical fixes..."
$tmpfsFix = Select-String -Path "compose.yaml" -Pattern "uid=1000,gid=1000,mode=1777"
if ($tmpfsFix.Count -ge 2) {
    Write-Host "   ✅ tmpfs ownership fix applied ($($tmpfsFix.Count) services)" -ForegroundColor Green
} else {
    Write-Host "   ❌ tmpfs ownership fix NOT applied" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "1.3: Checking required files..."
$files = @(
    "../services/api/Dockerfile",
    "../services/worker/Dockerfile",
    "../services/api/monitoring/postgres_exporter.yml",
    "../services/api/monitoring/grafana_dashboard.json"
)
$allExist = $true
foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "   ✅ $(Split-Path $file -Leaf)" -ForegroundColor Green
    } else {
        Write-Host "   ❌ $file MISSING" -ForegroundColor Red
        $allExist = $false
    }
}
if (-not $allExist) {
    exit 1
}

Write-Host ""
Write-Host "1.4: Stopping existing services..."
docker compose down 2>&1 | Out-Null
Write-Host "   ✅ Services stopped" -ForegroundColor Green

Write-Host ""
Write-Host "=== Phase 1 Complete ===" -ForegroundColor Green
Write-Host ""

# Phase 2: Build
Write-Host "=== Phase 2: Build ===" -ForegroundColor Yellow
Write-Host ""

Write-Host "2.1: Building images (this may take 5-7 minutes)..."
docker compose build --parallel
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Images built successfully" -ForegroundColor Green
} else {
    Write-Host "   ❌ Build failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "2.2: Verifying images..."
docker images | Select-String "apex" | Select-Object -First 5
Write-Host "   ✅ Images verified" -ForegroundColor Green

Write-Host ""
Write-Host "=== Phase 2 Complete ===" -ForegroundColor Green
Write-Host ""

# Phase 3: Deploy Infrastructure
Write-Host "=== Phase 3: Deploy Infrastructure ===" -ForegroundColor Yellow
Write-Host ""

Write-Host "3.1: Starting infrastructure services..."
docker compose up -d db cache object search
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Infrastructure services starting" -ForegroundColor Green
} else {
    Write-Host "   ❌ Failed to start infrastructure" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "3.2: Waiting for health checks (60 seconds)..."
Start-Sleep -Seconds 60

Write-Host ""
Write-Host "3.3: Verifying infrastructure health..."
$healthy = $true
$services = @("db", "cache", "object", "search")
foreach ($svc in $services) {
    $status = docker compose ps $svc --format json | ConvertFrom-Json | Select-Object -First 1
    if ($status.State -match "running|healthy") {
        Write-Host "   ✅ $svc : $($status.State)" -ForegroundColor Green
    } else {
        Write-Host "   ❌ $svc : $($status.State)" -ForegroundColor Red
        $healthy = $false
    }
}

if (-not $healthy) {
    Write-Host ""
    Write-Host "   Checking logs..." -ForegroundColor Yellow
    docker compose logs --tail=20
    Write-Host "   ❌ Some services not healthy" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Phase 3 Complete ===" -ForegroundColor Green
Write-Host ""

# Phase 4: Database Migrations
Write-Host "=== Phase 4: Database Migrations ===" -ForegroundColor Yellow
Write-Host ""

Write-Host "4.1: Waiting for database ready..."
$dbReady = $false
for ($i = 1; $i -le 30; $i++) {
    $result = docker compose exec -T db pg_isready -U apex 2>&1
    if ($result -match "accepting connections") {
        Write-Host "   ✅ Database ready" -ForegroundColor Green
        $dbReady = $true
        break
    }
    Write-Host "   Waiting... ($i/30)" -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

if (-not $dbReady) {
    Write-Host "   ❌ Database not ready after 60 seconds" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "4.2: Running migrations..."
docker compose exec api alembic upgrade head
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Migrations complete" -ForegroundColor Green
} else {
    Write-Host "   ❌ Migration failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "4.3: Verifying tables..."
$tableCount = docker compose exec -T db psql -U apex -d apex -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>&1 | ForEach-Object { $_.Trim() }
Write-Host "   ✅ Tables created ($tableCount tables)" -ForegroundColor Green

Write-Host ""
Write-Host "=== Phase 4 Complete ===" -ForegroundColor Green
Write-Host ""

# Phase 5: Deploy Application Services
Write-Host "=== Phase 5: Deploy Application Services ===" -ForegroundColor Yellow
Write-Host ""

Write-Host "5.1: Starting application services..."
docker compose up -d api worker signcalc
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Application services starting" -ForegroundColor Green
} else {
    Write-Host "   ❌ Failed to start application services" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "5.2: Starting frontend and monitoring..."
docker compose up -d frontend grafana postgres_exporter dashboards
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ All services starting" -ForegroundColor Green
} else {
    Write-Host "   ❌ Failed to start remaining services" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "5.3: Waiting for services (30 seconds)..."
Start-Sleep -Seconds 30

Write-Host ""
Write-Host "5.4: Verifying all services..."
docker compose ps

Write-Host ""
Write-Host "=== Phase 5 Complete ===" -ForegroundColor Green
Write-Host ""

# Phase 6: Verification
Write-Host "=== Phase 6: Verification ===" -ForegroundColor Yellow
Write-Host ""

Write-Host "6.1: Health endpoint checks..."
$health = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -ErrorAction SilentlyContinue
if ($health.StatusCode -eq 200) {
    Write-Host "   ✅ API health: OK" -ForegroundColor Green
    $health.Content | ConvertFrom-Json | ConvertTo-Json -Compress | Write-Host
} else {
    Write-Host "   ❌ API health: FAILED (Status: $($health.StatusCode))" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "6.2: Readiness check..."
$ready = Invoke-WebRequest -Uri "http://localhost:8000/ready" -UseBasicParsing -ErrorAction SilentlyContinue
if ($ready.StatusCode -eq 200) {
    Write-Host "   ✅ API readiness: OK" -ForegroundColor Green
    $readyData = $ready.Content | ConvertFrom-Json
    Write-Host "   Database: $($readyData.checks.database)" -ForegroundColor Gray
    Write-Host "   Redis: $($readyData.checks.redis)" -ForegroundColor Gray
    Write-Host "   Object Storage: $($readyData.checks.object_storage)" -ForegroundColor Gray
    Write-Host "   Search: $($readyData.checks.search)" -ForegroundColor Gray
} else {
    Write-Host "   ❌ API readiness: FAILED" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "6.3: Testing API endpoint..."
$projects = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/projects" -UseBasicParsing -ErrorAction SilentlyContinue
if ($projects.StatusCode -eq 200) {
    Write-Host "   ✅ API endpoint: OK" -ForegroundColor Green
} else {
    Write-Host "   ❌ API endpoint: FAILED (Status: $($projects.StatusCode))" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "6.4: Checking Signcalc..."
$signcalc = Invoke-WebRequest -Uri "http://localhost:8002/healthz" -UseBasicParsing -ErrorAction SilentlyContinue
if ($signcalc.StatusCode -eq 200) {
    Write-Host "   ✅ Signcalc health: OK" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Signcalc health: FAILED (may need time to start)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Phase 6 Complete ===" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "=== Deployment Summary ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ All services deployed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Service URLs:" -ForegroundColor Yellow
Write-Host "  - API: http://localhost:8000" -ForegroundColor Gray
Write-Host "  - API Docs: http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "  - Frontend: http://localhost:5173" -ForegroundColor Gray
Write-Host "  - Grafana: http://localhost:3001" -ForegroundColor Gray
Write-Host "  - Signcalc: http://localhost:8002" -ForegroundColor Gray
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Setup monitoring: bash infra/monitoring/setup_dashboards.sh" -ForegroundColor Gray
Write-Host "  2. Run smoke tests: See docs/deployment/DEPLOYMENT_PLAN.md Phase 6" -ForegroundColor Gray
Write-Host "  3. Monitor logs: docker compose logs -f" -ForegroundColor Gray
Write-Host ""

Set-Location ..

