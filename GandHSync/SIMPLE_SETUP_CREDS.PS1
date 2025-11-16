# Simple credential setup script - no special characters
Write-Host "==========================================="
Write-Host "BRADY NETWORK SETUP"
Write-Host "==========================================="
Write-Host ""

# Get credentials
$cred = Get-Credential -Message "Enter eagle\brady and your password"

if (-not $cred) {
    Write-Host "No credentials provided!" -ForegroundColor Red
    pause
    exit
}

# Save to Windows Credential Manager
Write-Host "Saving credentials..."
cmdkey /add:ES-FS02 /user:$($cred.UserName) /pass:$($cred.GetNetworkCredential().Password)

# Remove existing drives
Remove-PSDrive -Name G -Force -ErrorAction SilentlyContinue
Remove-PSDrive -Name H -Force -ErrorAction SilentlyContinue

# Map drives
Write-Host "Mapping G: drive..."
net use G: \\ES-FS02\customers2 /persistent:yes

Write-Host "Mapping H: drive..."
net use H: \\ES-FS02\users\brady /persistent:yes

Write-Host ""
Write-Host "==========================================="
Write-Host "COMPLETE! Test with TEST_CONNECTION.bat"
Write-Host "==========================================="
pause