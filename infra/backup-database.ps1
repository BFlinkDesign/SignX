Set-Location "C:\Scripts\Leo Ai Clone\infra"

$date = Get-Date -Format "yyyy-MM-dd_HH-mm"

# Backup PostgreSQL
docker compose exec -T db pg_dump -U apex apex > "backups/postgres/apex_$date.sql"

# Keep only last 7 days
Get-ChildItem backups/postgres/*.sql | 
    Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-7)} | 
    Remove-Item

Write-Host "Backup completed: apex_$date.sql"
