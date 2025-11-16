[CmdletBinding()]
param()

set-strictmode -version latest
$ErrorActionPreference = 'Stop'

$staging = "C:\Scripts\Ai Observation & Training\OBS_Staging"
try {
	if (-not (Test-Path -LiteralPath $staging)) {
		New-Item -ItemType Directory -Path $staging -Force | Out-Null
	}
	$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
	$path = Join-Path -Path $staging -ChildPath ("_test_drop_$ts.mp4")
	# Write a tiny marker
	[System.IO.File]::WriteAllBytes($path, [byte[]](65,66,67,68))
	Write-Host "Created: '$path'"
} catch {
	Write-Error "Failed to create test marker: $($_.Exception.Message)"
	exit 1
}


