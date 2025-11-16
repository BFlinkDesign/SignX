# CalcuSign Stack Validation Script (PowerShell)
# Validates all services are healthy and responsive

Write-Host "🔍 CalcuSign Stack Validation" -ForegroundColor Cyan
Write-Host "=============================="
Write-Host ""

$FAILED = 0

# Function to check service health
function Test-Service {
    param([string]$Name, [string]$Url, [int]$TimeoutSeconds = 5)
    
    try {
        Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec $TimeoutSeconds -UseBasicParsing -ErrorAction Stop | Out-Null
        Write-Host "✅ $Name" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "❌ $Name - FAILED" -ForegroundColor Red
        $script:FAILED++
        return $false
    }
}

# Check compose stack status
Write-Host "📊 Docker Compose Status:" -ForegroundColor Cyan
Write-Host "--------------------------"
docker-compose -f infra/compose.yaml ps
Write-Host ""

# Check PostgreSQL
Write-Host "🔍 Checking PostgreSQL (port 5432)..." -ForegroundColor Yellow
$tcpPort = Test-NetConnection -ComputerName localhost -Port 5432 -WarningAction SilentlyContinue
if ($tcpPort.TcpTestSucceeded) {
    Write-Host "✅ PostgreSQL is accepting connections" -ForegroundColor Green
} else {
    Write-Host "❌ PostgreSQL not reachable" -ForegroundColor Red
    $FAILED++
}

# Check Redis
Write-Host "🔍 Checking Redis (port 6379)..." -ForegroundColor Yellow
Test-Service -Name "Redis" -Url "http://localhost:6379" | Out-Null

# Check OpenSearch
Write-Host "🔍 Checking OpenSearch (port 9200)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:9200/_cluster/health" -Method Get -TimeoutSec 5
    Write-Host "✅ OpenSearch healthy" -ForegroundColor Green
    Write-Host "   Status: $($response.status)" -ForegroundColor Yellow
} catch {
    Write-Host "❌ OpenSearch not reachable" -ForegroundColor Red
    $FAILED++
}

# Check MinIO
Write-Host "🔍 Checking MinIO (port 9000)..." -ForegroundColor Yellow
Test-Service -Name "MinIO" -Url "http://localhost:9000/minio/health/live" | Out-Null

# Check API
Write-Host "🔍 Checking API (port 8000)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 5
    Write-Host "✅ API healthy" -ForegroundColor Green
    if ($response.result.status -eq "ok") {
        Write-Host "   API response: OK" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ API not reachable" -ForegroundColor Red
    $FAILED++
}

# Check Worker (skip for now, requires exec)
Write-Host "🔍 Checking Worker health..." -ForegroundColor Yellow
Write-Host "⚠️  Worker health check skipped (requires docker exec)" -ForegroundColor Yellow

# Check Postgres Exporter
Write-Host "🔍 Checking Postgres Exporter (port 9187)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9187/metrics" -Method Get -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Postgres Exporter healthy" -ForegroundColor Green
    $metrics = ($response.Content -split "`n" | Select-String "^pg_" | Measure-Object).Count
    Write-Host "   Metrics available: $metrics" -ForegroundColor Yellow
} catch {
    Write-Host "❌ Postgres Exporter not reachable" -ForegroundColor Red
    $FAILED++
}

# Check Grafana
Write-Host "🔍 Checking Grafana (port 3001)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:3001/api/health" -Method Get -TimeoutSec 5
    Write-Host "✅ Grafana healthy" -ForegroundColor Green
    Write-Host "   Grafana dashboard: http://localhost:3001" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Grafana not reachable" -ForegroundColor Red
    $FAILED++
}

# Check OpenSearch Dashboards
Write-Host "🔍 Checking OpenSearch Dashboards (port 5601)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:5601/api/status" -Method Get -TimeoutSec 5
    Write-Host "✅ OpenSearch Dashboards healthy" -ForegroundColor Green
    Write-Host "   OpenSearch UI: http://localhost:5601" -ForegroundColor Cyan
} catch {
    Write-Host "❌ OpenSearch Dashboards not reachable" -ForegroundColor Red
    $FAILED++
}

Write-Host ""
Write-Host "=============================="
if ($FAILED -eq 0) {
    Write-Host "✅ All services healthy" -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ $FAILED service(s) failed health checks" -ForegroundColor Red
    Write-Host ""
    Write-Host "Debugging tips:" -ForegroundColor Yellow
    Write-Host "  docker-compose -f infra/compose.yaml logs api"
    Write-Host "  docker-compose -f infra/compose.yaml logs worker"
    Write-Host "  docker-compose -f infra/compose.yaml logs db"
    Write-Host "  docker-compose -f infra/compose.yaml ps"
    exit 1
}

