<#
.SYNOPSIS
    SignX Studio - One-Click Windows Installer

.DESCRIPTION
    Automated installer for SignX Studio structural engineering software.
    Installs Docker, creates configuration, and starts the application.

.PARAMETER InstallPath
    Installation directory (default: C:\SignX-Studio)

.PARAMETER SkipDocker
    Skip Docker installation if already installed

.PARAMETER DataPath
    Path for database and application data (default: C:\SignX-Studio\data)

.EXAMPLE
    .\install_signx.ps1
    .\install_signx.ps1 -InstallPath "D:\Apps\SignX" -DataPath "D:\Data\SignX"
    .\install_signx.ps1 -SkipDocker

.NOTES
    Author: SignX Studio Engineering
    Version: 1.0.0
    Requires: Windows 10/11, PowerShell 5.1+, Administrator privileges
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$InstallPath = "C:\SignX-Studio",

    [Parameter(Mandatory=$false)]
    [switch]$SkipDocker,

    [Parameter(Mandatory=$false)]
    [string]$DataPath = "C:\SignX-Studio\data"
)

# ============================================================================
# Configuration
# ============================================================================
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$SIGNX_VERSION = "1.0.0"
$DOCKER_COMPOSE_VERSION = "2.24.0"
$REQUIRED_DOCKER_VERSION = "24.0.0"

# ============================================================================
# Helper Functions
# ============================================================================

