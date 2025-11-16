# C:\Scripts\obs_mover.ps1 — Move finished OBS .mp4 recordings to Google Drive\Recordings\YYYY\YYYY-MM-DD
# REQUIREMENT: In OBS, enable MKV recording + Auto-remux to MP4 (Settings → Advanced → Recording).
$ErrorActionPreference = 'Stop'

# --- CONFIG ---
$Staging = 'C:\Scripts\OBS_Staging'   # This must match OBS → Settings → Output → Recording Path

# --- Locate Google Drive "My Drive" (Drive for Desktop) ---
$DriveLetter = (Get-PSDrive -PSProvider FileSystem |
  Where-Object { Test-Path (Join-Path $_.Root 'My Drive') } |
  Select-Object -First 1).Root.TrimEnd('\')
if (-not $DriveLetter) { throw "Could not locate 'My Drive'. Is Google Drive for desktop running/mounted?" }

$GDriveRoot  = Join-Path $DriveLetter 'My Drive'
$ArchiveRoot = Join-Path $GDriveRoot 'Recordings'   # Final archive root inside My Drive

# --- Utils ---
function Ensure-Dir($p){ if(-not(Test-Path $p)){ New-Item -Type Directory -Path $p -Force | Out-Null } }
function Wait-FileUnlock($p,$t=600){
  $sw=[Diagnostics.Stopwatch]::StartNew()
  while($sw.Elapsed.TotalSeconds -lt $t){
    try{ $fs=[IO.File]::Open($p,'Open','ReadWrite','None'); $fs.Close(); return $true }
    catch { Start-Sleep -Milliseconds 500 }
  }
  return $false
}
function Log($m){ ("[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m) | Add-Content -Path 'C:\Scripts\obs_mover.log' }

# --- Guards ---
if (-not (Test-Path $Staging))   { throw "Staging not found: $Staging" }
Ensure-Dir $ArchiveRoot

# --- Watcher (mp4 only; ensures file is finalized) ---
$filter = '*.mp4'
$fsw = New-Object IO.FileSystemWatcher $Staging,$filter
$fsw.IncludeSubdirectories = $false
$fsw.NotifyFilter = [IO.NotifyFilters]'FileName, LastWrite, Size'
$fsw.EnableRaisingEvents = $true

Register-ObjectEvent $fsw Created -SourceIdentifier 'OBS_Mover_OnCreated' -Action {
  try {
    $src = $Event.SourceEventArgs.FullPath
    if(-not (Wait-FileUnlock $src)){ Log "Timeout waiting for $src"; return }
    $dt = (Get-Item $src).LastWriteTime
    $destDir = Join-Path $using:ArchiveRoot (Join-Path ($dt.ToString('yyyy')) ($dt.ToString('yyyy-MM-dd')))
    if(-not (Test-Path $destDir)){ New-Item -Type Directory -Path $destDir -Force | Out-Null }
    $dest = Join-Path $destDir (Split-Path $src -Leaf)
    Move-Item -LiteralPath $src -Destination $dest -Force
    Log "Archived -> $dest"
    Write-Host "Archived -> $dest"
  } catch {
    Log "ERROR: $($_.Exception.Message)"
    Write-Warning $_.Exception.Message
  }
} | Out-Null

Write-Host "OBS mover running. Watching $Staging → $ArchiveRoot (mp4 only). Press Ctrl+C to stop."

# --- Safety sweeper: picks up anything missed every 30s ---
while ($true) {
  Get-ChildItem -LiteralPath $Staging -Filter $filter -File | ForEach-Object {
    try {
      if (Wait-FileUnlock $_.FullName 5) {
        $dt = $_.LastWriteTime
        $destDir = Join-Path $ArchiveRoot (Join-Path ($dt.ToString('yyyy')) ($dt.ToString('yyyy-MM-dd')))
        Ensure-Dir $destDir
        $dest = Join-Path $destDir $_.Name
        Move-Item -LiteralPath $_.FullName -Destination $dest -Force
        Log "Sweeper archived -> $dest"
        Write-Host "Sweeper archived -> $dest"
      }
    } catch { Log "Sweeper ERROR: $($_.Exception.Message)" }
  }
  Start-Sleep 30
}

# OPTIONAL: To index archived files into Screenpipe automatically, add after Move-Item:
# Start-Process -FilePath "screenpipe" -ArgumentList @("add", $dest) -WindowStyle Hidden
