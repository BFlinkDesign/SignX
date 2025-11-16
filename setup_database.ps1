# SignX Studio Database Setup Script
# Renames database and creates .env file

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SignX Studio Database Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"

# Database parameters
$oldDbName = "calcusign_apex"
$newDbName = "signx_studio"
$dbUser = "postgres"
$dbHost = "localhost"
$dbPort = "5432"

# Find PostgreSQL installation
$psqlPaths = @(
    "C:\Program Files\PostgreSQL\16\bin\psql.exe",
    "C:\Program Files\PostgreSQL\15\bin\psql.exe",
    "C:\Program Files\PostgreSQL\14\bin\psql.exe",
    "C:\Program Files\PostgreSQL\13\bin\psql.exe",
    "C:\Program Files (x86)\PostgreSQL\16\bin\psql.exe",
    "C:\Program Files (x86)\PostgreSQL\15\bin\psql.exe"
)

$psqlExe = $null
foreach ($path in $psqlPaths) {
    if (Test-Path $path) {
        $psqlExe = $path
        Write-Host "[OK] Found PostgreSQL: $path" -ForegroundColor Green
        break
    }
}

if (-not $psqlExe) {
    Write-Host "[ERROR] PostgreSQL not found!" -ForegroundColor Red
    Write-Host "Please install PostgreSQL or provide the path manually." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Download from: https://www.postgresql.org/download/windows/" -ForegroundColor Cyan
    exit 1
}

# Prompt for password
Write-Host ""
$securePassword = Read-Host "Enter PostgreSQL password for user 'postgres'" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
$dbPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)

# Set PGPASSWORD environment variable for this session
$env:PGPASSWORD = $dbPassword

Write-Host ""
Write-Host "[1/5] Checking if database '$oldDbName' exists..." -ForegroundColor Yellow

# Check if old database exists
$checkDbQuery = "SELECT 1 FROM pg_database WHERE datname='$oldDbName'"
$dbExists = & $psqlExe -h $dbHost -p $dbPort -U $dbUser -d postgres -t -c $checkDbQuery 2>&1

if ($dbExists -match "1") {
    Write-Host "  [OK] Database '$oldDbName' exists" -ForegroundColor Green
    $renameNeeded = $true
} else {
    Write-Host "  [INFO] Database '$oldDbName' does not exist" -ForegroundColor Yellow
    $renameNeeded = $false
}

# Check if new database already exists
$checkNewDbQuery = "SELECT 1 FROM pg_database WHERE datname='$newDbName'"
$newDbExists = & $psqlExe -h $dbHost -p $dbPort -U $dbUser -d postgres -t -c $checkNewDbQuery 2>&1

if ($newDbExists -match "1") {
    Write-Host "  [WARN] Database '$newDbName' already exists! Skipping rename." -ForegroundColor Red
    $renameNeeded = $false
}

if ($renameNeeded) {
    Write-Host ""
    Write-Host "[2/5] Terminating active connections to '$oldDbName'..." -ForegroundColor Yellow

    $terminateQuery = @"
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '$oldDbName'
  AND pid <> pg_backend_pid();
"@

    & $psqlExe -h $dbHost -p $dbPort -U $dbUser -d postgres -c $terminateQuery 2>&1 | Out-Null
    Write-Host "  [OK] Connections terminated" -ForegroundColor Green

    Write-Host ""
    Write-Host "[3/5] Renaming database '$oldDbName' to '$newDbName'..." -ForegroundColor Yellow

    $renameQuery = "ALTER DATABASE $oldDbName RENAME TO $newDbName;"
    $result = & $psqlExe -h $dbHost -p $dbPort -U $dbUser -d postgres -c $renameQuery 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Database renamed successfully" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Failed to rename database" -ForegroundColor Red
        Write-Host "  Error: $result" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "[2/5] Skipping connection termination (rename not needed)" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "[3/5] Skipping database rename (already done or doesn't exist)" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "[4/5] Creating .env file..." -ForegroundColor Yellow

$projectPath = "C:\Scripts\Leo Ai Clone"
if (Test-Path "C:\Scripts\SignX-Studio") {
    $projectPath = "C:\Scripts\SignX-Studio"
}

$envContent = @"
# SignX Studio Environment Configuration
# Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

# Database Configuration
DB_NAME=$newDbName
DB_USER=$dbUser
DB_PASSWORD=$dbPassword
DB_HOST=$dbHost
DB_PORT=$dbPort

# Database URL (for SQLAlchemy)
DATABASE_URL=postgresql://${dbUser}:${dbPassword}@${dbHost}:${dbPort}/${newDbName}

# Application Settings
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO

# API Settings
API_HOST=localhost
API_PORT=8000

# Redis (if used)
REDIS_URL=redis://localhost:6379/0

# Secret Key (change in production!)
SECRET_KEY=dev-secret-key-change-in-production
"@

$envPath = Join-Path $projectPath ".env"
Set-Content -Path $envPath -Value $envContent -Encoding UTF8
Write-Host "  [OK] Created: $envPath" -ForegroundColor Green

# Also update .env.example
$envExamplePath = Join-Path $projectPath ".env.example"
$envExampleContent = @"
# SignX Studio Environment Configuration
# Copy this to .env and fill in your values

# Database Configuration
DB_NAME=signx_studio
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432

# Database URL (for SQLAlchemy)
DATABASE_URL=postgresql://postgres:your_password_here@localhost:5432/signx_studio

# Application Settings
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO

# API Settings
API_HOST=localhost
API_PORT=8000

# Redis (if used)
REDIS_URL=redis://localhost:6379/0

# Secret Key (change in production!)
SECRET_KEY=dev-secret-key-change-in-production
"@

Set-Content -Path $envExamplePath -Value $envExampleContent -Encoding UTF8
Write-Host "  [OK] Updated: $envExamplePath" -ForegroundColor Green

Write-Host ""
Write-Host "[5/5] Testing database connection..." -ForegroundColor Yellow

$testQuery = "SELECT version();"
$connectionTest = & $psqlExe -h $dbHost -p $dbPort -U $dbUser -d $newDbName -c $testQuery 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Connection successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Database version:" -ForegroundColor Cyan
    $connectionTest | Select-String "PostgreSQL" | ForEach-Object { Write-Host "    $($_.Line.Trim())" -ForegroundColor White }
} else {
    Write-Host "  [ERROR] Connection failed!" -ForegroundColor Red
    Write-Host "  Error: $connectionTest" -ForegroundColor Red
    exit 1
}

# Clear password from environment
$env:PGPASSWORD = $null

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Database Setup Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  * Database name: $newDbName" -ForegroundColor White
Write-Host "  * Database user: $dbUser" -ForegroundColor White
Write-Host "  * Database host: $dbHost" -ForegroundColor White
Write-Host "  * Database port: $dbPort" -ForegroundColor White
Write-Host "  * .env file: $envPath" -ForegroundColor White
Write-Host ""
Write-Host "[SUCCESS] Database setup complete!" -ForegroundColor Green
Write-Host ""
