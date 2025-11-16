# PowerShell script to save credentials and map drives
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "BRADY NETWORK SETUP WITH SAVED CREDENTIALS" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

# Server paths
$ServerG = "\\ES-FS02\customers2"
$ServerH = "\\ES-FS02\users\brady"

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator"))
{
    Write-Host "Please run this script as Administrator!" -ForegroundColor Red
    Write-Host "Right-click and select 'Run as Administrator'" -ForegroundColor Yellow
    pause
    exit
}

# Get credentials
Write-Host "Enter your Brady network credentials:" -ForegroundColor Yellow
Write-Host "(Use format: EAGLE\username or just username)" -ForegroundColor Gray
$cred = Get-Credential -Message "Brady Network Login"

if (-not $cred) {
    Write-Host "No credentials provided!" -ForegroundColor Red
    pause
    exit
}

# Remove any existing mappings
Write-Host "`nRemoving any existing mappings..." -ForegroundColor Gray
Remove-PSDrive -Name G -Force -ErrorAction SilentlyContinue
Remove-PSDrive -Name H -Force -ErrorAction SilentlyContinue
net use G: /delete /y 2>$null | Out-Null
net use H: /delete /y 2>$null | Out-Null

# Save credentials to Windows Credential Manager
Write-Host "Saving credentials securely..." -ForegroundColor Gray
cmdkey /add:ES-FS02 /user:$($cred.UserName) /pass:$($cred.GetNetworkCredential().Password)

# Map drives
Write-Host "`nMapping network drives..." -ForegroundColor Yellow

try {
    # Map G: drive
    Write-Host "Mapping G: drive (customers2)..." -ForegroundColor Gray
    New-PSDrive -Name G -PSProvider FileSystem -Root $ServerG -Credential $cred -Persist -Scope Global
    
    # Map H: drive
    Write-Host "Mapping H: drive (your brady folder)..." -ForegroundColor Gray
    New-PSDrive -Name H -PSProvider FileSystem -Root $ServerH -Credential $cred -Persist -Scope Global
    
    Write-Host "`n✓ Drives mapped successfully!" -ForegroundColor Green
    Write-Host "✓ Credentials saved for automatic reconnection!" -ForegroundColor Green
    
    # Test access
    Write-Host "`nTesting access..." -ForegroundColor Gray
    $testG = Get-ChildItem G:\ -ErrorAction SilentlyContinue | Select-Object -First 1
    $testH = Get-ChildItem H:\ -ErrorAction SilentlyContinue | Select-Object -First 1
    
    if ($testG -and $testH) {
        Write-Host "✓ Access confirmed!" -ForegroundColor Green
        
        # Create sync folders
        New-Item -ItemType Directory -Force -Path "C:\WorkSync\G_Drive" | Out-Null
        New-Item -ItemType Directory -Force -Path "C:\WorkSync\H_Drive" | Out-Null
        New-Item -ItemType Directory -Force -Path "C:\WorkSync\Logs" | Out-Null
        
        Write-Host "`n===========================================" -ForegroundColor Cyan
        Write-Host "SETUP COMPLETE!" -ForegroundColor Green
        Write-Host "===========================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Your credentials are saved. Drives will reconnect automatically."
        Write-Host ""
        Write-Host "Next step: Run MASTER_SYNC_AUTH.bat to sync your files"
        Write-Host ""
    } else {
        Write-Host "✗ Could not access one or both drives!" -ForegroundColor Red
    }
    
} catch {
    Write-Host "✗ Error mapping drives: $_" -ForegroundColor Red
}

pause