[CmdletBinding()]
param()

set-strictmode -version latest
$ErrorActionPreference = 'Stop'

function Write-Info([string]$msg) { Write-Host $msg -ForegroundColor Cyan }
function Write-Ok([string]$msg) { Write-Host $msg -ForegroundColor Green }
function Write-Warn2([string]$msg) { Write-Warning $msg }

$staging = "C:\Scripts\Ai Observation & Training\OBS_Staging"
$logs = "C:\Scripts\Logs"

try {
    if (-not (Test-Path -LiteralPath $logs)) { New-Item -ItemType Directory -Path $logs -Force | Out-Null }
    if (-not (Test-Path -LiteralPath $staging)) { New-Item -ItemType Directory -Path $staging -Force | Out-Null }
    Write-Ok "Folders ensured: '$logs' and '$staging'"
} catch {
    Write-Error "Failed to create required folders: $($_.Exception.Message)"
    exit 1
}

# Attempt to install Screenpipe CLI if missing
try {
    if (-not (Get-Command screenpipe -ErrorAction SilentlyContinue)) {
        Write-Info "Screenpipe CLI not found; attempting install..."
        iwr get.screenpi.pe/cli.ps1 -UseBasicParsing | iex
        if (Get-Command screenpipe -ErrorAction SilentlyContinue) {
            Write-Ok "Screenpipe CLI installed."
        } else {
            Write-Warn2 "Screenpipe CLI still not found after install attempt; continuing."
        }
    } else {
        Write-Ok "Screenpipe CLI present."
    }
} catch {
    Write-Warn2 "Screenpipe install attempt failed: $($_.Exception.Message)"
}

function Resolve-ArchiveRootLocal {
    try {
        $fsDrives = Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Root -match '^[A-Z]:\\$' }
        foreach ($d in $fsDrives) {
            $probe = Join-Path -Path $d.Root -ChildPath 'My Drive'
            if (Test-Path -LiteralPath $probe) {
                return (Join-Path -Path $probe -ChildPath 'Recordings')
            }
        }
    } catch { }
    return $null
}

$archiveRoot = Resolve-ArchiveRootLocal
if ($archiveRoot) {
    Write-Ok "Detected ArchiveRoot: '$archiveRoot'"
} else {
    Write-Warn2 "Could not detect Google Drive 'My Drive'. Start Google Drive for Desktop; mover will warn and keep watching."
}

# One-shot sweep of existing files
try {
    Write-Info "Running one-shot sweep..."
    & (Join-Path -Path $PSScriptRoot -ChildPath 'obs_mover.ps1') -OneShot | Out-Null
    Write-Ok "One-shot sweep complete."
} catch {
    Write-Warn2 "One-shot sweep failed: $($_.Exception.Message)"
}

# Install scheduled task
try {
    Write-Info "Installing scheduled task..."
    & (Join-Path -Path $PSScriptRoot -ChildPath 'obs_mover.ps1') -InstallTask | Out-Null
} catch {
    Write-Warn2 "Scheduled task installation failed: $($_.Exception.Message)"
}

Write-Host "" 
Write-Host "OBS Checklist:" -ForegroundColor Yellow
Write-Host "  • Output Mode: Advanced"
Write-Host "  • Recording: MKV"
Write-Host "  • Advanced → Recording: Auto-remux to MP4 = On"
Write-Host "  • Recording Path: \"C:\Scripts\Ai Observation & Training\OBS_Staging\""
Write-Host "  • Encoder: NVENC AV1 CQP (CQ18–22), Keyframe 2s, Preset P5"

Write-Ok "Bootstrap complete. Review any warnings above."


