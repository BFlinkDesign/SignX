<#
.SYNOPSIS
    SignX Studio - Automated Database Backup Script

.DESCRIPTION
    Creates compressed backups of the PostgreSQL database with rotation.
    Supports full backups, retention policies, and verification.

.PARAMETER BackupPath
    Directory to store backups (default: .\backups)

.PARAMETER RetentionDays
    Number of days to keep backups (default: 30)

.PARAMETER Compress
    Compress backup files (default: true)

.PARAMETER Verify
    Verify backup integrity after creation (default: true)

.EXAMPLE
    .\backup_database.ps1
    .\backup_database.ps1 -BackupPath "D:\Backups\SignX" -RetentionDays 90
    .\backup_database.ps1 -Verify:$false

.NOTES
    Author: SignX Studio Engineering
    Version: 1.0.0
    Requires: Docker, pg_dump
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$BackupPath = ".\backups",

    [Parameter(Mandatory=$false)]
    [int]$RetentionDays = 30,

    [Parameter(Mandatory=$false)]
    [switch]$Compress = $true,

    [Parameter(Mandatory=$false)]
    [switch]$Verify = $true,

    [Parameter(Mandatory=$false)]
    [string]$ContainerName = "signx-db"
)

# ============================================================================
# Configuration
# ============================================================================
$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFilename = "signx_backup_$timestamp.sql"

# ============================================================================
# Helper Functions
# ============================================================================

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"

    switch ($Level) {
        "ERROR"   { Write-Host $logMessage -ForegroundColor Red }
        "SUCCESS" { Write-Host $logMessage -ForegroundColor Green }
        "WARNING" { Write-Host $logMessage -ForegroundColor Yellow }
        default   { Write-Host $logMessage -ForegroundColor White }
    }

    # Append to log file
    $logFile = Join-Path $BackupPath "backup_log.txt"
    Add-Content -Path $logFile -Value $logMessage -ErrorAction SilentlyContinue
}

function Test-DockerContainer {
    param([string]$Name)

    try {
        $container = docker ps --filter "name=$Name" --format "{{.Names}}" 2>$null
        return $container -eq $Name
    } catch {
        return $false
    }
}

function Get-DatabaseCredentials {
    Write-Log "Loading database credentials from environment..."

    $envPath = ".\.env"
    if (-not (Test-Path $envPath)) {
        throw "Environment file not found: $envPath"
    }

    $credentials = @{}
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.+)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            $credentials[$key] = $value
        }
    }

    return @{
        User = $credentials['POSTGRES_USER']
        Password = $credentials['POSTGRES_PASSWORD']
        Database = $credentials['POSTGRES_DB']
    }
}

function New-DatabaseBackup {
    param(
        [hashtable]$Credentials,
        [string]$OutputPath
    )

    Write-Log "Creating database backup..."

    $pgUser = $Credentials.User
    $pgPassword = $Credentials.Password
    $pgDatabase = $Credentials.Database

    # Create backup using pg_dump inside the container
    $backupCommand = @"
PGPASSWORD='$pgPassword' pg_dump -U $pgUser -d $pgDatabase --verbose --no-owner --no-acl --format=plain
"@

    try {
        $backupData = docker exec -i $ContainerName sh -c $backupCommand

        if ($LASTEXITCODE -ne 0) {
            throw "pg_dump failed with exit code $LASTEXITCODE"
        }

        # Write backup to file
        Set-Content -Path $OutputPath -Value $backupData -Encoding UTF8

        $fileSize = (Get-Item $OutputPath).Length
        $fileSizeMB = [math]::Round($fileSize / 1MB, 2)

        Write-Log "Backup created: $OutputPath ($fileSizeMB MB)" "SUCCESS"

        return $OutputPath

    } catch {
        throw "Failed to create backup: $_"
    }
}

function Compress-Backup {
    param([string]$FilePath)

    Write-Log "Compressing backup..."

    try {
        $compressedPath = "$FilePath.gz"

        # Use .NET compression
        $sourceStream = [System.IO.File]::OpenRead($FilePath)
        $destStream = [System.IO.File]::Create($compressedPath)
        $gzipStream = New-Object System.IO.Compression.GZipStream($destStream, [System.IO.Compression.CompressionMode]::Compress)

        $sourceStream.CopyTo($gzipStream)

        $gzipStream.Close()
        $destStream.Close()
        $sourceStream.Close()

        # Remove uncompressed file
        Remove-Item $FilePath -Force

        $originalSize = (Get-Item $FilePath -ErrorAction SilentlyContinue).Length
        $compressedSize = (Get-Item $compressedPath).Length
        $compressionRatio = [math]::Round(($compressedSize / $originalSize) * 100, 1)

        Write-Log "Compressed to: $compressedPath (${compressionRatio}% of original)" "SUCCESS"

        return $compressedPath

    } catch {
        throw "Failed to compress backup: $_"
    }
}

