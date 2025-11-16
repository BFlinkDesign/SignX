# Import Grafana Dashboard Script
# Imports APEX overview dashboard to Grafana

$ErrorActionPreference = "Stop"

Write-Host "=== Importing Grafana Dashboard ===" -ForegroundColor Cyan
Write-Host ""

# Wait for Grafana to be ready
Write-Host "1. Waiting for Grafana to be ready..."
$grafanaReady = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $health = Invoke-WebRequest -Uri "http://localhost:3001/api/health" -UseBasicParsing -ErrorAction SilentlyContinue
        if ($health.StatusCode -eq 200) {
            Write-Host "   ✅ Grafana ready" -ForegroundColor Green
            $grafanaReady = $true
            break
        }
    } catch {
        # Grafana not ready yet
    }
    Write-Host "   Waiting... ($i/30)" -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

if (-not $grafanaReady) {
    Write-Host "   ❌ Grafana not ready after 60 seconds" -ForegroundColor Red
    Write-Host "   Check: docker compose logs grafana" -ForegroundColor Yellow
    exit 1
}

# Check dashboard file exists
Write-Host ""
Write-Host "2. Verifying dashboard file..."
$dashboardFile = "infra/monitoring/grafana/dashboards/apex-overview.json"
if (Test-Path $dashboardFile) {
    Write-Host "   ✅ Dashboard file exists" -ForegroundColor Green
} else {
    Write-Host "   ❌ Dashboard file not found: $dashboardFile" -ForegroundColor Red
    exit 1
}

# Import dashboard
Write-Host ""
Write-Host "3. Importing dashboard..."
$dashboardJson = Get-Content $dashboardFile -Raw | ConvertFrom-Json | ConvertTo-Json -Depth 10

$headers = @{
    "Content-Type" = "application/json"
    "Accept" = "application/json"
}

$base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:admin"))
$headers["Authorization"] = "Basic $base64Auth"

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3001/api/dashboards/db" `
        -Method Post `
        -Headers $headers `
        -Body $dashboardJson `
        -ErrorAction Stop

    if ($response.uid) {
        Write-Host "   ✅ Dashboard imported successfully" -ForegroundColor Green
        Write-Host "   Dashboard UID: $($response.uid)" -ForegroundColor Gray
        Write-Host "   Access at: http://localhost:3001/d/$($response.uid)/apex-overview" -ForegroundColor Cyan
    } else {
        Write-Host "   ⚠️  Dashboard import response unclear" -ForegroundColor Yellow
        Write-Host "   Response: $($response | ConvertTo-Json)" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ❌ Dashboard import failed" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    
    # Try alternative method
    Write-Host ""
    Write-Host "   Attempting alternative import method..." -ForegroundColor Yellow
    Write-Host "   Manual import:" -ForegroundColor Gray
    Write-Host "   1. Open: http://localhost:3001" -ForegroundColor Gray
    Write-Host "   2. Login: admin/admin" -ForegroundColor Gray
    Write-Host "   3. Go to: Dashboards → Import" -ForegroundColor Gray
    Write-Host "   4. Upload: $dashboardFile" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Dashboard Import Complete ===" -ForegroundColor Green
Write-Host ""

