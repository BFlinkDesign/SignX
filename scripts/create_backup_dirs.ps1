# Create backup directories with proper permissions

Write-Host "Creating backup directories..." -ForegroundColor Cyan

$directories = @(
    "backups/postgres",
    "backups/redis",
    "backups/config",
    "backups/minio",
    "backups/logs/api",
    "backups/logs/worker",
    "backups/logs/db"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Green
    } else {
        Write-Host "  Exists: $dir" -ForegroundColor Yellow
    }
}

Write-Host "✅ Backup directories ready" -ForegroundColor Green