function Test-BackupIntegrity {
    param([string]$FilePath)

    Write-Log "Verifying backup integrity..."

    try {
        # Check file size
        $fileInfo = Get-Item $FilePath
        if ($fileInfo.Length -eq 0) {
            throw "Backup file is empty"
        }

        # For compressed files, test decompression
        if ($FilePath -match '\.gz$') {
            $testStream = [System.IO.File]::OpenRead($FilePath)
            $gzipStream = New-Object System.IO.Compression.GZipStream($testStream, [System.IO.Compression.CompressionMode]::Decompress)

            # Read first 1KB to verify it's valid
            $buffer = New-Object byte[] 1024
            $bytesRead = $gzipStream.Read($buffer, 0, 1024)

            $gzipStream.Close()
            $testStream.Close()

            if ($bytesRead -eq 0) {
                throw "Compressed backup appears to be empty"
            }
        }

        # Check for SQL content markers
        $content = Get-Content $FilePath -First 10 -ErrorAction SilentlyContinue
        if ($content -notmatch 'PostgreSQL|CREATE|INSERT') {
            Write-Log "Warning: Backup may not contain valid SQL content" "WARNING"
        }

        Write-Log "Backup integrity verified" "SUCCESS"
        return $true

    } catch {
        Write-Log "Backup verification failed: $_" "ERROR"
        return $false
    }
}

function Remove-OldBackups {
    param(
        [string]$Path,
        [int]$Days
    )

    Write-Log "Removing backups older than $Days days..."

    $cutoffDate = (Get-Date).AddDays(-$Days)
    $removedCount = 0
    $freedSpace = 0

    Get-ChildItem -Path $Path -Filter "signx_backup_*.sql*" | ForEach-Object {
        if ($_.LastWriteTime -lt $cutoffDate) {
            $freedSpace += $_.Length
            Remove-Item $_.FullName -Force
            $removedCount++
            Write-Log "Removed old backup: $($_.Name)"
        }
    }

    if ($removedCount -gt 0) {
        $freedSpaceMB = [math]::Round($freedSpace / 1MB, 2)
        Write-Log "Removed $removedCount old backups, freed ${freedSpaceMB} MB" "SUCCESS"
    } else {
        Write-Log "No old backups to remove"
    }
}

function New-BackupMetadata {
    param(
        [string]$BackupFile,
        [hashtable]$Credentials
    )

    $metadataPath = "$BackupFile.meta.json"

    $metadata = @{
        timestamp = Get-Date -Format "o"
        filename = Split-Path $BackupFile -Leaf
        database = $Credentials.Database
        size_bytes = (Get-Item $BackupFile).Length
        compressed = $BackupFile -match '\.gz$'
        hostname = $env:COMPUTERNAME
        script_version = "1.0.0"
    } | ConvertTo-Json -Depth 10

    Set-Content -Path $metadataPath -Value $metadata -Encoding UTF8
    Write-Log "Metadata saved: $metadataPath"
}

function Send-BackupNotification {
    param(
        [string]$BackupFile,
        [bool]$Success,
        [string]$ErrorMessage = ""
    )

    # This function can be extended to send email/Slack notifications
    # For now, just log the result

    if ($Success) {
        $size = [math]::Round((Get-Item $BackupFile).Length / 1MB, 2)
        Write-Log "===== BACKUP SUCCESSFUL =====" "SUCCESS"
        Write-Log "File: $BackupFile" "SUCCESS"
        Write-Log "Size: $size MB" "SUCCESS"
    } else {
        Write-Log "===== BACKUP FAILED =====" "ERROR"
        Write-Log "Error: $ErrorMessage" "ERROR"
    }
}

# ============================================================================
# Main Backup Process
# ============================================================================

try {
    Write-Log "==================== SignX Studio Database Backup ===================="
    Write-Log "Backup started at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

    # Create backup directory if it doesn't exist
    if (-not (Test-Path $BackupPath)) {
        New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
        Write-Log "Created backup directory: $BackupPath"
    }

    # Check if Docker container is running
    if (-not (Test-DockerContainer -Name $ContainerName)) {
        throw "Database container '$ContainerName' is not running"
    }
    Write-Log "Database container is running"

    # Get database credentials
    $credentials = Get-DatabaseCredentials
    Write-Log "Database: $($credentials.Database)"

    # Create backup
    $backupPath = Join-Path $BackupPath $backupFilename
    $finalBackupPath = New-DatabaseBackup -Credentials $credentials -OutputPath $backupPath

    # Compress if requested
    if ($Compress) {
        $finalBackupPath = Compress-Backup -FilePath $finalBackupPath
    }

    # Verify backup integrity
    if ($Verify) {
        $isValid = Test-BackupIntegrity -FilePath $finalBackupPath
        if (-not $isValid) {
            throw "Backup verification failed"
        }
    }

    # Create metadata file
    New-BackupMetadata -BackupFile $finalBackupPath -Credentials $credentials

    # Remove old backups
    Remove-OldBackups -Path $BackupPath -Days $RetentionDays

    # Send notification
    Send-BackupNotification -BackupFile $finalBackupPath -Success $true

    Write-Log "Backup completed successfully"
    Write-Log "======================================================================"

    exit 0

} catch {
    $errorMessage = $_.Exception.Message
    Write-Log "Backup failed: $errorMessage" "ERROR"

    # Send failure notification
    Send-BackupNotification -BackupFile "" -Success $false -ErrorMessage $errorMessage

    Write-Log "======================================================================"
    exit 1
}