function Write-Header {
    param([string]$Message)
    Write-Host "`n============================================" -ForegroundColor Cyan
    Write-Host " $Message" -ForegroundColor Cyan
    Write-Host "============================================`n" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Test-Administrator {
    $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-DockerInstalled {
    try {
        $dockerVersion = docker --version 2>$null
        if ($dockerVersion) {
            Write-Success "Docker is installed: $dockerVersion"
            return $true
        }
    } catch {
        return $false
    }
    return $false
}

function Test-DockerRunning {
    try {
        docker ps 2>$null | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Install-DockerDesktop {
    Write-Header "Installing Docker Desktop"

    $dockerInstallerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
    $installerPath = "$env:TEMP\DockerDesktopInstaller.exe"

    Write-Info "Downloading Docker Desktop..."
    try {
        Invoke-WebRequest -Uri $dockerInstallerUrl -OutFile $installerPath -UseBasicParsing
        Write-Success "Downloaded Docker Desktop installer"
    } catch {
        Write-Error-Custom "Failed to download Docker Desktop: $_"
        throw
    }

    Write-Info "Installing Docker Desktop (this may take several minutes)..."
    try {
        Start-Process -FilePath $installerPath -ArgumentList "install","--quiet","--accept-license" -Wait -NoNewWindow
        Write-Success "Docker Desktop installed successfully"
    } catch {
        Write-Error-Custom "Failed to install Docker Desktop: $_"
        throw
    }

    Remove-Item $installerPath -ErrorAction SilentlyContinue

    Write-Info "Starting Docker Desktop..."
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

    Write-Info "Waiting for Docker to start (this may take 2-3 minutes)..."
    $maxAttempts = 60
    $attempt = 0
    while (-not (Test-DockerRunning) -and $attempt -lt $maxAttempts) {
        Start-Sleep -Seconds 5
        $attempt++
        Write-Host "." -NoNewline
    }
    Write-Host ""

    if (Test-DockerRunning) {
        Write-Success "Docker is running"
    } else {
        Write-Error-Custom "Docker failed to start. Please start Docker Desktop manually and run this script again."
        throw "Docker not running"
    }
}

function New-DirectoryStructure {
    param([string]$BasePath)

    Write-Header "Creating Directory Structure"

    $directories = @(
        $BasePath,
        "$BasePath\data",
        "$BasePath\data\postgres",
        "$BasePath\backups",
        "$BasePath\logs",
        "$BasePath\config"
    )

    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Success "Created: $dir"
        } else {
            Write-Info "Already exists: $dir"
        }
    }
}

function New-EnvironmentFile {
    param([string]$BasePath)

    Write-Header "Creating Environment Configuration"

    $envPath = "$BasePath\.env"

    if (Test-Path $envPath) {
        Write-Info "Environment file already exists. Backing up..."
        Copy-Item $envPath "$envPath.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    }

    # Generate secure random passwords
    Add-Type -AssemblyName System.Web
    $postgresPassword = [System.Web.Security.Membership]::GeneratePassword(32, 8)
    $redisPassword = [System.Web.Security.Membership]::GeneratePassword(32, 8)
    $secretKey = [System.Web.Security.Membership]::GeneratePassword(64, 16)

    $envContent = @"
# ============================================================================
# SignX Studio - Production Environment Configuration
# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
# ============================================================================

# Application
APP_VERSION=$SIGNX_VERSION
ENV=production
LOG_LEVEL=info

# Database Configuration
POSTGRES_USER=signx
POSTGRES_PASSWORD=$postgresPassword
POSTGRES_DB=signx_studio
POSTGRES_PORT=5432
DB_DATA_PATH=$DataPath\postgres

# Redis Configuration
REDIS_PASSWORD=$redisPassword
REDIS_PORT=6379

# Security
SECRET_KEY=$secretKey
CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
ALLOWED_HOSTS=localhost,127.0.0.1

# API Configuration
API_PORT=8000
RATE_LIMIT_PER_MIN=120

# Optional: Object Storage (MinIO)
# MINIO_URL=http://localhost:9000
# MINIO_ACCESS_KEY=minioadmin
# MINIO_SECRET_KEY=minioadmin
# MINIO_BUCKET=signx-uploads

# Optional: Authentication (Supabase)
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_KEY=your-anon-key
# SUPABASE_SERVICE_KEY=your-service-key

# Optional: Monitoring (Sentry)
# SENTRY_DSN=https://your-sentry-dsn
# SENTRY_TRACES_SAMPLE_RATE=0.1

# ============================================================================
# IMPORTANT: Keep this file secure and never commit to version control
# ============================================================================
"@

    Set-Content -Path $envPath -Value $envContent -Encoding UTF8
    Write-Success "Environment file created: $envPath"
    Write-Info "IMPORTANT: Passwords have been generated. Store them securely!"
}

function Copy-ApplicationFiles {
    param(
        [string]$SourcePath,
        [string]$DestPath
    )

    Write-Header "Copying Application Files"

    if (-not (Test-Path "$SourcePath\docker-compose.prod.yml")) {
        Write-Error-Custom "docker-compose.prod.yml not found in source directory"
        throw "Missing docker-compose.prod.yml"
    }

    $filesToCopy = @(
        "docker-compose.prod.yml",
        "services",
        "scripts"
    )

    foreach ($item in $filesToCopy) {
        $sourcePath = Join-Path $SourcePath $item
        $destPath = Join-Path $DestPath $item

        if (Test-Path $sourcePath) {
            if (Test-Path $destPath) {
                Write-Info "Updating: $item"
                Remove-Item $destPath -Recurse -Force -ErrorAction SilentlyContinue
            }
            Copy-Item $sourcePath $destPath -Recurse -Force
            Write-Success "Copied: $item"
        } else {
            Write-Info "Skipping (not found): $item"
        }
    }
}

function Start-SignXStudio {
    param([string]$BasePath)

    Write-Header "Starting SignX Studio"

    Set-Location $BasePath

    Write-Info "Building Docker images..."
    docker-compose -f docker-compose.prod.yml build --no-cache

    Write-Info "Starting services..."
    docker-compose -f docker-compose.prod.yml up -d

    Write-Info "Waiting for services to be healthy..."
    Start-Sleep -Seconds 10

    Write-Info "Running database migrations..."
    docker-compose -f docker-compose.prod.yml exec -T api alembic upgrade head

    Write-Success "SignX Studio is starting up!"
    Write-Info "Services will be available in 30-60 seconds"
}

function Show-CompletionMessage {
    param([string]$BasePath)

    Write-Header "Installation Complete!"

    Write-Host @"

SignX Studio has been installed successfully!

Installation Details:
  - Install Path: $BasePath
  - Data Path: $DataPath
  - Version: $SIGNX_VERSION

Access Points:
  - API: http://localhost:8000
  - API Documentation: http://localhost:8000/docs
  - Health Check: http://localhost:8000/health

Management Commands:
  - View logs:      docker-compose -f docker-compose.prod.yml logs -f
  - Stop services:  docker-compose -f docker-compose.prod.yml down
  - Start services: docker-compose -f docker-compose.prod.yml up -d
  - View status:    docker-compose -f docker-compose.prod.yml ps

Important Files:
  - Configuration: $BasePath\.env
  - Backups: $BasePath\backups
  - Logs: $BasePath\logs

Next Steps:
  1. Wait 30-60 seconds for all services to start
  2. Open http://localhost:8000/docs to verify installation
  3. Review configuration in .env file
  4. Set up automated backups (see docs\DEPLOY.md)

For help and documentation, see:
  - docs\INSTALL.md - User installation guide
  - docs\DEPLOY.md - IT deployment guide

"@ -ForegroundColor Green

    Write-Info "Opening API documentation in default browser..."
    Start-Sleep -Seconds 5
    Start-Process "http://localhost:8000/docs"
}

# ============================================================================
# Main Installation Process
# ============================================================================

try {
    Clear-Host
    Write-Host @"
  ╔═══════════════════════════════════════════════════════╗
  ║                                                       ║
  ║          SignX Studio Installer v$SIGNX_VERSION          ║
  ║     Structural Engineering Calculation Software       ║
  ║                                                       ║
  ╚═══════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

    # Check administrator privileges
    if (-not (Test-Administrator)) {
        Write-Error-Custom "This script requires Administrator privileges."
        Write-Info "Please run PowerShell as Administrator and try again."
        exit 1
    }
    Write-Success "Running with Administrator privileges"

    # Check and install Docker
    if ($SkipDocker) {
        Write-Info "Skipping Docker installation check"
    } else {
        if (-not (Test-DockerInstalled)) {
            $response = Read-Host "Docker is not installed. Install Docker Desktop? (Y/N)"
            if ($response -eq 'Y' -or $response -eq 'y') {
                Install-DockerDesktop
            } else {
                Write-Error-Custom "Docker is required. Please install Docker Desktop manually."
                exit 1
            }
        } else {
            if (-not (Test-DockerRunning)) {
                Write-Info "Starting Docker Desktop..."
                Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
                Start-Sleep -Seconds 30
            }
        }
    }

    # Create directory structure
    New-DirectoryStructure -BasePath $InstallPath

    # Create environment file
    New-EnvironmentFile -BasePath $InstallPath

    # Copy application files
    $currentPath = Split-Path -Parent $PSScriptRoot
    Copy-ApplicationFiles -SourcePath $currentPath -DestPath $InstallPath

    # Start the application
    $response = Read-Host "Start SignX Studio now? (Y/N)"
    if ($response -eq 'Y' -or $response -eq 'y') {
        Start-SignXStudio -BasePath $InstallPath
        Show-CompletionMessage -BasePath $InstallPath
    } else {
        Write-Info "Installation complete. Run 'docker-compose -f docker-compose.prod.yml up -d' to start."
    }

} catch {
    Write-Error-Custom "Installation failed: $_"
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
    exit 1
}
