<#
	OBS Mover – Production-safe mover for finalized OBS recordings

	Usage examples:
	  - Interactive watch (defaults):
	    .\obs_mover.ps1

	  - One-shot sweep of staging:
	    .\obs_mover.ps1 -OneShot

	  - Dry run (no changes):
	    .\obs_mover.ps1 -DryRun

	  - Install/Uninstall scheduled task:
	    .\obs_mover.ps1 -InstallTask
	    .\obs_mover.ps1 -UninstallTask

	Defaults:
	  StagingPath      = "C:\\Scripts\\Ai Observation & Training\\OBS_Staging"
	  ArchiveRoot      = Auto-detected (DriveFS: "<Drive>:\\My Drive\\Recordings")
	  ScanIntervalSec  = 30
	  MinStableSeconds = 3
	  WaitUnlockTimeoutSec = 600
	  MoveMaxRetries   = 3
	  LogPath          = "C:\\Scripts\\Logs\\obs_mover.log"
	  TaskName         = "OBS_Mover_To_GDrive"

	Notes:
	- Only handles finalized .mp4 files (assumes OBS records MKV and auto-remuxes to MP4)
	- Refuses to operate on staging paths under "\\tsclient\\" or any path containing "\\My Drive\\"
	- Logs rotate at 5MB x 5
#>

[CmdletBinding()]
param(
	[string]$StagingPath = "C:\Scripts\Ai Observation & Training\OBS_Staging",
	[string]$ArchiveRoot,
	[int]$ScanIntervalSec = 30,
	[int]$MinStableSeconds = 3,
	[int]$WaitUnlockTimeoutSec = 600,
	[int]$MoveMaxRetries = 3,
	[switch]$DryRun,
	[switch]$OneShot,
	[switch]$InstallTask,
	[switch]$UninstallTask,
	[string]$LogPath = "C:\Scripts\Logs\obs_mover.log",
	[string]$TaskName = "OBS_Mover_To_GDrive"
)

set-strictmode -version latest
$ErrorActionPreference = 'Stop'

function Write-Log {
	param(
		[string]$Message,
		[string]$Level = 'INFO'
	)

	try {
		$logFile = $LogPath
		$logDir = [System.IO.Path]::GetDirectoryName($logFile)
		if (-not (Test-Path -LiteralPath $logDir)) {
			New-Item -ItemType Directory -Path $logDir -Force | Out-Null
		}
		# Rotate: 5MB x 5
		if (Test-Path -LiteralPath $logFile) {
			try {
				$len = (Get-Item -LiteralPath $logFile).Length
				if ($len -ge 5MB) {
					for ($i = 5; $i -ge 1; $i--) {
						$src = "$logFile.$i"
						$dst = "$logFile." + ($i + 1)
						if ($i -eq 5 -and (Test-Path -LiteralPath $src)) { Remove-Item -LiteralPath $src -Force -ErrorAction SilentlyContinue }
						if (Test-Path -LiteralPath $src) {
							Move-Item -LiteralPath $src -Destination $dst -Force -ErrorAction SilentlyContinue
						}
					}
					Move-Item -LiteralPath $logFile -Destination "$logFile.1" -Force -ErrorAction SilentlyContinue
				}
			} catch { }
		}
		$ts = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss.fff')
		$line = "$ts [$Level] $Message"
		Add-Content -LiteralPath $logFile -Value $line
		Write-Verbose $line
	} catch {
		Write-Warning "Logging failed: $($_.Exception.Message)"
	}
}

function Is-ForbiddenStagingPath {
	param([string]$Path)
	if (-not $Path) { return $true }
	$normalized = $Path.ToLowerInvariant()
	if ($normalized.StartsWith('\\\\tsclient\\')) { return $true }
	if ($normalized -like '*\\my drive\\*') { return $true }
	return $false
}

function Resolve-ArchiveRootInternal {
	param([string]$Provided)
	if ($Provided) { return $Provided }
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

function Test-FileExclusive {
	param([string]$Path)
	try {
		$fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
		$fs.Close()
		return $true
	} catch {
		return $false
	}
}

function Test-FileStable {
	param(
		[string]$Path,
		[int]$MinStableSeconds,
		[int]$TimeoutSeconds
	)
	$start = Get-Date
	$lastSize = -1
	$lastChange = Get-Date
	while ($true) {
		try {
			$currentSize = (Get-Item -LiteralPath $Path).Length
		} catch {
			return $false
		}
		if ($currentSize -ne $lastSize) {
			$lastSize = $currentSize
			$lastChange = Get-Date
		}
		$stableFor = (New-TimeSpan -Start $lastChange -End (Get-Date)).TotalSeconds
		if ($stableFor -ge $MinStableSeconds) {
			if (Test-FileExclusive -Path $Path) { return $true }
		}
		if ((New-TimeSpan -Start $start -End (Get-Date)).TotalSeconds -ge $TimeoutSeconds) { return $false }
		Start-Sleep -Seconds 1
	}
}

function Ensure-DestinationDirectory {
	param([string]$ArchiveRoot,[DateTime]$When,[switch]$DryRun)
	$year = $When.ToString('yyyy')
	$day = $When.ToString('yyyy-MM-dd')
	$yearDir = Join-Path -Path $ArchiveRoot -ChildPath $year
	$dayDir = Join-Path -Path $yearDir -ChildPath $day
	if (-not (Test-Path -LiteralPath $dayDir)) {
		if ($DryRun) {
			Write-Log "DRYRUN: would create '$dayDir'"
		} else {
			New-Item -ItemType Directory -Path $dayDir -Force | Out-Null
		}
	}
	return $dayDir
}

function Move-FileWithRetries {
	param(
		[string]$Source,
		[string]$Destination,
		[int]$Retries,
		[switch]$DryRun
	)
	for ($attempt = 1; $attempt -le [Math]::Max(1,$Retries); $attempt++) {
		try {
			if ($DryRun) {
				Write-Log "DRYRUN: would move '$Source' -> '$Destination'"
				return $true
			}
			Move-Item -LiteralPath $Source -Destination $Destination -Force
			return $true
		} catch {
			Write-Log "Move attempt $attempt failed: $($_.Exception.Message)" 'WARN'
			Start-Sleep -Seconds ([Math]::Min(5, $attempt))
		}
	}
	# Fallback: copy + delete
	try {
		if ($DryRun) {
			Write-Log "DRYRUN: would COPY+DELETE '$Source' -> '$Destination'"
			return $true
		}
		Copy-Item -LiteralPath $Source -Destination $Destination -Force
		$srcLen = (Get-Item -LiteralPath $Source).Length
		$dstLen = (Get-Item -LiteralPath $Destination).Length
		if ($srcLen -eq $dstLen -and $dstLen -gt 0) {
			Remove-Item -LiteralPath $Source -Force
			return $true
		} else {
			Write-Log "Copy verification failed (size mismatch)." 'ERROR'
			return $false
		}
	} catch {
		Write-Log "Copy+Delete fallback failed: $($_.Exception.Message)" 'ERROR'
		return $false
	}
}

function Invoke-ScreenpipeIndex {
	param([string]$Path,[switch]$DryRun)
	try {
		$cmd = Get-Command screenpipe -ErrorAction SilentlyContinue
		if ($null -ne $cmd) {
			if ($DryRun) {
				Write-Log "DRYRUN: would index with screenpipe: '$Path'"
				return
			}
			Start-Process -FilePath "screenpipe" -ArgumentList @('add', $Path) -WindowStyle Hidden | Out-Null
			Write-Log "Screenpipe index queued: '$Path'"
		} else {
			Write-Log "Screenpipe not found; skipping index." 'WARN'
		}
	} catch {
		Write-Log "Screenpipe invocation failed: $($_.Exception.Message)" 'WARN'
	}
}

function Get-DestinationPath {
	param([string]$ArchiveRoot,[string]$SourcePath)
	$when = (Get-Item -LiteralPath $SourcePath).LastWriteTime
	$destDir = Ensure-DestinationDirectory -ArchiveRoot $ArchiveRoot -When $when -DryRun:$DryRun
	$destName = [System.IO.Path]::GetFileName($SourcePath)
	return (Join-Path -Path $destDir -ChildPath $destName)
}

function Process-CandidateFile {
	param([string]$Path,[hashtable]$Processed)
	if (-not (Test-Path -LiteralPath $Path)) { return }
	if ($Processed.ContainsKey($Path)) { return }
	if ([System.IO.Path]::GetExtension($Path).ToLowerInvariant() -ne '.mp4') { return }

	Write-Log "Evaluating: '$Path'"
	if (-not (Test-Path -LiteralPath $StagingPath)) { Write-Log "Staging path missing: '$StagingPath'" 'WARN'; return }

	if (-not (Test-FileStable -Path $Path -MinStableSeconds $MinStableSeconds -TimeoutSeconds $WaitUnlockTimeoutSec)) {
		Write-Log "File not yet stable (or timed out): '$Path'" 'WARN'
		return
	}

	$destRoot = Resolve-ArchiveRootInternal -Provided $ArchiveRoot
	if (-not $destRoot) {
		Write-Log "Google Drive 'My Drive' not detected. Will retry later." 'WARN'
		return
	}
	if (-not (Test-Path -LiteralPath $destRoot)) {
		Write-Log "Archive root unavailable: '$destRoot'" 'WARN'
		return
	}

	$dest = Get-DestinationPath -ArchiveRoot $destRoot -SourcePath $Path
	Write-Log "Moving to: '$dest'"
	$ok = Move-FileWithRetries -Source $Path -Destination $dest -Retries $MoveMaxRetries -DryRun:$DryRun
	if ($ok) {
		$Processed[$Path] = $true
		Write-Log "Moved: '$Path' -> '$dest'"
		Invoke-ScreenpipeIndex -Path $dest -DryRun:$DryRun
	} else {
		Write-Log "Failed to relocate file after retries: '$Path'" 'ERROR'
	}
}

function Start-Watchers {
    param([System.IO.FileSystemWatcher]$Watcher)
    # We register events to wake the main loop; processing happens in the sweeper to avoid cross-runspace issues.
    $null = Register-ObjectEvent -InputObject $Watcher -EventName Created -Action { } -SourceIdentifier 'obs_mover_created'
    $null = Register-ObjectEvent -InputObject $Watcher -EventName Renamed -Action { } -SourceIdentifier 'obs_mover_renamed'
}

function Stop-Watchers {
	Get-EventSubscriber | Where-Object { $_.SourceIdentifier -like 'obs_mover_*' } | ForEach-Object { try { Unregister-Event -SourceIdentifier $_.SourceIdentifier -Force } catch { } }
}

function Install-ObsScheduledTask {
	param([string]$TaskName)
	try {
		$scriptPath = Join-Path -Path $PSScriptRoot -ChildPath 'obs_mover.ps1'
		$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
		$trigger = New-ScheduledTaskTrigger -AtLogOn
		$settings = New-ScheduledTaskSettingsSet -Hidden -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
		Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description 'OBS mover to Google Drive (DriveFS)'
		Write-Log "Scheduled task '$TaskName' installed"
		Write-Host "Installed scheduled task '$TaskName'" -ForegroundColor Green
	} catch {
		Write-Log "Failed to install scheduled task via module: $($_.Exception.Message). Trying schtasks.exe." 'WARN'
        try {
            $scriptPath = Join-Path -Path $PSScriptRoot -ChildPath 'obs_mover.ps1'
            $cmd = "schtasks /Create /TN `"$TaskName`" /TR `"powershell.exe -NoProfile -ExecutionPolicy Bypass -File `\"$scriptPath`\"`" /SC ONLOGON /RL HIGHEST /F"
            cmd.exe /c $cmd | Out-Null
			Write-Log "Scheduled task '$TaskName' installed via schtasks.exe"
			Write-Host "Installed scheduled task '$TaskName' (schtasks)" -ForegroundColor Green
		} catch {
			Write-Log "Failed to install scheduled task: $($_.Exception.Message)" 'ERROR'
			throw
		}
	}
}

function Uninstall-ObsScheduledTask {
	param([string]$TaskName)
	try {
		Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
		Write-Log "Scheduled task '$TaskName' uninstalled"
		Write-Host "Uninstalled scheduled task '$TaskName'" -ForegroundColor Yellow
	} catch {
		try {
			$cmd = "schtasks /Delete /TN `"$TaskName`" /F"
			cmd.exe /c $cmd | Out-Null
			Write-Log "Scheduled task '$TaskName' uninstalled via schtasks.exe"
			Write-Host "Uninstalled scheduled task '$TaskName' (schtasks)" -ForegroundColor Yellow
		} catch {
			Write-Log "Failed to uninstall scheduled task: $($_.Exception.Message)" 'ERROR'
			throw
		}
	}
}

# Parameter validation and special modes
if (Is-ForbiddenStagingPath -Path $StagingPath) {
	Write-Log "Forbidden staging path: '$StagingPath'" 'ERROR'
	Write-Error "StagingPath is forbidden (\\tsclient or contains \\My Drive\\)."
	exit 1
}

if ($InstallTask) {
	Install-ObsScheduledTask -TaskName $TaskName
	return
}
if ($UninstallTask) {
	Uninstall-ObsScheduledTask -TaskName $TaskName
	return
}

if (-not (Test-Path -LiteralPath $StagingPath)) {
	New-Item -ItemType Directory -Path $StagingPath -Force | Out-Null
}

$ProcessedSet = @{}
Set-Variable -Name ProcessedSet -Scope Script -Value $ProcessedSet

Write-Log "obs_mover starting. StagingPath='$StagingPath' DryRun=$DryRun OneShot=$OneShot"

function Sweep-Staging {
	try {
		Get-ChildItem -LiteralPath $StagingPath -Filter '*.mp4' -File -ErrorAction SilentlyContinue | ForEach-Object {
			Process-CandidateFile -Path $_.FullName -Processed $ProcessedSet
		}
	} catch {
		Write-Log "Sweep error: $($_.Exception.Message)" 'WARN'
	}
}

if ($OneShot) {
	Sweep-Staging
	Write-Log "OneShot complete."
	return
}

$fsw = New-Object System.IO.FileSystemWatcher
$fsw.Path = $StagingPath
$fsw.Filter = '*.mp4'
$fsw.IncludeSubdirectories = $false
$fsw.NotifyFilter = [System.IO.NotifyFilters]'FileName, LastWrite, Size'
$fsw.EnableRaisingEvents = $true

Start-Watchers -Watcher $fsw

try {
	while ($true) {
		# Wait for any event or timeout, then sweep
		$evt = Wait-Event -Timeout $ScanIntervalSec
		if ($evt) { try { Remove-Event -EventIdentifier $evt.EventIdentifier -ErrorAction SilentlyContinue } catch { } }
		# Clear any backlog to prevent growth
		try { Get-Event | ForEach-Object { Remove-Event -EventIdentifier $_.EventIdentifier -ErrorAction SilentlyContinue } } catch { }
		Sweep-Staging
	}
} finally {
	Stop-Watchers
	$fsw.Dispose()
}

<#
TEST PLAN (manual)

- Create a file at "C:\Scripts\Ai Observation & Training\OBS_Staging\_ping.mp4" and observe move into "<Drive>:\My Drive\Recordings\YYYY\YYYY-MM-DD\_ping.mp4" within ~60s.
- Disconnect Google Drive for Desktop (DriveFS) and verify warnings in the log while the script keeps running without crashing.

#>


